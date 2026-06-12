import math
import unicodedata
from collections.abc import Iterable
from typing import Any

import httpx

from minerva_travel.itinerary_intent import parse_itinerary_intent, search_profiles_from_intent
from minerva_travel.models import Destination, DynamicItineraryRequest

GOOGLE_GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"
GOOGLE_TEXT_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
GOOGLE_PLACES_BASE_URL = "https://places.googleapis.com/v1"

PACE_STOP_LIMITS = {
    "light": 2,
    "balanced": 3,
    "full": 4,
}

TEXT_SEARCH_FIELD_MASK = (
    "places.id,"
    "places.displayName,"
    "places.formattedAddress,"
    "places.location,"
    "places.types,"
    "places.primaryType,"
    "places.photos,"
    "places.rating,"
    "places.userRatingCount,"
    "places.googleMapsUri"
)

LOCATION_SEARCH_RESULT_LIMIT = 3

INTEREST_ALIASES = {
    "animais": "animals",
    "animal": "animals",
    "arte": "art",
    "comida": "food",
    "gastronomia": "food",
    "historia": "history",
    "historia local": "history",
    "lojas": "shopping",
    "compras": "shopping",
    "museu": "museums",
    "museus": "museums",
    "parque": "parks",
    "parques": "parks",
    "pracas": "parks",
    "rio": "river",
    "vistas": "views",
}

INTEREST_LABELS = {
    "animals": "animais",
    "art": "arte",
    "food": "comida",
    "history": "historia",
    "museums": "museus",
    "parks": "parques",
    "river": "rio e passeios",
    "shopping": "lojas",
    "views": "vistas",
}

INTEREST_QUERIES = {
    "animals": "zoologicos aquarios atividades com animais para familia",
    "art": "museus de arte galerias arte para familia",
    "education": "atividades educativas para criancas",
    "food": "comida local restaurantes familiares doces famosos",
    "family": "lugares bons para ir com criancas",
    "history": "pontos historicos monumentos castelos centro historico",
    "museums": "museus pontos culturais para criancas",
    "parks": "parques jardins pracas atividades ao ar livre",
    "play": "atividades divertidas para criancas",
    "river": "passeio de barco rio waterfront familia",
    "science": "museus de ciencia e descobertas para criancas",
    "shopping": "lojas mercados compras familiares",
    "views": "mirantes vistas panoramicas observatorio",
}

DEFAULT_QUERIES = [
    ("icons", "principais pontos turisticos imperdiveis para familia"),
    ("parks", "parques jardins pracas para criancas"),
    ("museums", "museus atividades culturais para familia"),
]

GOOGLE_TYPE_CATEGORIES = {
    "amusement_park": "animals",
    "aquarium": "animals",
    "art_gallery": "art",
    "bakery": "food",
    "cafe": "food",
    "historical_landmark": "history",
    "library": "education",
    "market": "shopping",
    "museum": "museums",
    "park": "parks",
    "restaurant": "food",
    "shopping_mall": "shopping",
    "tourist_attraction": "icons",
    "zoo": "animals",
}

FOOD_PLACE_TYPES = {"bakery", "cafe", "restaurant"}
ADULT_OR_NIGHTLIFE_PLACE_TYPES = {
    "bar",
    "casino",
    "liquor_store",
    "night_club",
}

CATEGORY_DURATIONS = {
    "animals": 120,
    "art": 90,
    "education": 90,
    "family": 75,
    "food": 60,
    "history": 75,
    "icons": 75,
    "museums": 120,
    "parks": 75,
    "play": 90,
    "river": 90,
    "science": 120,
    "shopping": 90,
    "views": 60,
}


def discover_dynamic_itinerary(
    request: DynamicItineraryRequest,
    *,
    api_key: str | None,
    openai_api_key: str | None = None,
    client: httpx.Client | None = None,
    intent_responder=None,
) -> dict[str, Any]:
    if not api_key:
        raise RuntimeError("GOOGLE_MAPS_API_KEY nao configurada no backend.")

    owns_client = client is None
    http_client = client or httpx.Client(timeout=20)
    try:
        intent = parse_itinerary_intent(
            request.destination,
            api_key=openai_api_key,
            responder=intent_responder,
        )
        destination_query = intent.destination or request.destination
        resolved = _geocode_destination(http_client, api_key, destination_query)
        search_profiles = search_profiles_from_intent(intent, explicit_interests=request.interests)
        if not search_profiles:
            search_profiles = _search_profiles(request.interests)
        candidates = _discover_places(http_client, api_key, request, resolved, search_profiles)
        if not candidates:
            raise ValueError("Nao encontrei locais suficientes para montar o roteiro.")
        ranked = sorted(candidates.values(), key=lambda item: (-item["match_score"], item["name"]))
        target_count = min(len(ranked), request.days * PACE_STOP_LIMITS[request.pace])
        selected = _select_balanced_stops(ranked, target_count)
        selected_ids = {item["selection_id"] for item in selected}
        alternatives = [item for item in ranked if item["selection_id"] not in selected_ids][:8]
        _enrich_visible_stops_with_photos(http_client, api_key, [*selected, *alternatives])
        public_selected = [_public_stop(item) for item in selected]
        public_alternatives = [_public_stop(item) for item in alternatives]

        return {
            "summary": _summary(resolved, request.days),
            "recommendation_source": "google_places",
            "selected_landmarks": [item["selection_id"] for item in public_selected],
            "days": _build_days(public_selected, request.days, request.pace),
            "alternatives": public_alternatives,
            "resolved_destination": resolved,
        }
    finally:
        if owns_client:
            http_client.close()


def _geocode_destination(
    client: httpx.Client,
    api_key: str,
    destination: str,
) -> dict[str, Any]:
    response = client.get(
        GOOGLE_GEOCODE_URL,
        params={"address": destination, "key": api_key, "language": "pt-BR"},
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("status") != "OK" or not payload.get("results"):
        message = payload.get("error_message") or payload.get("status") or "destino nao encontrado"
        raise ValueError(f"Nao foi possivel localizar o destino: {message}")

    result = payload["results"][0]
    components = result.get("address_components", [])
    city = _component_value(
        components,
        ["locality", "postal_town", "administrative_area_level_2", "administrative_area_level_1"],
    )
    country = _component_value(components, ["country"])
    location = result["geometry"]["location"]
    display_name = city or result.get("formatted_address") or destination
    return {
        "id": f"google-{_slugify(display_name)}",
        "city": display_name,
        "country": country or "",
        "formatted_address": result.get("formatted_address", destination),
        "latitude": location["lat"],
        "longitude": location["lng"],
    }


def _discover_places(
    client: httpx.Client,
    api_key: str,
    request: DynamicItineraryRequest,
    resolved: dict[str, Any],
    search_profiles: list[tuple[str, str]],
) -> dict[str, dict[str, Any]]:
    candidates: dict[str, dict[str, Any]] = {}
    normalized_interests = _normalize_interests(request.interests)
    for profile_index, (profile_category, query) in enumerate(search_profiles):
        places = _search_places(client, api_key, resolved, query)
        profile_reason = _profile_reason(profile_category, query)
        for rank, place in enumerate(places, start=1):
            place_id = str(place.get("id") or "")
            if not place_id:
                continue
            if not _is_family_compatible_place(place, profile_category):
                continue
            candidate = _place_to_stop(
                place,
                resolved=resolved,
                query_category=profile_category,
                rank=rank,
                profile_index=profile_index,
                normalized_interests=normalized_interests,
                profile_reason=profile_reason,
            )
            existing = candidates.get(place_id)
            if not existing or candidate["match_score"] > existing["match_score"]:
                candidates[place_id] = candidate
    return candidates


def _is_family_compatible_place(place: dict[str, Any], query_category: str) -> bool:
    place_types = set(place.get("types", []))
    if place_types & ADULT_OR_NIGHTLIFE_PLACE_TYPES:
        return False
    if query_category != "food" and place_types & FOOD_PLACE_TYPES:
        return False
    return True


def _search_places(
    client: httpx.Client,
    api_key: str,
    resolved: dict[str, Any],
    query: str,
) -> list[dict[str, Any]]:
    body = {
        "textQuery": query,
        "languageCode": "pt-BR",
        "maxResultCount": 8,
        "locationBias": {
            "circle": {
                "center": {
                    "latitude": resolved["latitude"],
                    "longitude": resolved["longitude"],
                },
                "radius": 30000.0,
            }
        },
    }
    response = client.post(
        GOOGLE_TEXT_SEARCH_URL,
        headers={
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": TEXT_SEARCH_FIELD_MASK,
        },
        json=body,
    )
    response.raise_for_status()
    return response.json().get("places", [])


def resolve_landmark_locations(
    destinations: list[Destination],
    *,
    api_key: str | None,
    client: httpx.Client | None = None,
) -> dict[str, dict[str, Any]]:
    if not api_key or not destinations:
        return {}

    owns_client = client is None
    http_client = client or httpx.Client(timeout=20)
    try:
        resolved: dict[str, dict[str, Any]] = {}
        for destination in destinations:
            for landmark in destination.landmarks:
                selection_id = f"{destination.id}:{landmark.id}"
                place = _resolve_landmark_place(http_client, api_key, destination, landmark.name)
                if place:
                    resolved[selection_id] = _location_metadata(place)
        return resolved
    finally:
        if owns_client:
            http_client.close()


def _resolve_landmark_place(
    client: httpx.Client,
    api_key: str,
    destination: Destination,
    landmark_name: str,
) -> dict[str, Any] | None:
    for query in _landmark_location_queries(destination, landmark_name):
        places = _search_landmark_location(client, api_key, query)
        place = _best_landmark_place(places, landmark_name)
        if place:
            return place
    return None


def _landmark_location_queries(destination: Destination, landmark_name: str) -> list[str]:
    destination_terms = _destination_location_terms(destination)
    base_parts = [landmark_name, *destination_terms]
    base_query = " ".join(part.strip() for part in base_parts if part and part.strip())
    discovery_query = " ".join(
        part.strip()
        for part in [
            landmark_name,
            "ponto turistico",
            *destination_terms,
        ]
        if part and part.strip()
    )
    queries = [base_query, discovery_query]
    if not destination_terms:
        queries.append(landmark_name)
    return list(dict.fromkeys([query for query in queries if query]))


def _destination_location_terms(destination: Destination) -> list[str]:
    generic_terms = {"", "roteiro personalizado", "personalizado"}
    terms = []
    for value in [destination.city, destination.country]:
        normalized = _normalize_text(value)
        if normalized not in generic_terms:
            terms.append(value)
    return terms


def _search_landmark_location(
    client: httpx.Client,
    api_key: str,
    query: str,
) -> list[dict[str, Any]]:
    if not query:
        return []
    body = {
        "textQuery": query,
        "languageCode": "pt-BR",
        "maxResultCount": LOCATION_SEARCH_RESULT_LIMIT,
    }
    try:
        response = client.post(
            GOOGLE_TEXT_SEARCH_URL,
            headers={
                "X-Goog-Api-Key": api_key,
                "X-Goog-FieldMask": TEXT_SEARCH_FIELD_MASK,
            },
            json=body,
        )
        response.raise_for_status()
    except httpx.HTTPError:
        return []
    return response.json().get("places", [])


def _best_landmark_place(
    places: list[dict[str, Any]],
    landmark_name: str,
) -> dict[str, Any] | None:
    candidates = [place for place in places if _place_has_location(place)]
    if not candidates:
        return None
    normalized_requested = _normalize_text(landmark_name)
    requested_terms = {
        term
        for term in normalized_requested.split()
        if len(term) > 2
    }
    return max(
        candidates,
        key=lambda place: _place_name_score(place, normalized_requested, requested_terms),
    )


def _place_name_score(
    place: dict[str, Any],
    normalized_requested: str,
    requested_terms: set[str],
) -> float:
    candidate_name = str(place.get("displayName", {}).get("text") or "")
    normalized_candidate = _normalize_text(candidate_name)
    if normalized_requested and normalized_requested in normalized_candidate:
        return 2.0
    if normalized_candidate and normalized_candidate in normalized_requested:
        return 1.75
    if not requested_terms:
        return 0.0
    candidate_terms = set(normalized_candidate.split())
    return len(requested_terms & candidate_terms) / len(requested_terms)


def _place_has_location(place: dict[str, Any]) -> bool:
    location = place.get("location")
    if not isinstance(location, dict):
        return False
    return isinstance(location.get("latitude"), int | float) and isinstance(
        location.get("longitude"),
        int | float,
    )


def _location_metadata(place: dict[str, Any]) -> dict[str, Any]:
    location = place["location"]
    return {
        "place_id": str(place.get("id") or ""),
        "google_maps_uri": str(place.get("googleMapsUri") or ""),
        "formatted_address": str(place.get("formattedAddress") or ""),
        "latitude": location.get("latitude"),
        "longitude": location.get("longitude"),
        "location_status": "resolved",
    }


def _place_to_stop(
    place: dict[str, Any],
    *,
    resolved: dict[str, Any],
    query_category: str,
    rank: int,
    profile_index: int,
    normalized_interests: set[str],
    profile_reason: str | None,
) -> dict[str, Any]:
    place_id = str(place["id"])
    name = str(place.get("displayName", {}).get("text") or "Local sugerido")
    categories = _place_categories(place, query_category)
    score = max(0, 120 - (profile_index * 10) - rank)
    reasons: list[str] = []

    if profile_reason:
        score += 500 if query_category == "must_see" else 140
        reasons.append(profile_reason)

    matching_categories = [category for category in categories if category in normalized_interests]
    for category in matching_categories:
        score += 80
        reasons.append(f"Interesse da familia: {INTEREST_LABELS.get(category, category)}.")

    rating = place.get("rating")
    if isinstance(rating, int | float):
        score += int(max(0, rating - 4.0) * 20)
        if rating >= 4.5:
            reasons.append("Bem avaliado por viajantes.")

    rating_count = place.get("userRatingCount")
    if isinstance(rating_count, int) and rating_count > 0:
        score += min(30, int(math.log10(rating_count + 1) * 8))
        if rating_count >= 1000:
            reasons.append("Local popular no destino.")

    if not reasons:
        reasons.append("Boa opcao para apresentar a cidade as criancas.")

    primary_category = categories[0] if categories else "icons"
    photo = _first_place_photo(place)
    location = place.get("location") if isinstance(place.get("location"), dict) else {}
    return {
        "selection_id": f"google:{place_id}",
        "destination_id": resolved["id"],
        "landmark_id": _slugify(name),
        "name": name,
        "city": resolved["city"],
        "country": resolved["country"],
        "description": [_description_for(name, primary_category, resolved["city"])],
        "image": None,
        "categories": categories,
        "duration_minutes": CATEGORY_DURATIONS.get(primary_category, 75),
        "family_tip": _family_tip(primary_category),
        "source_type": "mentioned" if query_category == "must_see" else "suggested",
        "match_score": score,
        "match_reasons": list(dict.fromkeys(reasons))[:3],
        "editable": True,
        "google_maps_uri": place.get("googleMapsUri"),
        "formatted_address": place.get("formattedAddress"),
        "latitude": location.get("latitude"),
        "longitude": location.get("longitude"),
        "image_attributions": _photo_attributions(photo),
        "_photo_name": photo.get("name") if photo else "",
        "_search_profile_index": profile_index,
    }


def _first_place_photo(place: dict[str, Any]) -> dict[str, Any]:
    photos = place.get("photos")
    if not isinstance(photos, list) or not photos:
        return {}
    first = photos[0]
    return first if isinstance(first, dict) else {}


def _photo_attributions(photo: dict[str, Any]) -> list[dict[str, str]]:
    attributions = photo.get("authorAttributions") if photo else []
    if not isinstance(attributions, list):
        return []
    normalized: list[dict[str, str]] = []
    for attribution in attributions:
        if not isinstance(attribution, dict):
            continue
        display_name = str(attribution.get("displayName") or "").strip()
        uri = str(attribution.get("uri") or "").strip()
        if display_name or uri:
            normalized.append({"display_name": display_name, "uri": uri})
    return normalized


def _enrich_visible_stops_with_photos(
    client: httpx.Client,
    api_key: str,
    stops: list[dict[str, Any]],
) -> None:
    photo_uri_cache: dict[str, str | None] = {}
    for stop in stops:
        photo_name = str(stop.get("_photo_name") or "")
        if not photo_name:
            continue
        if photo_name not in photo_uri_cache:
            photo_uri_cache[photo_name] = _fetch_place_photo_uri(client, api_key, photo_name)
        photo_uri = photo_uri_cache[photo_name]
        if photo_uri:
            stop["image"] = photo_uri


def _fetch_place_photo_uri(
    client: httpx.Client,
    api_key: str,
    photo_name: str,
) -> str | None:
    response = client.get(
        f"{GOOGLE_PLACES_BASE_URL}/{photo_name}/media",
        headers={"X-Goog-Api-Key": api_key},
        params={"maxWidthPx": 900, "skipHttpRedirect": "true"},
    )
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError:
        return None
    payload = response.json()
    photo_uri = payload.get("photoUri")
    return str(photo_uri) if photo_uri else None


def _select_balanced_stops(
    ranked: list[dict[str, Any]],
    target_count: int,
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    selected_ids: set[str] = set()
    profile_indexes = sorted(
        {
            item["_search_profile_index"]
            for item in ranked
            if isinstance(item.get("_search_profile_index"), int)
        }
    )

    for profile_index in profile_indexes:
        if len(selected) >= target_count:
            break
        profile_candidates = [
            item
            for item in ranked
            if item.get("_search_profile_index") == profile_index
            and item["selection_id"] not in selected_ids
        ]
        if not profile_candidates:
            continue
        selected.append(profile_candidates[0])
        selected_ids.add(profile_candidates[0]["selection_id"])

    for item in ranked:
        if len(selected) >= target_count:
            break
        if item["selection_id"] in selected_ids:
            continue
        selected.append(item)
        selected_ids.add(item["selection_id"])

    return selected


def _public_stop(stop: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in stop.items() if not key.startswith("_")}


def _place_categories(place: dict[str, Any], query_category: str) -> list[str]:
    categories = [
        GOOGLE_TYPE_CATEGORIES[place_type]
        for place_type in place.get("types", [])
        if place_type in GOOGLE_TYPE_CATEGORIES
    ]
    if query_category != "must_see" and query_category not in categories:
        categories.append(query_category)
    return list(dict.fromkeys(categories))


def _profile_reason(category: str, query: str) -> str | None:
    normalized_query = _normalize_text(query)
    if category == "must_see":
        return "Ponto obrigatorio informado pela familia."
    if category == "food" and any(
        token in normalized_query
        for token in ["almoco", "almocar", "jantar", "restaurante", "comer", "refeicao"]
    ):
        return "Pedido da familia: refeicao com criancas."
    if any(token in normalized_query for token in ["aprender", "educativo", "educativa"]):
        return "Pedido da familia: educativo para criancas."
    if "crianca" in normalized_query or "filho" in normalized_query:
        return "Pedido da familia: bom para criancas."
    return None


def _search_profiles(interests: Iterable[str]) -> list[tuple[str, str]]:
    normalized = _normalize_interests(interests)
    profiles = [
        (interest, INTEREST_QUERIES[interest])
        for interest in normalized
        if interest in INTEREST_QUERIES
    ]
    if not profiles:
        return DEFAULT_QUERIES
    for profile in DEFAULT_QUERIES:
        if profile[0] not in {item[0] for item in profiles}:
            profiles.append(profile)
    return profiles[:4]


def _normalize_interests(interests: Iterable[str]) -> set[str]:
    normalized: set[str] = set()
    for interest in interests:
        key = _normalize_text(interest)
        normalized.add(INTEREST_ALIASES.get(key, key))
    return normalized


def _build_days(
    selected: list[dict[str, Any]],
    days: int,
    pace: str,
) -> list[dict[str, Any]]:
    capacity = max(PACE_STOP_LIMITS[pace], math.ceil(len(selected) / days))
    itinerary_days: list[dict[str, Any]] = []
    for day_number in range(1, days + 1):
        start = (day_number - 1) * capacity
        day_stops = selected[start : start + capacity]
        itinerary_days.append(
            {
                "day": day_number,
                "title": _day_title(day_number, day_stops),
                "theme": _day_theme(day_stops),
                "destination_ids": list(
                    dict.fromkeys(stop["destination_id"] for stop in day_stops)
                ),
                "stops": day_stops,
                "family_prompt": _family_prompt(day_stops),
            }
        )
    return itinerary_days


def _day_title(day_number: int, stops: list[dict[str, Any]]) -> str:
    cities = list(dict.fromkeys(stop["city"] for stop in stops))
    if len(cities) == 1:
        return f"Dia {day_number} em {cities[0]}"
    if cities:
        return f"Dia {day_number}: {' + '.join(cities)}"
    return f"Dia {day_number}: roteiro em familia"


def _day_theme(stops: list[dict[str, Any]]) -> str:
    categories = {category for stop in stops for category in stop["categories"]}
    if "parks" in categories or "river" in categories:
        return "Passeios com respiros para observar e brincar."
    if "museums" in categories or "art" in categories:
        return "Arte, historias e descobertas em ritmo de crianca."
    if "food" in categories:
        return "Sabores locais e lembrancas gostosas da viagem."
    return "Pontos especiais para reconhecer a cidade."


def _family_prompt(stops: list[dict[str, Any]]) -> str:
    if not stops:
        return "Use este dia para descansar, revisar o mapa ou registrar lembrancas."
    names = ", ".join(stop["name"] for stop in stops[:2])
    return f"Antes de sair, pergunte as criancas o que elas esperam encontrar em {names}."


def _summary(resolved: dict[str, Any], days: int) -> str:
    day_label = "dia" if days == 1 else "dias"
    return f"Roteiro sugerido para {resolved['city']} em {days} {day_label}."


def _description_for(name: str, category: str, city: str) -> str:
    if category == "food":
        return f"{name} entra no roteiro como uma parada para provar sabores locais em {city}."
    if category == "parks":
        return f"{name} e uma pausa ao ar livre para observar, brincar e respirar durante a viagem."
    if category in {"museums", "art"}:
        return (
            f"{name} ajuda a transformar cultura e arte em uma descoberta visual "
            "para as criancas."
        )
    if category == "history":
        return f"{name} conecta a familia com historias importantes do destino."
    return f"{name} e uma sugestao dinamica para explorar {city} em familia."


def _family_tip(category: str) -> str:
    if category == "food":
        return "Convide as criancas a escolherem um sabor novo para experimentar."
    if category == "parks":
        return "Separe alguns minutos para uma brincadeira curta ou desenho do lugar."
    if category in {"museums", "art"}:
        return "Escolha uma obra ou detalhe favorito antes de sair."
    if category == "history":
        return "Conte uma historia curta e peça para as criancas imaginarem a cena."
    if category == "views":
        return "Procurem juntos tres formas ou cores que aparecam na paisagem."
    return "Marque no livrinho quando visitar e registre uma lembranca."


def _component_value(components: list[dict[str, Any]], type_names: list[str]) -> str | None:
    for type_name in type_names:
        for component in components:
            if type_name in component.get("types", []):
                return str(component.get("long_name", "")).strip() or None
    return None


def _normalize_text(value: str) -> str:
    ascii_value = unicodedata.normalize("NFKD", value)
    ascii_value = "".join(
        character for character in ascii_value if not unicodedata.combining(character)
    )
    return " ".join(ascii_value.strip().casefold().split())


def _slugify(value: str) -> str:
    return "-".join(_normalize_text(value).split()) or "destino"
