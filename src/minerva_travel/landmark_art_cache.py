"""Cache em duas camadas para a arte estilizada dos pontos turisticos.

A arte aquarela de um ponto turistico e identica para todos os clientes, entao
ela e gerada uma unica vez e reaproveitada:

1. Camada quente: ``runtime/landmark-art/`` no disco da instancia (efemero no
   Render, apenas um atalho local).
2. Camada duravel: bucket ``landmark-assets`` no Supabase Storage, compartilhado
   entre instancias e deploys.

A chave preferencial e o ``place_id`` do Google (estavel independentemente de
como o usuario digitou o nome); sem ele, cai para um slug nome+cidade. O
prefixo de versao de estilo invalida o cache quando o prompt visual mudar.
"""

from pathlib import Path

import httpx

from minerva_travel import storage
from minerva_travel.custom_landmarks import slugify
from minerva_travel.models import Destination, Landmark
from minerva_travel.supabase_storage import SupabaseStorageClient, SupabaseStorageConfig

STYLE_VERSION = "v1"


def stylized_art_cache_key(destination: Destination, landmark: Landmark) -> str:
    if landmark.place_id:
        identity = slugify(landmark.place_id) or landmark.place_id
    else:
        identity = slugify(f"{landmark.name}-{destination.city}") or landmark.id
    return f"stylized/{STYLE_VERSION}/{identity}.png"


def local_cache_path(cache_key: str) -> Path:
    # Resolve o diretorio a cada chamada para respeitar RUNTIME_DIR
    # monkeypatchado nos testes (mesmo idioma dos demais modulos).
    return storage.RUNTIME_DIR / "landmark-art" / cache_key


def load_cached_stylized_art(
    cache_key: str,
    *,
    storage_client: SupabaseStorageClient | None = None,
) -> Path | None:
    """Retorna o arquivo local da arte em cache, buscando no bucket se preciso."""
    local_path = local_cache_path(cache_key)
    if local_path.exists():
        return local_path

    client = storage_client or _default_storage_client()
    if client is None:
        return None
    try:
        found = client.download_file(
            bucket=client.config.landmark_assets_bucket,
            storage_path=cache_key,
            local_path=local_path,
        )
    except httpx.HTTPError:
        return None
    return local_path if found else None


def store_stylized_art(
    cache_key: str,
    local_path: Path,
    *,
    storage_client: SupabaseStorageClient | None = None,
) -> None:
    """Sobe a arte recem-gerada para a camada duravel (melhor esforco)."""
    client = storage_client or _default_storage_client()
    if client is None or not local_path.exists():
        return
    try:
        client.upload_file(
            bucket=client.config.landmark_assets_bucket,
            storage_path=cache_key,
            local_path=local_path,
            content_type="image/png",
        )
    except httpx.HTTPError:
        # Cache duravel indisponivel nao pode impedir a geracao do guia; a
        # arte local segue valida e a proxima geracao tenta subir de novo.
        return


def _default_storage_client() -> SupabaseStorageClient | None:
    config = SupabaseStorageConfig.from_env()
    if config is None:
        return None
    return SupabaseStorageClient(config)
