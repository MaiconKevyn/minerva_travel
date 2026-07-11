import json
from pathlib import Path

from pydantic import BaseModel

# Versioned catalog assets are part of the release artifact. Runtime assets are
# reserved for temporary custom-landmark lookups and must not be the only source
# of truth for a production guide.
DEFAULT_WIKIMEDIA_MANIFEST = Path("data/wikimedia/manifest.json")
LEGACY_WIKIMEDIA_MANIFEST = Path("runtime/wikimedia/manifest.json")


class WikimediaAsset(BaseModel):
    selection_id: str
    title: str
    source_url: str
    image_url: str
    local_path: Path
    public_url: str | None = None
    storage_path: str | None = None
    author: str
    license_short_name: str
    license_url: str
    credit: str


class ImageCredit(BaseModel):
    landmark_name: str
    source_url: str
    author: str
    license_short_name: str
    license_url: str
    credit: str


def load_wikimedia_manifest(
    path: Path = DEFAULT_WIKIMEDIA_MANIFEST,
) -> dict[str, WikimediaAsset]:
    if (
        path == DEFAULT_WIKIMEDIA_MANIFEST
        and not path.exists()
        and LEGACY_WIKIMEDIA_MANIFEST.exists()
    ):
        path = LEGACY_WIKIMEDIA_MANIFEST
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    assets = [WikimediaAsset.model_validate(item) for item in data.get("assets", [])]
    return {asset.selection_id: asset for asset in assets}
