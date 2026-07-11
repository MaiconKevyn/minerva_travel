import os
import warnings
from collections.abc import Iterator
from contextlib import contextmanager
from io import BufferedWriter
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile
from PIL import Image, ImageOps, UnidentifiedImageError

from minerva_travel.contract_limits import (
    DEFAULT_IMAGE_UPLOAD_MAX_BYTES,
    DEFAULT_IMAGE_UPLOAD_MAX_HEIGHT,
    DEFAULT_IMAGE_UPLOAD_MAX_PIXELS,
    DEFAULT_IMAGE_UPLOAD_MAX_WIDTH,
)

RUNTIME_DIR = Path("runtime")

IMAGE_UPLOAD_CHUNK_BYTES = 64 * 1024

_FORMAT_MIME_TYPES = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "WEBP": "image/webp",
}
_FORMAT_EXTENSIONS = {
    "JPEG": {".jpg", ".jpeg"},
    "PNG": {".png"},
    "WEBP": {".webp"},
}
_OUTPUT_EXTENSIONS = {
    "JPEG": ".jpg",
    "PNG": ".png",
    "WEBP": ".webp",
}


class ImageUploadError(ValueError):
    """Erro seguro e acionavel para rejeicoes de upload de imagem."""

    code = "invalid_image_upload"
    status_code = 400

    def __init__(self, message: str, **details: object) -> None:
        super().__init__(message)
        self.message = message
        self.details = details

    def as_detail(self) -> dict[str, object]:
        return {"code": self.code, "message": self.message, **self.details}


class InvalidUploadConfigurationError(RuntimeError):
    """Configuracao interna de limite invalida."""


class EmptyImageUploadError(ImageUploadError):
    code = "empty_image_upload"

    def __init__(self) -> None:
        super().__init__("A imagem enviada esta vazia.")


class ImageUploadTooLargeError(ImageUploadError):
    code = "image_upload_too_large"
    status_code = 413

    def __init__(self, *, max_bytes: int, bytes_read: int) -> None:
        super().__init__(
            "A imagem excede o limite permitido.",
            max_bytes=max_bytes,
            bytes_read=bytes_read,
        )


class UnsupportedImageMimeTypeError(ImageUploadError):
    code = "unsupported_image_mime_type"
    status_code = 415

    def __init__(self, declared_mime_type: str | None) -> None:
        super().__init__(
            "Envie uma imagem JPEG, PNG ou WebP.",
            declared_mime_type=declared_mime_type or "",
        )


class UnsupportedImageExtensionError(ImageUploadError):
    code = "unsupported_image_extension"
    status_code = 415


class InvalidImageContentError(ImageUploadError):
    code = "invalid_image_content"
    status_code = 415

    def __init__(self) -> None:
        super().__init__("O arquivo enviado nao e uma imagem valida.")


class ImageContentMismatchError(ImageUploadError):
    code = "image_content_mismatch"
    status_code = 415

    def __init__(
        self,
        *,
        detected_format: str,
        declared_mime_type: str,
        declared_extension: str,
    ) -> None:
        super().__init__(
            "O conteudo da imagem nao corresponde ao tipo de arquivo informado.",
            detected_format=detected_format,
            declared_mime_type=declared_mime_type,
            declared_extension=declared_extension,
        )


class ImageDimensionsExceededError(ImageUploadError):
    code = "image_dimensions_exceeded"
    status_code = 413

    def __init__(
        self,
        *,
        width: int | None,
        height: int | None,
        max_width: int,
        max_height: int,
        max_pixels: int,
    ) -> None:
        super().__init__(
            "As dimensoes da imagem excedem o limite permitido.",
            width=width,
            height=height,
            max_width=max_width,
            max_height=max_height,
            max_pixels=max_pixels,
        )


class AnimatedImageUploadError(ImageUploadError):
    code = "animated_image_not_supported"
    status_code = 415

    def __init__(self) -> None:
        super().__init__("Imagens animadas nao sao aceitas.")


class ImageUploadProcessingError(ImageUploadError):
    code = "image_upload_processing_failed"
    status_code = 500

    def __init__(self) -> None:
        super().__init__("Nao foi possivel processar a imagem enviada.")


def ensure_runtime_dirs() -> None:
    for name in ("uploads", "generated", "pdfs"):
        (RUNTIME_DIR / name).mkdir(parents=True, exist_ok=True)


def image_upload_max_bytes() -> int:
    return _positive_environment_integer(
        "IMAGE_UPLOAD_MAX_BYTES",
        DEFAULT_IMAGE_UPLOAD_MAX_BYTES,
    )


def image_upload_max_pixels() -> int:
    return _positive_environment_integer(
        "IMAGE_UPLOAD_MAX_PIXELS",
        DEFAULT_IMAGE_UPLOAD_MAX_PIXELS,
    )


def image_upload_max_width() -> int:
    return _positive_environment_integer(
        "IMAGE_UPLOAD_MAX_WIDTH",
        DEFAULT_IMAGE_UPLOAD_MAX_WIDTH,
    )


def image_upload_max_height() -> int:
    return _positive_environment_integer(
        "IMAGE_UPLOAD_MAX_HEIGHT",
        DEFAULT_IMAGE_UPLOAD_MAX_HEIGHT,
    )


async def save_upload(
    upload: UploadFile,
    *,
    max_bytes: int | None = None,
    max_pixels: int | None = None,
    max_width: int | None = None,
    max_height: int | None = None,
    chunk_bytes: int = IMAGE_UPLOAD_CHUNK_BYTES,
) -> Path:
    """Valida, normaliza e persiste uma imagem sem confiar no nome do cliente.

    O corpo e lido em chunks para que o limite seja aplicado durante o upload.
    Somente a imagem reencodada e movida para o nome final; o arquivo bruto e
    removido inclusive em cancelamentos e falhas de decodificacao.
    """

    byte_limit = max_bytes if max_bytes is not None else image_upload_max_bytes()
    pixel_limit = max_pixels if max_pixels is not None else image_upload_max_pixels()
    width_limit = max_width if max_width is not None else image_upload_max_width()
    height_limit = max_height if max_height is not None else image_upload_max_height()
    _validate_limits(byte_limit, pixel_limit, width_limit, height_limit, chunk_bytes)

    uploads_dir = RUNTIME_DIR / "uploads"
    upload_id = uuid4().hex
    raw_path = uploads_dir / f".{upload_id}.uploading"
    encoded_path = uploads_dir / f".{upload_id}.encoding"
    final_path: Path | None = None

    try:
        ensure_runtime_dirs()
        declared_mime_type = _declared_mime_type(upload)
        declared_extension = Path(upload.filename or "").suffix.lower()
        if declared_mime_type not in _FORMAT_MIME_TYPES.values():
            raise UnsupportedImageMimeTypeError(declared_mime_type)
        allowed_extensions = {item for items in _FORMAT_EXTENSIONS.values() for item in items}
        if declared_extension not in allowed_extensions:
            raise UnsupportedImageExtensionError(
                "A extensao informada deve ser .jpg, .jpeg, .png ou .webp."
            )
        await _stream_upload_to_path(
            upload,
            raw_path,
            max_bytes=byte_limit,
            chunk_bytes=chunk_bytes,
        )
        detected_format = _validate_image_file(
            raw_path,
            declared_mime_type=declared_mime_type,
            declared_extension=declared_extension,
            max_pixels=pixel_limit,
            max_width=width_limit,
            max_height=height_limit,
        )
        final_path = uploads_dir / f"{upload_id}{_OUTPUT_EXTENSIONS[detected_format]}"
        _write_sanitized_image(
            raw_path,
            encoded_path,
            detected_format=detected_format,
            max_pixels=pixel_limit,
            max_width=width_limit,
            max_height=height_limit,
        )
        os.replace(encoded_path, final_path)
        return final_path
    except ImageUploadError:
        if final_path is not None:
            final_path.unlink(missing_ok=True)
        raise
    except (OSError, ValueError) as exc:
        if final_path is not None:
            final_path.unlink(missing_ok=True)
        raise ImageUploadProcessingError() from exc
    finally:
        raw_path.unlink(missing_ok=True)
        encoded_path.unlink(missing_ok=True)
        try:
            await upload.close()
        except Exception:
            # O artefato temporario ja foi removido; erro de fechamento nao deve
            # esconder a validacao que sera apresentada ao cliente.
            pass


async def _stream_upload_to_path(
    upload: UploadFile,
    output_path: Path,
    *,
    max_bytes: int,
    chunk_bytes: int,
) -> None:
    bytes_read = 0
    with _open_private_binary(output_path) as output:
        while True:
            chunk = await upload.read(chunk_bytes)
            if not chunk:
                break
            bytes_read += len(chunk)
            if bytes_read > max_bytes:
                raise ImageUploadTooLargeError(
                    max_bytes=max_bytes,
                    bytes_read=bytes_read,
                )
            output.write(chunk)
    if bytes_read == 0:
        raise EmptyImageUploadError()


def _validate_image_file(
    path: Path,
    *,
    declared_mime_type: str,
    declared_extension: str,
    max_pixels: int,
    max_width: int,
    max_height: int,
) -> str:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(path) as image:
                detected_format = (image.format or "").upper()
                width, height = image.size
                _validate_dimensions(
                    width,
                    height,
                    max_pixels=max_pixels,
                    max_width=max_width,
                    max_height=max_height,
                )
                if getattr(image, "n_frames", 1) != 1:
                    raise AnimatedImageUploadError()
                if detected_format not in _FORMAT_MIME_TYPES:
                    raise InvalidImageContentError()
                if (
                    _FORMAT_MIME_TYPES[detected_format] != declared_mime_type
                    or declared_extension not in _FORMAT_EXTENSIONS[detected_format]
                ):
                    raise ImageContentMismatchError(
                        detected_format=detected_format,
                        declared_mime_type=declared_mime_type,
                        declared_extension=declared_extension,
                    )
                # verify() percorre a estrutura do arquivo e detecta truncamento
                # sem manter a imagem descomprimida em memoria.
                image.verify()
                return detected_format
    except ImageUploadError:
        raise
    except (Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise ImageDimensionsExceededError(
            width=None,
            height=None,
            max_width=max_width,
            max_height=max_height,
            max_pixels=max_pixels,
        ) from exc
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError) as exc:
        raise InvalidImageContentError() from exc


def _write_sanitized_image(
    source_path: Path,
    output_path: Path,
    *,
    detected_format: str,
    max_pixels: int,
    max_width: int,
    max_height: int,
) -> None:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(source_path) as source:
                source.load()
                image = ImageOps.exif_transpose(source)
                _validate_dimensions(
                    image.width,
                    image.height,
                    max_pixels=max_pixels,
                    max_width=max_width,
                    max_height=max_height,
                )
                sanitized = _normalized_pixel_image(image, detected_format)
                try:
                    sanitized.info.clear()
                    with _open_private_binary(output_path) as output:
                        if detected_format == "JPEG":
                            sanitized.save(
                                output,
                                format="JPEG",
                                quality=90,
                                optimize=True,
                                progressive=True,
                            )
                        elif detected_format == "PNG":
                            sanitized.save(output, format="PNG", optimize=True)
                        else:
                            sanitized.save(output, format="WEBP", quality=90, method=4)
                finally:
                    if sanitized is not image:
                        sanitized.close()
    except ImageUploadError:
        raise
    except (Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise ImageDimensionsExceededError(
            width=None,
            height=None,
            max_width=max_width,
            max_height=max_height,
            max_pixels=max_pixels,
        ) from exc
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError) as exc:
        raise InvalidImageContentError() from exc


def _normalized_pixel_image(image: Image.Image, detected_format: str) -> Image.Image:
    has_transparency = image.mode in {"RGBA", "LA"} or (
        image.mode == "P" and "transparency" in image.info
    )
    if detected_format == "JPEG":
        return image.convert("RGB")
    if detected_format == "WEBP":
        return image.convert("RGBA" if has_transparency else "RGB")
    if has_transparency and image.mode != "RGBA":
        return image.convert("RGBA")
    if image.mode not in {"1", "L", "LA", "P", "RGB", "RGBA", "I", "I;16"}:
        return image.convert("RGB")
    return image.copy()


def _validate_dimensions(
    width: int,
    height: int,
    *,
    max_pixels: int,
    max_width: int,
    max_height: int,
) -> None:
    if (
        width <= 0
        or height <= 0
        or width > max_width
        or height > max_height
        or width * height > max_pixels
    ):
        raise ImageDimensionsExceededError(
            width=width,
            height=height,
            max_width=max_width,
            max_height=max_height,
            max_pixels=max_pixels,
        )


def _declared_mime_type(upload: UploadFile) -> str:
    return (upload.content_type or "").split(";", maxsplit=1)[0].strip().lower()


def _positive_environment_integer(name: str, default: int) -> int:
    raw_value = os.getenv(name, str(default))
    try:
        value = int(raw_value)
    except ValueError:
        return default
    return value if value > 0 else default


def _validate_limits(
    max_bytes: int,
    max_pixels: int,
    max_width: int,
    max_height: int,
    chunk_bytes: int,
) -> None:
    if min(max_bytes, max_pixels, max_width, max_height, chunk_bytes) <= 0:
        raise InvalidUploadConfigurationError("Os limites de upload devem ser positivos.")


@contextmanager
def _open_private_binary(path: Path) -> Iterator[BufferedWriter]:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as output:
        yield output


def generated_path(filename: str) -> Path:
    ensure_runtime_dirs()
    return RUNTIME_DIR / "generated" / filename


def pdf_path(filename: str) -> Path:
    ensure_runtime_dirs()
    return RUNTIME_DIR / "pdfs" / filename
