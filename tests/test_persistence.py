from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi.testclient import TestClient

from minerva_travel import storage
from minerva_travel.app import app
from minerva_travel.auth import AuthenticatedUser, get_current_user
from minerva_travel.persistence import (
    GuideRepository,
    cleanup_expired_drafts,
    cleanup_expired_guides,
    delete_all_guides_for_owner,
    delete_guide_and_assets,
)


def _save_guide(
    repository: GuideRepository,
    *,
    guide_id: str = "guide-123",
    user_id: str = "user-a",
    pdf_filename: str = "guide-123.pdf",
    assets: list[tuple[str, Path]] | None = None,
):
    return repository.save_succeeded_guide(
        guide_id=guide_id,
        user_id=user_id,
        title="Guia da família",
        pdf_filename=pdf_filename,
        cover_fallback_used=False,
        metadata={"destinations": [{"place": "Paris, França"}]},
        assets=assets or [],
    )


def test_repository_scopes_guide_and_assets_by_owner(tmp_path):
    repository = GuideRepository(tmp_path / "minerva.sqlite3")
    pdf = tmp_path / "pdfs" / "guide-123.pdf"
    pdf.parent.mkdir()
    pdf.write_bytes(b"pdf")

    _save_guide(repository, assets=[("generated_guide", pdf)])

    assert repository.get_for_owner("guide-123", "user-a") is not None
    assert repository.get_for_owner("guide-123", "user-b") is None
    assert repository.get_by_pdf_for_owner("guide-123.pdf", "user-b") is None
    assert repository.assets_for_owner("guide-123", "user-b") == []


def test_drafts_are_owner_scoped_and_use_optimistic_revisions(tmp_path):
    repository = GuideRepository(tmp_path / "minerva.sqlite3")
    created = repository.create_draft(
        user_id="user-a",
        title="Paris em família",
        payload={"family_name": "Silva", "step": 2},
    )

    assert created.revision == 1
    assert repository.get_draft_for_owner(created.id, "user-b") is None
    updated = repository.update_draft(
        draft_id=created.id,
        user_id="user-a",
        title="Paris revisado",
        payload={"family_name": "Silva", "step": 3},
        expected_revision=1,
    )

    assert updated is not None
    assert (updated.title, updated.revision, updated.payload["step"]) == (
        "Paris revisado",
        2,
        3,
    )
    assert (
        repository.update_draft(
            draft_id=created.id,
            user_id="user-a",
            title="Conflito",
            payload={},
            expected_revision=1,
        )
        is None
    )
    assert repository.discard_draft(created.id, "user-a")
    assert repository.latest_draft_for_owner("user-a") is None


def test_expired_drafts_are_hard_deleted_with_their_payload(tmp_path):
    repository = GuideRepository(tmp_path / "minerva.sqlite3")
    draft = repository.create_draft(
        user_id="user-a",
        title="Expira",
        payload={"family_name": "Silva"},
    )
    expired_at = datetime.now(UTC) - timedelta(seconds=1)
    with repository._connection() as connection:
        connection.execute(
            "UPDATE guide_drafts SET expires_at = ? WHERE id = ?",
            (expired_at.isoformat(), draft.id),
        )

    assert cleanup_expired_drafts(repository, now=datetime.now(UTC)) == 1
    assert repository.get_draft_for_owner(draft.id, "user-a") is None


def test_draft_api_restores_updates_and_discards_only_the_owner_draft(tmp_path, monkeypatch):
    runtime = tmp_path / "runtime"
    monkeypatch.setattr(storage, "RUNTIME_DIR", runtime)

    async def user_a():
        return AuthenticatedUser(id="user-a")

    client = TestClient(app)
    try:
        app.dependency_overrides[get_current_user] = user_a
        created = client.post(
            "/api/drafts",
            json={"title": "Paris", "payload": {"step": 1, "family_name": "Silva"}},
        )
        draft_id = created.json()["id"]
        current = client.get("/api/drafts/current")
        updated = client.put(
            f"/api/drafts/{draft_id}",
            json={"title": "Paris revisado", "payload": {"step": 2}, "revision": 1},
        )
        stale = client.put(
            f"/api/drafts/{draft_id}",
            json={"title": "Conflito", "payload": {}, "revision": 1},
        )
        deleted = client.delete(f"/api/drafts/{draft_id}")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert created.status_code == 201
    assert current.json()["draft"]["id"] == draft_id
    assert current.headers["cache-control"] == "private, no-store, max-age=0"
    assert (updated.status_code, updated.json()["revision"]) == (200, 2)
    assert stale.status_code == 409
    assert deleted.json() == {"deleted": True}


def test_delete_guide_removes_private_assets_but_never_external_files(tmp_path, monkeypatch):
    runtime = tmp_path / "runtime"
    monkeypatch.setattr(storage, "RUNTIME_DIR", runtime)
    repository = GuideRepository(runtime / "minerva.sqlite3")
    private_pdf = runtime / "pdfs" / "guide-123.pdf"
    private_pdf.parent.mkdir(parents=True)
    private_pdf.write_bytes(b"pdf")
    external = tmp_path / "do-not-delete.txt"
    external.write_text("preserve", encoding="utf-8")
    _save_guide(
        repository,
        assets=[("generated_guide", private_pdf), ("malicious", external)],
    )

    assert delete_guide_and_assets(repository, "guide-123", "user-b") is False
    assert private_pdf.exists()
    assert delete_guide_and_assets(repository, "guide-123", "user-a") is True
    assert not private_pdf.exists()
    assert external.exists()
    assert repository.get_for_owner("guide-123", "user-a") is None


def test_delete_guide_never_removes_runtime_asset_referenced_by_another_owner(
    tmp_path,
    monkeypatch,
):
    runtime = tmp_path / "runtime"
    monkeypatch.setattr(storage, "RUNTIME_DIR", runtime)
    repository = GuideRepository(runtime / "minerva.sqlite3")
    shared_pdf = runtime / "pdfs" / "shared.pdf"
    shared_pdf.parent.mkdir(parents=True)
    shared_pdf.write_bytes(b"must remain")

    _save_guide(
        repository,
        guide_id="guide-a",
        user_id="user-a",
        pdf_filename="guide-a.pdf",
        assets=[("generated_guide", shared_pdf)],
    )
    _save_guide(
        repository,
        guide_id="guide-b",
        user_id="user-b",
        pdf_filename="guide-b.pdf",
        assets=[("corrupt_shared_reference", shared_pdf)],
    )

    assert delete_guide_and_assets(repository, "guide-a", "user-a") is True
    assert shared_pdf.read_bytes() == b"must remain"


def test_download_requires_matching_owner_and_sets_private_headers(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "RUNTIME_DIR", tmp_path)
    pdf = storage.pdf_path("guide-123.pdf")
    pdf.write_bytes(b"%PDF-test")
    _save_guide(
        GuideRepository(tmp_path / "minerva.sqlite3"),
        assets=[("generated_guide", pdf)],
    )

    async def user_b():
        return AuthenticatedUser(id="user-b")

    async def user_a():
        return AuthenticatedUser(id="user-a")

    client = TestClient(app)
    try:
        app.dependency_overrides[get_current_user] = user_b
        assert client.get("/download/guide-123.pdf").status_code == 404

        app.dependency_overrides[get_current_user] = user_a
        response = client.get("/download/guide-123.pdf")
        assert response.status_code == 200
        assert response.content == b"%PDF-test"
        assert response.headers["cache-control"] == "private, no-store, max-age=0"
        assert response.headers["x-content-type-options"] == "nosniff"
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_expired_guide_download_returns_gone(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "RUNTIME_DIR", tmp_path)
    pdf = storage.pdf_path("guide-123.pdf")
    pdf.write_bytes(b"%PDF-test")
    repository = GuideRepository(tmp_path / "minerva.sqlite3")
    _save_guide(repository, assets=[("generated_guide", pdf)])
    with repository._connection() as connection:
        connection.execute(
            "UPDATE guides SET expires_at = ? WHERE id = ?",
            ((datetime.now(UTC) - timedelta(minutes=1)).isoformat(), "guide-123"),
        )

    async def user_a():
        return AuthenticatedUser(id="user-a")

    client = TestClient(app)
    try:
        app.dependency_overrides[get_current_user] = user_a
        response = client.get("/download/guide-123.pdf")
        assert response.status_code == 410
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_cleanup_removes_only_expired_guides_and_owned_assets(tmp_path, monkeypatch):
    runtime = tmp_path / "runtime"
    monkeypatch.setattr(storage, "RUNTIME_DIR", runtime)
    repository = GuideRepository(runtime / "minerva.sqlite3")
    expired_pdf = storage.pdf_path("expired.pdf")
    active_pdf = storage.pdf_path("active.pdf")
    expired_pdf.write_bytes(b"expired")
    active_pdf.write_bytes(b"active")
    _save_guide(
        repository,
        guide_id="expired",
        pdf_filename="expired.pdf",
        assets=[("generated_guide", expired_pdf)],
    )
    _save_guide(
        repository,
        guide_id="active",
        pdf_filename="active.pdf",
        assets=[("generated_guide", active_pdf)],
    )
    with repository._connection() as connection:
        connection.execute(
            "UPDATE guides SET expires_at = ? WHERE id = 'expired'",
            ((datetime.now(UTC) - timedelta(minutes=1)).isoformat(),),
        )

    assert cleanup_expired_guides(repository) == 1
    assert not expired_pdf.exists()
    assert active_pdf.exists()
    assert repository.get_for_owner("expired", "user-a") is None
    assert repository.get_for_owner("active", "user-a") is not None


def test_delete_all_guides_is_scoped_to_owner(tmp_path, monkeypatch):
    runtime = tmp_path / "runtime"
    monkeypatch.setattr(storage, "RUNTIME_DIR", runtime)
    repository = GuideRepository(runtime / "minerva.sqlite3")
    _save_guide(repository, guide_id="a-one", user_id="user-a", pdf_filename="a-one.pdf")
    _save_guide(repository, guide_id="a-two", user_id="user-a", pdf_filename="a-two.pdf")
    _save_guide(repository, guide_id="b-one", user_id="user-b", pdf_filename="b-one.pdf")

    assert delete_all_guides_for_owner(repository, "user-a") == 2
    assert repository.list_all_for_owner("user-a") == []
    assert [record.id for record in repository.list_all_for_owner("user-b")] == ["b-one"]


def test_job_claim_progress_result_cancellation_and_restart_recovery(tmp_path):
    repository = GuideRepository(tmp_path / "minerva.sqlite3")
    photo = tmp_path / "runtime" / "uploads" / "photo.jpg"
    photo.parent.mkdir(parents=True)
    photo.write_bytes(b"photo")
    created = repository.create_job(
        job_id="job-123",
        user_id="user-a",
        idempotency_key="idempotency-key-123",
        request_snapshot={"title": "Guia da família"},
        photo_path=photo,
    )

    assert created.status == "queued"
    assert repository.get_job_for_owner("job-123", "user-b") is None

    claimed = repository.claim_next_job(lease_seconds=1)
    assert claimed is not None
    assert (claimed.status, claimed.stage, claimed.progress, claimed.attempt_count) == (
        "running",
        "validating",
        5,
        1,
    )
    assert repository.update_job_progress("job-123", stage="rendering_pdf", progress=75)
    assert repository.finish_job(
        "job-123",
        result_payload={"download_url": "/download/guide.pdf", "filename": "guide.pdf"},
    )
    finished = repository.get_job_for_owner("job-123", "user-a")
    assert finished is not None
    assert finished.public_payload()["result"] == {
        "download_url": "/download/guide.pdf",
        "filename": "guide.pdf",
    }

    repository.create_job(
        job_id="job-cancel",
        user_id="user-a",
        idempotency_key="idempotency-key-cancel",
        request_snapshot={"title": "Cancelar"},
        photo_path=photo,
    )
    cancelled = repository.request_job_cancellation("job-cancel", "user-a")
    assert cancelled is not None
    assert (cancelled.status, cancelled.stage, cancelled.cancel_requested) == (
        "cancelled",
        "complete",
        True,
    )

    repository.create_job(
        job_id="job-recover",
        user_id="user-a",
        idempotency_key="idempotency-key-recover",
        request_snapshot={"title": "Recuperar"},
        photo_path=photo,
    )
    running = repository.claim_next_job(lease_seconds=1)
    assert running is not None and running.id == "job-recover"
    with repository._connection() as connection:
        connection.execute(
            "UPDATE guide_jobs SET lease_expires_at = ? WHERE id = 'job-recover'",
            ("2000-01-01T00:00:00+00:00",),
        )
    recovered = repository.claim_next_job(lease_seconds=60)
    assert recovered is not None
    assert (recovered.id, recovered.status, recovered.attempt_count) == (
        "job-recover",
        "running",
        2,
    )


def test_job_lease_recovery_stops_after_its_attempt_budget(tmp_path):
    repository = GuideRepository(tmp_path / "minerva.sqlite3")
    photo = tmp_path / "runtime" / "uploads" / "photo.jpg"
    photo.parent.mkdir(parents=True)
    photo.write_bytes(b"photo")
    repository.create_job(
        job_id="job-exhausted",
        user_id="user-a",
        idempotency_key="idempotency-key-exhausted",
        request_snapshot={"title": "Esgotado"},
        photo_path=photo,
        max_attempts=1,
    )
    claimed = repository.claim_next_job(lease_seconds=1)
    assert claimed is not None and claimed.id == "job-exhausted"
    with repository._connection() as connection:
        connection.execute(
            "UPDATE guide_jobs SET lease_expires_at = ? WHERE id = 'job-exhausted'",
            ("2000-01-01T00:00:00+00:00",),
        )

    assert repository.claim_next_job(lease_seconds=1) is None
    exhausted = repository.get_job_for_owner("job-exhausted", "user-a")
    assert exhausted is not None
    assert (exhausted.status, exhausted.error_code) == ("failed", "worker_lease_expired")


def test_job_api_is_owner_scoped_and_supports_queue_cancellation(tmp_path, monkeypatch):
    runtime = tmp_path / "runtime"
    monkeypatch.setattr(storage, "RUNTIME_DIR", runtime)
    repository = GuideRepository(runtime / "minerva.sqlite3")
    photo = runtime / "uploads" / "photo.jpg"
    photo.parent.mkdir(parents=True)
    photo.write_bytes(b"photo")
    repository.create_job(
        job_id="job-a",
        user_id="user-a",
        idempotency_key="job-a-key",
        request_snapshot={"title": "Guia A"},
        photo_path=photo,
    )
    repository.create_job(
        job_id="job-b",
        user_id="user-b",
        idempotency_key="job-b-key",
        request_snapshot={"title": "Guia B"},
        photo_path=photo,
    )

    async def user_a():
        return AuthenticatedUser(id="user-a")

    client = TestClient(app)
    try:
        app.dependency_overrides[get_current_user] = user_a
        listed = client.get("/api/jobs")
        details = client.get("/api/jobs/job-a")
        cross_owner = client.get("/api/jobs/job-b")
        cancelled = client.delete("/api/jobs/job-a")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert listed.status_code == 200
    assert [job["id"] for job in listed.json()["jobs"]] == ["job-a"]
    assert listed.headers["cache-control"] == "private, no-store, max-age=0"
    assert details.status_code == 200
    assert cross_owner.status_code == 404
    assert (cancelled.status_code, cancelled.json()["status"]) == (200, "cancelled")
