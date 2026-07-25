"""Miniatura da capa do guia para o painel da família.

O painel lista livros ilustrados, então precisa mostrar a capa — mas a capa
gerada tem 1-2 MB e o disco da instância é efêmero (some a cada deploy).
Este módulo cria uma miniatura leve e a guarda em duas camadas, no mesmo
padrão do cache de arte dos pontos turísticos:

1. ``runtime/generated/`` na instância — atalho rápido;
2. bucket privado ``generated-covers`` — camada durável entre deploys.

A miniatura nunca é servida publicamente: o endpoint do guia confere o dono
antes de entregar o arquivo.
"""

from pathlib import Path

import httpx
from PIL import Image, ImageOps, UnidentifiedImageError

from minerva_travel import storage
from minerva_travel.supabase_storage import SupabaseStorageClient, SupabaseStorageConfig

COVER_THUMBNAIL_WIDTH = 480
COVER_THUMBNAIL_QUALITY = 82


def cover_thumbnail_filename(guide_id: str) -> str:
    return f"{guide_id}-cover-thumb.jpg"


def cover_thumbnail_storage_path(guide_id: str) -> str:
    return f"thumbnails/{cover_thumbnail_filename(guide_id)}"


def write_cover_thumbnail(source: Path, guide_id: str) -> Path | None:
    """Gera a miniatura JPEG da capa. Devolve ``None`` se a origem não servir."""
    output = storage.generated_path(cover_thumbnail_filename(guide_id))
    try:
        with Image.open(source) as loaded:
            image = ImageOps.exif_transpose(loaded).convert("RGB")
            if image.width > COVER_THUMBNAIL_WIDTH:
                ratio = COVER_THUMBNAIL_WIDTH / image.width
                image = image.resize(
                    (COVER_THUMBNAIL_WIDTH, max(1, round(image.height * ratio))),
                    Image.Resampling.LANCZOS,
                )
            output.parent.mkdir(parents=True, exist_ok=True)
            image.save(output, format="JPEG", quality=COVER_THUMBNAIL_QUALITY, optimize=True)
    except (OSError, UnidentifiedImageError, ValueError):
        # Uma miniatura ausente degrada para o placeholder do painel; nunca
        # pode impedir a entrega do guia que a família acabou de gerar.
        return None
    return output


def store_cover_thumbnail(
    guide_id: str,
    thumbnail: Path,
    *,
    storage_client: SupabaseStorageClient | None = None,
) -> None:
    """Sobe a miniatura para a camada durável (melhor esforço)."""
    client = storage_client or _default_storage_client()
    if client is None or not thumbnail.is_file():
        return
    try:
        client.upload_file(
            bucket=client.config.generated_covers_bucket,
            storage_path=cover_thumbnail_storage_path(guide_id),
            local_path=thumbnail,
            content_type="image/jpeg",
        )
    except httpx.HTTPError:
        return


def load_cover_thumbnail(
    guide_id: str,
    *,
    storage_client: SupabaseStorageClient | None = None,
) -> Path | None:
    """Resolve a miniatura local, baixando do bucket quando o disco não a tem."""
    local_path = storage.generated_path(cover_thumbnail_filename(guide_id))
    if local_path.is_file():
        return local_path

    client = storage_client or _default_storage_client()
    if client is None:
        return None
    try:
        found = client.download_file(
            bucket=client.config.generated_covers_bucket,
            storage_path=cover_thumbnail_storage_path(guide_id),
            local_path=local_path,
        )
    except httpx.HTTPError:
        return None
    return local_path if found else None


def _default_storage_client() -> SupabaseStorageClient | None:
    config = SupabaseStorageConfig.from_env()
    if config is None:
        return None
    return SupabaseStorageClient(config)
