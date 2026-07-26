import pytest

from minerva_travel.child_phrasebook import (
    PHRASEBOOKS,
    PHRASES_PER_PAGE,
    country_has_phrasebook,
    phrasebook_for_country,
)


@pytest.mark.parametrize("language", sorted(PHRASEBOOKS))
def test_every_language_teaches_the_same_five_things(language):
    book = PHRASEBOOKS[language]

    assert len(book.phrases) == PHRASES_PER_PAGE
    for phrase in book.phrases:
        assert phrase.phrase and phrase.pronunciation and phrase.meaning
        # Pronúncia é para uma criança brasileira ler em voz alta, não IPA.
        assert not any(char in phrase.pronunciation for char in "ʃʒθðŋɪʊæɑɔə")


def test_countries_map_to_the_language_actually_spoken_there():
    assert phrasebook_for_country("França").language == "francês"
    assert phrasebook_for_country("Reino Unido").language == "inglês"
    assert phrasebook_for_country("Argentina").language == "espanhol"
    assert phrasebook_for_country("Japão").language == "japonês"


def test_lookup_ignores_accents_and_casing_from_google_places():
    assert phrasebook_for_country("franca") is phrasebook_for_country("FRANÇA")
    assert phrasebook_for_country(" Itália ") is not None


def test_brazil_and_unchecked_countries_get_no_phrasebook():
    # Sem idioma conferido, inventar pronúncia ensinaria errado.
    assert phrasebook_for_country("Brasil") is None
    assert phrasebook_for_country("Cazaquistão") is None
    assert not country_has_phrasebook("")
