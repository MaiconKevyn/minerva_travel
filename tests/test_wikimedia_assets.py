import json
from pathlib import Path

from minerva_travel.wikimedia_assets import load_wikimedia_manifest


def test_load_wikimedia_manifest_maps_assets_by_selection_id(tmp_path):
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "assets": [
                    {
                        "selection_id": "paris:eiffel-tower",
                        "title": "File:Eiffel Tower.jpg",
                        "source_url": "https://commons.wikimedia.org/wiki/File:Eiffel_Tower.jpg",
                        "image_url": "https://upload.wikimedia.org/example.jpg",
                        "local_path": "runtime/wikimedia/paris/eiffel-tower.jpg",
                        "author": "Jane Doe",
                        "license_short_name": "CC BY-SA 4.0",
                        "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
                        "credit": "Jane Doe / Wikimedia Commons",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    assets = load_wikimedia_manifest(manifest)

    assert assets["paris:eiffel-tower"].local_path == Path(
        "runtime/wikimedia/paris/eiffel-tower.jpg"
    )
    assert assets["paris:eiffel-tower"].license_short_name == "CC BY-SA 4.0"
