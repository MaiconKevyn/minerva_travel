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
        self.requests: list[dict] = []
        self.fail_next = False

    def _write(self, kind: str, output_path: Path, request: dict) -> Path:
        self.calls.append(kind)
        self.requests.append({"kind": kind, **request})
        if self.fail_next:
            self.fail_next = False
            raise PageGenerationError("Falha simulada do provedor.")
        colors = {
            "cover": "#4f86b7",
            "summary": "#69b482",
            "destination": "#6f9fb8",
            "landmark": "#c9a94d",
            "activity": "#8f79b8",
            "memory": "#d69b79",
        }
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(_png_bytes(colors[kind]))
        return output_path

    def generate_cover_page(self, *, output_path, **kwargs):
        return self._write("cover", output_path, kwargs)

    def generate_summary_page(self, *, output_path, **kwargs):
        return self._write("summary", output_path, kwargs)

    def generate_destination_intro_page(self, *, output_path, **kwargs):
        return self._write("destination", output_path, kwargs)

    def generate_landmark_page(self, *, output_path, **kwargs):
        return self._write("landmark", output_path, kwargs)

    def generate_coloring_page(self, *, output_path, **kwargs):
        return self._write("activity", output_path, kwargs)

    def generate_detail_hunt_page(self, *, output_path, **kwargs):
        return self._write("activity", output_path, kwargs)

    def generate_word_search_page(self, *, output_path, **kwargs):
        return self._write("activity", output_path, kwargs)

    def generate_drawing_page(self, *, output_path, **kwargs):
        return self._write("activity", output_path, kwargs)

    def generate_best_memory_page(self, *, output_path, **kwargs):
        return self._write("memory", output_path, kwargs)


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
            "expected_visible_family_member_count": "2",
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


def _generate(
    client: TestClient,
    session_id: str,
    page_id: str,
    key: str,
    revision_instruction: str | None = None,
    include_family: bool | None = None,
):
    payload = {}
    if revision_instruction is not None:
        payload["revision_instruction"] = revision_instruction
    if include_family is not None:
        payload["include_family"] = include_family
    return client.post(
        f"/api/guide-builder/{session_id}/pages/{page_id}/attempts",
        headers={"Idempotency-Key": key},
        json=payload or None,
    )


def _approve(client: TestClient, session_id: str, page_id: str, attempt_id: str):
    return client.post(
        f"/api/guide-builder/{session_id}/pages/{page_id}/approve",
        json={"attempt_id": attempt_id},
    )


def test_page_builder_generates_approves_completes_and_exports_pdf(tmp_path, monkeypatch):
    client, generator = _setup(monkeypatch, tmp_path)
    created = _create_session(client)
    session_id = created["session_id"]

    incomplete_pdf = client.post(f"/api/guide-builder/{session_id}/pdf")
    assert incomplete_pdf.status_code == 409
    assert incomplete_pdf.json()["detail"]["code"] == "builder_incomplete"

    assert generator.calls == []
    assert created["active_page_id"] == "cover"
    assert [page["kind"] for page in created["pages"]] == [
        "cover",
        "trip_summary",
        "destination_intro",
        "landmark",
        "destination_intro",
        "landmark",
        "best_memory",
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
        ("destination-1", "destination"),
        ("landmark-1", "landmark"),
        ("destination-2", "destination"),
        ("landmark-2", "landmark"),
        ("best-memory", "memory"),
    ):
        generated = _generate(client, session_id, page_id, f"{page_id}-request")
        assert generated.status_code == 200, generated.text
        page = next(item for item in generated.json()["pages"] if item["id"] == page_id)
        assert _approve(client, session_id, page_id, page["selected_attempt_id"]).status_code == 200
        assert generator.calls[-1] == kind
        request = generator.requests[-1]
        assert request["reference_page"] is None
        if page_id == "summary" or page_id.startswith("landmark-"):
            assert request["expected_visible_family_member_count"] == 2
        if page_id == "summary":
            assert request["family_photo"].is_file()
            assert request["family_cover"].name == "cover-1.png"
            assert page["attempts"][-1]["include_family"] is True
        elif page_id.startswith("landmark-"):
            assert request["family_photo"] is None
            assert request["family_cover"] is None
            assert request["include_family"] is False
            assert page["attempts"][-1]["include_family"] is False
        elif page_id.startswith("destination-"):
            assert "family_photo" not in request
            assert "family_cover" not in request
            assert page["attempts"][-1]["include_family"] is False
        else:
            assert page["attempts"][-1]["include_family"] is False
            assert "family_photo" not in request

    completed = client.post(f"/api/guide-builder/{session_id}/complete")
    assert completed.status_code == 200, completed.text
    payload = completed.json()
    assert len(payload["pages"]) == 7
    assert all(page["asset_url"].startswith("/guide-builder/") for page in payload["pages"])
    assert "download_url" not in payload
    assert "preview_url" not in payload
    assert "filename" not in payload

    chosen_cover = next(page for page in payload["pages"] if page["page_id"] == "cover")
    assert chosen_cover["attempt_id"] == "cover-1"

    exported = client.post(f"/api/guide-builder/{session_id}/pdf")
    assert exported.status_code == 200, exported.text
    pdf_payload = exported.json()
    assert pdf_payload == {
        "session_id": session_id,
        "download_url": f"/guide-builder/{session_id}/pdf",
        "filename": "familia-moraes-minerva-travel.pdf",
        "page_count": 7,
    }
    pdf_path = tmp_path / "generated" / "builder" / session_id / "approved-guide.pdf"
    first_bytes = pdf_path.read_bytes()
    assert first_bytes.startswith(b"%PDF-")

    replayed = client.post(f"/api/guide-builder/{session_id}/pdf")
    assert replayed.status_code == 200
    assert pdf_path.read_bytes() == first_bytes

    download = client.get(pdf_payload["download_url"])
    assert download.status_code == 200
    assert download.headers["content-type"] == "application/pdf"
    assert "familia-moraes-minerva-travel.pdf" in download.headers["content-disposition"]
    assert download.content == first_bytes

    (tmp_path / "generated" / "builder" / session_id / "landmark-2-1.png").unlink()
    missing_page = client.post(f"/api/guide-builder/{session_id}/pdf")
    assert missing_page.status_code == 409
    assert missing_page.json()["detail"]["code"] == "builder_approved_asset_missing"


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


def test_regeneration_uses_selected_attempt_and_persists_bounded_feedback(tmp_path, monkeypatch):
    client, generator = _setup(monkeypatch, tmp_path)
    session_id = _create_session(client)["session_id"]

    first = _generate(client, session_id, "cover", "cover-first")
    assert first.status_code == 200
    assert generator.requests[-1]["reference_page"] is None
    assert generator.requests[-1]["revision_instruction"] == ""

    feedback = "  Mude   para estilo de colagem 3D\ne use tons azuis.  "
    revised = _generate(client, session_id, "cover", "cover-revised", feedback)
    assert revised.status_code == 200, revised.text
    request = generator.requests[-1]
    assert request["reference_page"].name == "cover-1.png"
    assert request["revision_instruction"] == "Mude para estilo de colagem 3D e use tons azuis."
    attempts = revised.json()["pages"][0]["attempts"]
    assert attempts[-1]["revision_instruction"] == (
        "Mude para estilo de colagem 3D e use tons azuis."
    )

    selected = client.patch(
        f"/api/guide-builder/{session_id}/pages/cover/selection",
        json={"attempt_id": "cover-1"},
    )
    assert selected.status_code == 200
    third = _generate(client, session_id, "cover", "cover-selected", "Troque o fundo.")
    assert third.status_code == 200
    assert generator.requests[-1]["reference_page"].name == "cover-1.png"

    too_long = _generate(client, session_id, "cover", "cover-too-long", "x" * 601)
    assert too_long.status_code == 422
    assert generator.calls == ["cover", "cover", "cover"]


def test_summary_regeneration_keeps_canonical_family_references(tmp_path, monkeypatch):
    client, generator = _setup(monkeypatch, tmp_path)
    session_id = _create_session(client)["session_id"]
    cover = _generate(client, session_id, "cover", "cover-first").json()
    cover_attempt = cover["pages"][0]["selected_attempt_id"]
    assert _approve(client, session_id, "cover", cover_attempt).status_code == 200

    first = _generate(client, session_id, "summary", "summary-first")
    assert first.status_code == 200, first.text
    first_request = generator.requests[-1]
    assert first_request["family_cover"].name == "cover-1.png"
    assert first_request["reference_page"] is None

    revised = _generate(
        client,
        session_id,
        "summary",
        "summary-revised",
        "Use um estilo de recortes de papel.",
    )
    assert revised.status_code == 200, revised.text
    revised_request = generator.requests[-1]
    assert revised_request["family_photo"].is_file()
    assert revised_request["family_cover"].name == "cover-1.png"
    assert revised_request["reference_page"].name == "summary-1.png"
    assert revised_request["expected_visible_family_member_count"] == 2


def test_landmark_can_opt_in_to_family_and_idempotent_replay_keeps_choice(tmp_path, monkeypatch):
    client, generator = _setup(monkeypatch, tmp_path)
    session_id = _create_session(client)["session_id"]
    cover = _generate(client, session_id, "cover", "cover-first").json()
    cover_attempt = cover["pages"][0]["selected_attempt_id"]
    assert _approve(client, session_id, "cover", cover_attempt).status_code == 200
    summary = _generate(client, session_id, "summary", "summary-first").json()
    summary_attempt = next(page for page in summary["pages"] if page["id"] == "summary")[
        "selected_attempt_id"
    ]
    assert _approve(client, session_id, "summary", summary_attempt).status_code == 200
    destination = _generate(client, session_id, "destination-1", "destination-first").json()
    destination_attempt = next(
        page for page in destination["pages"] if page["id"] == "destination-1"
    )["selected_attempt_id"]
    assert _approve(client, session_id, "destination-1", destination_attempt).status_code == 200

    generated = _generate(
        client,
        session_id,
        "landmark-1",
        "landmark-family",
        include_family=True,
    )
    assert generated.status_code == 200, generated.text
    request = generator.requests[-1]
    assert request["include_family"] is True
    assert request["family_photo"].is_file()
    assert request["family_cover"].name == "cover-1.png"
    landmark_page = next(page for page in generated.json()["pages"] if page["id"] == "landmark-1")
    assert landmark_page["attempts"][-1]["include_family"] is True

    replay = _generate(
        client,
        session_id,
        "landmark-1",
        "landmark-family",
        include_family=False,
    )
    assert replay.status_code == 200
    assert replay.headers["Idempotency-Replayed"] == "true"
    assert generator.calls.count("landmark") == 1
    replayed_page = next(page for page in replay.json()["pages"] if page["id"] == "landmark-1")
    assert replayed_page["attempts"][-1]["include_family"] is True


def test_landmark_without_family_does_not_require_cover_but_opt_in_does(tmp_path, monkeypatch):
    client, generator = _setup(monkeypatch, tmp_path)
    session_id = _create_session(client)["session_id"]
    cover = _generate(client, session_id, "cover", "cover-first").json()
    cover_attempt = cover["pages"][0]["selected_attempt_id"]
    assert _approve(client, session_id, "cover", cover_attempt).status_code == 200
    summary = _generate(client, session_id, "summary", "summary-first").json()
    summary_attempt = next(page for page in summary["pages"] if page["id"] == "summary")[
        "selected_attempt_id"
    ]
    assert _approve(client, session_id, "summary", summary_attempt).status_code == 200
    (tmp_path / "generated" / "builder" / session_id / "cover-1.png").unlink()

    destination = _generate(
        client,
        session_id,
        "destination-1",
        "destination-without-family",
        include_family=True,
    )
    assert destination.status_code == 200, destination.text
    destination_page = next(
        page for page in destination.json()["pages"] if page["id"] == "destination-1"
    )
    assert destination_page["attempts"][-1]["include_family"] is False
    assert "family_photo" not in generator.requests[-1]
    assert (
        _approve(
            client,
            session_id,
            "destination-1",
            destination_page["selected_attempt_id"],
        ).status_code
        == 200
    )

    generated = _generate(
        client,
        session_id,
        "landmark-1",
        "landmark-without-family",
        include_family=False,
    )
    assert generated.status_code == 200, generated.text
    assert generator.requests[-1]["family_photo"] is None
    assert generator.requests[-1]["family_cover"] is None

    failed = _generate(
        client,
        session_id,
        "landmark-1",
        "landmark-with-family",
        include_family=True,
    )
    assert failed.status_code == 502
    assert failed.json()["detail"]["message"] == (
        "A capa aprovada da família não está mais disponível."
    )
    assert generator.calls.count("landmark") == 1


def test_summary_fails_without_the_approved_cover_asset(tmp_path, monkeypatch):
    client, generator = _setup(monkeypatch, tmp_path)
    session_id = _create_session(client)["session_id"]
    generated = _generate(client, session_id, "cover", "cover-first").json()
    cover_attempt = generated["pages"][0]["selected_attempt_id"]
    assert _approve(client, session_id, "cover", cover_attempt).status_code == 200
    (tmp_path / "generated" / "builder" / session_id / "cover-1.png").unlink()

    summary = _generate(client, session_id, "summary", "summary-missing-cover")
    assert summary.status_code == 502
    assert summary.json()["detail"]["message"] == (
        "A capa aprovada da família não está mais disponível."
    )
    assert generator.calls == ["cover"]
    state = client.get(f"/api/guide-builder/{session_id}").json()
    summary_page = next(page for page in state["pages"] if page["id"] == "summary")
    assert summary_page["status"] == "error"
    assert summary_page["attempts"] == []


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
        assert client.post(f"/api/guide-builder/{session_id}/pdf").status_code == 404
        assert client.get(f"/guide-builder/{session_id}/pdf").status_code == 404
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_account_deletion_removes_builder_session_photo_and_pages(tmp_path, monkeypatch):
    client, _generator = _setup(monkeypatch, tmp_path)
    created = _create_session(client)
    session_id = created["session_id"]
    for page_id in (
        "cover",
        "summary",
        "destination-1",
        "landmark-1",
        "destination-2",
        "landmark-2",
        "best-memory",
    ):
        generated = _generate(client, session_id, page_id, f"delete-{page_id}")
        assert generated.status_code == 200
        page = next(item for item in generated.json()["pages"] if item["id"] == page_id)
        assert _approve(client, session_id, page_id, page["selected_attempt_id"]).status_code == 200
    assert client.post(f"/api/guide-builder/{session_id}/pdf").status_code == 200
    pdf_path = tmp_path / "generated" / "builder" / session_id / "approved-guide.pdf"
    assert pdf_path.is_file()

    response = client.delete("/api/account/data")
    assert response.status_code == 200
    assert client.get(f"/api/guide-builder/{session_id}").status_code == 404
    assert not (tmp_path / "builder" / f"{session_id}.json").exists()
    assert not (tmp_path / "generated" / "builder" / session_id).exists()
    assert not pdf_path.exists()
