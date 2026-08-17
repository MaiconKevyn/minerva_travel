"""O que a família recebe depois de aprovar tudo: o PDF certo, uma vez só."""

import asyncio
import smtplib
from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from pypdf import PdfReader

from minerva_travel import app as app_module
from minerva_travel import storage
from minerva_travel.app import app
from minerva_travel.auth import AuthenticatedUser, get_current_user
from minerva_travel.jobs import GuideJobWorker
from minerva_travel.page_generation import PageGenerationRetryableError
from minerva_travel.persistence import GuideRepository

PAGE_COLORS = [
    "#4f86b7",
    "#69b482",
    "#c58f4a",
    "#6f9fb8",
    "#c9a94d",
    "#8f79b8",
    "#d69b79",
    "#d9a45f",
    "#7ab8a0",
    "#b87a9f",
]


class ColorPerCallGenerator:
    """Uma cor distinta por página gerada, na ordem em que foi gerada."""

    def __init__(self) -> None:
        self.colors: list[str] = []

    def _write(self, output_path: Path) -> Path:
        color = PAGE_COLORS[len(self.colors) % len(PAGE_COLORS)]
        self.colors.append(color)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (1024, 1536), color).save(output_path, format="PNG")
        return output_path

    def __getattr__(self, name):
        if not name.startswith("generate_"):
            raise AttributeError(name)

        def generate(*, output_path, **_kwargs):
            return self._write(Path(output_path))

        return generate


class RecordingSmtp:
    sent: list = []

    def __init__(self, host, port, timeout=None):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False

    def starttls(self, context=None):
        pass

    def login(self, username, password):
        pass

    def send_message(self, message):
        RecordingSmtp.sent.append(message)


@pytest.fixture
def delivery(monkeypatch, tmp_path):
    monkeypatch.setattr(storage, "RUNTIME_DIR", tmp_path / "runtime")
    monkeypatch.setenv("SMTP_HOST", "smtp.example.test")
    monkeypatch.setenv("SMTP_FROM", "guias@minerva.test")
    monkeypatch.setenv("SMTP_USERNAME", "")
    monkeypatch.setenv("FRONTEND_BASE_URL", "http://127.0.0.1:3000")
    monkeypatch.setattr(smtplib, "SMTP", RecordingSmtp)
    RecordingSmtp.sent = []

    generator = ColorPerCallGenerator()
    monkeypatch.setattr(app_module, "get_guide_page_generator", lambda: generator)

    async def owner():
        return AuthenticatedUser(id="owner-delivery", email="familia@example.test")

    app.dependency_overrides[get_current_user] = owner
    try:
        yield TestClient(app), generator
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        RecordingSmtp.sent = []


def _create_without_photo(client: TestClient) -> dict:
    response = client.post(
        "/api/guide-builder",
        data={
            "title": "Família Lima",
            "children_names": "Aurora",
            "children_ages": "8",
            "parents_names": "Marina",
            "year": "2026",
            "selected_landmarks": ["paris:eiffel-tower", "rome:colosseum"],
            "cover_brief": "Um balão de ar quente sobrevoando os campos",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _approve_every_page(client: TestClient, session: dict, order: list[str]) -> None:
    session_id = session["session_id"]
    for page_id in order:
        made = client.post(
            f"/api/guide-builder/{session_id}/pages/{page_id}/attempts",
            headers={"Idempotency-Key": f"gen-{page_id}"},
            json={"include_family": False},
        )
        assert made.status_code == 200, made.text
        page = next(item for item in made.json()["pages"] if item["id"] == page_id)
        approved = client.post(
            f"/api/guide-builder/{session_id}/pages/{page_id}/approve",
            json={"attempt_id": page["selected_attempt_id"]},
        )
        assert approved.status_code == 200, approved.text


def _pdf_page_colors(client: TestClient, download_url: str) -> list[str]:
    response = client.get(download_url)
    assert response.status_code == 200
    colors = []
    for page in PdfReader(BytesIO(response.content)).pages:
        images = list(page.images)
        assert images, "uma página do PDF saiu sem imagem"
        with Image.open(BytesIO(images[0].data)) as image:
            red, green, blue = image.convert("RGB").getpixel((10, 10))
            colors.append(f"#{red:02x}{green:02x}{blue:02x}")
    return colors


def test_a_guide_without_a_photo_reaches_the_pdf_and_the_email(delivery):
    """Sem foto, a volta para casa não gerava e o guia nunca ficava pronto.

    A exigência era por tipo de página; agora só vale quando a sessão tinha
    uma foto e o arquivo sumiu do disco.
    """

    client, _generator = delivery
    session = _create_without_photo(client)
    ordered_ids = [page["id"] for page in session["pages"]]

    _approve_every_page(client, session, ordered_ids)

    completed = client.post(f"/api/guide-builder/{session['session_id']}/complete")
    assert completed.status_code == 200, completed.text
    assert completed.json()["emailed_to"] == "familia@example.test"


def test_the_pdf_follows_the_guide_order_not_the_order_pages_were_generated(delivery):
    client, generator = delivery
    session = _create_without_photo(client)
    ordered_ids = [page["id"] for page in session["pages"]]

    # A família aprova de trás para frente; o livro tem de sair na ordem certa.
    generation_order = ordered_ids[::-1]
    _approve_every_page(client, session, generation_order)
    color_by_page = dict(zip(generation_order, generator.colors, strict=True))

    exported = client.post(f"/api/guide-builder/{session['session_id']}/pdf")
    assert exported.status_code == 200, exported.text
    payload = exported.json()
    assert payload["page_count"] == len(ordered_ids)

    assert _pdf_page_colors(client, payload["download_url"]) == [
        color_by_page[page_id] for page_id in ordered_ids
    ]


def test_finishing_sends_one_email_and_downloading_never_sends_another(delivery):
    client, _generator = delivery
    session = _create_without_photo(client)
    session_id = session["session_id"]
    _approve_every_page(client, session, [page["id"] for page in session["pages"]])

    # Concluir já avisa: quem aprova tudo e fecha a aba não fica sem o guia.
    assert client.post(f"/api/guide-builder/{session_id}/complete").status_code == 200
    assert len(RecordingSmtp.sent) == 1

    for _ in range(3):
        exported = client.post(f"/api/guide-builder/{session_id}/pdf")
        assert exported.status_code == 200
        assert exported.json()["emailed_to"] == "familia@example.test"

    # Reenviar a cada download encheria a caixa de entrada da família.
    assert len(RecordingSmtp.sent) == 1
    body = RecordingSmtp.sent[0].get_content()
    assert session_id in body
    assert f"com {len(session['pages'])} páginas" in body


def test_an_incomplete_guide_is_refused_and_nothing_is_emailed(delivery):
    client, _generator = delivery
    session = _create_without_photo(client)
    session_id = session["session_id"]

    # Só a capa aprovada: o guia não está pronto para sair.
    _approve_every_page(client, session, [session["pages"][0]["id"]])

    completed = client.post(f"/api/guide-builder/{session_id}/complete")
    assert completed.status_code == 409
    assert completed.json()["detail"]["code"] == "builder_incomplete"
    assert RecordingSmtp.sent == []


def test_approved_cover_queues_the_rest_and_worker_delivers_in_background(delivery):
    client, _generator = delivery
    session = _create_without_photo(client)
    session_id = session["session_id"]
    _approve_every_page(client, session, ["cover"])

    queued = client.post(
        f"/api/guide-builder/{session_id}/generation-jobs",
        headers={"Idempotency-Key": "finish-guide-1"},
    )

    assert queued.status_code == 202, queued.text
    assert queued.json()["status"] == "queued"
    job_id = queued.json()["job_id"]
    restored = client.get(f"/api/guide-builder/{session_id}").json()
    assert restored["generation_job_id"] == job_id
    assert restored["generation_requested_at"]
    frozen = client.post(
        f"/api/guide-builder/{session_id}/pages/summary/attempts",
        headers={"Idempotency-Key": "late-manual-page"},
    )
    assert frozen.status_code == 409
    assert frozen.json()["detail"]["code"] == "builder_generation_already_requested"

    repository = GuideRepository(storage.RUNTIME_DIR / "minerva.sqlite3")
    result = asyncio.run(GuideJobWorker(repository).run_once())

    assert result == result.__class__(job_id=job_id, outcome="succeeded")
    finished = client.get(f"/api/jobs/{job_id}")
    assert finished.status_code == 200
    assert finished.json()["status"] == "succeeded"
    assert finished.json()["result"]["page_count"] == len(session["pages"])
    assert finished.json()["result"]["emailed_to"] == "familia@example.test"
    assert len(RecordingSmtp.sent) == 1

    final_session = client.get(f"/api/guide-builder/{session_id}").json()
    assert final_session["is_complete"] is True
    assert all(page["status"] == "approved" for page in final_session["pages"])
    assert client.get(finished.json()["result"]["download_url"]).status_code == 200


def test_background_builder_resumes_after_a_temporary_provider_limit(delivery):
    client, generator = delivery
    session = _create_without_photo(client)
    session_id = session["session_id"]
    _approve_every_page(client, session, ["cover"])

    original_write = generator._write
    background_calls = 0

    def flaky_write(output_path: Path) -> Path:
        nonlocal background_calls
        background_calls += 1
        if background_calls == 2:
            raise PageGenerationRetryableError(
                "A OpenAI está temporariamente ocupada.",
                retry_after_seconds=5,
            )
        return original_write(output_path)

    generator._write = flaky_write
    queued = client.post(
        f"/api/guide-builder/{session_id}/generation-jobs",
        headers={"Idempotency-Key": "finish-guide-with-retry"},
    ).json()
    repository = GuideRepository(storage.RUNTIME_DIR / "minerva.sqlite3")

    first = asyncio.run(GuideJobWorker(repository).run_once())
    after_first = client.get(f"/api/guide-builder/{session_id}").json()
    summary = next(page for page in after_first["pages"] if page["id"] == "summary")

    assert first.outcome == "retrying"
    assert summary["status"] == "approved"
    assert len(summary["attempts"]) == 1
    with repository._connection() as connection:
        connection.execute(
            "UPDATE guide_jobs SET next_attempt_at = ? WHERE id = ?",
            ("2000-01-01T00:00:00+00:00", queued["job_id"]),
        )

    second = asyncio.run(GuideJobWorker(repository).run_once())
    final_session = client.get(f"/api/guide-builder/{session_id}").json()

    assert second.outcome == "succeeded"
    assert final_session["is_complete"] is True
    final_summary = next(page for page in final_session["pages"] if page["id"] == "summary")
    assert len(final_summary["attempts"]) == 1
    assert len(RecordingSmtp.sent) == 1


def test_failed_builder_job_can_be_requeued_with_a_new_idempotency_key(delivery):
    client, _generator = delivery
    session = _create_without_photo(client)
    session_id = session["session_id"]
    _approve_every_page(client, session, ["cover"])

    first = client.post(
        f"/api/guide-builder/{session_id}/generation-jobs",
        headers={"Idempotency-Key": "first-submission"},
    )
    assert first.status_code == 202
    first_job_id = first.json()["job_id"]

    repository = GuideRepository(storage.RUNTIME_DIR / "minerva.sqlite3")
    claimed = repository.claim_next_job()
    assert claimed is not None and claimed.id == first_job_id
    assert repository.fail_job(
        first_job_id,
        error_code="generation_failed",
        error_message_safe="Não foi possível gerar o guia.",
    )

    replay = client.post(
        f"/api/guide-builder/{session_id}/generation-jobs",
        headers={"Idempotency-Key": "first-submission"},
    )
    assert replay.status_code == 202
    assert replay.json()["job_id"] == first_job_id

    retry = client.post(
        f"/api/guide-builder/{session_id}/generation-jobs",
        headers={"Idempotency-Key": "deliberate-retry"},
    )
    assert retry.status_code == 202
    assert retry.json()["status"] == "queued"
    assert retry.json()["job_id"] != first_job_id

    restored = client.get(f"/api/guide-builder/{session_id}").json()
    assert restored["generation_job_id"] == retry.json()["job_id"]
