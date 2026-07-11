from pathlib import Path

from fastapi.testclient import TestClient

from minerva_travel.app import app
from minerva_travel.request_control import get_request_control, reset_request_control_cache

TEST_PHOTO = Path("assets/landmarks/paris/eiffel-tower.png").read_bytes()


def _enable_controls(monkeypatch, database_path: Path) -> None:
    reset_request_control_cache()
    monkeypatch.setenv("REQUEST_CONTROL_ENABLED", "true")
    monkeypatch.setenv("REQUEST_CONTROL_FAIL_CLOSED", "true")
    monkeypatch.setenv("REQUEST_CONTROL_DB_PATH", str(database_path))
    monkeypatch.setenv("CONCURRENCY_USER_LIMIT", "10")
    monkeypatch.setenv("CONCURRENCY_PROVIDER_OPENAI_LIMIT", "10")
    monkeypatch.setenv("CONCURRENCY_PROVIDER_GOOGLE_LIMIT", "10")


def test_expensive_endpoint_burst_returns_structured_429_before_provider(
    tmp_path,
    monkeypatch,
):
    _enable_controls(monkeypatch, tmp_path / "limits.sqlite3")
    monkeypatch.setenv("RATE_LIMIT_LANDMARKS_PARSE_USER", "1")
    monkeypatch.setenv("RATE_LIMIT_LANDMARKS_PARSE_IP", "10")
    provider_calls = 0

    def fake_parse(_message: str):
        nonlocal provider_calls
        provider_calls += 1
        return [
            {
                "name": "Torre Eiffel",
                "city": "Paris",
                "country": "Franca",
                "confidence": 1.0,
            }
        ]

    monkeypatch.setattr("minerva_travel.app.parse_landmarks_from_message", fake_parse)
    monkeypatch.setattr("minerva_travel.app.google_maps_api_key", lambda: None)
    client = TestClient(app)
    payload = {"message": "Em Paris vamos visitar a Torre Eiffel."}
    headers = {"Origin": "http://localhost:3000"}

    first = client.post("/api/landmarks/parse", json=payload, headers=headers)
    blocked = client.post("/api/landmarks/parse-preview", json=payload, headers=headers)

    assert first.status_code == 200
    assert blocked.status_code == 429
    assert blocked.headers["Retry-After"].isdigit()
    assert blocked.headers["access-control-expose-headers"] == (
        "Idempotency-Replayed, Retry-After, X-Request-ID"
    )
    assert blocked.json()["detail"] == {
        "code": "rate_limit_exceeded",
        "message": "Muitas solicitacoes. Aguarde antes de tentar novamente.",
        "scope": "landmarks_parse",
        "reason": "user_rate_limit",
        "retry_after_seconds": int(blocked.headers["Retry-After"]),
    }
    assert provider_calls == 1


def test_expensive_endpoint_fails_closed_when_control_database_is_unavailable(
    tmp_path,
    monkeypatch,
):
    blocker = tmp_path / "not-a-directory"
    blocker.write_text("blocked", encoding="utf-8")
    _enable_controls(monkeypatch, blocker / "limits.sqlite3")
    provider_called = False

    def fake_discovery(*_args, **_kwargs):
        nonlocal provider_called
        provider_called = True
        return {"selected_landmarks": [], "days": []}

    monkeypatch.setattr("minerva_travel.app.discover_dynamic_itinerary", fake_discovery)

    response = TestClient(app).post(
        "/api/itinerary/discover",
        json={"destination": "Paris", "days": 2},
    )

    assert response.status_code == 503
    assert response.headers["Retry-After"] == "5"
    assert response.json()["detail"]["code"] == "request_control_unavailable"
    assert provider_called is False


def test_api_generation_requires_idempotency_key_when_configured(
    tmp_path,
    monkeypatch,
):
    _enable_controls(monkeypatch, tmp_path / "limits.sqlite3")
    monkeypatch.setenv("IDEMPOTENCY_KEY_REQUIRED", "true")
    generation_called = False

    async def fake_generation(**_kwargs):
        nonlocal generation_called
        generation_called = True
        raise AssertionError("generation must not start without idempotency key")

    monkeypatch.setattr("minerva_travel.app.generate_pdf_from_form", fake_generation)

    response = TestClient(app).post(
        "/api/generate",
        data={
            "title": "Guia de Paris",
            "children_names": "Alice",
            "parents_names": "Ana",
            "year": "2026",
            "selected_landmarks": ["paris:eiffel-tower"],
        },
        files={"family_photo": ("family.png", TEST_PHOTO, "image/png")},
    )

    assert response.status_code == 428
    assert response.json()["detail"]["code"] == "idempotency_key_required"
    assert generation_called is False


def test_api_generation_replays_same_key_without_repeating_work_or_quota(
    tmp_path,
    monkeypatch,
):
    _enable_controls(monkeypatch, tmp_path / "limits.sqlite3")
    monkeypatch.setenv("IDEMPOTENCY_KEY_REQUIRED", "true")
    monkeypatch.setenv("RATE_LIMIT_GUIDE_GENERATE_USER", "100")
    monkeypatch.setenv("RATE_LIMIT_GUIDE_GENERATE_IP", "100")
    monkeypatch.setenv("QUOTA_GUIDE_GENERATE_USER", "100")
    monkeypatch.setenv("CONCURRENCY_GUIDE_GENERATE_USER_LIMIT", "10")
    generation_calls = 0

    async def fake_generation(**kwargs):
        nonlocal generation_calls
        generation_calls += 1
        assert await kwargs["family_photo"].read() == TEST_PHOTO
        return {
            "request_id": "guide-123",
            "download_url": "/download/guide-123.pdf",
            "filename": "guide-123.pdf",
            "cover_status": {"fallback_used": False},
        }

    monkeypatch.setattr("minerva_travel.app.generate_pdf_from_form", fake_generation)
    client = TestClient(app)
    headers = {"Idempotency-Key": "generation-key-123"}
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
        files={"family_photo": ("family.png", TEST_PHOTO, "image/png")},
        headers=headers,
    )
    replay = client.post(
        "/api/generate",
        data=data,
        files={"family_photo": ("family.png", TEST_PHOTO, "image/png")},
        headers=headers,
    )

    assert first.status_code == 200
    assert replay.status_code == 200
    assert first.json() == replay.json()
    assert first.headers["Idempotency-Replayed"] == "false"
    assert replay.headers["Idempotency-Replayed"] == "true"
    assert generation_calls == 1
    rate_events = get_request_control().audit_events(scope="guide_generate")
    quota_events = get_request_control().audit_events(scope="quota:guide_generate")
    assert [event["outcome"] for event in rate_events if event["kind"] == "rate"] == ["allowed"]
    assert [event["outcome"] for event in quota_events if event["kind"] == "rate"] == ["allowed"]


def test_api_generation_rejects_same_key_with_different_normalized_payload(
    tmp_path,
    monkeypatch,
):
    _enable_controls(monkeypatch, tmp_path / "limits.sqlite3")
    monkeypatch.setenv("IDEMPOTENCY_KEY_REQUIRED", "true")

    async def fake_generation(**_kwargs):
        return {
            "request_id": "guide-123",
            "download_url": "/download/guide-123.pdf",
            "filename": "guide-123.pdf",
            "cover_status": {"fallback_used": False},
        }

    monkeypatch.setattr("minerva_travel.app.generate_pdf_from_form", fake_generation)
    client = TestClient(app)
    headers = {"Idempotency-Key": "generation-key-123"}
    base_data = {
        "children_names": "Alice",
        "parents_names": "Ana",
        "year": "2026",
        "selected_landmarks": ["paris:eiffel-tower"],
    }
    first = client.post(
        "/api/generate",
        data={**base_data, "title": "Guia de Paris"},
        files={"family_photo": ("family.png", TEST_PHOTO, "image/png")},
        headers=headers,
    )
    conflict = client.post(
        "/api/generate",
        data={**base_data, "title": "Outro guia"},
        files={"family_photo": ("family.png", TEST_PHOTO, "image/png")},
        headers=headers,
    )

    assert first.status_code == 200
    assert conflict.status_code == 409
    assert conflict.json()["detail"]["code"] == "idempotency_key_conflict"
