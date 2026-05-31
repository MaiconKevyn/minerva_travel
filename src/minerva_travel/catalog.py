import json
from pathlib import Path

from minerva_travel.models import Catalog

DEFAULT_CATALOG_PATH = Path("data/destinations/europe_2026.json")


def load_catalog(path: Path = DEFAULT_CATALOG_PATH) -> Catalog:
    data = json.loads(path.read_text(encoding="utf-8"))
    catalog = Catalog.model_validate(data)
    for destination in catalog.destinations:
        destination.landmarks = destination.sorted_landmarks()
    return catalog
