import json
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

import httpx

from minerva_travel.config import (
    supabase_bucket_landmark_assets,
    supabase_service_role_key,
    supabase_storage_enabled,
    supabase_url,
)
from minerva_travel.wikimedia_assets import WikimediaAsset


@dataclass(frozen=True)
class SupabaseStorageConfig:
    url: str
    service_role_key: str
    landmark_assets_bucket: str = "landmark-assets"

    @classmethod
    def from_env(cls) -> "SupabaseStorageConfig | None":
        if not supabase_storage_enabled():
            return None
        url = supabase_url()
        service_role_key = supabase_service_role_key()
        if not url or not service_role_key:
            return None
        return cls(
            url=url.rstrip("/"),
            service_role_key=service_role_key,
            landmark_assets_bucket=supabase_bucket_landmark_assets(),
        )


class SupabaseStorageClient:
    def __init__(
        self,
        config: SupabaseStorageConfig,
        http_client: httpx.Client | None = None,
    ) -> None:
        self.config = config
        self._client = http_client or httpx.Client(timeout=60, follow_redirects=True)

    def upload_file(
        self,
        bucket: str,
        storage_path: str,
        local_path: Path,
        content_type: str,
    ) -> None:
        self.upload_bytes(
            bucket=bucket,
            storage_path=storage_path,
            content=local_path.read_bytes(),
            content_type=content_type,
        )

    def upload_json(self, bucket: str, storage_path: str, payload: dict[str, object]) -> None:
        self.upload_bytes(
            bucket=bucket,
            storage_path=storage_path,
            content=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            content_type="application/json",
        )

    def upload_bytes(
        self,
        bucket: str,
        storage_path: str,
        content: bytes,
        content_type: str,
    ) -> None:
        path = quote(storage_path, safe="/")
        response = self._client.post(
            f"{self.config.url}/storage/v1/object/{bucket}/{path}",
            content=content,
            headers={
                "Authorization": f"Bearer {self.config.service_role_key}",
                "apikey": self.config.service_role_key,
                "Content-Type": content_type,
                "x-upsert": "true",
            },
        )
        response.raise_for_status()

    def download_file(self, bucket: str, storage_path: str, local_path: Path) -> bool:
        """Baixa um objeto do bucket privado para o disco. False quando nao existe."""
        path = quote(storage_path, safe="/")
        response = self._client.get(
            f"{self.config.url}/storage/v1/object/{bucket}/{path}",
            headers={
                "Authorization": f"Bearer {self.config.service_role_key}",
                "apikey": self.config.service_role_key,
            },
        )
        if response.status_code == 404:
            return False
        response.raise_for_status()
        local_path.parent.mkdir(parents=True, exist_ok=True)
        local_path.write_bytes(response.content)
        return True


def sync_wikimedia_asset_to_storage(
    client: SupabaseStorageClient,
    asset: WikimediaAsset,
) -> WikimediaAsset:
    if not asset.local_path.exists():
        return asset

    image_path = _asset_image_storage_path(asset)
    metadata_path = _asset_metadata_storage_path(asset)
    bucket = client.config.landmark_assets_bucket
    client.upload_file(
        bucket=bucket,
        storage_path=image_path,
        local_path=asset.local_path,
        content_type=_content_type(asset.local_path),
    )
    client.upload_json(
        bucket=bucket,
        storage_path=metadata_path,
        payload={
            **asset.model_dump(mode="json"),
            # Buckets are deliberately private. The PDF renderer consumes the
            # reviewed local file, and any future browser delivery must use an
            # owner-authorized signed URL instead of a durable public URL.
            "public_url": None,
            "storage_path": image_path,
        },
    )
    return asset.model_copy(update={"public_url": None, "storage_path": image_path})


def sync_wikimedia_assets_to_storage(
    assets: dict[str, WikimediaAsset],
) -> dict[str, WikimediaAsset]:
    config = SupabaseStorageConfig.from_env()
    if not config:
        return assets

    client = SupabaseStorageClient(config)
    synced: dict[str, WikimediaAsset] = {}
    for selection_id, asset in assets.items():
        try:
            synced[selection_id] = sync_wikimedia_asset_to_storage(client, asset)
        except httpx.HTTPError:
            synced[selection_id] = asset
    return synced


def _asset_image_storage_path(asset: WikimediaAsset) -> str:
    suffix = asset.local_path.suffix.lower() or ".jpg"
    return f"wikimedia/{asset.selection_id.replace(':', '/')}{suffix}"


def _asset_metadata_storage_path(asset: WikimediaAsset) -> str:
    return f"wikimedia/{asset.selection_id.replace(':', '/')}.json"


def _content_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".png":
        return "image/png"
    if suffix == ".webp":
        return "image/webp"
    return "image/jpeg"
