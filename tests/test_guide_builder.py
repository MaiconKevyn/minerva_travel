from pathlib import Path

from minerva_travel.catalog import load_catalog
from minerva_travel.guide_builder import build_guide_context
from minerva_travel.models import GuideRequest
from minerva_travel.wikimedia_assets import WikimediaAsset


def test_build_guide_context_keeps_only_selected_landmarks():
    catalog = load_catalog(Path("data/destinations/europe_2026.json"))
    request = GuideRequest(
        title="Pequenos Exploradores pela Europa",
        children_names=["Alice", "Antonio"],
        parents_names=["Ana", "Otavio"],
        year=2026,
        selected_landmarks=["paris:eiffel-tower", "london:big-ben", "lisbon:oceanario"],
    )

    context = build_guide_context(request, catalog, Path("runtime/generated/cover.png"))

    assert [item.destination.id for item in context.destinations] == ["paris", "london", "lisbon"]
    assert [item.landmarks[0].id for item in context.destinations] == [
        "eiffel-tower",
        "big-ben",
        "oceanario",
    ]


def test_build_guide_context_preserves_catalog_order_inside_destination():
    catalog = load_catalog(Path("data/destinations/europe_2026.json"))
    request = GuideRequest(
        title="Pequenos Exploradores pela Europa",
        children_names=["Alice"],
        parents_names=["Ana"],
        year=2026,
        selected_landmarks=["paris:louvre", "paris:eiffel-tower"],
    )

    context = build_guide_context(request, catalog, Path("runtime/generated/cover.png"))

    assert [landmark.id for landmark in context.destinations[0].landmarks] == [
        "eiffel-tower",
        "louvre",
    ]


def test_build_guide_context_uses_wikimedia_images_and_credits():
    catalog = load_catalog(Path("data/destinations/europe_2026.json"))
    request = GuideRequest(
        title="Pequenos Exploradores pela Europa",
        children_names=["Alice"],
        parents_names=["Ana"],
        year=2026,
        selected_landmarks=["paris:eiffel-tower"],
    )
    assets = {
        "paris:eiffel-tower": WikimediaAsset(
            selection_id="paris:eiffel-tower",
            title="File:Eiffel Tower.jpg",
            source_url="https://commons.wikimedia.org/wiki/File:Eiffel_Tower.jpg",
            image_url="https://upload.wikimedia.org/example.jpg",
            local_path=Path("runtime/wikimedia/paris/eiffel-tower.jpg"),
            author="Jane Doe",
            license_short_name="CC BY-SA 4.0",
            license_url="https://creativecommons.org/licenses/by-sa/4.0/",
            credit="Jane Doe / Wikimedia Commons",
        )
    }

    context = build_guide_context(
        request,
        catalog,
        Path("runtime/generated/cover.png"),
        wikimedia_assets=assets,
    )

    assert context.destinations[0].landmarks[0].image == Path(
        "runtime/wikimedia/paris/eiffel-tower.jpg"
    )
    assert context.image_credits[0].landmark_name == "Torre Eiffel"
