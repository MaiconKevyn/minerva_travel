import json

import httpx

from minerva_travel.custom_landmarks import build_custom_destinations, parse_custom_landmarks
from minerva_travel.models import DynamicItineraryRequest
from minerva_travel.place_discovery import (
    _place_categories,
    discover_dynamic_itinerary,
    resolve_landmark_locations,
)


def test_discover_dynamic_itinerary_normalizes_options_with_category_and_identity():
    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "maps/api/geocode/json" in url:
            return _geocode_response("Paris", "Franca", 48.8566, 2.3522)
        if "places:searchText" in url:
            return httpx.Response(
                200,
                json={
                    "places": [
                        _place("museum-central", "Museu Central", ["museum"]),
                    ]
                },
            )
        raise AssertionError(f"Unexpected request: {url}")

    transport = httpx.MockTransport(handler)

    with httpx.Client(transport=transport) as client:
        recommendation = discover_dynamic_itinerary(
            DynamicItineraryRequest(
                destination="Paris",
                days=1,
                interests=["museus"],
                pace="light",
                children_ages=[6],
            ),
            api_key="test-key",
            client=client,
        )

    visible_options = [
        *[stop for day in recommendation["days"] for stop in day["stops"]],
        *recommendation["alternatives"],
    ]

    assert visible_options
    option = visible_options[0]
    assert option["destination_id"] == "google-paris"
    assert option["name"] == "Museu Central"
    assert option["category"] == "museums"
    assert "museums" in option["categories"]
    assert option["selection_id"] == "google:museum-central"
    assert option["landmark_id"] == "museu-central"
    assert "Boa opcao para criancas menores." in option["match_reasons"]


def test_google_place_type_takes_priority_over_the_search_profile_category():
    categories = _place_categories(_place("museum-central", "Museu Central", ["museum"]), "food")

    assert categories == ["museums", "food"]


def test_discover_dynamic_itinerary_returns_broader_family_categories_when_available():
    requested_queries: list[str] = []

    places_by_token = [
        ("parque", _place("park", "Parque Botanico", ["park"])),
        ("praca", _place("square", "Praca Central", ["tourist_attraction"])),
        ("teatro", _place("theater", "Teatro Infantil", ["performing_arts_theater"])),
        ("museu", _place("museum", "Museu das Criancas", ["museum"])),
        ("arte", _place("art", "Galeria de Arte Kids", ["art_gallery"])),
        ("ar livre", _place("outdoor", "Circuito ao Ar Livre", ["tourist_attraction"])),
        ("lojas locais", _place("local-store", "Loja Local de Brinquedos", ["market"])),
        ("familia", _place("family", "Programa em Familia", ["tourist_attraction"])),
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "maps/api/geocode/json" in url:
            return _geocode_response("Porto", "Portugal", 41.1579, -8.6291)
        if "places:searchText" in url:
            payload = json.loads(request.read().decode())
            query = payload["textQuery"]
            requested_queries.append(query)
            normalized_query = _ascii(query)
            places = [place for token, place in places_by_token if token in normalized_query]
            return httpx.Response(200, json={"places": places})
        raise AssertionError(f"Unexpected request: {url}")

    transport = httpx.MockTransport(handler)

    with httpx.Client(transport=transport) as client:
        recommendation = discover_dynamic_itinerary(
            DynamicItineraryRequest(
                destination="Porto",
                days=2,
                interests=[],
                pace="full",
                children_ages=[4, 9],
            ),
            api_key="test-key",
            client=client,
        )

    visible_options = [
        *[stop for day in recommendation["days"] for stop in day["stops"]],
        *recommendation["alternatives"],
    ]
    categories = {stop["category"] for stop in visible_options}

    assert {
        "parks",
        "squares",
        "theaters",
        "museums",
        "art",
        "outdoor",
        "local_stores",
        "family",
    }.issubset(categories)
    assert any("teatro" in _ascii(query) for query in requested_queries)
    assert any("lojas locais" in _ascii(query) for query in requested_queries)


def test_discover_dynamic_itinerary_supplements_generic_intent_with_default_categories():
    places_by_token = [
        ("parque", _place("park", "Parque Botanico", ["park"])),
        ("praca", _place("square", "Praca Central", ["tourist_attraction"])),
        ("teatro", _place("theater", "Teatro Infantil", ["performing_arts_theater"])),
        ("museu", _place("museum", "Museu das Criancas", ["museum"])),
        ("arte", _place("art", "Galeria de Arte Kids", ["art_gallery"])),
        ("ar livre", _place("outdoor", "Circuito ao Ar Livre", ["tourist_attraction"])),
        ("lojas locais", _place("local-store", "Loja Local de Brinquedos", ["market"])),
        ("familia", _place("family", "Programa em Familia", ["tourist_attraction"])),
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "maps/api/geocode/json" in url:
            return _geocode_response("Porto", "Portugal", 41.1579, -8.6291)
        if "places:searchText" in url:
            payload = json.loads(request.read().decode())
            normalized_query = _ascii(payload["textQuery"])
            return httpx.Response(
                200,
                json={
                    "places": [
                        place for token, place in places_by_token if token in normalized_query
                    ]
                },
            )
        raise AssertionError(f"Unexpected request: {url}")

    transport = httpx.MockTransport(handler)

    with httpx.Client(transport=transport) as client:
        recommendation = discover_dynamic_itinerary(
            DynamicItineraryRequest(
                destination="Porto",
                days=2,
                pace="full",
                children_ages=[4, 9],
            ),
            api_key="test-key",
            openai_api_key="test-openai-key",
            client=client,
            intent_responder=lambda **_: {
                "output_text": (
                    "{"
                    '"destination":"Porto, Portugal",'
                    '"must_see_places":[],'
                    '"discovery_requests":['
                    '{"kind":"general","query":"viajar com a familia",'
                    '"topic":"viajar com a familia","near":"","meal":"",'
                    '"audience":"children"}'
                    "],"
                    '"inferred_interests":[]'
                    "}"
                )
            },
        )

    visible_options = [
        *[stop for day in recommendation["days"] for stop in day["stops"]],
        *recommendation["alternatives"],
    ]

    assert {
        "parks",
        "squares",
        "theaters",
        "museums",
        "art",
        "outdoor",
        "local_stores",
        "family",
    }.issubset({stop["category"] for stop in visible_options})


def test_discover_dynamic_itinerary_exposes_minimum_unique_options_when_available():
    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "maps/api/geocode/json" in url:
            return _geocode_response("Lisboa", "Portugal", 38.7223, -9.1393)
        if "places:searchText" in url:
            return httpx.Response(
                200,
                json={
                    "places": [
                        _place(f"place-{idx}", f"Local {idx}", ["tourist_attraction"])
                        for idx in range(1, 15)
                    ]
                },
            )
        raise AssertionError(f"Unexpected request: {url}")

    transport = httpx.MockTransport(handler)

    with httpx.Client(transport=transport) as client:
        recommendation = discover_dynamic_itinerary(
            DynamicItineraryRequest(destination="Lisboa", days=1, pace="light"),
            api_key="test-key",
            client=client,
        )

    visible_ids = [
        *[stop["selection_id"] for day in recommendation["days"] for stop in day["stops"]],
        *[stop["selection_id"] for stop in recommendation["alternatives"]],
    ]

    assert len(visible_ids) >= 12
    assert len(visible_ids) == len(set(visible_ids))


def test_discover_dynamic_itinerary_uses_natural_language_intent_for_child_requests():
    search_queries: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "maps/api/geocode/json" in url:
            return _geocode_response("Paris", "Franca", 48.8566, 2.3522)
        if "places:searchText" in url:
            text = request.read().decode()
            search_queries.append(text)
            if "almoco" in text or "almoço" in text:
                return httpx.Response(
                    200,
                    json={
                        "places": [
                            _place(
                                "lunch-eiffel",
                                "Bistro Familiar da Torre",
                                ["restaurant"],
                            )
                        ]
                    },
                )
            if "Torre Eiffel" in text:
                return httpx.Response(
                    200,
                    json={"places": [_place("eiffel", "Torre Eiffel", ["tourist_attraction"])]},
                )
            if "arte" in text:
                return httpx.Response(
                    200,
                    json={
                        "places": [_place("art-kids", "Atelier Infantil de Arte", ["art_gallery"])]
                    },
                )
            return httpx.Response(200, json={"places": []})
        raise AssertionError(f"Unexpected request: {url}")

    transport = httpx.MockTransport(handler)

    with httpx.Client(transport=transport) as client:
        recommendation = discover_dynamic_itinerary(
            DynamicItineraryRequest(
                destination=(
                    "Vamos para Paris. Ja vamos na Torre Eiffel. Quero lugares onde "
                    "as criancas aprendam sobre arte e um local para almocar com meus "
                    "filhos perto da Torre Eiffel."
                ),
                days=1,
                pace="full",
            ),
            api_key="test-key",
            openai_api_key="test-openai-key",
            client=client,
            intent_responder=lambda **_: {
                "output_text": (
                    "{"
                    '"destination":"Paris, Franca",'
                    '"must_see_places":["Torre Eiffel"],'
                    '"discovery_requests":['
                    '{"kind":"educational","query":"lugares para criancas aprenderem arte",'
                    '"topic":"arte","near":"","meal":"","audience":"children"},'
                    '{"kind":"restaurant","query":"almoco com criancas",'
                    '"topic":"comida","near":"Torre Eiffel","meal":"lunch",'
                    '"audience":"children"}'
                    "],"
                    '"inferred_interests":["arte","comida"]'
                    "}"
                )
            },
        )

    stops = [stop for day in recommendation["days"] for stop in day["stops"]]
    selected_ids = [stop["selection_id"] for stop in stops]

    assert selected_ids[:3] == [
        "google:eiffel",
        "google:art-kids",
        "google:lunch-eiffel",
    ]
    assert stops[0]["source_type"] == "mentioned"
    assert stops[1]["source_type"] == "suggested"
    assert stops[2]["source_type"] == "suggested"
    assert "Ponto obrigatorio informado pela familia." in stops[0]["match_reasons"]
    assert "Pedido da familia: educativo para criancas." in stops[1]["match_reasons"]
    assert "Pedido da familia: refeicao com criancas." in stops[2]["match_reasons"]
    assert any("perto de Torre Eiffel" in query for query in search_queries)


def test_resolve_landmark_locations_retries_until_google_places_returns_coordinates():
    search_queries: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "places:searchText" in url:
            text = request.read().decode()
            search_queries.append(text)
            if "ponto turistico" not in text:
                return httpx.Response(200, json={"places": []})
            return httpx.Response(
                200,
                json={"places": [_place("eiffel", "Torre Eiffel", ["tourist_attraction"])]},
            )
        raise AssertionError(f"Unexpected request: {url}")

    destinations, _selected = build_custom_destinations(
        parse_custom_landmarks("Torre Eiffel, Paris, Franca")
    )
    transport = httpx.MockTransport(handler)

    with httpx.Client(transport=transport) as client:
        metadata = resolve_landmark_locations(
            destinations,
            api_key="test-key",
            client=client,
        )

    assert metadata["custom-paris:torre-eiffel"]["latitude"] == 48.8566
    assert metadata["custom-paris:torre-eiffel"]["longitude"] == 2.3522
    assert metadata["custom-paris:torre-eiffel"]["google_maps_uri"] == (
        "https://maps.google.com/?cid=eiffel"
    )
    assert len(search_queries) == 2


def test_resolve_landmark_locations_include_photos_adds_image_metadata():
    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "places:searchText" in url:
            return httpx.Response(
                200,
                json={
                    "places": [
                        _place(
                            "eiffel",
                            "Torre Eiffel",
                            ["tourist_attraction"],
                            photos=[
                                {
                                    "name": "places/eiffel/photos/photo-1",
                                    "authorAttributions": [
                                        {"displayName": "Guia Local", "uri": "https://exemplo"}
                                    ],
                                }
                            ],
                        )
                    ]
                },
            )
        if "/photos/photo-1/media" in url:
            return httpx.Response(
                200,
                json={"photoUri": "https://lh3.googleusercontent.com/eiffel-photo"},
            )
        raise AssertionError(f"Unexpected request: {url}")

    destinations, _selected = build_custom_destinations(
        parse_custom_landmarks("Torre Eiffel, Paris, Franca")
    )
    transport = httpx.MockTransport(handler)

    with httpx.Client(transport=transport) as client:
        metadata = resolve_landmark_locations(
            destinations,
            api_key="test-key",
            client=client,
            include_photos=True,
        )

    resolved = metadata["custom-paris:torre-eiffel"]
    assert resolved["image_url"] == "https://lh3.googleusercontent.com/eiffel-photo"
    assert resolved["image_attributions"] == [
        {"display_name": "Guia Local", "uri": "https://exemplo"}
    ]


def test_resolve_landmark_locations_does_not_fall_back_to_bare_query_for_known_destination():
    search_queries: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "places:searchText" in url:
            text = request.read().decode()
            search_queries.append(text)
            if "ponto turistico" in text or "Espanha" in text:
                return httpx.Response(200, json={"places": []})
            return httpx.Response(
                200,
                json={
                    "places": [
                        _place(
                            "wrong-country",
                            "Santiago de Compostela",
                            ["tourist_attraction"],
                            address="Santiago de Compostela, Brasil",
                            lat=-15.7797,
                            lng=-47.9297,
                        )
                    ]
                },
            )
        raise AssertionError(f"Unexpected request: {url}")

    destinations, _selected = build_custom_destinations(
        parse_custom_landmarks("Santiago de Compostela, Santiago de Compostela, Espanha")
    )
    transport = httpx.MockTransport(handler)

    with httpx.Client(transport=transport) as client:
        metadata = resolve_landmark_locations(
            destinations,
            api_key="test-key",
            client=client,
        )

    assert metadata == {}
    assert len(search_queries) == 2


def test_discover_dynamic_itinerary_adds_google_place_photos_to_visible_cards():
    photo_requests: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "maps/api/geocode/json" in url:
            return _geocode_response("Paris", "Franca", 48.8566, 2.3522)
        if "places:searchText" in url:
            return httpx.Response(
                200,
                json={
                    "places": [
                        _place(
                            "museum-photo",
                            "Museu com Foto",
                            ["museum"],
                            photos=[
                                {
                                    "name": "places/museum-photo/photos/photo-1",
                                    "authorAttributions": [
                                        {
                                            "displayName": "Maria Fotografa",
                                            "uri": "https://example.com/maria",
                                        }
                                    ],
                                }
                            ],
                        )
                    ]
                },
            )
        if "places/museum-photo/photos/photo-1/media" in url:
            photo_requests.append(url)
            assert request.url.params["skipHttpRedirect"] == "true"
            return httpx.Response(
                200,
                json={"photoUri": "https://lh3.googleusercontent.com/photo=w900"},
            )
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

    stop = recommendation["days"][0]["stops"][0]

    assert stop["image"] == "https://lh3.googleusercontent.com/photo=w900"
    assert stop["latitude"] == 48.8566
    assert stop["longitude"] == 2.3522
    assert stop["image_attributions"] == [
        {
            "display_name": "Maria Fotografa",
            "uri": "https://example.com/maria",
        }
    ]
    assert photo_requests


def test_discover_dynamic_itinerary_keeps_stop_when_google_photo_fails():
    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "maps/api/geocode/json" in url:
            return _geocode_response("Paris", "Franca", 48.8566, 2.3522)
        if "places:searchText" in url:
            return httpx.Response(
                200,
                json={
                    "places": [
                        _place(
                            "museum-photo",
                            "Museu com Foto Instavel",
                            ["museum"],
                            photos=[{"name": "places/museum-photo/photos/photo-1"}],
                        )
                    ]
                },
            )
        if "places/museum-photo/photos/photo-1/media" in url:
            return httpx.Response(404, json={"error": {"message": "photo unavailable"}})
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

    stop = recommendation["days"][0]["stops"][0]

    assert stop["name"] == "Museu com Foto Instavel"
    assert stop["image"] is None


def test_discover_dynamic_itinerary_keeps_one_stop_per_explicit_family_request():
    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "maps/api/geocode/json" in url:
            return _geocode_response("Paris", "Franca", 48.8566, 2.3522)
        if "places:searchText" in url:
            text = request.read().decode()
            if "almoco" in text:
                return httpx.Response(
                    200,
                    json={"places": [_place("lunch", "Almoco Familiar", ["restaurant"])]},
                )
            if "Torre Eiffel" in text:
                return httpx.Response(
                    200,
                    json={
                        "places": [
                            _place("eiffel", "Torre Eiffel", ["tourist_attraction"]),
                            _place("eiffel-view", "Vista da Torre Eiffel", ["tourist_attraction"]),
                        ]
                    },
                )
            if "arte" in text:
                return httpx.Response(
                    200,
                    json={"places": [_place("art-kids", "Atelier Infantil de Arte", ["museum"])]},
                )
            return httpx.Response(200, json={"places": []})
        raise AssertionError(f"Unexpected request: {url}")

    transport = httpx.MockTransport(handler)

    with httpx.Client(transport=transport) as client:
        recommendation = discover_dynamic_itinerary(
            DynamicItineraryRequest(
                destination="Paris com Torre Eiffel, arte para criancas e almoco perto da torre",
                days=1,
                pace="balanced",
            ),
            api_key="test-key",
            openai_api_key="test-openai-key",
            client=client,
            intent_responder=lambda **_: {
                "output_text": (
                    "{"
                    '"destination":"Paris, Franca",'
                    '"must_see_places":["Torre Eiffel"],'
                    '"discovery_requests":['
                    '{"kind":"educational","query":"arte para criancas",'
                    '"topic":"arte","near":"","meal":"","audience":"children"},'
                    '{"kind":"restaurant","query":"almoco com criancas",'
                    '"topic":"comida","near":"Torre Eiffel","meal":"lunch",'
                    '"audience":"children"}'
                    "],"
                    '"inferred_interests":[]'
                    "}"
                )
            },
        )

    stop_names = [stop["name"] for day in recommendation["days"] for stop in day["stops"]]

    assert stop_names == ["Torre Eiffel", "Atelier Infantil de Arte", "Almoco Familiar"]


def test_discover_dynamic_itinerary_keeps_only_best_google_result_for_mentioned_place():
    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "maps/api/geocode/json" in url:
            return _geocode_response("Paris", "Franca", 48.8566, 2.3522)
        if "places:searchText" in url:
            text = request.read().decode()
            if "Louvre" in text:
                return httpx.Response(
                    200,
                    json={
                        "places": [
                            _place("louvre", "Museu do Louvre", ["museum", "tourist_attraction"]),
                            _place(
                                "louvre-pyramid",
                                "Piramide do Louvre",
                                ["tourist_attraction"],
                            ),
                        ]
                    },
                )
            if "educativo" in text:
                return httpx.Response(
                    200,
                    json={
                        "places": [
                            _place(
                                "science-museum",
                                "Palacio da descoberta",
                                ["museum", "tourist_attraction"],
                            )
                        ]
                    },
                )
            return httpx.Response(200, json={"places": []})
        raise AssertionError(f"Unexpected request: {url}")

    transport = httpx.MockTransport(handler)

    with httpx.Client(transport=transport) as client:
        recommendation = discover_dynamic_itinerary(
            DynamicItineraryRequest(
                destination="Quero ir no Louvre e depois em um museu educativo em Paris",
                days=1,
                pace="full",
            ),
            api_key="test-key",
            openai_api_key="test-openai-key",
            client=client,
            intent_responder=lambda **_: {
                "output_text": (
                    "{"
                    '"destination":"Paris, Franca",'
                    '"must_see_places":["Louvre"],'
                    '"discovery_requests":['
                    '{"kind":"educational","query":"museu educativo",'
                    '"topic":"educativo","near":"","meal":"","audience":"children"}'
                    "],"
                    '"inferred_interests":[]'
                    "}"
                )
            },
        )

    visible_stops = [
        *[stop for day in recommendation["days"] for stop in day["stops"]],
        *recommendation["alternatives"],
    ]
    stop_names = [stop["name"] for stop in visible_stops]
    mentioned_names = [stop["name"] for stop in visible_stops if stop["source_type"] == "mentioned"]

    assert "Museu do Louvre" in stop_names
    assert "Piramide do Louvre" not in stop_names
    assert mentioned_names == ["Museu do Louvre"]


def test_discover_dynamic_itinerary_skips_restaurants_for_non_food_requests():
    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "maps/api/geocode/json" in url:
            return _geocode_response("Lisboa", "Portugal", 38.7223, -9.1393)
        if "places:searchText" in url:
            text = request.read().decode()
            if "rio" in text or "barco" in text:
                return httpx.Response(
                    200,
                    json={
                        "places": [
                            _place("restaurant-rio", "Feel Rio", ["restaurant"]),
                            _place("tejo-boat", "Passeio de Barco no Tejo", ["tourist_attraction"]),
                        ]
                    },
                )
            return httpx.Response(200, json={"places": []})
        raise AssertionError(f"Unexpected request: {url}")

    transport = httpx.MockTransport(handler)

    with httpx.Client(transport=transport) as client:
        recommendation = discover_dynamic_itinerary(
            DynamicItineraryRequest(
                destination="Lisboa",
                days=1,
                interests=["rio"],
                pace="light",
            ),
            api_key="test-key",
            client=client,
        )

    stop_names = [stop["name"] for day in recommendation["days"] for stop in day["stops"]]

    assert "Feel Rio" not in stop_names
    assert stop_names[0] == "Passeio de Barco no Tejo"


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

    selected_ids = [stop["selection_id"] for day in recommendation["days"] for stop in day["stops"]]

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
    photos: list[dict[str, object]] | None = None,
    address: str = "Endereco",
    lat: float = 48.8566,
    lng: float = 2.3522,
) -> dict[str, object]:
    return {
        "id": place_id,
        "displayName": {"text": name},
        "formattedAddress": address,
        "location": {"latitude": lat, "longitude": lng},
        "types": types,
        "rating": rating,
        "userRatingCount": count,
        "photos": photos or [],
        "googleMapsUri": f"https://maps.google.com/?cid={place_id}",
    }


def _ascii(value: str) -> str:
    return value.encode("ascii", errors="ignore").decode().casefold()


def _geocode_response(city: str, country: str, lat: float, lng: float) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "status": "OK",
            "results": [
                {
                    "formatted_address": f"{city}, {country}",
                    "address_components": [
                        {"long_name": city, "types": ["locality"]},
                        {"long_name": country, "types": ["country"]},
                    ],
                    "geometry": {"location": {"lat": lat, "lng": lng}},
                }
            ],
        },
    )
