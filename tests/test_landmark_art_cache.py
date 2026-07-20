from pathlib import Path

import httpx

from minerva_travel.custom_landmarks import build_custom_destinations, parse_custom_landmarks
from minerva_travel.landmark_art_cache import (
    STYLE_VERSION,
    load_cached_stylized_art,
    local_cache_path,
    store_stylized_art,
    stylized_art_cache_key,
)
from minerva_travel.supabase_storage import SupabaseStorageClient, SupabaseStorageConfig


def _client(handler) -> SupabaseStorageClient:
    config = SupabaseStorageConfig(
        url="https://cache-test.supabase.co",
        service_role_key="service-key",
        landmark_assets_bucket="landmark-assets",
    )
    transport = httpx.MockTransport(handler)
    return SupabaseStorageClient(config, http_client=httpx.Client(transport=transport))


def _paris_destination():
    destinations, _selected = build_custom_destinations(
        parse_custom_landmarks(
            '[{"name":"Torre Eiffel","city":"Paris","country":"França",'
            '"place_id":"ChIJLU7jZClu5kcR4PcOOO6p3I0"}]'
        )
    )
    return destinations[0]


def test_cache_key_prefers_place_id_and_carries_style_version():
    destination = _paris_destination()

    key = stylized_art_cache_key(destination, destination.landmarks[0])

    assert key == f"stylized/{STYLE_VERSION}/chijlu7jzclu5kcr4pcooo6p3i0.png"


def test_cache_key_falls_back_to_name_and_city_slug():
    destinations, _selected = build_custom_destinations(
        parse_custom_landmarks("Torre Eiffel, Paris, França")
    )
    destination = destinations[0]

    key = stylized_art_cache_key(destination, destination.landmarks[0])

    assert key == f"stylized/{STYLE_VERSION}/torre-eiffel-paris.png"


def test_load_cached_stylized_art_prefers_local_layer(tmp_path, monkeypatch):
    monkeypatch.setattr("minerva_travel.storage.RUNTIME_DIR", tmp_path)
    cache_key = f"stylized/{STYLE_VERSION}/torre-eiffel-paris.png"
    local_file = local_cache_path(cache_key)
    local_file.parent.mkdir(parents=True, exist_ok=True)
    local_file.write_bytes(b"cached-art")

    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("nao deve consultar o bucket quando o arquivo local existe")

    resolved = load_cached_stylized_art(cache_key, storage_client=_client(handler))

    assert resolved == local_file


def test_load_cached_stylized_art_downloads_from_bucket_on_local_miss(tmp_path, monkeypatch):
    monkeypatch.setattr("minerva_travel.storage.RUNTIME_DIR", tmp_path)
    cache_key = f"stylized/{STYLE_VERSION}/torre-eiffel-paris.png"

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert "/storage/v1/object/landmark-assets/" in str(request.url)
        assert "stylized/" in str(request.url)
        return httpx.Response(200, content=b"bucket-art")

    resolved = load_cached_stylized_art(cache_key, storage_client=_client(handler))

    assert resolved is not None
    assert resolved.read_bytes() == b"bucket-art"


def test_load_cached_stylized_art_returns_none_on_bucket_miss(tmp_path, monkeypatch):
    monkeypatch.setattr("minerva_travel.storage.RUNTIME_DIR", tmp_path)
    cache_key = f"stylized/{STYLE_VERSION}/desconhecido.png"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"error": "not_found"})

    resolved = load_cached_stylized_art(cache_key, storage_client=_client(handler))

    assert resolved is None


def test_store_stylized_art_uploads_to_shared_bucket(tmp_path):
    cache_key = f"stylized/{STYLE_VERSION}/torre-eiffel-paris.png"
    art = tmp_path / "art.png"
    art.write_bytes(b"fresh-art")
    uploaded: dict[str, bytes] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        uploaded[str(request.url)] = request.read()
        return httpx.Response(200, json={"Key": cache_key})

    store_stylized_art(cache_key, art, storage_client=_client(handler))

    assert len(uploaded) == 1
    url, content = next(iter(uploaded.items()))
    assert url.endswith(f"/storage/v1/object/landmark-assets/{cache_key}")
    assert content == b"fresh-art"


def test_store_stylized_art_swallows_bucket_errors(tmp_path):
    art = tmp_path / "art.png"
    art.write_bytes(b"fresh-art")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "boom"})

    # Nao deve levantar: cache duravel indisponivel nao bloqueia o guia.
    store_stylized_art(f"stylized/{STYLE_VERSION}/x.png", art, storage_client=_client(handler))


def test_local_cache_path_stays_inside_shared_dir(monkeypatch, tmp_path):
    monkeypatch.setattr("minerva_travel.storage.RUNTIME_DIR", tmp_path)
    path = local_cache_path(f"stylized/{STYLE_VERSION}/abc.png")

    assert Path(tmp_path / "landmark-art") in path.parents
