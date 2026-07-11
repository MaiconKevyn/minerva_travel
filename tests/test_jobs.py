import asyncio
from pathlib import Path

from fastapi.testclient import TestClient

from minerva_travel import storage
from minerva_travel.app import app
from minerva_travel.jobs import GuideJobWorker
from minerva_travel.persistence import GuideRepository
from minerva_travel.request_control import reset_request_control_cache


def _job(
    repository: GuideRepository,
    photo: Path,
    *,
    job_id: str = "job-123",
    max_attempts: int = 3,
) -> None:
    repository.create_job(
        job_id=job_id,
        user_id="user-a",
        idempotency_key=f"key-{job_id}",
        request_snapshot={
            "title": "Guia da família",
            "children_names": "Alice",
            "children_ages": [7],
            "parents_names": "Ana",
            "year": 2026,
            "selected_landmarks": ["paris:eiffel-tower"],
            "expected_visible_family_member_count": 2,
            "photo_processing_consent": True,
            "privacy_consent_version": "2026-07-09",
            "privacy_consent_at": "2026-07-09T10:00:00+00:00",
        },
        photo_path=photo,
        max_attempts=max_attempts,
    )


def test_worker_claims_persists_and_finishes_a_job(tmp_path, monkeypatch):
    repository = GuideRepository(tmp_path / "minerva.sqlite3")
    photo = tmp_path / "runtime" / "uploads" / "photo.jpg"
    photo.parent.mkdir(parents=True)
    photo.write_bytes(b"photo")
    _job(repository, photo)
    calls = []

    async def fake_generate(**kwargs):
        calls.append(kwargs)
        return {
            "request_id": "job-123",
            "download_url": "/download/guide.pdf",
            "filename": "guide.pdf",
            "cover_status": {"fallback_used": False},
        }

    monkeypatch.setattr("minerva_travel.app.generate_pdf_from_saved_photo", fake_generate)
    result = asyncio.run(GuideJobWorker(repository).run_once())

    assert result.outcome == "succeeded"
    assert calls[0]["guide_id"] == "job-123"
    record = repository.get_job_for_owner("job-123", "user-a")
    assert record is not None
    assert record.public_payload()["result"]["download_url"] == "/download/guide.pdf"


def test_worker_returns_safe_failure_and_deletes_unpersisted_photo(tmp_path, monkeypatch):
    from minerva_travel import storage

    runtime = tmp_path / "runtime"
    monkeypatch.setattr(storage, "RUNTIME_DIR", runtime)
    repository = GuideRepository(runtime / "minerva.sqlite3")
    photo = runtime / "uploads" / "photo.jpg"
    photo.parent.mkdir(parents=True)
    photo.write_bytes(b"photo")
    _job(repository, photo, max_attempts=1)

    async def failing_generate(**_kwargs):
        raise RuntimeError("provider secret must never reach the client")

    monkeypatch.setattr("minerva_travel.app.generate_pdf_from_saved_photo", failing_generate)
    result = asyncio.run(GuideJobWorker(repository).run_once())

    assert result.outcome == "failed"
    record = repository.get_job_for_owner("job-123", "user-a")
    assert record is not None
    assert record.public_payload()["error"] == {
        "code": "generation_failed",
        "message": "Não foi possível gerar o guia. Tente novamente.",
    }
    assert not photo.exists()


def test_worker_retries_transient_failures_with_a_bounded_backoff(tmp_path, monkeypatch):
    runtime = tmp_path / "runtime"
    monkeypatch.setattr(storage, "RUNTIME_DIR", runtime)
    repository = GuideRepository(runtime / "minerva.sqlite3")
    photo = runtime / "uploads" / "photo.jpg"
    photo.parent.mkdir(parents=True)
    photo.write_bytes(b"photo")
    _job(repository, photo, max_attempts=2)

    async def failing_generate(**_kwargs):
        raise RuntimeError("temporary provider outage")

    monkeypatch.setattr("minerva_travel.app.generate_pdf_from_saved_photo", failing_generate)
    first = asyncio.run(GuideJobWorker(repository).run_once())
    queued = repository.get_job_for_owner("job-123", "user-a")

    assert first.outcome == "retrying"
    assert queued is not None
    assert (queued.status, queued.attempt_count) == ("queued", 1)
    assert queued.next_attempt_at is not None
    assert photo.exists()

    with repository._connection() as connection:
        connection.execute(
            "UPDATE guide_jobs SET next_attempt_at = ? WHERE id = 'job-123'",
            ("2000-01-01T00:00:00+00:00",),
        )
    second = asyncio.run(GuideJobWorker(repository).run_once())

    assert second.outcome == "failed"
    assert not photo.exists()


def test_api_queues_idempotent_job_and_worker_exposes_owner_status(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "RUNTIME_DIR", tmp_path / "runtime")
    monkeypatch.setenv("ASYNC_GUIDE_JOBS_ENABLED", "true")
    monkeypatch.setenv("REQUEST_CONTROL_DB_PATH", str(tmp_path / "request-control.sqlite3"))
    reset_request_control_cache()
    client = TestClient(app)
    headers = {"Idempotency-Key": "async-job-key-123"}
    data = {
        "title": "Guia de Paris",
        "children_names": "Alice",
        "parents_names": "Ana",
        "year": "2026",
        "selected_landmarks": ["paris:eiffel-tower"],
    }

    first = client.post(
        "/api/generate",
        data=data,
        files={
            "family_photo": (
                "family.png",
                Path("assets/landmarks/paris/eiffel-tower.png").read_bytes(),
                "image/png",
            )
        },
        headers=headers,
    )
    replay = client.post(
        "/api/generate",
        data=data,
        files={
            "family_photo": (
                "family.png",
                Path("assets/landmarks/paris/eiffel-tower.png").read_bytes(),
                "image/png",
            )
        },
        headers=headers,
    )

    assert first.status_code == 202
    assert replay.status_code == 202
    assert first.json() == replay.json()
    assert replay.headers["Idempotency-Replayed"] == "true"
    job_id = first.json()["job_id"]
    repository = GuideRepository(tmp_path / "runtime" / "minerva.sqlite3")
    queued = repository.get_job_for_owner(job_id, "development-user")
    assert queued is not None
    assert queued.photo_path.is_file()
    assert queued.request_snapshot["title"] == "Guia de Paris"

    async def fake_generate(**kwargs):
        assert kwargs["guide_id"] == job_id
        return {
            "request_id": job_id,
            "download_url": "/download/guide.pdf",
            "filename": "guide.pdf",
            "cover_status": {"fallback_used": False},
        }

    monkeypatch.setattr("minerva_travel.app.generate_pdf_from_saved_photo", fake_generate)
    worker_result = asyncio.run(GuideJobWorker(repository).run_once())
    status = client.get(f"/api/jobs/{job_id}")

    assert worker_result.outcome == "succeeded"
    assert status.status_code == 200
    assert status.json()["result"]["download_url"] == "/download/guide.pdf"
