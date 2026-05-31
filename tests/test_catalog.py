from pathlib import Path

from minerva_travel.catalog import load_catalog


def test_catalog_loads_reference_itinerary():
    catalog = load_catalog(Path("data/destinations/europe_2026.json"))

    assert [destination.city for destination in catalog.destinations] == [
        "Paris",
        "Londres",
        "Cambridge",
        "Lisboa",
    ]
    assert catalog.find_landmark("paris", "eiffel-tower").name == "Torre Eiffel"
    assert catalog.find_landmark("lisbon", "pastel-de-belem").name == "Comer Pastel de Belem"
    assert "clock" in catalog.find_landmark("london", "big-ben").required_terms


def test_catalog_returns_destinations_with_sorted_landmarks():
    catalog = load_catalog(Path("data/destinations/europe_2026.json"))
    paris = catalog.find_destination("paris")

    assert [landmark.id for landmark in paris.landmarks[:3]] == [
        "eiffel-tower",
        "arc-de-triomphe",
        "champs-elysees",
    ]
