"""A foto da família deixou de ser obrigatória para existir um guia."""

from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from minerva_travel import storage
from minerva_travel.app import (
    FAMILY_PHOTO_ACTIVITY_TYPES,
    ActivitySelectionInputError,
    app,
    normalize_landmark_activity_selections,
)
from minerva_travel.auth import AuthenticatedUser, get_current_user
from minerva_travel.catalog import load_catalog
from minerva_travel.models import LandmarkActivitySelection
from minerva_travel.page_generation import cover_page_prompt, homecoming_page_prompt


def _photo_bytes() -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (96, 96), "#4f86b7").save(buffer, format="PNG")
    return buffer.getvalue()


def _form(**extra) -> dict:
    data = {
        "title": "Família Lima",
        "children_names": "Aurora",
        "children_ages": "8",
        "parents_names": "Marina",
        "year": "2026",
        "selected_landmarks": ["paris:eiffel-tower"],
    }
    data.update(extra)
    return data


def _client(monkeypatch, tmp_path) -> TestClient:
    monkeypatch.setattr(storage, "RUNTIME_DIR", tmp_path / "runtime")

    async def owner():
        return AuthenticatedUser(id="owner-a", email="familia@example.com")

    app.dependency_overrides[get_current_user] = owner
    return TestClient(app)


def test_a_guide_can_be_built_without_any_photo(monkeypatch, tmp_path):
    try:
        response = _client(monkeypatch, tmp_path).post(
            "/api/guide-builder",
            data=_form(cover_brief="Um balão de ar quente sobrevoando os campos ao amanhecer."),
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 201, response.text
    payload = response.json()
    # O guia inteiro continua sendo planejado; só a foto ficou de fora.
    assert [page["kind"] for page in payload["pages"]][:2] == ["cover", "trip_summary"]


def test_the_photo_still_works_and_still_asks_for_consent(monkeypatch, tmp_path):
    # O conftest desliga a exigência para o resto da suíte; aqui ela é o ponto.
    monkeypatch.setenv("PHOTO_PROCESSING_CONSENT_REQUIRED", "true")
    try:
        client = _client(monkeypatch, tmp_path)
        without_consent = client.post(
            "/api/guide-builder",
            data=_form(),
            files={"family_photo": ("family.png", _photo_bytes(), "image/png")},
        )
        with_consent = client.post(
            "/api/guide-builder",
            data=_form(
                photo_processing_consent="true",
                privacy_consent_version="2026-07-09",
                privacy_consent_at="2026-07-26T10:00:00+00:00",
            ),
            files={"family_photo": ("family.png", _photo_bytes(), "image/png")},
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    # Mandar a foto sem consentir continua sendo recusado.
    assert without_consent.status_code == 422
    assert with_consent.status_code == 201, with_consent.text


def test_activities_that_draw_the_family_are_refused_without_a_photo():
    catalog = load_catalog()
    landmarks = [
        item
        for destination in catalog.destinations
        for item in destination.landmarks
        if item.id == "eiffel-tower"
    ]
    assert landmarks

    from minerva_travel.app import _selected_builder_landmarks

    contexts = _selected_builder_landmarks(
        catalog.destinations, ["paris:eiffel-tower"], [8]
    )
    selections = [
        LandmarkActivitySelection(
            landmark_selection_id="paris:eiffel-tower",
            activity_type="investigator",
            order=1,
        )
    ]

    # Com foto passa; sem foto, recusa explicando qual atividade é o problema.
    assert normalize_landmark_activity_selections(
        selections,
        selected_landmarks=contexts,
        all_landmark_ids={"paris:eiffel-tower"},
        has_family_photo=True,
    )
    with pytest.raises(ActivitySelectionInputError) as raised:
        normalize_landmark_activity_selections(
            selections,
            selected_landmarks=contexts,
            all_landmark_ids={"paris:eiffel-tower"},
            has_family_photo=False,
        )
    assert raised.value.code == "activity_requires_family_photo"
    assert "Investigador" in raised.value.message


def test_every_family_photo_activity_is_actually_blocked():
    # A lista existe para o plano e para a tela; se uma delas escapar, o guia
    # sai com uma família inventada no lugar da real.
    assert FAMILY_PHOTO_ACTIVITY_TYPES == frozenset({"family_coloring", "investigator"})


def test_the_cover_comes_from_the_written_brief_when_there_is_no_photo():
    prompt = cover_page_prompt(
        family_title="Família Lima",
        trip_date="Julho de 2026",
        landmark_names=["Torre Eiffel"],
        cover_brief="Um balão de ar quente sobre os campos",
        has_family_photo=False,
    )

    assert "Um balão de ar quente sobre os campos" in prompt
    assert "original family photo" not in prompt
    assert "Do not invent a specific real family" in prompt
    # O contrato de texto impresso continua igual.
    assert '"Família Lima"' in prompt
    assert '"Julho de 2026"' in prompt


def test_without_a_brief_the_cover_falls_back_to_the_places_and_no_people():
    prompt = cover_page_prompt(
        family_title="Família Lima",
        trip_date="Julho de 2026",
        landmark_names=["Torre Eiffel"],
        has_family_photo=False,
    )

    # Sem direção nenhuma o modelo inventa uma família; a saída é dizer "sem gente".
    assert "with no people in it" in prompt
    assert "Torre Eiffel" in prompt


def test_the_brief_can_style_the_scene_without_changing_who_appears():
    prompt = cover_page_prompt(
        family_title="Família Lima",
        trip_date="Julho de 2026",
        landmark_names=["Torre Eiffel"],
        cover_brief="À noite, com fogos de artifício",
        expected_visible_family_member_count=4,
        has_family_photo=True,
    )

    assert "À noite, com fogos de artifício" in prompt
    assert "it never changes who appears" in prompt
    assert "Preserve exactly 4 recognizable family members" in prompt


def test_the_homecoming_closes_the_trip_without_inventing_a_family():
    without_photo = homecoming_page_prompt(
        family_title="Família Lima",
        trip_date="Julho de 2026",
        landmark_names=["Torre Eiffel"],
        age_complexity="early_reader",
        has_family_photo=False,
    )
    with_photo = homecoming_page_prompt(
        family_title="Família Lima",
        trip_date="Julho de 2026",
        landmark_names=["Torre Eiffel"],
        age_complexity="early_reader",
        expected_visible_family_member_count=4,
    )

    assert "PEOPLE-FREE CONTRACT" in without_photo
    assert "canonical family" not in without_photo
    assert "packed suitcase" in without_photo
    # Com foto a página continua sendo o reencontro da família.
    assert "complete canonical family" in with_photo
