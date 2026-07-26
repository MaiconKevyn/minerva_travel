"""As primeiras palavras do idioma, uma página por país, antes de pousar."""

from pathlib import Path

import pytest
from PIL import Image

from minerva_travel.activity_page_compositor import (
    PAGE_IMAGE_SIZE,
    ActivityPageCompositionError,
    compose_flight_vocabulary_page,
    flight_vocabulary_title,
)
from minerva_travel.app import _builder_page_plan
from minerva_travel.catalog import load_catalog
from minerva_travel.flight_vocabulary import (
    EVERYDAY_WORDS,
    EVERYDAY_WORDS_PER_PAGE,
    GENERAL_PLACE_WORDS,
    LANGUAGE_NAMES,
    PLACE_WORDS,
    WORDS_PER_PAGE,
    flight_vocabulary_for,
    landmark_category,
)


def _plan(selected: list[str], **form_extra):
    catalog = load_catalog()
    pages, _ = _builder_page_plan(
        {
            "title": "Família Lima",
            "year": 2026,
            "children_ages": [8],
            "activity_selections": [],
            **form_extra,
        },
        catalog.destinations,
        selected,
    )
    return pages


def test_the_page_teaches_the_places_the_family_will_actually_visit():
    vocabulary = flight_vocabulary_for("França", ["Torre Eiffel", "Museu do Louvre"])

    assert vocabulary is not None
    assert vocabulary.language == "francês"
    assert len(vocabulary.words) == WORDS_PER_PAGE
    meanings = [word.meaning for word in vocabulary.words]
    # Metade dia a dia, metade sobre o que a família vai ver de verdade.
    assert "A torre" in meanings
    assert "O museu" in meanings
    assert meanings[:EVERYDAY_WORDS_PER_PAGE] == [
        word.meaning for word in EVERYDAY_WORDS["frances"][:EVERYDAY_WORDS_PER_PAGE]
    ]


def test_the_order_of_the_stops_decides_the_order_of_the_words():
    first = flight_vocabulary_for("Japão", ["Templo Senso-ji", "Monte Fuji"])
    reversed_stops = flight_vocabulary_for("Japão", ["Monte Fuji", "Templo Senso-ji"])

    assert first is not None and reversed_stops is not None
    # A primeira coisa que a família vê é a primeira palavra que ela aprende.
    assert [word.meaning for word in first.words][4:6] == ["O templo", "A montanha"]
    assert [word.meaning for word in reversed_stops.words][4:6] == ["A montanha", "O templo"]


def test_a_name_that_hides_its_kind_falls_back_to_words_about_any_place():
    vocabulary = flight_vocabulary_for("Espanha", ["Machu Picchu"])

    assert vocabulary is not None
    assert landmark_category("Machu Picchu") == "montanha"
    # "Alhambra" não diz que é um palácio para quem lê o nome cru.
    assert landmark_category("Big Ben") == "torre"
    assert landmark_category("Parque das Aves") == "parque"
    assert landmark_category("Estação Central") is None

    generic = flight_vocabulary_for("Espanha", ["Estação Central"])
    assert generic is not None
    assert [word.meaning for word in generic.words][EVERYDAY_WORDS_PER_PAGE:] == [
        word.meaning for word in GENERAL_PLACE_WORDS["espanhol"]
    ]


def test_a_country_without_a_checked_language_has_no_page_instead_of_a_guess():
    assert flight_vocabulary_for("Brasil", ["Cristo Redentor"]) is None
    assert flight_vocabulary_for("", ["Qualquer lugar"]) is None

    pages = _plan(["paris:eiffel-tower"])
    assert any(page.kind == "flight_vocabulary" for page in pages)


@pytest.mark.parametrize("language", sorted(EVERYDAY_WORDS))
def test_every_curated_language_can_fill_a_whole_page(language):
    # Um idioma com poucas palavras gerais deixaria a página incompleta e o
    # compositor recusaria a página inteira na hora de gerar.
    assert len(EVERYDAY_WORDS[language]) >= EVERYDAY_WORDS_PER_PAGE
    assert len(GENERAL_PLACE_WORDS[language]) >= WORDS_PER_PAGE - EVERYDAY_WORDS_PER_PAGE
    assert language in LANGUAGE_NAMES
    # Toda categoria reconhecida precisa existir em todos os idiomas: uma falta
    # faria a criança receber palavra genérica no lugar do lugar que vai ver.
    assert set(PLACE_WORDS[language]) == set(PLACE_WORDS["frances"])
    for word in (*EVERYDAY_WORDS[language], *GENERAL_PLACE_WORDS[language]):
        assert word.word and word.pronunciation and word.meaning


def test_one_page_per_country_and_it_comes_before_that_country():
    pages = _plan(["paris:eiffel-tower", "paris:louvre", "london:tower-bridge"])
    kinds = [page.kind for page in pages]

    vocabulary_positions = [i for i, kind in enumerate(kinds) if kind == "flight_vocabulary"]
    assert len(vocabulary_positions) == 2
    # Paris e o Louvre são o mesmo país: uma página só, e antes do destino.
    for index in vocabulary_positions:
        assert kinds[index + 1] == "destination_intro"

    vocabulary_pages = [page for page in pages if page.kind == "flight_vocabulary"]
    assert [page.metadata["country"] for page in vocabulary_pages] == ["França", "Inglaterra"]
    assert vocabulary_pages[0].metadata["landmark_names"] == [
        "Torre Eiffel",
        "Museu do Louvre",
    ]


def test_the_page_is_on_by_default_and_can_be_switched_off():
    assert any(page.kind == "flight_vocabulary" for page in _plan(["paris:eiffel-tower"]))
    assert any(
        page.kind == "flight_vocabulary"
        for page in _plan(["paris:eiffel-tower"], flight_vocabulary_pages=True)
    )
    assert not any(
        page.kind == "flight_vocabulary"
        for page in _plan(["paris:eiffel-tower"], flight_vocabulary_pages=False)
    )


def test_the_printed_contract_lists_every_word_and_its_meaning():
    page = next(page for page in _plan(["paris:eiffel-tower"]) if page.kind == "flight_vocabulary")
    vocabulary = flight_vocabulary_for("França", ["Torre Eiffel"])

    assert vocabulary is not None
    assert flight_vocabulary_title("francês") in page.required_copy
    assert "França" in page.required_copy
    for word in vocabulary.words:
        assert word.word in page.required_copy
        assert word.meaning in page.required_copy


def test_the_landmark_page_does_not_promise_the_phrasebook_heading():
    """ "Sobrevivência no idioma" estava no contrato de toda página de ponto.

    A lista "Confira na imagem" mandava o usuário procurar um texto que nunca
    é impresso ali, em todo ponto turístico de todo guia.
    """
    from minerva_travel.activity_page_compositor import LANGUAGE_TITLE

    landmark_pages = [page for page in _plan(["paris:eiffel-tower"]) if page.kind == "landmark"]

    assert landmark_pages
    for page in landmark_pages:
        assert LANGUAGE_TITLE not in page.required_copy


def test_composer_refuses_an_incomplete_word_list(tmp_path: Path):
    from dataclasses import replace

    artwork = tmp_path / "art.png"
    Image.new("RGB", PAGE_IMAGE_SIZE, "#f6efdd").save(artwork)
    vocabulary = flight_vocabulary_for("França", ["Torre Eiffel"])
    assert vocabulary is not None

    # Uma página com metade das palavras sai da gráfica com espaço vazio.
    with pytest.raises(ActivityPageCompositionError):
        compose_flight_vocabulary_page(
            artwork,
            tmp_path / "page.png",
            vocabulary=replace(vocabulary, words=vocabulary.words[:3]),
            instruction="Treine no avião.",
        )


def test_composer_prints_a_full_page(tmp_path: Path):
    artwork = tmp_path / "art.png"
    Image.new("RGB", PAGE_IMAGE_SIZE, "#f6efdd").save(artwork)
    vocabulary = flight_vocabulary_for("Itália", ["Coliseu", "Torre de Pisa"])
    assert vocabulary is not None

    output = compose_flight_vocabulary_page(
        artwork,
        tmp_path / "page.png",
        vocabulary=vocabulary,
        instruction="Treine no avião e marque cada palavra que você conseguir falar.",
    )

    with Image.open(output) as page:
        assert page.size == PAGE_IMAGE_SIZE
