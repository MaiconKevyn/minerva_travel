"""Provenance policy for images that are rendered in a customer's guide.

The catalog's geometric illustrations remain useful for development fixtures and
offline tests, but they must never silently become paid-production content.
Every selected landmark in production therefore needs a local, attributed
Wikimedia asset before cover/PDF generation starts.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from pathlib import Path

from minerva_travel.config import app_environment
from minerva_travel.wikimedia_assets import WikimediaAsset


class AssetProvenanceError(ValueError):
    """Raised when a production guide would fall back to an uncredited asset."""

    def __init__(self, missing_selection_ids: Iterable[str]) -> None:
        self.missing_selection_ids = tuple(sorted(set(missing_selection_ids)))
        joined = ", ".join(self.missing_selection_ids)
        super().__init__(
            "Não foi possível confirmar uma imagem licenciada para: "
            f"{joined}. Tente novamente mais tarde."
        )


def asset_provenance_required() -> bool:
    """Only production rejects the deliberately offline development fixtures."""

    return app_environment() == "production"


def assert_selected_asset_provenance(
    selection_ids: Iterable[str],
    assets: Mapping[str, WikimediaAsset],
    *,
    required: bool | None = None,
) -> None:
    """Ensure every selected landmark has a complete, local attribution record."""

    if required is None:
        required = asset_provenance_required()
    if not required:
        return

    missing: list[str] = []
    for selection_id in selection_ids:
        asset = assets.get(selection_id)
        if asset is None or not _has_publishable_provenance(asset):
            missing.append(selection_id)
    if missing:
        raise AssetProvenanceError(missing)


def _has_publishable_provenance(asset: WikimediaAsset) -> bool:
    required_strings = (
        asset.title,
        asset.source_url,
        asset.image_url,
        asset.author,
        asset.license_short_name,
        asset.license_url,
        asset.credit,
    )
    if not all(value.strip() for value in required_strings):
        return False
    try:
        return Path(asset.local_path).is_file()
    except OSError:
        return False
