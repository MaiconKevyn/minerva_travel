import httpx

from minerva_travel.place_suggestions import MIN_QUERY_LENGTH, suggest_places


def _place(
    place_id: str,
    name: str,
    *,
    city: str = "Paris",
    country: str = "França",
    address: str = "Champ de Mars, Paris, França",
) -> dict:
    return {
        "id": place_id,
        "displayName": {"text": name},
        "formattedAddress": address,
        "addressComponents": [
            {"longText": city, "types": ["locality", "political"]},
            {"longText": country, "types": ["country", "political"]},
        ],
        "location": {"latitude": 48.8584, "longitude": 2.2945},
        "types": ["tourist_attraction"],
    }


def _client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_suggestions_return_the_official_name_and_place_id():
    def handler(request: httpx.Request) -> httpx.Response:
        assert "places:searchText" in str(request.url)
        assert request.headers["X-Goog-Api-Key"] == "chave-do-servidor"
        return httpx.Response(200, json={"places": [_place("eiffel-id", "Torre Eiffel")]})

    with _client(handler) as client:
        # A família digitou errado; a sugestão precisa trazer a grafia oficial.
        suggestions = suggest_places("Torre Eifel", api_key="chave-do-servidor", client=client)

    assert len(suggestions) == 1
    suggestion = suggestions[0]
    assert suggestion.name == "Torre Eiffel"
    assert suggestion.place_id == "eiffel-id"
    assert suggestion.city == "Paris"
    assert suggestion.country == "França"
    assert suggestion.location_label == "Paris, França"
    assert suggestion.as_payload()["latitude"] == 48.8584


def test_city_lookup_restricts_results_to_localities():
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(__import__("json").loads(request.read()))
        return httpx.Response(200, json={"places": [_place("paris-id", "Paris")]})

    with _client(handler) as client:
        suggest_places("Paris", api_key="chave", kind="city", client=client)

    assert captured["includedType"] == "locality"
    assert captured["languageCode"] == "pt-BR"


def test_landmark_lookup_biases_by_the_destination_already_chosen():
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(__import__("json").loads(request.read()))
        return httpx.Response(200, json={"places": []})

    with _client(handler) as client:
        suggest_places("Louvre", api_key="chave", near="Paris, França", client=client)

    assert captured["textQuery"] == "Louvre Paris, França"


def test_short_queries_and_missing_key_never_call_google():
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("não deve chamar o Google")

    with _client(handler) as client:
        assert suggest_places("To", api_key="chave", client=client) == []
        assert suggest_places("Torre Eiffel", api_key=None, client=client) == []
        assert suggest_places("   ", api_key="chave", client=client) == []
    assert MIN_QUERY_LENGTH == 3


def test_google_failures_degrade_to_free_typing():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "boom"})

    with _client(handler) as client:
        # Autocomplete é conveniência: falhar não pode travar o formulário.
        assert suggest_places("Torre Eiffel", api_key="chave", client=client) == []


def test_places_without_locality_fall_back_to_the_formatted_address():
    def handler(request: httpx.Request) -> httpx.Response:
        place = {
            "id": "ilha-id",
            "displayName": {"text": "Praia do Sancho"},
            "formattedAddress": "Praia do Sancho, Fernando de Noronha, Brasil",
            "addressComponents": [{"longText": "Brasil", "types": ["country"]}],
            "location": {"latitude": -3.85, "longitude": -32.44},
        }
        return httpx.Response(200, json={"places": [place]})

    with _client(handler) as client:
        suggestions = suggest_places("Praia do Sancho", api_key="chave", client=client)

    assert suggestions[0].city == "Fernando de Noronha"
    assert suggestions[0].country == "Brasil"


def test_malformed_places_are_skipped_without_breaking_the_list():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"places": [{"id": "", "displayName": {}}, _place("ok-id", "Museu do Louvre")]},
        )

    with _client(handler) as client:
        suggestions = suggest_places("Louvre", api_key="chave", client=client)

    assert [item.name for item in suggestions] == ["Museu do Louvre"]
