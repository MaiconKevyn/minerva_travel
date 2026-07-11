import asyncio
import stat
from io import BytesIO
from pathlib import Path

import pytest
from fastapi import UploadFile
from PIL import Image
from starlette.datastructures import Headers

from minerva_travel import storage
from minerva_travel.storage import (
    EmptyImageUploadError,
    ImageContentMismatchError,
    ImageDimensionsExceededError,
    ImageUploadTooLargeError,
    InvalidImageContentError,
    UnsupportedImageExtensionError,
    UnsupportedImageMimeTypeError,
)


def _upload(data: bytes, *, filename: str, content_type: str) -> UploadFile:
    return UploadFile(
        file=BytesIO(data),
        filename=filename,
        headers=Headers({"content-type": content_type}),
    )


def _image_bytes(
    image_format: str,
    *,
    size: tuple[int, int] = (32, 20),
    exif: Image.Exif | None = None,
) -> bytes:
    image = Image.new("RGB", size, "#3f8fa8")
    output = BytesIO()
    save_options = {"exif": exif} if exif is not None else {}
    image.save(output, format=image_format, **save_options)
    image.close()
    return output.getvalue()


@pytest.mark.parametrize(
    ("image_format", "filename", "content_type", "expected_suffix"),
    [
        ("JPEG", "family.jpeg", "image/jpeg", ".jpg"),
        ("PNG", "family.png", "image/png", ".png"),
        ("WEBP", "family.webp", "image/webp", ".webp"),
    ],
)
def test_save_upload_reencodes_supported_images_with_server_name(
    tmp_path,
    monkeypatch,
    image_format,
    filename,
    content_type,
    expected_suffix,
):
    monkeypatch.setattr(storage, "RUNTIME_DIR", tmp_path)

    result = asyncio.run(
        storage.save_upload(
            _upload(
                _image_bytes(image_format),
                filename=filename,
                content_type=content_type,
            )
        )
    )

    assert result.parent == tmp_path / "uploads"
    assert result.suffix == expected_suffix
    assert filename not in result.name
    assert stat.S_IMODE(result.stat().st_mode) & 0o077 == 0
    with Image.open(result) as persisted:
        assert persisted.format == image_format
        assert persisted.size == (32, 20)
        assert not persisted.getexif()


def test_save_upload_corrects_orientation_and_removes_all_exif(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "RUNTIME_DIR", tmp_path)
    exif = Image.Exif()
    exif[274] = 6  # Rotate 90 degrees clockwise.
    exif[315] = "Sensitive photographer metadata"
    exif[34853] = {
        1: "N",
        2: (51.0, 30.0, 0.0),
        3: "W",
        4: (0.0, 7.0, 0.0),
    }
    source = _image_bytes("JPEG", size=(30, 10), exif=exif)

    result = asyncio.run(
        storage.save_upload(_upload(source, filename="portrait.jpg", content_type="image/jpeg"))
    )

    with Image.open(result) as persisted:
        assert persisted.size == (10, 30)
        assert dict(persisted.getexif()) == {}


@pytest.mark.parametrize(
    ("data", "expected_error"),
    [
        (b"", EmptyImageUploadError),
        (b"not an image", InvalidImageContentError),
        (b'<svg xmlns="http://www.w3.org/2000/svg"></svg>', InvalidImageContentError),
        (_image_bytes("PNG")[:24], InvalidImageContentError),
    ],
)
def test_save_upload_rejects_empty_fake_svg_binary_and_truncated_files(
    tmp_path,
    monkeypatch,
    data,
    expected_error,
):
    monkeypatch.setattr(storage, "RUNTIME_DIR", tmp_path)

    with pytest.raises(expected_error):
        asyncio.run(
            storage.save_upload(_upload(data, filename="family.png", content_type="image/png"))
        )

    assert list((tmp_path / "uploads").iterdir()) == []


@pytest.mark.parametrize(
    ("filename", "content_type", "expected_error"),
    [
        ("family.svg", "image/svg+xml", UnsupportedImageMimeTypeError),
        ("family.gif", "image/png", UnsupportedImageExtensionError),
        ("family", "image/png", UnsupportedImageExtensionError),
    ],
)
def test_save_upload_rejects_unannounced_mime_and_extension(
    tmp_path,
    monkeypatch,
    filename,
    content_type,
    expected_error,
):
    monkeypatch.setattr(storage, "RUNTIME_DIR", tmp_path)

    with pytest.raises(expected_error):
        asyncio.run(
            storage.save_upload(
                _upload(_image_bytes("PNG"), filename=filename, content_type=content_type)
            )
        )


@pytest.mark.parametrize(
    ("image_format", "filename", "content_type"),
    [
        ("PNG", "family.jpg", "image/jpeg"),
        ("JPEG", "family.png", "image/png"),
        ("WEBP", "family.jpeg", "image/jpeg"),
    ],
)
def test_save_upload_requires_signature_mime_and_extension_to_match(
    tmp_path,
    monkeypatch,
    image_format,
    filename,
    content_type,
):
    monkeypatch.setattr(storage, "RUNTIME_DIR", tmp_path)

    with pytest.raises(ImageContentMismatchError):
        asyncio.run(
            storage.save_upload(
                _upload(
                    _image_bytes(image_format),
                    filename=filename,
                    content_type=content_type,
                )
            )
        )


def test_save_upload_stops_streaming_as_soon_as_size_limit_is_crossed(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(storage, "RUNTIME_DIR", tmp_path)
    upload = _upload(b"x" * 100, filename="family.png", content_type="image/png")
    bytes_returned = 0
    original_read = upload.read

    async def tracked_read(size: int = -1) -> bytes:
        nonlocal bytes_returned
        chunk = await original_read(size)
        bytes_returned += len(chunk)
        return chunk

    upload.read = tracked_read

    with pytest.raises(ImageUploadTooLargeError) as raised:
        asyncio.run(storage.save_upload(upload, max_bytes=10, chunk_bytes=4))

    assert bytes_returned == 12
    assert bytes_returned < 100
    assert raised.value.status_code == 413
    assert raised.value.as_detail()["max_bytes"] == 10
    assert list((tmp_path / "uploads").iterdir()) == []


def test_save_upload_uses_configurable_ten_megabyte_default(monkeypatch):
    monkeypatch.delenv("IMAGE_UPLOAD_MAX_BYTES", raising=False)
    assert storage.image_upload_max_bytes() == 10 * 1024 * 1024

    monkeypatch.setenv("IMAGE_UPLOAD_MAX_BYTES", "12345")
    assert storage.image_upload_max_bytes() == 12345


@pytest.mark.parametrize(
    ("max_pixels", "max_width", "max_height"),
    [
        (4_999, 1_000, 1_000),
        (1_000_000, 99, 1_000),
        (1_000_000, 1_000, 49),
    ],
)
def test_save_upload_rejects_excessive_dimensions(
    tmp_path,
    monkeypatch,
    max_pixels,
    max_width,
    max_height,
):
    monkeypatch.setattr(storage, "RUNTIME_DIR", tmp_path)

    with pytest.raises(ImageDimensionsExceededError):
        asyncio.run(
            storage.save_upload(
                _upload(
                    _image_bytes("PNG", size=(100, 50)),
                    filename="large.png",
                    content_type="image/png",
                ),
                max_pixels=max_pixels,
                max_width=max_width,
                max_height=max_height,
            )
        )


def test_save_upload_converts_pillow_decompression_bomb_to_typed_error(
    tmp_path,
    monkeypatch,
):
    source = _image_bytes("PNG", size=(50, 50))
    monkeypatch.setattr(storage, "RUNTIME_DIR", tmp_path)
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", 1_000)

    with pytest.raises(ImageDimensionsExceededError):
        asyncio.run(
            storage.save_upload(
                _upload(source, filename="bomb.png", content_type="image/png"),
                max_pixels=1_000_000,
            )
        )


def test_save_upload_ignores_path_traversal_filename(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "RUNTIME_DIR", tmp_path)

    result = asyncio.run(
        storage.save_upload(
            _upload(
                _image_bytes("JPEG"),
                filename="../../../../owned.jpeg",
                content_type="image/jpeg",
            )
        )
    )

    assert result.parent == tmp_path / "uploads"
    assert result.name != "owned.jpeg"
    assert not (tmp_path.parent / "owned.jpeg").exists()


def test_save_upload_supports_concurrent_uploads_without_name_collisions(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(storage, "RUNTIME_DIR", tmp_path)
    source = _image_bytes("PNG")

    async def save_both() -> list[Path]:
        return await asyncio.gather(
            storage.save_upload(_upload(source, filename="same.png", content_type="image/png")),
            storage.save_upload(_upload(source, filename="same.png", content_type="image/png")),
        )

    first, second = asyncio.run(save_both())

    assert first != second
    assert first.exists()
    assert second.exists()


def test_save_upload_removes_partial_file_when_request_is_cancelled(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "RUNTIME_DIR", tmp_path)
    upload = _upload(b"unused", filename="family.png", content_type="image/png")
    read_count = 0

    async def interrupted_read(_size: int = -1) -> bytes:
        nonlocal read_count
        read_count += 1
        if read_count == 1:
            return b"partial"
        raise asyncio.CancelledError

    upload.read = interrupted_read

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(storage.save_upload(upload, chunk_bytes=7))

    assert list((tmp_path / "uploads").iterdir()) == []
