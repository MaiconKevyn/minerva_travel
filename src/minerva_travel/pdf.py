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
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen.canvas import Canvas

from minerva_travel import storage
from minerva_travel.models import GuideContext

TEMPLATE_DIR = Path(__file__).parent / "templates"
APPROVED_PAGE_IMAGE_SIZE = (1024, 1536)
APPROVED_PDF_PAGE_SIZE = (6 * inch, 9 * inch)

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


class ApprovedPagePdfError(ValueError):
    """An approved page sequence cannot be safely exported."""

    code = "approved_page_pdf_failed"


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
        # Cache global da arte estilizada dos pontos turisticos (por place_id);
        # derivado de referencias ja aprovadas, compartilhado entre pedidos.
        runtime_dir / "landmark-art",
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


def write_approved_page_images_pdf(
    image_paths: Iterable[Path],
    output_path: Path,
    *,
    title: str = "Guia Minerva Travel",
) -> Path:
    """Package approved 2:3 PNG pages into an atomic full-bleed PDF."""

    pages = tuple(Path(path) for path in image_paths)
    if not pages:
        raise ApprovedPagePdfError("O guia não possui páginas aprovadas para exportar.")
    for page in pages:
        _validate_approved_page_image(page)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_suffix(f"{output_path.suffix}.tmp")
    temporary.unlink(missing_ok=True)
    page_width, page_height = APPROVED_PDF_PAGE_SIZE
    try:
        document = Canvas(
            str(temporary),
            pagesize=APPROVED_PDF_PAGE_SIZE,
            pageCompression=1,
            invariant=1,
        )
        document.setTitle(title[:200] or "Guia Minerva Travel")
        document.setAuthor("Minerva Travel")
        document.setCreator("Minerva Travel")
        for page in pages:
            document.drawImage(
                ImageReader(str(page)),
                0,
                0,
                width=page_width,
                height=page_height,
                preserveAspectRatio=True,
                anchor="c",
            )
            document.showPage()
        document.save()
        with temporary.open("rb") as exported:
            has_pdf_header = exported.read(5) == b"%PDF-"
        if temporary.stat().st_size < 8 or not has_pdf_header:
            raise ApprovedPagePdfError("O compositor não produziu um PDF válido.")
        temporary.chmod(0o600)
        temporary.replace(output_path)
    except ApprovedPagePdfError:
        temporary.unlink(missing_ok=True)
        raise
    except (OSError, TypeError, ValueError, RuntimeError) as error:
        temporary.unlink(missing_ok=True)
        raise ApprovedPagePdfError(
            "Não foi possível montar o PDF das páginas aprovadas."
        ) from error
    return output_path


def _validate_approved_page_image(path: Path) -> None:
    try:
        with Image.open(path) as image:
            image.verify()
        with Image.open(path) as image:
            if image.format != "PNG" or image.size != APPROVED_PAGE_IMAGE_SIZE:
                raise ApprovedPagePdfError(
                    "Uma página aprovada não possui o formato ou as dimensões esperadas."
                )
    except ApprovedPagePdfError:
        raise
    except (FileNotFoundError, UnidentifiedImageError, OSError) as error:
        raise ApprovedPagePdfError("Uma página aprovada não está disponível.") from error


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
