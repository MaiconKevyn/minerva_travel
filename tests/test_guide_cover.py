import httpx
from PIL import Image

from minerva_travel import storage
from minerva_travel.guide_cover import (
    COVER_THUMBNAIL_WIDTH,
    cover_thumbnail_storage_path,
    load_cover_thumbnail,
    store_cover_thumbnail,
    write_cover_thumbnail,
)
from minerva_travel.supabase_storage import SupabaseStorageClient, SupabaseStorageConfig


def _client(handler) -> SupabaseStorageClient:
    config = SupabaseStorageConfig(
        url="https://covers-test.supabase.co",
        service_role_key="service-key",
        generated_covers_bucket="generated-covers",
    )
    transport = httpx.MockTransport(handler)
    return SupabaseStorageClient(config, http_client=httpx.Client(transport=transport))


def test_write_cover_thumbnail_shrinks_the_cover_and_keeps_proportion(tmp_path, monkeypatch):
    monkeypatch.setattr("minerva_travel.storage.RUNTIME_DIR", tmp_path)
    cover = tmp_path / "cover.png"
    Image.new("RGB", (1200, 1600), "#4f86b7").save(cover)

    thumbnail = write_cover_thumbnail(cover, "guide-1")

    assert thumbnail is not None
    assert thumbnail.name == "guide-1-cover-thumb.jpg"
    with Image.open(thumbnail) as image:
        assert image.width == COVER_THUMBNAIL_WIDTH
        # Proporção 3:4 preservada: a capa não pode chegar distorcida ao painel.
        assert image.height == 640
    assert thumbnail.stat().st_size < cover.stat().st_size


def test_write_cover_thumbnail_returns_none_for_unreadable_source(tmp_path, monkeypatch):
    monkeypatch.setattr("minerva_travel.storage.RUNTIME_DIR", tmp_path)
    broken = tmp_path / "broken.png"
    broken.write_bytes(b"nao-e-imagem")

    assert write_cover_thumbnail(broken, "guide-1") is None
    assert write_cover_thumbnail(tmp_path / "inexistente.png", "guide-1") is None


def test_load_cover_thumbnail_prefers_the_local_file(tmp_path, monkeypatch):
    monkeypatch.setattr("minerva_travel.storage.RUNTIME_DIR", tmp_path)
    local = storage.generated_path("guide-1-cover-thumb.jpg")
    local.parent.mkdir(parents=True, exist_ok=True)
    local.write_bytes(b"thumb-local")

    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("não deve consultar o bucket quando o arquivo local existe")

    assert load_cover_thumbnail("guide-1", storage_client=_client(handler)) == local


def test_load_cover_thumbnail_downloads_from_bucket_after_a_deploy(tmp_path, monkeypatch):
    # Cenário real: o disco do Render é efêmero e a miniatura local sumiu.
    monkeypatch.setattr("minerva_travel.storage.RUNTIME_DIR", tmp_path)
    requested: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested.append(str(request.url))
        return httpx.Response(200, content=b"thumb-do-bucket")

    resolved = load_cover_thumbnail("guide-1", storage_client=_client(handler))

    assert resolved is not None
    assert resolved.read_bytes() == b"thumb-do-bucket"
    assert cover_thumbnail_storage_path("guide-1") in requested[0]


def test_load_cover_thumbnail_returns_none_when_the_bucket_has_no_cover(tmp_path, monkeypatch):
    monkeypatch.setattr("minerva_travel.storage.RUNTIME_DIR", tmp_path)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"error": "not_found"})

    assert load_cover_thumbnail("guide-1", storage_client=_client(handler)) is None


def test_store_cover_thumbnail_uploads_to_the_covers_bucket(tmp_path):
    thumbnail = tmp_path / "thumb.jpg"
    thumbnail.write_bytes(b"thumb")
    uploaded: dict[str, bytes] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        uploaded[str(request.url)] = request.read()
        return httpx.Response(200, json={"Key": "ok"})

    store_cover_thumbnail("guide-1", thumbnail, storage_client=_client(handler))

    url, content = next(iter(uploaded.items()))
    assert "/storage/v1/object/generated-covers/thumbnails/guide-1-cover-thumb.jpg" in url
    assert content == b"thumb"


def test_store_cover_thumbnail_never_breaks_the_guide_when_the_bucket_fails(tmp_path):
    thumbnail = tmp_path / "thumb.jpg"
    thumbnail.write_bytes(b"thumb")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "boom"})

    # Não deve levantar: a família já tem o guia pronto.
    store_cover_thumbnail("guide-1", thumbnail, storage_client=_client(handler))
