import pytest

from minerva_travel.catalog import load_catalog
from minerva_travel.itinerary_intent import ItineraryIntent
from minerva_travel.itinerary_routes import suggest_itinerary_routes
from minerva_travel.models import RouteSuggestionRequest


def test_route_suggestion_uses_natural_language_destinations_outside_catalog():
    response = suggest_itinerary_routes(
        RouteSuggestionRequest(
            trip_idea="Queremos Rio de Janeiro e Búzios com praia e ritmo leve.",
            days=5,
        ),
        load_catalog(),
        intent_parser=lambda _: ItineraryIntent(
            destination="Rio de Janeiro, Brasil",
            destinations=["Rio de Janeiro, Brasil", "Búzios, Brasil"],
        ),
    )

    destinations = response.options[0].structured_destinations
    assert [item.place for item in destinations] == [
        "Rio de Janeiro, Brasil",
        "Búzios, Brasil",
    ]
    assert [item.days for item in destinations] == [3, 2]


def test_route_suggestion_rejects_a_sentence_when_no_destination_was_identified():
    with pytest.raises(ValueError, match="Inclua pelo menos uma cidade"):
        suggest_itinerary_routes(
            RouteSuggestionRequest(trip_idea="Queremos uma viagem divertida.", days=3),
            load_catalog(),
            intent_parser=lambda message: ItineraryIntent(destination=message),
        )
