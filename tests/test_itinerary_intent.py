from minerva_travel.itinerary_intent import (
    ItineraryIntent,
    parse_itinerary_intent,
    search_profiles_from_intent,
)


def test_parse_itinerary_intent_extracts_destination_must_see_and_child_requests():
    response = {
        "output_text": (
            "{"
            '"destination":"Paris, Franca",'
            '"must_see_places":["Torre Eiffel","Louvre"],'
            '"discovery_requests":['
            '{"kind":"educational","query":"locais para criancas aprenderem sobre arte",'
            '"topic":"arte","near":"","meal":"","audience":"children"},'
            '{"kind":"restaurant","query":"almoco com criancas",'
            '"topic":"comida","near":"Torre Eiffel","meal":"lunch","audience":"children"}'
            "],"
            '"inferred_interests":["arte","comida"]'
            "}"
        )
    }

    intent = parse_itinerary_intent(
        "Vamos para Paris. Ja vamos na Torre Eiffel e Louvre. "
        "Quero lugares para as criancas aprenderem arte e almocar perto da Torre Eiffel.",
        api_key="test-key",
        responder=lambda **_: response,
    )

    assert intent.destination == "Paris, Franca"
    assert intent.must_see_places == ["Torre Eiffel", "Louvre"]
    assert [request.kind for request in intent.discovery_requests] == [
        "educational",
        "restaurant",
    ]
    assert intent.discovery_requests[1].near == "Torre Eiffel"
    assert intent.inferred_interests == ["arte", "comida"]


def test_search_profiles_from_intent_prioritizes_child_and_contextual_requests():
    intent = ItineraryIntent(
        destination="Paris, Franca",
        must_see_places=["Torre Eiffel"],
        discovery_requests=[
            {
                "kind": "educational",
                "query": "locais para criancas aprenderem sobre arte",
                "topic": "arte",
                "near": "",
                "meal": "",
                "audience": "children",
            },
            {
                "kind": "restaurant",
                "query": "almoco com criancas",
                "topic": "comida",
                "near": "Torre Eiffel",
                "meal": "lunch",
                "audience": "children",
            },
        ],
        inferred_interests=["arte"],
    )

    profiles = search_profiles_from_intent(intent, explicit_interests=[])

    assert profiles[0] == (
        "must_see",
        "Torre Eiffel em Paris, Franca",
    )
    assert profiles[1] == (
        "art",
        "locais para criancas aprenderem sobre arte em Paris, Franca",
    )
    assert profiles[2] == (
        "food",
        "almoco com criancas perto de Torre Eiffel em Paris, Franca",
    )
