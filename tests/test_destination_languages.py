from pathlib import Path

from minerva_travel.catalog import load_catalog
from minerva_travel.destination_languages import lookup_destination_language
from minerva_travel.models import Destination, Landmark


def test_lookup_destination_language_uses_known_destination_metadata():
    catalog = load_catalog(Path("data/destinations/europe_2026.json"))

    language = lookup_destination_language(catalog.find_destination("paris"))

    assert language is not None
    assert language.name == "francês"
    assert [tip.phrase for tip in language.tips[:2]] == ["Bonjour", "Merci"]


def test_lookup_destination_language_uses_curated_mapping_when_catalog_has_no_tips():
    destination = Destination(
        id="custom-rome",
        country="Italia",
        city="Roma",
        display_title="Italia - Roma",
        intro=["Roteiro personalizado."],
        favorites_prompt="Meu lugar favorito em Roma foi...",
        coloring_title="Desenhos para colorir",
        coloring_subtitle="Para colorir e desenhar",
        landmarks=[_sample_landmark()],
    )

    language = lookup_destination_language(destination)

    assert language is not None
    assert language.name == "italiano"
    assert language.tips[0].phrase == "Ciao"


def test_lookup_destination_language_omits_unknown_or_family_language_destinations():
    unknown = Destination(
        id="custom-atlantida",
        country="Atlantida",
        city="Cidade Misteriosa",
        display_title="Atlantida - Cidade Misteriosa",
        intro=["Roteiro personalizado."],
        favorites_prompt="Meu lugar favorito foi...",
        coloring_title="Desenhos para colorir",
        coloring_subtitle="Para colorir e desenhar",
        landmarks=[_sample_landmark()],
    )
    brazil = Destination(
        id="custom-rio",
        country="Brasil",
        city="Rio de Janeiro",
        display_title="Brasil - Rio de Janeiro",
        intro=["Roteiro personalizado."],
        favorites_prompt="Meu lugar favorito no Rio foi...",
        coloring_title="Desenhos para colorir",
        coloring_subtitle="Para colorir e desenhar",
        landmarks=[_sample_landmark()],
    )

    assert lookup_destination_language(unknown) is None
    assert lookup_destination_language(brazil) is None


def _sample_landmark() -> Landmark:
    return Landmark(
        id="sample",
        name="Lugar Especial",
        description=["Um lugar para observar."],
        image=Path("assets/landmarks/sample.png"),
        lineart_image=Path("assets/lineart/sample.png"),
        sort_order=1,
    )
