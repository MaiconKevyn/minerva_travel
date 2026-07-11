from pathlib import Path

import pytest

from minerva_travel import pdf, storage
from minerva_travel.pdf import (
    PdfResourceAccessError,
    PdfResourceNotFoundError,
    build_pdf_url_fetcher,
)


def test_pdf_url_fetcher_reads_regular_file_inside_approved_root(tmp_path):
    root = tmp_path / "assets"
    image_path = root / "nested" / "photo.png"
    image_path.parent.mkdir(parents=True)
    image_path.write_bytes(b"trusted-image")

    result = build_pdf_url_fetcher([root])(image_path.as_uri())

    assert result["string"] == b"trusted-image"
    assert result["mime_type"] == "image/png"
    assert result["redirected_url"] == image_path.as_uri()
    assert result["filename"] == "photo.png"


def test_pdf_url_fetcher_resolves_relative_paths_without_expanding_approved_root(
    tmp_path,
    monkeypatch,
):
    root = tmp_path / "assets"
    image_path = root / "photo.webp"
    root.mkdir()
    image_path.write_bytes(b"trusted-image")
    monkeypatch.chdir(tmp_path)

    result = build_pdf_url_fetcher([root])("assets/photo.webp")

    assert result["string"] == b"trusted-image"
    assert result["mime_type"] == "image/webp"


@pytest.mark.parametrize(
    "url",
    [
        "http://localhost/private",
        "http://127.0.0.1/private",
        "http://[::1]/private",
        "https://10.0.0.1/private",
        "https://169.254.169.254/latest/meta-data",
        "ftp://example.com/image.png",
        "data:image/png;base64,AAAA",
        "//127.0.0.1/private",
        "file://localhost/etc/passwd",
    ],
)
def test_pdf_url_fetcher_blocks_network_non_file_schemes_and_file_authorities(
    tmp_path,
    url,
):
    with pytest.raises(PdfResourceAccessError):
        build_pdf_url_fetcher([tmp_path])(url)


def test_pdf_url_fetcher_blocks_absolute_and_encoded_traversal_outside_root(tmp_path):
    root = tmp_path / "assets"
    root.mkdir()
    secret = tmp_path / "secret.txt"
    secret.write_text("secret", encoding="utf-8")
    fetch = build_pdf_url_fetcher([root])

    with pytest.raises(PdfResourceAccessError):
        fetch(secret.as_uri())
    with pytest.raises(PdfResourceAccessError):
        fetch(f"{root.as_uri()}/%2e%2e/secret.txt")
    with pytest.raises(PdfResourceAccessError):
        fetch("file:///etc/passwd")


def test_pdf_url_fetcher_blocks_symlink_that_escapes_approved_root(tmp_path):
    root = tmp_path / "assets"
    root.mkdir()
    secret = tmp_path / "secret.txt"
    secret.write_text("secret", encoding="utf-8")
    link = root / "photo.png"
    link.symlink_to(secret)

    with pytest.raises(PdfResourceAccessError):
        build_pdf_url_fetcher([root])(link.as_uri())


def test_pdf_url_fetcher_distinguishes_missing_internal_asset(tmp_path):
    root = tmp_path / "assets"
    root.mkdir()

    with pytest.raises(PdfResourceNotFoundError) as raised:
        build_pdf_url_fetcher([root])((root / "missing.png").as_uri())

    assert raised.value.code == "pdf_resource_not_found"
    assert raised.value.reason == "file_not_found"


def test_default_pdf_roots_exclude_raw_family_uploads(tmp_path, monkeypatch):
    runtime_dir = tmp_path / "runtime"
    generated = runtime_dir / "generated" / "cover.png"
    raw_upload = runtime_dir / "uploads" / "family.png"
    generated.parent.mkdir(parents=True)
    raw_upload.parent.mkdir(parents=True)
    generated.write_bytes(b"generated")
    raw_upload.write_bytes(b"raw-family-photo")
    monkeypatch.setattr(storage, "RUNTIME_DIR", runtime_dir)
    fetch = build_pdf_url_fetcher(pdf.default_pdf_asset_roots())

    assert fetch(generated.as_uri())["string"] == b"generated"
    with pytest.raises(PdfResourceAccessError):
        fetch(raw_upload.as_uri())


def test_write_pdf_supplies_local_only_fetcher_to_weasyprint(tmp_path, monkeypatch):
    captured: dict[str, object] = {}

    class FakeDocument:
        def write_pdf(self, output_path: Path, **options: object) -> None:
            captured["write_options"] = options
            output_path.write_bytes(b"%PDF-secure-test")

    class FakeHtmlRenderer:
        def __init__(self, **kwargs: object) -> None:
            captured.update(kwargs)

        def write_pdf(self, output_path: Path, **options: object) -> None:
            FakeDocument().write_pdf(output_path, **options)

    assets = tmp_path / "approved"
    assets.mkdir()
    monkeypatch.setattr(pdf, "_load_html_renderer", lambda: FakeHtmlRenderer)
    monkeypatch.setattr(
        pdf,
        "render_guide_html",
        lambda _context, **_kwargs: "<html></html>",
    )
    output = tmp_path / "output" / "guide.pdf"

    result = pdf.write_pdf(object(), output, allowed_asset_roots=[assets])

    assert result == output
    assert output.read_bytes() == b"%PDF-secure-test"
    assert captured["base_url"] == Path.cwd().resolve().as_uri()
    assert captured["write_options"] == {"presentational_hints": False}
    fetch = captured["url_fetcher"]
    assert callable(fetch)
    with pytest.raises(PdfResourceAccessError):
        fetch("http://127.0.0.1/admin")
