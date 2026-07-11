import json
import re
from datetime import datetime
from pathlib import Path

from fastapi.testclient import TestClient

from minerva_travel import storage
from minerva_travel.app import app
from minerva_travel.auth import AuthenticatedUser, get_current_user
from minerva_travel.persistence import GuideRepository


def _save_guide(
    repository: GuideRepository,
    *,
    guide_id: str,
    user_id: str,
    pdf_filename: str,
    metadata: dict[str, object] | None = None,
    assets: list[tuple[str, Path]] | None = None,
) -> None:
    repository.save_succeeded_guide(
        guide_id=guide_id,
        user_id=user_id,
        title=f"Guia {guide_id}",
        pdf_filename=pdf_filename,
        cover_fallback_used=False,
        metadata=metadata or {},
        assets=assets or [],
    )


def test_account_export_is_owner_scoped_allowlisted_and_not_cached(tmp_path, monkeypatch):
    runtime = tmp_path / "runtime"
    monkeypatch.setattr(storage, "RUNTIME_DIR", runtime)
    repository = GuideRepository(runtime / "minerva.sqlite3")
    internal_path = str(runtime / "uploads" / "family-photo.jpg")
    _save_guide(
        repository,
        guide_id="guide-a",
        user_id="user-a",
        pdf_filename="private-guide-a.pdf",
        metadata={
            "year": 2026,
            "destinations": [
                {
                    "id": "paris",
                    "place": "Paris, França",
                    "landmarks": ["Torre Eiffel", {"internal_path": internal_path}],
                    "local_path": internal_path,
                }
            ],
            "privacy_consent": {
                "version": "2026-07-09",
                "granted_at": "2026-07-09T10:00:00+00:00",
                "provider_token": "do-not-export",
            },
            "internal_path": internal_path,
            "provider_api_key": "top-secret",
        },
    )
    _save_guide(
        repository,
        guide_id="guide-b",
        user_id="user-b",
        pdf_filename="private-guide-b.pdf",
        metadata={"destinations": [{"place": "Berlim, Alemanha"}]},
    )
    repository.create_draft(
        user_id="user-a",
        title="Rascunho de Paris",
        payload={"family_name": "Silva", "current_step": 3},
    )
    repository.create_draft(
        user_id="user-b",
        title="Rascunho alheio",
        payload={"family_name": "Outro"},
    )

    async def user_a():
        return AuthenticatedUser(id="user-a", email="a@example.com")

    client = TestClient(app)
    try:
        app.dependency_overrides[get_current_user] = user_a
        response = client.get("/api/account/export")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    assert response.headers["cache-control"] == "private, no-store, max-age=0"
    assert response.headers["pragma"] == "no-cache"
    assert response.headers["content-disposition"] == (
        'attachment; filename="minerva-travel-data-export.json"'
    )
    assert response.headers["x-content-type-options"] == "nosniff"
    assert re.fullmatch(r"[a-f0-9]{32}", response.headers["x-request-id"])

    payload = response.json()
    assert payload["schema_version"] == 1
    assert datetime.fromisoformat(payload["exported_at"]).tzinfo is not None
    assert payload["account"] == {"id": "user-a", "email": "a@example.com"}
    assert payload["guides"] == [
        {
            "id": "guide-a",
            "title": "Guia guide-a",
            "status": "succeeded",
            "created_at": payload["guides"][0]["created_at"],
            "updated_at": payload["guides"][0]["updated_at"],
            "expires_at": payload["guides"][0]["expires_at"],
            "deleted_at": None,
            "cover_fallback_used": False,
            "destinations": [
                {
                    "id": "paris",
                    "place": "Paris, França",
                    "landmarks": ["Torre Eiffel"],
                }
            ],
            "privacy_consent": {
                "version": "2026-07-09",
                "granted_at": "2026-07-09T10:00:00+00:00",
            },
            "pdf_available": True,
            "year": 2026,
        }
    ]
    assert payload["drafts"] == [
        {
            "id": payload["drafts"][0]["id"],
            "title": "Rascunho de Paris",
            "payload": {"family_name": "Silva", "current_step": 3},
            "revision": 1,
            "status": "active",
            "created_at": payload["drafts"][0]["created_at"],
            "updated_at": payload["drafts"][0]["updated_at"],
            "expires_at": payload["drafts"][0]["expires_at"],
        }
    ]
    serialized = json.dumps(payload, ensure_ascii=False)
    for forbidden in (
        "guide-b",
        "private-guide-a.pdf",
        "private-guide-b.pdf",
        internal_path,
        "Rascunho alheio",
        "do-not-export",
        "top-secret",
        "provider_api_key",
        "local_path",
    ):
        assert forbidden not in serialized


def test_account_export_includes_retained_soft_deleted_guide(tmp_path, monkeypatch):
    runtime = tmp_path / "runtime"
    monkeypatch.setattr(storage, "RUNTIME_DIR", runtime)
    repository = GuideRepository(runtime / "minerva.sqlite3")
    _save_guide(
        repository,
        guide_id="retained-deleted-guide",
        user_id="user-a",
        pdf_filename="retained-deleted-guide.pdf",
        metadata={"year": 2025},
    )
    assert repository.mark_deleted("retained-deleted-guide", "user-a") is True

    async def user_a():
        return AuthenticatedUser(id="user-a")

    client = TestClient(app)
    try:
        app.dependency_overrides[get_current_user] = user_a
        response = client.get("/api/account/export")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 200
    guide = response.json()["guides"][0]
    assert guide["id"] == "retained-deleted-guide"
    assert guide["status"] == "cancelled"
    assert guide["deleted_at"] is not None
    assert guide["pdf_available"] is False


def test_account_delete_hard_deletes_only_owner_data_and_is_idempotent(tmp_path, monkeypatch):
    runtime = tmp_path / "runtime"
    monkeypatch.setattr(storage, "RUNTIME_DIR", runtime)
    repository = GuideRepository(runtime / "minerva.sqlite3")

    owner_pdf = runtime / "pdfs" / "owner.pdf"
    owner_upload = runtime / "uploads" / "owner.jpg"
    other_pdf = runtime / "pdfs" / "other.pdf"
    for path, content in (
        (owner_pdf, b"owner-pdf"),
        (owner_upload, b"owner-photo"),
        (other_pdf, b"other-pdf"),
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    external_file = tmp_path / "outside-runtime.txt"
    external_file.write_text("must remain", encoding="utf-8")

    _save_guide(
        repository,
        guide_id="owner-active",
        user_id="user-a",
        pdf_filename="owner-active.pdf",
        assets=[("generated_guide", owner_pdf), ("invalid_external", external_file)],
    )
    _save_guide(
        repository,
        guide_id="owner-soft-deleted",
        user_id="user-a",
        pdf_filename="owner-soft-deleted.pdf",
        assets=[("family_upload", owner_upload)],
    )
    assert repository.mark_deleted("owner-soft-deleted", "user-a") is True
    _save_guide(
        repository,
        guide_id="other-owner",
        user_id="user-b",
        pdf_filename="other-owner.pdf",
        assets=[("generated_guide", other_pdf)],
    )

    async def user_a():
        return AuthenticatedUser(id="user-a", email="a@example.com")

    client = TestClient(app)
    try:
        app.dependency_overrides[get_current_user] = user_a
        first = client.delete("/api/account/data")
        second = client.delete("/api/account/data")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert first.status_code == 200
    assert first.json() == {
        "deleted": True,
        "guides_deleted": 2,
        "private_files_deleted": 2,
    }
    assert first.headers["cache-control"] == "private, no-store, max-age=0"
    assert first.headers["pragma"] == "no-cache"
    assert first.headers["x-content-type-options"] == "nosniff"
    assert second.status_code == 200
    assert second.json() == {
        "deleted": True,
        "guides_deleted": 0,
        "private_files_deleted": 0,
    }

    assert not owner_pdf.exists()
    assert not owner_upload.exists()
    assert other_pdf.read_bytes() == b"other-pdf"
    assert external_file.read_text(encoding="utf-8") == "must remain"
    with repository._connection() as connection:
        owner_guides = connection.execute(
            "SELECT COUNT(*) AS count FROM guides WHERE user_id = 'user-a'"
        ).fetchone()["count"]
        owner_assets = connection.execute(
            "SELECT COUNT(*) AS count FROM guide_assets WHERE user_id = 'user-a'"
        ).fetchone()["count"]
        other_guides = connection.execute(
            "SELECT COUNT(*) AS count FROM guides WHERE user_id = 'user-b'"
        ).fetchone()["count"]
        other_assets = connection.execute(
            "SELECT COUNT(*) AS count FROM guide_assets WHERE user_id = 'user-b'"
        ).fetchone()["count"]
    assert (owner_guides, owner_assets) == (0, 0)
    assert (other_guides, other_assets) == (1, 1)


def test_account_delete_preserves_runtime_asset_referenced_by_another_owner(tmp_path, monkeypatch):
    runtime = tmp_path / "runtime"
    monkeypatch.setattr(storage, "RUNTIME_DIR", runtime)
    repository = GuideRepository(runtime / "minerva.sqlite3")
    shared_pdf = runtime / "pdfs" / "shared.pdf"
    shared_pdf.parent.mkdir(parents=True)
    shared_pdf.write_bytes(b"other-owner-reference")

    _save_guide(
        repository,
        guide_id="owner-guide",
        user_id="user-a",
        pdf_filename="owner.pdf",
        assets=[("generated_guide", shared_pdf)],
    )
    _save_guide(
        repository,
        guide_id="other-guide",
        user_id="user-b",
        pdf_filename="other.pdf",
        assets=[("corrupt_shared_reference", shared_pdf)],
    )

    async def user_a():
        return AuthenticatedUser(id="user-a")

    client = TestClient(app)
    try:
        app.dependency_overrides[get_current_user] = user_a
        response = client.delete("/api/account/data")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["private_files_deleted"] == 0
    assert shared_pdf.read_bytes() == b"other-owner-reference"


def test_account_delete_removes_queued_job_photo_and_snapshot(tmp_path, monkeypatch):
    runtime = tmp_path / "runtime"
    monkeypatch.setattr(storage, "RUNTIME_DIR", runtime)
    repository = GuideRepository(runtime / "minerva.sqlite3")
    queued_photo = runtime / "uploads" / "queued.jpg"
    queued_photo.parent.mkdir(parents=True)
    queued_photo.write_bytes(b"private photo")
    repository.create_job(
        job_id="queued-job",
        user_id="user-a",
        idempotency_key="queued-job-key",
        request_snapshot={"title": "Nome privado", "children_names": "Alice"},
        photo_path=queued_photo,
    )

    async def user_a():
        return AuthenticatedUser(id="user-a")

    client = TestClient(app)
    try:
        app.dependency_overrides[get_current_user] = user_a
        response = client.delete("/api/account/data")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "deleted": True,
        "guides_deleted": 0,
        "private_files_deleted": 1,
    }
    assert not queued_photo.exists()
    assert repository.get_job_for_owner("queued-job", "user-a") is None
