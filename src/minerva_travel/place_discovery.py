import math
import unicodedata
from collections.abc import Iterable
from typing import Any

import httpx

from minerva_travel.models import DynamicItineraryRequest

GOOGLE_GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"
GOOGLE_TEXT_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"

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
    "places.rating,"
    "places.userRatingCount,"
    "places.googleMapsUri"
)

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
    "food": "comida local restaurantes familiares doces famosos",
    "history": "pontos historicos monumentos castelos centro historico",
    "museums": "museus pontos culturais para criancas",
    "parks": "parques jardins pracas atividades ao ar livre",
    "river": "passeio de barco rio waterfront familia",
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
    "market": "shopping",
    "museum": "museums",
    "park": "parks",
    "restaurant": "food",
    "shopping_mall": "shopping",
    "tourist_attraction": "icons",
    "zoo": "animals",
}

CATEGORY_DURATIONS = {
    "animals": 120,
    "art": 90,
    "food": 60,
    "history": 75,
    "icons": 75,
    "museums": 120,
    "parks": 75,
    "river": 90,
    "shopping": 90,
    "views": 60,
}


def discover_dynamic_itinerary(
    request: DynamicItineraryRequest,
    *,
    api_key: str | None,
    client: httpx.Client | None = None,
) -> dict[str, Any]:
    if not api_key:
        raise RuntimeError("GOOGLE_MAPS_API_KEY nao configurada no backend.")

    owns_client = client is None
    http_client = client or httpx.Client(timeout=20)
    try:
        resolved = _geocode_destination(http_client, api_key, request.destination)
        search_profiles = _search_profiles(request.interests)
        candidates = _discover_places(http_client, api_key, request, resolved, search_profiles)
        if not candidates:
            raise ValueError("Nao encontrei locais suficientes para montar o roteiro.")
        ranked = sorted(candidates.values(), key=lambda item: (-item["match_score"], item["name"]))
        target_count = min(len(ranked), request.days * PACE_STOP_LIMITS[request.pace])
        selected = ranked[:target_count]
        selected_ids = {item["selection_id"] for item in selected}
        alternatives = [item for item in ranked if item["selection_id"] not in selected_ids][:8]

        return {
            "summary": _summary(resolved, request.days),
            "recommendation_source": "google_places",
            "selected_landmarks": [item["selection_id"] for item in selected],
            "days": _build_days(selected, request.days, request.pace),
            "alternatives": alternatives,
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
        places = _search_places(client, api_key, request, resolved, query)
        for rank, place in enumerate(places, start=1):
            place_id = str(place.get("id") or "")
            if not place_id:
                continue
            candidate = _place_to_stop(
                place,
                resolved=resolved,
                query_category=profile_category,
                rank=rank,
                profile_index=profile_index,
                normalized_interests=normalized_interests,
            )
            existing = candidates.get(place_id)
            if not existing or candidate["match_score"] > existing["match_score"]:
                candidates[place_id] = candidate
    return candidates


def _search_places(
    client: httpx.Client,
    api_key: str,
    request: DynamicItineraryRequest,
    resolved: dict[str, Any],
    query: str,
) -> list[dict[str, Any]]:
    body = {
        "textQuery": f"{query} em {request.destination}",
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


def _place_to_stop(
    place: dict[str, Any],
    *,
    resolved: dict[str, Any],
    query_category: str,
    rank: int,
    profile_index: int,
    normalized_interests: set[str],
) -> dict[str, Any]:
    place_id = str(place["id"])
    name = str(place.get("displayName", {}).get("text") or "Local sugerido")
    categories = _place_categories(place, query_category)
    score = max(0, 120 - (profile_index * 10) - rank)
    reasons: list[str] = []

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
        "match_score": score,
        "match_reasons": list(dict.fromkeys(reasons))[:3],
        "editable": True,
        "google_maps_uri": place.get("googleMapsUri"),
        "formatted_address": place.get("formattedAddress"),
    }


def _place_categories(place: dict[str, Any], query_category: str) -> list[str]:
    categories = [
        GOOGLE_TYPE_CATEGORIES[place_type]
        for place_type in place.get("types", [])
        if place_type in GOOGLE_TYPE_CATEGORIES
    ]
    if query_category not in categories:
        categories.append(query_category)
    return list(dict.fromkeys(categories))


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
