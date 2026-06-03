from fastapi.testclient import TestClient

from minerva_travel.app import app
from minerva_travel.catalog import load_catalog
from minerva_travel.itinerary import recommend_itinerary
from minerva_travel.models import ItineraryRecommendationRequest


def test_recommend_itinerary_prioritizes_family_interests_and_must_see():
    catalog = load_catalog()
    request = ItineraryRecommendationRequest(
        destination_ids=["paris"],
        days=2,
        interests=["museus", "parques"],
        pace="light",
        children_ages=[5, 8],
        must_see_landmarks=["paris:eiffel-tower"],
    )

    recommendation = recommend_itinerary(catalog, request)
    stops = [stop for day in recommendation.days for stop in day.stops]
    selected_ids = [stop.selection_id for stop in stops]

    assert len(recommendation.days) == 2
    assert recommendation.selected_landmarks == selected_ids
    assert "paris:eiffel-tower" in selected_ids
    assert "paris:louvre" in selected_ids
    assert "paris:luxembourg" in selected_ids
    assert recommendation.recommendation_source == "curated_catalog"

    louvre = next(stop for stop in stops if stop.selection_id == "paris:louvre")
    luxembourg = next(stop for stop in stops if stop.selection_id == "paris:luxembourg")
    eiffel = next(stop for stop in stops if stop.selection_id == "paris:eiffel-tower")

    assert "museums" in louvre.categories
    assert "Interesse da familia: museus." in louvre.match_reasons
    assert "parks" in luxembourg.categories
    assert "Interesse da familia: parques." in luxembourg.match_reasons
    assert "Ponto obrigatorio informado pela familia." in eiffel.match_reasons
    assert all(stop.editable for stop in stops)
    assert recommendation.alternatives


def test_recommend_itinerary_api_returns_cards_ready_for_frontend_editing():
    client = TestClient(app)

    response = client.post(
        "/api/itinerary/recommend",
        json={
            "destination_ids": ["lisbon"],
            "days": 1,
            "interests": ["animais", "comida"],
            "pace": "balanced",
            "children_ages": [6],
            "must_see_landmarks": ["lisbon:pastel-de-belem"],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    selected_ids = [
        stop["selection_id"]
        for day in payload["days"]
        for stop in day["stops"]
    ]

    assert payload["summary"] == "Roteiro sugerido para Lisboa em 1 dia."
    assert payload["selected_landmarks"] == selected_ids
    assert "lisbon:oceanario" in selected_ids
    assert "lisbon:pastel-de-belem" in selected_ids
    assert payload["days"][0]["title"] == "Dia 1 em Lisboa"
    assert payload["days"][0]["stops"][0]["editable"] is True
    assert payload["days"][0]["stops"][0]["duration_minutes"] >= 30
    assert payload["alternatives"][0]["selection_id"].startswith("lisbon:")


def test_recommend_itinerary_keeps_all_must_see_cards_visible():
    catalog = load_catalog()
    request = ItineraryRecommendationRequest(
        destination_ids=["paris"],
        days=1,
        pace="light",
        must_see_landmarks=[
            "paris:eiffel-tower",
            "paris:louvre",
            "paris:luxembourg",
        ],
    )

    recommendation = recommend_itinerary(catalog, request)
    visible_stop_ids = [
        stop.selection_id
        for day in recommendation.days
        for stop in day.stops
    ]

    assert recommendation.selected_landmarks == visible_stop_ids
    assert visible_stop_ids == [
        "paris:eiffel-tower",
        "paris:louvre",
        "paris:luxembourg",
    ]


def test_recommend_itinerary_api_rejects_unknown_destination():
    client = TestClient(app)

    response = client.post(
        "/api/itinerary/recommend",
        json={
            "destination_ids": ["tokyo"],
            "days": 2,
            "interests": ["museus"],
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Destino desconhecido: tokyo"
