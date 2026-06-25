from unicodedata import normalize

from minerva_travel.models import (
    Catalog,
    RouteSuggestionOption,
    RouteSuggestionRequest,
    RouteSuggestionResponse,
    StructuredDestinationInput,
)


def suggest_itinerary_routes(
    request: RouteSuggestionRequest,
    catalog: Catalog,
) -> RouteSuggestionResponse:
    destinations = _structured_destinations_from_request(request, catalog)
    if not destinations:
        destinations = [
            StructuredDestinationInput(
                id="suggested-1",
                place="Destino principal",
                timing="defina a data ou período",
                days=request.days,
            )
        ]

    interests = ", ".join(request.interests) if request.interests else "os interesses da família"
    summary = (
        f"Roteiro {request.pace} com foco em {interests}, pronto para editar antes das atrações."
    )
    return RouteSuggestionResponse(
        options=[
            RouteSuggestionOption(
                id="suggested-route-1",
                title="Sugestão equilibrada",
                summary=summary,
                structured_destinations=destinations,
            )
        ]
    )


def _structured_destinations_from_request(
    request: RouteSuggestionRequest,
    catalog: Catalog,
) -> list[StructuredDestinationInput]:
    if request.structured_destinations:
        places = [destination.place for destination in request.structured_destinations]
        return _editable_destinations_from_places(
            places=places,
            total_days=request.days,
            source_destinations=request.structured_destinations,
        )

    places = _mentioned_catalog_cities(request.trip_idea, catalog)
    return _editable_destinations_from_places(
        places=places,
        total_days=request.days,
    )


def _editable_destinations_from_places(
    places: list[str],
    total_days: int,
    source_destinations: list[StructuredDestinationInput] | None = None,
) -> list[StructuredDestinationInput]:
    source_destinations = source_destinations or []
    return [
        StructuredDestinationInput(
            id=f"suggested-{index + 1}",
            place=place,
            timing=_source_timing(source_destinations, index) or _default_timing(index, places),
            days=_source_days(source_destinations, index)
            or _allocated_days(total_days, len(places), index),
        )
        for index, place in enumerate(places)
    ]


def _mentioned_catalog_cities(trip_idea: str, catalog: Catalog) -> list[str]:
    normalized_text = _normalize_text(trip_idea)
    matches: list[str] = []
    for destination in catalog.destinations:
        city = destination.city.strip()
        if city and _normalize_text(city) in normalized_text and city not in matches:
            matches.append(city)
    return matches


def _allocated_days(total_days: int, destination_count: int, index: int) -> int:
    if destination_count <= 0:
        return max(total_days, 1)
    base = max(total_days // destination_count, 1)
    remainder = max(total_days % destination_count, 0)
    return base + (1 if index < remainder else 0)


def _source_timing(
    source_destinations: list[StructuredDestinationInput],
    index: int,
) -> str:
    if index >= len(source_destinations):
        return ""
    return source_destinations[index].timing


def _source_days(
    source_destinations: list[StructuredDestinationInput],
    index: int,
) -> int:
    if index >= len(source_destinations):
        return 0
    return source_destinations[index].days


def _default_timing(index: int, places: list[str]) -> str:
    if index == 0:
        return "defina a data ou período"
    previous = places[index - 1] if len(places) > index - 1 else places[index]
    return f"depois de {previous}"


def _normalize_text(value: str) -> str:
    return normalize("NFKD", value).encode("ascii", "ignore").decode("ascii").lower()
