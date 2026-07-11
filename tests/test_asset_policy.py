from pathlib import Path

import pytest

from minerva_travel.app import create_local_lineart_fallbacks
from minerva_travel.asset_policy import AssetProvenanceError, assert_selected_asset_provenance
from minerva_travel.catalog import load_catalog
from minerva_travel.wikimedia_assets import WikimediaAsset, load_wikimedia_manifest


def _asset(path: Path, **overrides: object) -> WikimediaAsset:
    values: dict[str, object] = {
        "selection_id": "paris:eiffel-tower",
        "title": "File:Eiffel Tower.jpg",
        "source_url": "https://commons.wikimedia.org/wiki/File:Eiffel_Tower.jpg",
        "image_url": "https://upload.wikimedia.org/eiffel-tower.jpg",
        "local_path": path,
        "author": "Jane Doe",
        "license_short_name": "CC BY-SA 4.0",
        "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
        "credit": "Jane Doe / Wikimedia Commons",
    }
    values.update(overrides)
    return WikimediaAsset.model_validate(values)


def test_production_asset_policy_requires_every_selected_attributed_local_asset(tmp_path):
    path = tmp_path / "eiffel.jpg"
    path.write_bytes(b"image")
    assets = {"paris:eiffel-tower": _asset(path)}

    assert_selected_asset_provenance(
        ["paris:eiffel-tower"],
        assets,
        required=True,
    )

    with pytest.raises(AssetProvenanceError) as missing:
        assert_selected_asset_provenance(
            ["paris:eiffel-tower", "london:big-ben"],
            assets,
            required=True,
        )

    assert missing.value.missing_selection_ids == ("london:big-ben",)


@pytest.mark.parametrize(
    "overrides",
    [
        {"license_url": ""},
        {"credit": ""},
        {"local_path": Path("/definitely/missing.jpg")},
    ],
)
def test_production_asset_policy_rejects_incomplete_or_missing_provenance(tmp_path, overrides):
    path = tmp_path / "eiffel.jpg"
    path.write_bytes(b"image")

    with pytest.raises(AssetProvenanceError):
        assert_selected_asset_provenance(
            ["paris:eiffel-tower"],
            {"paris:eiffel-tower": _asset(path, **overrides)},
            required=True,
        )


def test_development_asset_policy_allows_offline_fixture_mode():
    assert_selected_asset_provenance(
        ["paris:eiffel-tower"],
        {},
        required=False,
    )


def test_strict_lineart_generation_does_not_substitute_a_named_placeholder(tmp_path, monkeypatch):
    from minerva_travel import storage
    from minerva_travel.models import Destination, Landmark

    monkeypatch.setattr(storage, "RUNTIME_DIR", tmp_path / "runtime")
    destination = Destination(
        id="paris",
        country="França",
        city="Paris",
        display_title="FRANÇA - PARIS",
        intro=["Paris é uma cidade."],
        favorites_prompt="Favoritos",
        coloring_title="Colorir",
        coloring_subtitle="Colorir",
        landmarks=[
            Landmark(
                id="eiffel-tower",
                name="Torre Eiffel",
                description=["Uma torre."],
                image=Path("assets/landmarks/paris/eiffel-tower.png"),
                lineart_image=Path("assets/lineart/paris/eiffel-tower.png"),
                sort_order=1,
            )
        ],
    )

    result = create_local_lineart_fallbacks(
        [destination],
        ["paris:eiffel-tower"],
        "request-123",
        reference_images={"paris:eiffel-tower": tmp_path / "missing.jpg"},
        allow_named_placeholder=False,
    )

    assert result == {}


def test_versioned_wikimedia_manifest_covers_every_catalog_landmark():
    catalog = load_catalog()
    assets = load_wikimedia_manifest()
    selection_ids = [
        f"{destination.id}:{landmark.id}"
        for destination in catalog.destinations
        for landmark in destination.landmarks
    ]

    assert_selected_asset_provenance(selection_ids, assets, required=True)
