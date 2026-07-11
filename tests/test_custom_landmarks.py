from minerva_travel.custom_landmarks import (
    build_custom_destinations,
    parse_custom_landmarks,
    required_terms,
)


def test_parse_custom_landmarks_from_text_lines():
    landmarks = parse_custom_landmarks("Colosseum, Rome, Italy\nTrevi Fountain, Rome, Italy")

    assert [landmark.name for landmark in landmarks] == ["Colosseum", "Trevi Fountain"]
    assert landmarks[0].city == "Rome"
    assert landmarks[0].country == "Italy"


def test_parse_custom_landmarks_from_json_keeps_child_friendly_description():
    landmarks = parse_custom_landmarks(
        '[{"name":"Cristo Redentor","city":"Rio de Janeiro","country":"Brasil",'
        '"description":["O Cristo Redentor fica no alto do Corcovado.",'
        '"Ele parece abracar a cidade inteira."]}]'
    )
    destinations, _selected = build_custom_destinations(landmarks)

    assert destinations[0].landmarks[0].description == [
        "O Cristo Redentor fica no alto do Corcovado.",
        "Ele parece abracar a cidade inteira.",
    ]


def test_build_custom_destinations_groups_by_city_and_creates_selection_ids():
    landmarks = parse_custom_landmarks(
        "Colosseum, Rome, Italy\nTrevi Fountain, Rome, Italy\nLouvre, Paris, France"
    )

    destinations, selected = build_custom_destinations(landmarks)

    assert [destination.city for destination in destinations] == ["Rome", "Paris"]
    assert selected == [
        "custom-rome:colosseum",
        "custom-rome:trevi-fountain",
        "custom-paris:louvre",
    ]
    assert destinations[0].landmarks[0].representative_query == (
        "Colosseum Rome Italy tourist attraction exterior"
    )


def test_build_custom_destinations_enriches_known_country_with_kid_facts():
    landmarks = parse_custom_landmarks("Torre Eiffel, Paris, França")

    destinations, _selected = build_custom_destinations(landmarks)

    paris = destinations[0]
    assert paris.country == "França"
    assert paris.display_title == "FRANÇA - PARIS"
    assert len(paris.curiosities) == 3
    assert any("Torre Eiffel" in curiosity for curiosity in paris.curiosities)
    assert "Cidade Luz" in " ".join(paris.intro)


def test_build_custom_destinations_never_exposes_personalizado_label():
    landmarks = parse_custom_landmarks("Portal do Sol, Atlântida")

    destinations, _selected = build_custom_destinations(landmarks)

    atlantida = destinations[0]
    assert atlantida.country == ""
    assert atlantida.display_title == "ATLÂNTIDA"
    assert atlantida.location_label == "Atlântida"
    assert atlantida.curiosities == []


def test_required_terms_ignores_common_words():
    assert required_terms("The Tower of London") == ["tower", "london"]
