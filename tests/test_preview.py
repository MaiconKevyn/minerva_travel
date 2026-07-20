import base64
from html.parser import HTMLParser
from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from minerva_travel.app import app
from minerva_travel.catalog import load_catalog
from minerva_travel.guide_builder import build_guide_context
from minerva_travel.models import GuideRequest
from minerva_travel.pdf import (
    PdfResourceAccessError,
    build_guide_asset_src,
    default_pdf_asset_roots,
    render_guide_html,
    resolve_approved_asset_path,
)


class _PreviewMarkupParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.images: list[dict[str, str]] = []
        self.fallback_elements: list[dict[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {key: value or "" for key, value in attrs}
        if tag == "img":
            self.images.append(attributes)
        if "image-fallback" in attributes.get("class", "").split():
            self.fallback_elements.append(attributes)


def _decode_image_data_url(source: str) -> tuple[str, bytes]:
    header, encoded = source.split(",", maxsplit=1)
    assert header.startswith("data:image/")
    assert header.endswith(";base64")
    return header.removeprefix("data:").removesuffix(";base64"), base64.b64decode(
        encoded,
        validate=True,
    )


def test_sample_preview_embeds_only_decodable_images_and_has_no_broken_sources():
    response = TestClient(app).get("/preview/sample")
    parser = _PreviewMarkupParser()
    parser.feed(response.text)

    assert response.status_code == 200
    assert parser.images
    assert parser.fallback_elements == []
    assert "runtime/generated/representative-full-cover.png" not in response.text
    assert all(image.get("src") for image in parser.images)
    assert all(image["src"].startswith("data:image/") for image in parser.images)

    unique_sources = {image["src"] for image in parser.images}
    for source in unique_sources:
        mime_type, content = _decode_image_data_url(source)
        with Image.open(BytesIO(content)) as image:
            image.verify()
            assert Image.MIME[image.format] == mime_type


def test_sample_preview_uses_existing_catalog_image_when_representative_cover_is_missing():
    response = TestClient(app).get("/preview/sample")
    parser = _PreviewMarkupParser()
    parser.feed(response.text)
    cover = next(image for image in parser.images if "cover-image" in image["class"].split())
    _mime_type, content = _decode_image_data_url(cover["src"])

    assert content == Path("assets/landmarks/paris/eiffel-tower.png").read_bytes()


@pytest.mark.parametrize(
    "unsafe_reference",
    [
        "https://example.com/image.png",
        "http://127.0.0.1/private.png",
        "file:///etc/passwd",
        "//169.254.169.254/latest/meta-data",
    ],
)
def test_preview_asset_helper_rejects_network_and_unapproved_file_references(
    unsafe_reference,
):
    with pytest.raises(PdfResourceAccessError):
        resolve_approved_asset_path(unsafe_reference)


def test_preview_asset_helper_rejects_outside_path_and_uses_approved_fallback(tmp_path):
    root = tmp_path / "assets"
    root.mkdir()
    fallback = root / "fallback.png"
    fallback.write_bytes(Path("assets/landmarks/paris/eiffel-tower.png").read_bytes())
    secret = tmp_path / "secret.png"
    secret.write_bytes(b"must-not-leak")
    asset_src = build_guide_asset_src(preview=True, allowed_roots=[root])

    with pytest.raises(PdfResourceAccessError):
        resolve_approved_asset_path(secret, allowed_roots=[root])
    source = asset_src(secret, fallback)
    assert source is not None
    _mime_type, content = _decode_image_data_url(source)
    assert content == fallback.read_bytes()
    assert b"must-not-leak" not in content


def test_pdf_asset_helper_keeps_validated_local_path_instead_of_data_url(
    tmp_path,
    monkeypatch,
):
    root = tmp_path / "assets"
    root.mkdir()
    image = root / "photo.png"
    image.write_bytes(Path("assets/landmarks/paris/eiffel-tower.png").read_bytes())
    monkeypatch.chdir(tmp_path)
    asset_src = build_guide_asset_src(preview=False, allowed_roots=[root])

    assert asset_src(Path("assets/photo.png")) == image.resolve().as_uri()
    assert asset_src("https://example.com/photo.png") is None


def test_preview_render_never_serializes_model_path_outside_approved_roots(tmp_path):
    catalog = load_catalog()
    request = GuideRequest(
        title="Preview seguro",
        children_names=["Alice"],
        parents_names=["Ana"],
        year=2026,
        selected_landmarks=["paris:eiffel-tower"],
    )
    context = build_guide_context(
        request,
        catalog,
        Path("runtime/generated/missing-cover.png"),
    )
    secret = tmp_path / "secret.png"
    secret.write_bytes(Path("assets/landmarks/paris/eiffel-tower.png").read_bytes())
    landmark = context.destinations[0].landmarks[0].model_copy(update={"image": secret})
    destination = context.destinations[0].model_copy(update={"landmarks": [landmark]})
    unsafe_context = context.model_copy(
        update={"cover_image": secret, "destinations": [destination]}
    )

    html = render_guide_html(
        unsafe_context,
        preview=True,
        allowed_asset_roots=default_pdf_asset_roots(),
    )
    parser = _PreviewMarkupParser()
    parser.feed(html)

    assert str(secret) not in html
    assert all(image.get("src") for image in parser.images)
    assert all(image["src"].startswith("data:image/") for image in parser.images)


def test_default_pdf_asset_roots_include_shared_stylized_art_cache(tmp_path, monkeypatch):
    monkeypatch.setattr("minerva_travel.storage.RUNTIME_DIR", tmp_path)
    stylized = tmp_path / "landmark-art" / "stylized" / "v1" / "torre-eiffel-paris.png"
    stylized.parent.mkdir(parents=True)
    Image.new("RGB", (60, 40), "#4f86b7").save(stylized)

    resolved = resolve_approved_asset_path(stylized)

    assert resolved == stylized.resolve()
