import json
from io import BytesIO
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image

from minerva_travel.app import app
from minerva_travel.auth import AuthenticatedUser, get_current_user
from minerva_travel.page_generation import PageGenerationError

FAMILY_PHOTO = Path("assets/landmarks/paris/eiffel-tower.png").read_bytes()


def _png_bytes(color: str) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (1024, 1536), color).save(buffer, format="PNG")
    return buffer.getvalue()


class FakePageGenerator:
    def __init__(self) -> None:
        self.calls: list[str] = []
        self.fail_next = False

    def _write(self, kind: str, output_path: Path) -> Path:
        self.calls.append(kind)
        if self.fail_next:
            self.fail_next = False
            raise PageGenerationError("Falha simulada do provedor.")
        colors = {
            "cover": "#4f86b7",
            "summary": "#69b482",
            "landmark": "#c9a94d",
        }
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(_png_bytes(colors[kind]))
        return output_path

    def generate_cover_page(self, *, output_path, **_kwargs):
        return self._write("cover", output_path)

    def generate_summary_page(self, *, output_path, **_kwargs):
        return self._write("summary", output_path)

    def generate_landmark_page(self, *, output_path, **_kwargs):
        return self._write("landmark", output_path)


CUSTOM_LANDMARKS = json.dumps(
    [
        {"name": "Torre Eiffel", "city": "Paris", "country": "França"},
        {"name": "Coliseu", "city": "Roma", "country": "Itália"},
    ]
)


def _create_session(client: TestClient) -> dict:
    response = client.post(
        "/api/guide-builder",
        data={
            "title": "Família Moraes",
            "children_names": "Alice",
            "children_ages": ["7"],
            "parents_names": "Ana",
            "year": "2026",
            "custom_landmarks": CUSTOM_LANDMARKS,
            "itinerary_json": json.dumps(
                {"destinations": [{"place": "Paris", "timing": "Julho de 2026", "days": 3}]}
            ),
        },
        files={"family_photo": ("family.png", FAMILY_PHOTO, "image/png")},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _setup(monkeypatch, tmp_path) -> tuple[TestClient, FakePageGenerator]:
    generator = FakePageGenerator()
    monkeypatch.setattr("minerva_travel.storage.RUNTIME_DIR", tmp_path)
    monkeypatch.setattr("minerva_travel.app.get_guide_page_generator", lambda: generator)
    return TestClient(app), generator


def _generate(client: TestClient, session_id: str, page_id: str, key: str):
    return client.post(
        f"/api/guide-builder/{session_id}/pages/{page_id}/attempts",
        headers={"Idempotency-Key": key},
    )


def _approve(client: TestClient, session_id: str, page_id: str, attempt_id: str):
    return client.post(
        f"/api/guide-builder/{session_id}/pages/{page_id}/approve",
        json={"attempt_id": attempt_id},
    )


def test_page_builder_generates_approves_and_completes_without_pdf(tmp_path, monkeypatch):
    client, generator = _setup(monkeypatch, tmp_path)
    created = _create_session(client)
    session_id = created["session_id"]

    assert generator.calls == []
    assert created["active_page_id"] == "cover"
    assert [page["kind"] for page in created["pages"]] == [
        "cover",
        "trip_summary",
        "landmark",
        "landmark",
    ]
    assert created["pages"][0]["required_copy"] == ["Família Moraes", "Julho de 2026"]
    assert "Torre Eiffel" in created["pages"][1]["required_copy"]
    assert "Coliseu" in created["pages"][1]["required_copy"]

    assert _generate(client, session_id, "summary", "summary-early").status_code == 409
    assert generator.calls == []

    first = _generate(client, session_id, "cover", "cover-request-1")
    assert first.status_code == 200, first.text
    first_payload = first.json()
    cover_page = first_payload["pages"][0]
    first_attempt = cover_page["attempts"][0]
    assert cover_page["status"] == "awaiting_approval"
    assert first_attempt["asset_url"].startswith(f"/guide-builder/{session_id}/assets/")
    assert client.get(first_attempt["asset_url"]).status_code == 200

    replay = _generate(client, session_id, "cover", "cover-request-1")
    assert replay.status_code == 200
    assert replay.headers["Idempotency-Replayed"] == "true"
    assert generator.calls == ["cover"]

    second = _generate(client, session_id, "cover", "cover-request-2").json()
    assert len(second["pages"][0]["attempts"]) == 2
    assert second["pages"][0]["selected_attempt_id"] == "cover-2"

    selected = client.patch(
        f"/api/guide-builder/{session_id}/pages/cover/selection",
        json={"attempt_id": "cover-1"},
    )
    assert selected.status_code == 200
    assert selected.json()["pages"][0]["selected_attempt_id"] == "cover-1"
    assert _approve(client, session_id, "cover", "cover-1").status_code == 200

    for page_id, kind in (
        ("summary", "summary"),
        ("landmark-1", "landmark"),
        ("landmark-2", "landmark"),
    ):
        generated = _generate(client, session_id, page_id, f"{page_id}-request")
        assert generated.status_code == 200, generated.text
        page = next(item for item in generated.json()["pages"] if item["id"] == page_id)
        assert _approve(client, session_id, page_id, page["selected_attempt_id"]).status_code == 200
        assert generator.calls[-1] == kind

    completed = client.post(f"/api/guide-builder/{session_id}/complete")
    assert completed.status_code == 200, completed.text
    payload = completed.json()
    assert len(payload["pages"]) == 4
    assert all(page["asset_url"].startswith("/guide-builder/") for page in payload["pages"])
    assert "download_url" not in payload
    assert "preview_url" not in payload
    assert "filename" not in payload

    chosen_cover = next(page for page in payload["pages"] if page["page_id"] == "cover")
    assert chosen_cover["attempt_id"] == "cover-1"


def test_page_attempt_limit_is_checked_before_provider_call(tmp_path, monkeypatch):
    client, generator = _setup(monkeypatch, tmp_path)
    session_id = _create_session(client)["session_id"]

    for index in range(4):
        assert _generate(client, session_id, "cover", f"cover-{index}").status_code == 200
    blocked = _generate(client, session_id, "cover", "cover-5")
    assert blocked.status_code == 429
    assert generator.calls == ["cover"] * 4


def test_provider_failure_is_retryable_and_does_not_consume_attempt(tmp_path, monkeypatch):
    client, generator = _setup(monkeypatch, tmp_path)
    session_id = _create_session(client)["session_id"]
    generator.fail_next = True

    failed = _generate(client, session_id, "cover", "same-safe-key")
    assert failed.status_code == 502
    state = client.get(f"/api/guide-builder/{session_id}").json()
    assert state["pages"][0]["status"] == "error"
    assert state["pages"][0]["attempts"] == []
    assert state["pages"][0]["attempts_left"] == 4

    retried = _generate(client, session_id, "cover", "same-safe-key")
    assert retried.status_code == 200
    assert len(retried.json()["pages"][0]["attempts"]) == 1


def test_builder_session_and_assets_are_owner_scoped(tmp_path, monkeypatch):
    client, _generator = _setup(monkeypatch, tmp_path)

    async def owner_a():
        return AuthenticatedUser(id="owner-a", email="a@example.com")

    async def owner_b():
        return AuthenticatedUser(id="owner-b", email="b@example.com")

    app.dependency_overrides[get_current_user] = owner_a
    try:
        created = _create_session(client)
        session_id = created["session_id"]
        generated = _generate(client, session_id, "cover", "owner-a-cover").json()
        asset_url = generated["pages"][0]["attempts"][0]["asset_url"]
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    app.dependency_overrides[get_current_user] = owner_b
    try:
        assert client.get(f"/api/guide-builder/{session_id}").status_code == 404
        assert client.get(asset_url).status_code == 404
        assert _generate(client, session_id, "cover", "owner-b-cover").status_code == 404
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_account_deletion_removes_builder_session_photo_and_pages(tmp_path, monkeypatch):
    client, _generator = _setup(monkeypatch, tmp_path)
    created = _create_session(client)
    session_id = created["session_id"]
    generated = _generate(client, session_id, "cover", "delete-cover")
    assert generated.status_code == 200

    response = client.delete("/api/account/data")
    assert response.status_code == 200
    assert client.get(f"/api/guide-builder/{session_id}").status_code == 404
    assert not (tmp_path / "builder" / f"{session_id}.json").exists()
    assert not (tmp_path / "generated" / "builder" / session_id).exists()
