import json
from datetime import UTC, datetime, timedelta
from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from minerva_travel.app import (
    DEFAULT_BUILDER_PAGE_GENERATION_QUOTA,
    MAX_PROGRESSIVE_BUILDER_PAGES,
    ActivitySelectionInputError,
    _activity_selection_snapshot,
    _builder_page_plan,
    _selected_builder_landmarks,
    app,
    normalize_landmark_activity_selections,
    parse_landmark_activity_selections,
)
from minerva_travel.builder import BuilderSession, load_builder_session
from minerva_travel.catalog import load_catalog
from minerva_travel.custom_landmarks import CustomLandmarkInput, build_custom_destinations
from minerva_travel.models import LandmarkActivitySelection


def _family_photo() -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (96, 96), "#4f86b7").save(buffer, format="PNG")
    return buffer.getvalue()


def _builder_data(*, activity_selections: object | None = None) -> dict:
    data: dict = {
        "title": "Família Lima",
        "children_names": "Bia",
        "children_ages": "7",
        "parents_names": "Ana",
        "year": "2026",
        "selected_landmarks": ["paris:eiffel-tower", "paris:louvre"],
    }
    if activity_selections is not None:
        data["activity_selections_json"] = (
            activity_selections
            if isinstance(activity_selections, str)
            else json.dumps(activity_selections)
        )
    return data


def _post_builder(client: TestClient, data: dict):
    return client.post(
        "/api/guide-builder",
        data=data,
        files={"family_photo": ("family.png", _family_photo(), "image/png")},
    )


class RecordingPageGenerator:
    def __init__(self) -> None:
        self.requests: list[dict] = []

    def _write(self, kind: str, output_path: Path, kwargs: dict):
        self.requests.append({"kind": kind, **kwargs})
        output_path.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (1024, 1536), "#7a91b8").save(output_path, format="PNG")
        return output_path

    def generate_cover_page(self, *, output_path, **kwargs):
        return self._write("cover", output_path, kwargs)

    def generate_summary_page(self, *, output_path, **kwargs):
        return self._write("summary", output_path, kwargs)

    def generate_destination_intro_page(self, *, output_path, **kwargs):
        return self._write("destination_intro", output_path, kwargs)

    def generate_landmark_page(self, *, output_path, **kwargs):
        return self._write("landmark", output_path, kwargs)

    def generate_coloring_page(self, *, output_path, **kwargs):
        return self._write("coloring", output_path, kwargs)

    def generate_family_coloring_page(self, *, output_path, **kwargs):
        return self._write("family_coloring", output_path, kwargs)

    def generate_detail_hunt_page(self, *, output_path, **kwargs):
        return self._write("detail_hunt", output_path, kwargs)

    def generate_word_search_page(self, *, output_path, **kwargs):
        return self._write("word_search", output_path, kwargs)

    def generate_drawing_page(self, *, output_path, **kwargs):
        return self._write("drawing", output_path, kwargs)

    def generate_best_memory_page(self, *, output_path, **kwargs):
        return self._write("best_memory", output_path, kwargs)

    def generate_homecoming_page(self, *, output_path, **kwargs):
        return self._write("homecoming", output_path, kwargs)


def _generate_and_approve(client: TestClient, session_id: str, page_id: str):
    generated = client.post(
        f"/api/guide-builder/{session_id}/pages/{page_id}/attempts",
        headers={"Idempotency-Key": f"generate-{page_id}"},
        json={"include_family": True},
    )
    assert generated.status_code == 200, generated.text
    page = next(item for item in generated.json()["pages"] if item["id"] == page_id)
    approved = client.post(
        f"/api/guide-builder/{session_id}/pages/{page_id}/approve",
        json={"attempt_id": page["selected_attempt_id"]},
    )
    assert approved.status_code == 200, approved.text
    return page


def test_activity_selection_parser_is_strict_and_backward_compatible():
    assert parse_landmark_activity_selections(None) == []
    parsed = parse_landmark_activity_selections(
        json.dumps(
            [
                {
                    "landmark_selection_id": "paris:eiffel-tower",
                    "activity_type": "coloring",
                    "order": 1,
                }
            ]
        )
    )
    assert parsed == [
        LandmarkActivitySelection(
            landmark_selection_id="paris:eiffel-tower",
            activity_type="coloring",
            order=1,
        )
    ]

    invalid_payloads = [
        "{",
        json.dumps({"activity_type": "coloring"}),
        json.dumps(
            [
                {
                    "landmark_selection_id": "paris:eiffel-tower",
                    "activity_type": "maze",
                    "order": 1,
                }
            ]
        ),
        json.dumps(
            [
                {
                    "landmark_selection_id": "paris:eiffel-tower",
                    "activity_type": "coloring",
                    "order": "1",
                }
            ]
        ),
        json.dumps(
            [
                {
                    "landmark_selection_id": "paris:eiffel-tower",
                    "activity_type": "coloring",
                    "order": 1,
                    "prompt": "não confiar neste texto",
                }
            ]
        ),
    ]
    for payload in invalid_payloads:
        with pytest.raises(ActivitySelectionInputError):
            parse_landmark_activity_selections(payload)


def test_default_generation_quota_covers_the_largest_first_attempt_page_plan():
    assert MAX_PROGRESSIVE_BUILDER_PAGES == 52
    assert DEFAULT_BUILDER_PAGE_GENERATION_QUOTA >= MAX_PROGRESSIVE_BUILDER_PAGES


def test_activity_snapshot_is_canonical_for_idempotency_hashing():
    first = LandmarkActivitySelection(
        landmark_selection_id="paris:eiffel-tower",
        activity_type="word_search",
        order=2,
    )
    second = LandmarkActivitySelection(
        landmark_selection_id="paris:eiffel-tower",
        activity_type="coloring",
        order=1,
    )
    assert _activity_selection_snapshot([first, second]) == _activity_selection_snapshot(
        [second, first]
    )


@pytest.mark.parametrize(
    ("selections", "expected_code"),
    [
        (
            [
                {
                    "landmark_selection_id": "unknown:place",
                    "activity_type": "coloring",
                    "order": 1,
                }
            ],
            "activity_landmark_unknown",
        ),
        (
            [
                {
                    "landmark_selection_id": "paris:louvre",
                    "activity_type": "coloring",
                    "order": 1,
                }
            ],
            "activity_landmark_not_selected",
        ),
        (
            [
                {
                    "landmark_selection_id": "paris:eiffel-tower",
                    "activity_type": "coloring",
                    "order": 1,
                },
                {
                    "landmark_selection_id": "paris:eiffel-tower",
                    "activity_type": "coloring",
                    "order": 2,
                },
            ],
            "activity_selection_duplicate",
        ),
        (
            [
                {
                    "landmark_selection_id": "paris:eiffel-tower",
                    "activity_type": activity_type,
                    "order": order,
                }
                for activity_type, order in (
                    ("coloring", 1),
                    ("drawing", 2),
                    ("word_search", 1),
                )
            ],
            "activity_selection_landmark_limit",
        ),
    ],
)
def test_activity_selection_rejects_unknown_unselected_duplicates_and_per_point_limit(
    selections,
    expected_code,
):
    catalog = load_catalog()
    selected = _selected_builder_landmarks(
        catalog.destinations,
        ["paris:eiffel-tower"],
        [7],
    )
    with pytest.raises(ActivitySelectionInputError) as raised:
        normalize_landmark_activity_selections(
            [LandmarkActivitySelection.model_validate(item) for item in selections],
            selected_landmarks=selected,
            all_landmark_ids={
                f"{destination.id}:{landmark.id}"
                for destination in catalog.destinations
                for landmark in destination.landmarks
            },
        )
    assert raised.value.code == expected_code


def test_builder_api_rejects_malformed_unsupported_and_total_overflow(tmp_path, monkeypatch):
    monkeypatch.setattr("minerva_travel.storage.RUNTIME_DIR", tmp_path)
    client = TestClient(app)

    malformed = _post_builder(client, _builder_data(activity_selections="{"))
    assert malformed.status_code == 422
    assert malformed.json()["detail"]["code"] == "activity_selections_json_invalid"

    unsupported = _post_builder(
        client,
        _builder_data(
            activity_selections=[
                {
                    "landmark_selection_id": "paris:eiffel-tower",
                    "activity_type": "maze",
                    "order": 1,
                }
            ]
        ),
    )
    assert unsupported.status_code == 422
    assert unsupported.json()["detail"]["code"] == "activity_selection_record_invalid"

    overflow = _post_builder(
        client,
        _builder_data(
            activity_selections=[
                {
                    "landmark_selection_id": "paris:eiffel-tower",
                    "activity_type": "coloring",
                    "order": 1,
                }
                for _ in range(9)
            ]
        ),
    )
    assert overflow.status_code == 422
    assert overflow.json()["detail"]["code"] == "activity_selection_guide_limit"


def test_builder_api_rejects_unknown_unselected_duplicate_and_per_point_overflow(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr("minerva_travel.storage.RUNTIME_DIR", tmp_path)
    client = TestClient(app)
    invalid_requests = [
        (
            [
                {
                    "landmark_selection_id": "unknown:place",
                    "activity_type": "coloring",
                    "order": 1,
                }
            ],
            "activity_landmark_unknown",
        ),
        (
            [
                {
                    "landmark_selection_id": "paris:louvre",
                    "activity_type": "coloring",
                    "order": 1,
                }
            ],
            "activity_landmark_not_selected",
        ),
        (
            [
                {
                    "landmark_selection_id": "paris:eiffel-tower",
                    "activity_type": "coloring",
                    "order": 1,
                },
                {
                    "landmark_selection_id": "paris:eiffel-tower",
                    "activity_type": "coloring",
                    "order": 2,
                },
            ],
            "activity_selection_duplicate",
        ),
        (
            [
                {
                    "landmark_selection_id": "paris:eiffel-tower",
                    "activity_type": activity_type,
                    "order": order,
                }
                for activity_type, order in (
                    ("coloring", 1),
                    ("drawing", 2),
                    ("detail_hunt", 1),
                )
            ],
            "activity_selection_landmark_limit",
        ),
    ]
    for selections, expected_code in invalid_requests:
        data = _builder_data(activity_selections=selections)
        data["selected_landmarks"] = ["paris:eiffel-tower"]
        response = _post_builder(client, data)
        assert response.status_code == 422, response.text
        assert response.json()["detail"]["code"] == expected_code


def test_page_plan_interleaves_activities_and_appends_one_memory_page(tmp_path, monkeypatch):
    monkeypatch.setattr("minerva_travel.storage.RUNTIME_DIR", tmp_path)
    client = TestClient(app)
    selections = [
        {
            "landmark_selection_id": "paris:louvre",
            "activity_type": "drawing",
            "order": 1,
        },
        {
            "landmark_selection_id": "paris:eiffel-tower",
            "activity_type": "coloring",
            "order": 2,
        },
        {
            "landmark_selection_id": "paris:eiffel-tower",
            "activity_type": "word_search",
            "order": 1,
        },
    ]

    response = _post_builder(client, _builder_data(activity_selections=selections))
    assert response.status_code == 201, response.text
    payload = response.json()
    assert [page["id"] for page in payload["pages"]] == [
        "cover",
        "summary",
        "destination-1",
        "landmark-1",
        "activity-1-word-search",
        "activity-1-coloring",
        "landmark-2",
        "activity-2-drawing",
        "best-memory",
        "homecoming",
    ]
    assert [page["position"] for page in payload["pages"]] == list(range(1, 11))
    assert sum(page["kind"] == "best_memory" for page in payload["pages"]) == 1
    assert sum(page["kind"] == "homecoming" for page in payload["pages"]) == 1
    assert payload["pages"][-2]["kind"] == "best_memory"
    assert payload["pages"][-1]["kind"] == "homecoming"
    assert payload["pages"][-1]["required_copy"][-1] == (
        "Uma coisa que quero contar quando chegar em casa:"
    )

    destination = next(page for page in payload["pages"] if page["id"] == "destination-1")
    assert destination["metadata"]["destination_title"] == "Paris"
    assert destination["metadata"]["country"] == "França"
    assert len(destination["metadata"]["learning_points"]) == 2
    assert destination["metadata"]["curiosity_kind"] == "trusted"
    assert destination["metadata"]["curiosity"] in destination["required_copy"]
    assert "Descubra este destino" in destination["required_copy"]

    eiffel = next(page for page in payload["pages"] if page["id"] == "landmark-1")
    assert eiffel["metadata"]["curiosity_kind"] == "trusted"
    assert eiffel["metadata"]["source_image_available"] is True
    assert eiffel["metadata"]["description"] in eiffel["required_copy"]
    assert eiffel["metadata"]["curiosity"] in eiffel["required_copy"]
    assert "Conheça o lugar" in eiffel["required_copy"]
    assert "Você sabia?" in eiffel["required_copy"]
    assert "Já visitei" in eiffel["required_copy"]
    assert "source_image" not in eiffel["metadata"]

    activity = next(page for page in payload["pages"] if page["id"] == "activity-1-word-search")
    assert activity["metadata"]["activity_type"] == "word_search"
    assert activity["metadata"]["linked_landmark_page_id"] == "landmark-1"
    assert activity["metadata"]["instruction"] in activity["required_copy"]

    painting = next(page for page in payload["pages"] if page["id"] == "activity-2-drawing")
    assert painting["metadata"]["activity_type"] == "drawing"
    assert painting["metadata"]["activity_label"] == "Minha pintura"
    assert painting["metadata"]["instruction"] == (
        "Agora é a sua vez de criar uma pintura de Museu do Louvre do seu jeito."
    )
    assert painting["required_copy"][:2] == ["Minha pintura", "Museu do Louvre"]
    assert painting["metadata"]["instruction"] in painting["required_copy"]

    session = load_builder_session(payload["session_id"], "development-user")
    assert session.form["activity_selections"] == [
        {
            "landmark_selection_id": "paris:eiffel-tower",
            "activity_type": "word_search",
            "order": 1,
        },
        {
            "landmark_selection_id": "paris:eiffel-tower",
            "activity_type": "coloring",
            "order": 2,
        },
        {
            "landmark_selection_id": "paris:louvre",
            "activity_type": "drawing",
            "order": 1,
        },
    ]


def test_page_plan_accepts_exact_total_activity_boundary():
    catalog = load_catalog()
    selected = [
        "paris:eiffel-tower",
        "paris:louvre",
        "london:big-ben",
        "lisbon:oceanario",
    ]
    selections = [
        {
            "landmark_selection_id": selection_id,
            "activity_type": activity_type,
            "order": order,
        }
        for selection_id in selected
        for activity_type, order in (("coloring", 1), ("drawing", 2))
    ]
    pages, normalized = _builder_page_plan(
        {
            "title": "Família Lima",
            "year": 2026,
            "children_ages": [7],
            "activity_selections": selections,
        },
        catalog.destinations,
        selected,
    )

    assert len(normalized) == 8
    assert sum(page.kind == "landmark_activity" for page in pages) == 8
    assert pages[-2].kind == "best_memory"
    assert pages[-1].kind == "homecoming"


def test_page_plan_adds_one_learning_page_before_each_selected_destination():
    catalog = load_catalog()
    pages, activities = _builder_page_plan(
        {
            "title": "Família Lima",
            "year": 2026,
            "children_ages": [7],
            "activity_selections": [],
        },
        catalog.destinations,
        ["paris:eiffel-tower", "paris:louvre", "london:tower-bridge"],
    )

    assert activities == []
    assert [(page.id, page.kind) for page in pages] == [
        ("cover", "cover"),
        ("summary", "trip_summary"),
        ("destination-1", "destination_intro"),
        ("landmark-1", "landmark"),
        ("landmark-2", "landmark"),
        ("destination-2", "destination_intro"),
        ("landmark-3", "landmark"),
        ("best-memory", "best_memory"),
        ("homecoming", "homecoming"),
    ]
    destination_pages = [page for page in pages if page.kind == "destination_intro"]
    assert [page.metadata["destination_title"] for page in destination_pages] == [
        "Paris",
        "Londres",
    ]
    assert [page.metadata["country"] for page in destination_pages] == [
        "França",
        "Inglaterra",
    ]
    assert destination_pages[0].metadata["landmark_names"] == [
        "Torre Eiffel",
        "Museu do Louvre",
    ]


def test_unknown_destination_uses_observation_instead_of_invented_fact():
    destinations, selected = build_custom_destinations(
        [
            CustomLandmarkInput(
                selection_id="google:farol-atlantida-456",
                name="Farol de Atlântida",
                city="Atlântida",
                country="País Imaginário",
            )
        ]
    )
    pages, _activities = _builder_page_plan(
        {"title": "Família Lima", "year": 2026, "activity_selections": []},
        destinations,
        selected,
    )

    destination_page = next(page for page in pages if page.kind == "destination_intro")
    assert destination_page.metadata["curiosity_kind"] == "observation"
    assert destination_page.metadata["curiosity_label"] == "Missão de observação"
    assert destination_page.metadata["curiosity"] == (
        "Em Atlântida, procure uma forma, cor ou detalhe que ajude você a reconhecer este destino."
    )


def test_custom_landmark_without_curiosity_or_source_uses_safe_observation():
    destinations, selected = build_custom_destinations(
        [
            CustomLandmarkInput(
                selection_id="google:farol-ilha-123",
                name="Farol da Ilha",
                city="Cidade Inventada",
                country="Brasil",
                description=["Um farol escolhido pela família para conhecer durante a viagem."],
            )
        ]
    )
    pages, activities = _builder_page_plan(
        {
            "title": "Família Lima",
            "year": 2026,
            "children_ages": [7],
            "activity_selections": [
                {
                    "landmark_selection_id": "google:farol-ilha-123",
                    "activity_type": "coloring",
                    "order": 1,
                }
            ],
        },
        destinations,
        selected,
    )

    landmark_page = next(page for page in pages if page.kind == "landmark")
    coloring_page = next(page for page in pages if page.kind == "landmark_activity")
    assert selected[0] == "custom-cidade-inventada:farol-da-ilha"
    assert activities[0].landmark_selection_id == "google:farol-ilha-123"
    assert landmark_page.metadata["selection_id"] == "google:farol-ilha-123"
    assert landmark_page.metadata["place_id"] is None
    assert landmark_page.metadata["source_image"] is None
    assert landmark_page.metadata["source_image_available"] is False
    assert landmark_page.metadata["curiosity_kind"] == "observation"
    assert landmark_page.metadata["curiosity_label"] == "Missão de observação"
    assert landmark_page.metadata["curiosity"] == (
        "Observe os detalhes de Farol da Ilha e descubra qual deles mais chama sua atenção."
    )
    assert coloring_page.required_copy == [
        "Atividade para colorir",
        "Farol da Ilha",
        "Agora é a vez de colorir Farol da Ilha do seu jeito.",
    ]
    assert coloring_page.metadata["instruction"] == (
        "Agora é a vez de colorir Farol da Ilha do seu jeito."
    )


def test_activity_can_generate_before_linked_landmark_without_any_visual_reference(
    tmp_path,
    monkeypatch,
):
    generator = RecordingPageGenerator()
    monkeypatch.setattr("minerva_travel.storage.RUNTIME_DIR", tmp_path)
    monkeypatch.setattr("minerva_travel.app.get_guide_page_generator", lambda: generator)
    client = TestClient(app)
    response = _post_builder(
        client,
        {
            "title": "Família Lima",
            "children_names": "Bia",
            "children_ages": "7",
            "parents_names": "Ana",
            "year": "2026",
            "custom_landmarks": json.dumps(
                [
                    {
                        "selection_id": "google:pantheon-123",
                        "name": "Pantheon",
                        "city": "Roma",
                        "country": "Itália",
                        "description": ["Um monumento histórico escolhido pela família."],
                    }
                ]
            ),
            "activity_selections_json": json.dumps(
                [
                    {
                        "landmark_selection_id": "google:pantheon-123",
                        "activity_type": "drawing",
                        "order": 1,
                    }
                ]
            ),
        },
    )
    assert response.status_code == 201, response.text
    session_id = response.json()["session_id"]

    generated = client.post(
        f"/api/guide-builder/{session_id}/pages/activity-1-drawing/attempts",
        headers={"Idempotency-Key": "generate-pantheon-drawing"},
        json={},
    )

    assert generated.status_code == 200, generated.text
    activity_request = generator.requests[-1]
    assert activity_request["kind"] == "drawing"
    assert activity_request["landmark_reference"] is None
    assert activity_request["landmark_page_reference"] is None
    assert activity_request["landmark_context"]["name"] == "Pantheon"


def test_family_coloring_generates_from_private_photo_without_approved_cover(
    tmp_path,
    monkeypatch,
):
    generator = RecordingPageGenerator()
    monkeypatch.setattr("minerva_travel.storage.RUNTIME_DIR", tmp_path)
    monkeypatch.setattr("minerva_travel.app.get_guide_page_generator", lambda: generator)
    client = TestClient(app)
    response = _post_builder(
        client,
        {
            "title": "Família Lima",
            "children_names": "Bia",
            "children_ages": "7",
            "parents_names": "Ana",
            "year": "2026",
            "expected_visible_family_member_count": "2",
            "custom_landmarks": json.dumps(
                [
                    {
                        "selection_id": "google:pantheon-family-123",
                        "name": "Pantheon",
                        "city": "Roma",
                        "country": "Itália",
                        "description": ["Um monumento escolhido pela família."],
                    }
                ]
            ),
            "activity_selections_json": json.dumps(
                [
                    {
                        "landmark_selection_id": "google:pantheon-family-123",
                        "activity_type": "family_coloring",
                        "order": 1,
                    }
                ]
            ),
        },
    )
    assert response.status_code == 201, response.text
    session_id = response.json()["session_id"]
    activity = next(
        page for page in response.json()["pages"] if page["id"] == "activity-1-family-coloring"
    )
    assert activity["required_copy"] == [
        "Família de férias para colorir",
        "Família Lima",
        "Pantheon",
        "Agora é a vez de colorir a aventura da sua família em Pantheon.",
    ]

    generated = client.post(
        f"/api/guide-builder/{session_id}/pages/activity-1-family-coloring/attempts",
        headers={"Idempotency-Key": "generate-family-coloring-before-cover"},
        json={},
    )

    assert generated.status_code == 200, generated.text
    request = generator.requests[-1]
    assert request["kind"] == "family_coloring"
    assert request["family_photo"].is_file()
    assert request["family_cover"] is None
    assert request["landmark_reference"] is None
    assert request["landmark_page_reference"] is None
    assert request["family_title"] == "Família Lima"
    assert request["expected_visible_family_member_count"] == 2
    generated_activity = next(
        page for page in generated.json()["pages"] if page["id"] == "activity-1-family-coloring"
    )
    assert generated_activity["attempts"][-1]["include_family"] is True


def test_activity_and_memory_dispatch_never_require_or_forward_family_photo(
    tmp_path,
    monkeypatch,
):
    generator = RecordingPageGenerator()
    monkeypatch.setattr("minerva_travel.storage.RUNTIME_DIR", tmp_path)
    monkeypatch.setattr("minerva_travel.app.get_guide_page_generator", lambda: generator)
    client = TestClient(app)
    custom_landmarks = json.dumps(
        [
            {
                "selection_id": "google:farol-ilha-123",
                "name": "Farol da Ilha",
                "city": "Cidade Inventada",
                "country": "Brasil",
                "description": ["Um farol escolhido pela família para visitar."],
            }
        ]
    )
    response = _post_builder(
        client,
        {
            "title": "Família Lima",
            "children_names": "Bia",
            "children_ages": "7",
            "parents_names": "Ana",
            "year": "2026",
            "custom_landmarks": custom_landmarks,
            "activity_selections_json": json.dumps(
                [
                    {
                        "landmark_selection_id": "google:farol-ilha-123",
                        "activity_type": "coloring",
                        "order": 1,
                    }
                ]
            ),
        },
    )
    assert response.status_code == 201, response.text
    session_id = response.json()["session_id"]

    for page_id in ("cover", "summary", "destination-1", "landmark-1"):
        _generate_and_approve(client, session_id, page_id)

    destination_request = next(
        request for request in generator.requests if request["kind"] == "destination_intro"
    )
    assert "family_photo" not in destination_request
    assert "family_cover" not in destination_request

    session = load_builder_session(session_id, "development-user")
    Path(session.photo_filename).unlink()

    activity_page = _generate_and_approve(client, session_id, "activity-1-coloring")
    activity_request = generator.requests[-1]
    assert activity_request["kind"] == "coloring"
    assert activity_request["landmark_reference"] is None
    assert activity_request["landmark_page_reference"].name == "landmark-1-1.png"
    assert activity_request["landmark_context"]["name"] == "Farol da Ilha"
    assert "family_photo" not in activity_request
    assert activity_page["attempts"][-1]["include_family"] is False

    memory_page = _generate_and_approve(client, session_id, "best-memory")
    memory_request = generator.requests[-1]
    assert memory_request["kind"] == "best_memory"
    assert "family_photo" not in memory_request
    assert memory_page["attempts"][-1]["include_family"] is False

    Path(session.photo_filename).write_bytes(_family_photo())
    homecoming_page = _generate_and_approve(client, session_id, "homecoming")
    homecoming_request = generator.requests[-1]
    assert homecoming_request["kind"] == "homecoming"
    assert homecoming_request["family_photo"].is_file()
    assert homecoming_request["family_cover"].name == "cover-1.png"
    assert homecoming_request["expected_visible_family_member_count"] is None
    assert homecoming_page["attempts"][-1]["include_family"] is True

    exported = client.post(f"/api/guide-builder/{session_id}/pdf")
    assert exported.status_code == 200, exported.text
    assert exported.json()["page_count"] == 7
    assert (tmp_path / "generated" / "builder" / session_id / "approved-guide.pdf").is_file()

    deleted = client.delete("/api/account/data")
    assert deleted.status_code == 200, deleted.text
    assert client.get(f"/api/guide-builder/{session_id}").status_code == 404
    assert not (tmp_path / "generated" / "builder" / session_id).exists()


def test_old_persisted_builder_session_is_not_replanned(tmp_path, monkeypatch):
    monkeypatch.setattr("minerva_travel.storage.RUNTIME_DIR", tmp_path)
    now = datetime.now(UTC)
    payload = {
        "id": "legacybuilder1",
        "owner_id": "owner-1",
        "created_at": now.isoformat(),
        "expires_at": (now + timedelta(days=1)).isoformat(),
        "form": {"title": "Guia antigo"},
        "photo_filename": str(tmp_path / "legacy-photo.png"),
        "privacy_consent": None,
        "pages": [
            {
                "id": "cover",
                "kind": "cover",
                "title": "Capa",
                "position": 1,
                "required_copy": ["Guia antigo"],
            },
            {
                "id": "summary",
                "kind": "trip_summary",
                "title": "Resumo",
                "position": 2,
                "required_copy": ["Resumo"],
            },
            {
                "id": "landmark-1",
                "kind": "landmark",
                "title": "Ponto antigo",
                "position": 3,
                "required_copy": ["Ponto antigo"],
            },
        ],
    }
    session_path = tmp_path / "builder" / "legacybuilder1.json"
    session_path.parent.mkdir(parents=True)
    session_path.write_text(json.dumps(payload), encoding="utf-8")

    loaded: BuilderSession = load_builder_session("legacybuilder1", "owner-1")
    assert [page.kind for page in loaded.pages] == ["cover", "trip_summary", "landmark"]
    assert all(page.id != "best-memory" for page in loaded.pages)
    assert all(page.id != "homecoming" for page in loaded.pages)
