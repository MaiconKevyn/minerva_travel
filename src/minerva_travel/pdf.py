import base64
import mimetypes
import os
import warnings
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit
from urllib.request import url2pathname

from jinja2 import Environment, FileSystemLoader, select_autoescape
from PIL import Image, UnidentifiedImageError

from minerva_travel import storage
from minerva_travel.models import GuideContext

TEMPLATE_DIR = Path(__file__).parent / "templates"

UrlFetcherResult = Any
UrlFetcher = Callable[[str], UrlFetcherResult]
AssetSource = Callable[[Path | str | None, Path | str | None], str | None]

_PREVIEW_IMAGE_MIME_TYPES = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "WEBP": "image/webp",
}


class PdfResourceAccessError(ValueError):
    """Recurso recusado pelo limite de seguranca do renderer de PDF."""

    code = "pdf_resource_access_denied"

    def __init__(self, url: str, reason: str) -> None:
        super().__init__(f"PDF resource denied ({reason}): {url}")
        self.url = url
        self.reason = reason


class PdfResourceNotFoundError(PdfResourceAccessError):
    code = "pdf_resource_not_found"


def render_guide_html(
    context: GuideContext,
    preview: bool = False,
    *,
    allowed_asset_roots: Iterable[Path] | None = None,
) -> str:
    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = env.get_template("guide.html")
    css = (TEMPLATE_DIR / "styles.css").read_text(encoding="utf-8")
    roots = allowed_asset_roots if allowed_asset_roots is not None else default_pdf_asset_roots()
    asset_src = build_guide_asset_src(preview=preview, allowed_roots=roots)
    return template.render(
        guide=context,
        css=css,
        preview=preview,
        asset_src=asset_src,
    )


def default_pdf_asset_roots() -> tuple[Path, ...]:
    """Diretorios locais que podem fornecer recursos ao WeasyPrint.

    O upload familiar bruto fica deliberadamente fora desta lista. O renderer
    recebe apenas assets versionados, imagens geradas e copias internas ja
    baixadas/validadas.
    """

    runtime_dir = storage.RUNTIME_DIR
    return (
        Path.cwd() / "assets",
        runtime_dir / "generated",
        runtime_dir / "custom-images",
        runtime_dir / "wikimedia",
        TEMPLATE_DIR,
    )


def build_pdf_url_fetcher(
    allowed_roots: Iterable[Path],
    *,
    modern_response: bool = False,
) -> UrlFetcher:
    """Cria fetcher local-only; rede e arquivos fora das raizes sao negados."""

    roots = _normalized_roots(allowed_roots)

    def fetch(url: str) -> UrlFetcherResult:
        resolved_path = _resolve_approved_local_path(url, roots, require_exists=True)
        try:
            content = resolved_path.read_bytes()
        except OSError as exc:
            raise PdfResourceAccessError(url, "file_unreadable") from exc
        mime_type, encoding = mimetypes.guess_type(resolved_path.name)
        legacy_result = {
            "string": content,
            "mime_type": mime_type or "application/octet-stream",
            "encoding": encoding,
            "redirected_url": resolved_path.as_uri(),
            "filename": resolved_path.name,
        }
        # Mantém testes da política independentes das bibliotecas nativas.
        # O render real solicita explicitamente a API moderna.
        if not modern_response:
            return legacy_result
        from weasyprint.urls import URLFetcherResponse

        content_type = mime_type or "application/octet-stream"
        if encoding:
            content_type = f"{content_type}; charset={encoding}"
        return URLFetcherResponse(
            url=resolved_path.as_uri(),
            body=content,
            headers={"Content-Type": content_type},
        )

    return fetch


def resolve_approved_asset_path(
    asset: Path | str,
    *,
    allowed_roots: Iterable[Path] | None = None,
    require_exists: bool = True,
) -> Path:
    """Resolve um asset local ou levanta erro tipado quando ele sai da politica."""

    roots = _normalized_roots(
        allowed_roots if allowed_roots is not None else default_pdf_asset_roots()
    )
    return _resolve_approved_local_path(
        str(asset),
        roots,
        require_exists=require_exists,
    )


def build_guide_asset_src(
    *,
    preview: bool,
    allowed_roots: Iterable[Path],
) -> AssetSource:
    """Cria helper Jinja seguro para assets do preview e do PDF.

    No preview, somente imagens locais existentes e validas viram data URLs.
    No PDF, a referencia continua sendo um path local e sera lida pelo fetcher
    restrito do WeasyPrint. Referencias recusadas usam o fallback aprovado ou
    retornam ``None``, permitindo que o template omita a tag quebrada.
    """

    roots = _normalized_roots(allowed_roots)
    cache: dict[tuple[str, bool], str | None] = {}

    def asset_src(
        asset: Path | str | None,
        fallback: Path | str | None = None,
    ) -> str | None:
        for reference in (asset, fallback):
            if reference is None or not str(reference).strip():
                continue
            key = (str(reference), preview)
            if key in cache:
                cached = cache[key]
                if cached is not None:
                    return cached
                continue
            try:
                resolved_path = _resolve_approved_local_path(
                    str(reference),
                    roots,
                    require_exists=preview,
                )
                source = (
                    _preview_image_data_url(resolved_path)
                    if preview
                    else _local_pdf_reference(str(reference), resolved_path)
                )
            except PdfResourceAccessError:
                source = None
            cache[key] = source
            if source is not None:
                return source
        return None

    return asset_src


def write_pdf(
    context: GuideContext,
    output_path: Path,
    *,
    allowed_asset_roots: Iterable[Path] | None = None,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    roots = tuple(
        allowed_asset_roots if allowed_asset_roots is not None else default_pdf_asset_roots()
    )
    html = render_guide_html(context, allowed_asset_roots=roots)
    html_renderer = _load_html_renderer()
    url_fetcher = build_pdf_url_fetcher(
        roots,
        modern_response=html_renderer.__module__.startswith("weasyprint"),
    )
    html_renderer(
        string=html,
        base_url=Path.cwd().resolve().as_uri(),
        url_fetcher=url_fetcher,
    ).write_pdf(output_path, presentational_hints=False)
    return output_path


def _load_html_renderer() -> type[Any]:
    # O import tardio permite que endpoints sem PDF iniciem mesmo quando as
    # bibliotecas nativas do WeasyPrint ainda nao estao disponiveis. A geracao
    # continua falhando de forma explicita nesse ambiente incompleto.
    from weasyprint import HTML

    return HTML


def _local_path_from_url(url: str) -> Path:
    try:
        parsed = urlsplit(url)
    except ValueError as exc:
        raise PdfResourceAccessError(url, "malformed_url") from exc
    scheme = parsed.scheme.lower()
    if scheme not in {"", "file"}:
        raise PdfResourceAccessError(url, "network_and_non_file_schemes_are_disabled")
    if parsed.netloc:
        # Tambem bloqueia caminhos scheme-relative (//host/path) e file://host.
        raise PdfResourceAccessError(url, "file_authority_is_disabled")

    try:
        decoded_path = url2pathname(unquote(parsed.path))
        if not decoded_path or "\x00" in decoded_path:
            raise ValueError("empty or null-containing path")
        return Path(decoded_path)
    except (TypeError, ValueError) as exc:
        raise PdfResourceAccessError(url, "malformed_file_path") from exc


def _resolved_root(root: Path) -> Path:
    return root.expanduser().resolve(strict=False)


def _normalized_roots(allowed_roots: Iterable[Path]) -> tuple[Path, ...]:
    roots = tuple(_resolved_root(root) for root in allowed_roots)
    if not roots:
        raise ValueError("At least one guide asset root must be configured.")
    return roots


def _resolve_approved_local_path(
    url: str,
    roots: tuple[Path, ...],
    *,
    require_exists: bool,
) -> Path:
    path = _local_path_from_url(url)
    unresolved_path = path if path.is_absolute() else Path.cwd() / path
    lexical_path = Path(os.path.abspath(unresolved_path))
    if not _is_within_roots(lexical_path, roots):
        raise PdfResourceAccessError(url, "path_outside_allowed_roots")

    try:
        resolved_path = unresolved_path.resolve(strict=require_exists)
    except (FileNotFoundError, OSError) as exc:
        raise PdfResourceNotFoundError(url, "file_not_found") from exc
    if not _is_within_roots(resolved_path, roots):
        raise PdfResourceAccessError(url, "symlink_outside_allowed_roots")
    if require_exists and not resolved_path.is_file():
        raise PdfResourceAccessError(url, "not_a_regular_file")
    return resolved_path


def _preview_image_data_url(path: Path) -> str:
    try:
        if path.stat().st_size > storage.image_upload_max_bytes():
            raise PdfResourceAccessError(str(path), "preview_asset_too_large")
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(path) as image:
                image_format = (image.format or "").upper()
                if image_format not in _PREVIEW_IMAGE_MIME_TYPES:
                    raise PdfResourceAccessError(str(path), "unsupported_preview_image")
                if getattr(image, "n_frames", 1) != 1:
                    raise PdfResourceAccessError(str(path), "animated_preview_image")
                if (
                    image.width > storage.image_upload_max_width()
                    or image.height > storage.image_upload_max_height()
                    or image.width * image.height > storage.image_upload_max_pixels()
                ):
                    raise PdfResourceAccessError(str(path), "preview_image_dimensions_exceeded")
                image.verify()
    except PdfResourceAccessError:
        raise
    except (Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise PdfResourceAccessError(str(path), "preview_image_dimensions_exceeded") from exc
    except (OSError, SyntaxError, UnidentifiedImageError, ValueError) as exc:
        raise PdfResourceAccessError(str(path), "invalid_preview_image") from exc

    try:
        content = path.read_bytes()
    except OSError as exc:
        raise PdfResourceAccessError(str(path), "file_unreadable") from exc
    encoded = base64.b64encode(content).decode("ascii")
    return f"data:{_PREVIEW_IMAGE_MIME_TYPES[image_format]};base64,{encoded}"


def _local_pdf_reference(reference: str, resolved_path: Path) -> str:
    # Sempre use URI absoluta: uma base URL sem barra final pode fazer o
    # renderer interpretar o diretório do projeto como se fosse um arquivo e
    # resolver ``assets/...`` um nível acima da raiz aprovada.
    return resolved_path.as_uri()


def _is_within_roots(path: Path, roots: tuple[Path, ...]) -> bool:
    return any(path == root or path.is_relative_to(root) for root in roots)
