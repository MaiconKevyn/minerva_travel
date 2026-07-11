import unicodedata
from collections.abc import Iterable
from math import ceil
from pathlib import Path

from minerva_travel.models import (
    Catalog,
    Destination,
    ItineraryDay,
    ItineraryRecommendation,
    ItineraryRecommendationRequest,
    ItineraryStop,
    Landmark,
)

PACE_STOP_LIMITS = {
    "light": 2,
    "balanced": 3,
    "full": 4,
}

INTEREST_ALIASES = {
    "animais": "animals",
    "animal": "animals",
    "aquario": "animals",
    "aquarium": "animals",
    "arquitetura": "architecture",
    "architecture": "architecture",
    "arte": "art",
    "art": "art",
    "barco": "river",
    "boat": "river",
    "castelos": "history",
    "castelo": "history",
    "cidade": "city-symbols",
    "comida": "food",
    "doces": "food",
    "food": "food",
    "historia": "history",
    "history": "history",
    "icones": "icons",
    "icons": "icons",
    "lojas": "shopping",
    "lojas locais": "local_stores",
    "compras": "shopping",
    "shopping": "shopping",
    "mercados": "local_stores",
    "museu": "museums",
    "museus": "museums",
    "museum": "museums",
    "museums": "museums",
    "parque": "parks",
    "parques": "parks",
    "praca": "squares",
    "pracas": "squares",
    "parks": "parks",
    "rio": "river",
    "river": "river",
    "teatro": "theaters",
    "teatros": "theaters",
    "ar livre": "outdoor",
    "outdoor": "outdoor",
    "vistas": "views",
    "views": "views",
}

INTEREST_LABELS = {
    "animals": "animais",
    "architecture": "arquitetura",
    "art": "arte",
    "city-symbols": "simbolos da cidade",
    "food": "comida",
    "history": "historia",
    "icons": "icones",
    "local_stores": "lojas locais",
    "museums": "museus",
    "outdoor": "ao ar livre",
    "parks": "parques",
    "river": "rio e passeios",
    "shopping": "lojas",
    "squares": "pracas",
    "theaters": "teatros",
    "views": "vistas",
}

YOUNG_CHILD_CATEGORIES = {"animals", "food", "parks", "river", "slow-walk", "views"}


def recommend_itinerary(
    catalog: Catalog,
    request: ItineraryRecommendationRequest,
) -> ItineraryRecommendation:
    destinations = _find_destinations(catalog, request.destination_ids)
    destination_ids = {destination.id for destination in destinations}
    must_see = _validate_must_see(catalog, request.must_see_landmarks, destination_ids)
    interests = _normalize_interests(request.interests)
    cards = [
        _build_stop(destination, landmark, interests, request.children_ages, must_see)
        for destination in destinations
        for landmark in destination.landmarks
    ]
    ranked_cards = sorted(
        cards,
        key=lambda card: (
            card.selection_id not in must_see,
            -card.match_score,
            request.destination_ids.index(card.destination_id),
            card.name,
        ),
    )
    target_count = min(
        len(ranked_cards),
        max(len(must_see), request.days * PACE_STOP_LIMITS[request.pace]),
    )
    selected = ranked_cards[:target_count]
    selected_ids = {card.selection_id for card in selected}
    alternatives = [card for card in ranked_cards if card.selection_id not in selected_ids][:8]

    return ItineraryRecommendation(
        summary=_summary(destinations, request.days),
        selected_landmarks=[card.selection_id for card in selected],
        days=_build_days(selected, request.days, request.pace),
        alternatives=alternatives,
    )


def _find_destinations(catalog: Catalog, destination_ids: Iterable[str]) -> list[Destination]:
    destinations: list[Destination] = []
    for destination_id in destination_ids:
        try:
            destinations.append(catalog.find_destination(destination_id))
        except KeyError as error:
            raise ValueError(f"Destino desconhecido: {destination_id}") from error
    return destinations


def _validate_must_see(
    catalog: Catalog,
    must_see_landmarks: Iterable[str],
    destination_ids: set[str],
) -> set[str]:
    valid: set[str] = set()
    for selection_id in must_see_landmarks:
        try:
            destination_id, landmark_id = selection_id.split(":", maxsplit=1)
        except ValueError as error:
            raise ValueError(f"Ponto turistico invalido: {selection_id}") from error
        if destination_id not in destination_ids:
            raise ValueError(f"Ponto turistico fora dos destinos selecionados: {selection_id}")
        try:
            catalog.find_landmark(destination_id, landmark_id)
        except KeyError as error:
            raise ValueError(f"Ponto turistico desconhecido: {selection_id}") from error
        valid.add(selection_id)
    return valid


def _build_stop(
    destination: Destination,
    landmark: Landmark,
    interests: set[str],
    children_ages: list[int],
    must_see: set[str],
) -> ItineraryStop:
    selection_id = f"{destination.id}:{landmark.id}"
    score = max(0, 120 - landmark.sort_order)
    reasons: list[str] = []

    if selection_id in must_see:
        score += 500
        reasons.append("Ponto obrigatorio informado pela familia.")

    matching_categories = [category for category in landmark.categories if category in interests]
    for category in matching_categories:
        score += 80
        reasons.append(f"Interesse da familia: {INTEREST_LABELS.get(category, category)}.")

    if children_ages and min(children_ages) <= 7:
        if any(category in YOUNG_CHILD_CATEGORIES for category in landmark.categories):
            score += 20
            reasons.append("Boa opcao para criancas menores.")

    if not reasons:
        reasons.append("Bom ponto para apresentar a cidade as criancas.")

    return ItineraryStop(
        selection_id=selection_id,
        destination_id=destination.id,
        landmark_id=landmark.id,
        name=landmark.name,
        city=destination.city,
        country=destination.country,
        description=landmark.description,
        image=Path(landmark.image),
        category=landmark.categories[0] if landmark.categories else None,
        categories=landmark.categories,
        duration_minutes=landmark.duration_minutes,
        family_tip=landmark.family_tip,
        match_score=score,
        match_reasons=reasons,
    )


def _normalize_interests(interests: Iterable[str]) -> set[str]:
    normalized: set[str] = set()
    for interest in interests:
        key = _normalize_text(interest)
        normalized.add(INTEREST_ALIASES.get(key, key))
    return normalized


def _normalize_text(value: str) -> str:
    ascii_value = unicodedata.normalize("NFKD", value)
    ascii_value = "".join(
        character for character in ascii_value if not unicodedata.combining(character)
    )
    return " ".join(ascii_value.strip().casefold().split())


def _build_days(
    selected: list[ItineraryStop],
    days: int,
    pace: str,
) -> list[ItineraryDay]:
    capacity = max(PACE_STOP_LIMITS[pace], ceil(len(selected) / days))
    itinerary_days: list[ItineraryDay] = []
    for day_number in range(1, days + 1):
        start = (day_number - 1) * capacity
        day_stops = selected[start : start + capacity]
        itinerary_days.append(
            ItineraryDay(
                day=day_number,
                title=_day_title(day_number, day_stops),
                theme=_day_theme(day_stops),
                destination_ids=list(dict.fromkeys(stop.destination_id for stop in day_stops)),
                stops=day_stops,
                family_prompt=_family_prompt(day_stops),
            )
        )
    return itinerary_days


def _day_title(day_number: int, stops: list[ItineraryStop]) -> str:
    cities = list(dict.fromkeys(stop.city for stop in stops))
    if len(cities) == 1:
        return f"Dia {day_number} em {cities[0]}"
    if cities:
        return f"Dia {day_number}: {' + '.join(cities)}"
    return f"Dia {day_number}: roteiro em familia"


def _day_theme(stops: list[ItineraryStop]) -> str:
    categories = {category for stop in stops for category in stop.categories}
    if "parks" in categories or "river" in categories:
        return "Passeios com respiros para observar e brincar."
    if "museums" in categories or "art" in categories:
        return "Arte, historias e descobertas em ritmo de crianca."
    if "food" in categories:
        return "Sabores locais e lembrancas gostosas da viagem."
    return "Pontos especiais para reconhecer a cidade."


def _family_prompt(stops: list[ItineraryStop]) -> str:
    if not stops:
        return "Use este dia para descansar, revisar o mapa ou registrar lembrancas."
    names = ", ".join(stop.name for stop in stops[:2])
    return f"Antes de sair, pergunte as criancas o que elas esperam encontrar em {names}."


def _summary(destinations: list[Destination], days: int) -> str:
    names = ", ".join(destination.city for destination in destinations)
    day_label = "dia" if days == 1 else "dias"
    return f"Roteiro sugerido para {names} em {days} {day_label}."
