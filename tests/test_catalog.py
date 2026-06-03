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


def test_catalog_loads_language_tips_and_phase_activities():
    catalog = load_catalog(Path("data/destinations/europe_2026.json"))

    paris = catalog.find_destination("paris")
    london = catalog.find_destination("london")
    cambridge = catalog.find_destination("cambridge")
    lisbon = catalog.find_destination("lisbon")

    assert paris.language_name == "frances"
    assert [tip.phrase for tip in paris.language_tips] == [
        "Bonjour",
        "Merci",
        "S'il vous plait",
    ]
    assert paris.phase_activities.before == (
        "No aviao, encontre Paris no mapa e circule o lugar que voce esta mais "
        "curioso para visitar."
    )

    assert london.language_name == "ingles"
    assert [tip.phrase for tip in london.language_tips] == [
        "Hello",
        "Thank you",
        "Please",
        "Excuse me",
    ]
    assert london.phase_activities.during == (
        "Procure uma placa, um onibus vermelho ou um relogio grande e desenhe o "
        "detalhe que chamou sua atencao."
    )

    assert cambridge.language_name == "ingles"
    assert cambridge.phase_activities.after == (
        "Escreva ou desenhe uma coisa que voce aprendeu em Cambridge."
    )

    assert lisbon.language_name == "portugues de Portugal"
    assert [tip.phrase for tip in lisbon.language_tips] == [
        "Ola",
        "Bom dia",
        "Por favor",
        "Obrigado/obrigada",
        "Autocarro",
    ]
    assert lisbon.phase_activities.before == (
        "No caminho, procure no mapa onde o rio Tejo encontra a cidade."
    )


def test_catalog_loads_recommendation_metadata_for_landmarks():
    catalog = load_catalog(Path("data/destinations/europe_2026.json"))

    eiffel = catalog.find_landmark("paris", "eiffel-tower")
    louvre = catalog.find_landmark("paris", "louvre")
    luxembourg = catalog.find_landmark("paris", "luxembourg")
    oceanario = catalog.find_landmark("lisbon", "oceanario")

    assert eiffel.categories == ["icons", "views", "architecture"]
    assert eiffel.duration_minutes == 90
    assert eiffel.family_tip == "Bom para abrir a viagem com um simbolo que as criancas reconhecem."

    assert "museums" in louvre.categories
    assert "art" in louvre.categories
    assert "parks" in luxembourg.categories
    assert "animals" in oceanario.categories
