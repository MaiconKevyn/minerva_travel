import httpx

from minerva_travel.models import DynamicItineraryRequest
from minerva_travel.place_discovery import discover_dynamic_itinerary


def test_discover_dynamic_itinerary_prioritizes_requested_interests():
    calls: list[tuple[str, dict[str, object] | None]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        payload = None
        if request.content:
            payload = request.read()
        url = str(request.url)
        if "maps/api/geocode/json" in url:
            return httpx.Response(
                200,
                json={
                    "status": "OK",
                    "results": [
                        {
                            "formatted_address": "Paris, Franca",
                            "address_components": [
                                {"long_name": "Paris", "types": ["locality"]},
                                {"long_name": "Franca", "types": ["country"]},
                            ],
                            "geometry": {"location": {"lat": 48.8566, "lng": 2.3522}},
                        }
                    ],
                },
            )
        if "places:searchText" in url:
            body = httpx.Request("POST", "http://test", content=payload).read()
            text = body.decode()
            calls.append((url, None))
            if "museus" in text or "museum" in text:
                places = [
                    _place("museum-1", "Museu Central", ["museum"], rating=4.8, count=9000),
                    _place("park-1", "Jardim Historico", ["park"], rating=4.6, count=3000),
                ]
            else:
                places = [
                    _place("park-1", "Jardim Historico", ["park"], rating=4.6, count=3000),
                    _place("museum-1", "Museu Central", ["museum"], rating=4.8, count=9000),
                ]
            return httpx.Response(200, json={"places": places})
        raise AssertionError(f"Unexpected request: {url}")

    transport = httpx.MockTransport(handler)

    with httpx.Client(transport=transport) as client:
        recommendation = discover_dynamic_itinerary(
            DynamicItineraryRequest(
                destination="Paris",
                days=1,
                interests=["museus"],
                pace="light",
            ),
            api_key="test-key",
            client=client,
        )

    selected_ids = [
        stop["selection_id"]
        for day in recommendation["days"]
        for stop in day["stops"]
    ]

    assert recommendation["recommendation_source"] == "google_places"
    assert selected_ids[0] == "google:museum-1"
    assert recommendation["selected_landmarks"] == selected_ids
    assert recommendation["days"][0]["stops"][0]["name"] == "Museu Central"
    assert "Interesse da familia: museus." in recommendation["days"][0]["stops"][0]["match_reasons"]
    assert calls


def test_discover_dynamic_itinerary_pace_controls_stop_count():
    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "maps/api/geocode/json" in url:
            return httpx.Response(
                200,
                json={
                    "status": "OK",
                    "results": [
                        {
                            "formatted_address": "Lisboa, Portugal",
                            "address_components": [
                                {"long_name": "Lisboa", "types": ["locality"]},
                                {"long_name": "Portugal", "types": ["country"]},
                            ],
                            "geometry": {"location": {"lat": 38.7223, "lng": -9.1393}},
                        }
                    ],
                },
            )
        if "places:searchText" in url:
            return httpx.Response(
                200,
                json={
                    "places": [
                        _place(f"place-{idx}", f"Local {idx}", ["tourist_attraction"])
                        for idx in range(1, 8)
                    ]
                },
            )
        raise AssertionError(f"Unexpected request: {url}")

    transport = httpx.MockTransport(handler)

    with httpx.Client(transport=transport) as client:
        light = discover_dynamic_itinerary(
            DynamicItineraryRequest(destination="Lisboa", days=1, pace="light"),
            api_key="test-key",
            client=client,
        )
        full = discover_dynamic_itinerary(
            DynamicItineraryRequest(destination="Lisboa", days=1, pace="full"),
            api_key="test-key",
            client=client,
        )

    light_stops = [stop for day in light["days"] for stop in day["stops"]]
    full_stops = [stop for day in full["days"] for stop in day["stops"]]

    assert len(light_stops) == 2
    assert len(full_stops) == 4


def _place(
    place_id: str,
    name: str,
    types: list[str],
    *,
    rating: float = 4.5,
    count: int = 1000,
) -> dict[str, object]:
    return {
        "id": place_id,
        "displayName": {"text": name},
        "formattedAddress": "Endereco",
        "location": {"latitude": 48.8566, "longitude": 2.3522},
        "types": types,
        "rating": rating,
        "userRatingCount": count,
        "googleMapsUri": f"https://maps.google.com/?cid={place_id}",
    }
