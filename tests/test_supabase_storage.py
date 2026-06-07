import httpx

from minerva_travel.supabase_storage import (
    SupabaseStorageClient,
    SupabaseStorageConfig,
    sync_wikimedia_asset_to_storage,
)
from minerva_travel.wikimedia_assets import WikimediaAsset


def test_sync_wikimedia_asset_uploads_image_and_metadata_to_public_bucket(tmp_path):
    image_path = tmp_path / "eiffel.jpg"
    image_path.write_bytes(b"image-bytes")
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={})

    asset = WikimediaAsset(
        selection_id="paris:eiffel-tower",
        title="File:Eiffel Tower.jpg",
        source_url="https://commons.wikimedia.org/wiki/File:Eiffel_Tower.jpg",
        image_url="https://upload.wikimedia.org/example.jpg",
        local_path=image_path,
        author="Jane Doe",
        license_short_name="CC BY-SA 4.0",
        license_url="https://creativecommons.org/licenses/by-sa/4.0/",
        credit="Jane Doe / Wikimedia Commons",
    )
    client = SupabaseStorageClient(
        SupabaseStorageConfig(
            url="https://project.supabase.co",
            service_role_key="secret",
            landmark_assets_bucket="landmark-assets",
        ),
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    synced = sync_wikimedia_asset_to_storage(client, asset)

    assert synced.storage_path == "wikimedia/paris/eiffel-tower.jpg"
    assert synced.public_url == (
        "https://project.supabase.co/storage/v1/object/public/"
        "landmark-assets/wikimedia/paris/eiffel-tower.jpg"
    )
    assert [request.method for request in requests] == ["POST", "POST"]
    assert requests[0].headers["content-type"] == "image/jpeg"
    assert requests[1].headers["content-type"] == "application/json"
    assert requests[1].url.path.endswith("/landmark-assets/wikimedia/paris/eiffel-tower.json")
