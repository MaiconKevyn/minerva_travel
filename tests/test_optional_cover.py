"""A foto da família deixou de ser obrigatória para existir um guia."""

import json
from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image

from minerva_travel import storage
from minerva_travel.app import (
    FAMILY_PHOTO_ACTIVITY_TYPES,
    app,
)
from minerva_travel.auth import AuthenticatedUser, get_current_user
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


def test_activities_that_use_the_photo_are_still_planned_without_it(monkeypatch, tmp_path):
    """Elas não somem do guia: são planejadas sem a família como inspiração.

    Bloqueá-las tirava da criança páginas que funcionam sem foto nenhuma — o
    investigador vive das missões, que vêm de nome e idade.
    """

    selections = [
        {
            "landmark_selection_id": "paris:eiffel-tower",
            "activity_type": activity_type,
            "order": index,
        }
        for index, activity_type in enumerate(sorted(FAMILY_PHOTO_ACTIVITY_TYPES), start=1)
    ]

    try:
        response = _client(monkeypatch, tmp_path).post(
            "/api/guide-builder",
            data=_form(activity_selections_json=json.dumps(selections)),
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 201, response.text
    planned = [page["metadata"].get("activity_type") for page in response.json()["pages"]]
    for activity_type in FAMILY_PHOTO_ACTIVITY_TYPES:
        assert activity_type in planned


def test_the_two_photo_activities_swap_the_family_for_a_generic_scene():
    from minerva_travel.page_generation import (
        family_coloring_artwork_prompt,
        investigator_artwork_prompt,
    )

    common = {
        "landmark_name": "Coliseu",
        "city": "Roma",
        "country": "Itália",
        "age_complexity": "early_reader",
        "expected_visible_family_member_count": None,
        "has_family_cover": False,
        "has_landmark_reference": False,
        "has_landmark_page_reference": False,
        "has_revision_reference": False,
    }
    coloring = family_coloring_artwork_prompt(**common, has_family_photo=False)
    investigator = investigator_artwork_prompt(**common, child_count=2, has_family_photo=False)

    # Colorir vira uma cena de férias qualquer, que a criança pinta e decide
    # quem é; nenhum dos dois pode pedir semelhança com pessoa real.
    assert "generic" in coloring
    assert "no portrait likeness of any real person" in coloring
    assert "original family photo" not in coloring
    # O investigador some com as pessoas: as missões impressas já as nomeiam.
    assert "PEOPLE-FREE CONTRACT" in investigator
    assert "magnifying glass" in investigator
    assert "original family photo" not in investigator


def test_the_photo_still_drives_these_two_when_it_exists():
    from minerva_travel.page_generation import (
        family_coloring_artwork_prompt,
        investigator_artwork_prompt,
    )

    common = {
        "landmark_name": "Coliseu",
        "city": "Roma",
        "country": "Itália",
        "age_complexity": "early_reader",
        "expected_visible_family_member_count": 4,
        "has_family_cover": True,
        "has_landmark_reference": False,
        "has_landmark_page_reference": False,
        "has_revision_reference": False,
    }
    coloring = family_coloring_artwork_prompt(**common)
    investigator = investigator_artwork_prompt(**common, child_count=2)

    assert "original family photo" in coloring
    assert "Depict exactly 4 family members" in coloring
    assert "original family photo" in investigator
    assert "Show exactly 4 recognizable family members" in investigator


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
    # O texto saiu do prompt: quem imprime o nome e a data e o compositor, na
    # fonte do caderno. Deixar o modelo escrever fazia a capa falar numa
    # familia tipografica diferente das paginas de atividade.
    assert "TEXT-FREE CONTRACT" in prompt
    assert '"Família Lima"' not in prompt
    assert '"Julho de 2026"' not in prompt


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
