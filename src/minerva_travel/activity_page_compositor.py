"""Deterministic overlays for printable progressive-guide activity pages.

OpenAI supplies the landmark-specific visual layer.  This module owns every
functional element whose spelling, geometry, or blank space must be exact.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import cast

from PIL import Image, ImageDraw, ImageFont, UnidentifiedImageError

PAGE_IMAGE_SIZE = (1024, 1536)
INK = "#153451"
MUTED_INK = "#42617a"
ACCENT = "#db8b45"
PAPER = "#fffdf8"
PANEL_OUTLINE = "#b9ccda"
COLORING_TITLE = "Atividade para colorir"
DETAIL_HUNT_TITLE = "Caça aos detalhes"
WORD_SEARCH_TITLE = "Caça-palavras"
DRAWING_TITLE = "Desenhe sua versão"
BEST_MEMORY_REQUIRED_COPY = (
    "Minha melhor memória",
    "Meu lugar favorito foi...",
    "O que eu mais gostei foi...",
    "Eu descobri que...",
    "Desenhe sua melhor lembrança",
    "Assinatura",
    "Data",
)

# These inner rectangles intentionally exclude captions and borders.  They are
# exported for semantic tests and for the final output validator.
DRAWING_BLANK_REGION = (106, 366, 918, 1260)
MEMORY_BLANK_REGION = (106, 670, 918, 1190)


class ActivityPageCompositionError(ValueError):
    """An activity specification or artwork cannot produce a usable page."""


def compose_coloring_page(
    artwork_path: Path,
    output_path: Path,
    *,
    landmark_name: str,
    instruction: str,
) -> Path:
    image = _load_artwork(artwork_path)
    draw = ImageDraw.Draw(image)
    _panel(draw, (38, 34, 986, 238))
    _draw_centered(draw, COLORING_TITLE, 66, 48, bold=True)
    _draw_centered(draw, _bounded(landmark_name, "landmark_name", 100), 134, 36, bold=True)
    _panel(draw, (54, 1350, 970, 1492))
    _draw_wrapped(
        draw,
        _bounded(instruction, "instruction", 240),
        (84, 1380, 940, 1470),
        font=_font(27),
        fill=INK,
        align="center",
    )
    # The simplifier emits pure black and white; thresholding after the exact
    # overlay also removes font antialiasing and guarantees printer-safe output.
    image = image.convert("L").point(lambda value: 0 if value < 210 else 255).convert("RGB")
    return _atomic_save(image, output_path, monochrome=True)


def compose_detail_hunt_page(
    artwork_path: Path,
    output_path: Path,
    *,
    landmark_name: str,
    instruction: str,
    clues: Sequence[str],
) -> Path:
    normalized_clues = _validated_items(clues, label="clues", minimum=2, maximum=6, item_max=150)
    image = _load_artwork(artwork_path)
    draw = ImageDraw.Draw(image)
    _panel(draw, (38, 34, 986, 252))
    _draw_centered(draw, DETAIL_HUNT_TITLE, 55, 55, bold=True)
    _draw_centered(draw, _bounded(landmark_name, "landmark_name", 100), 125, 31, bold=True)
    _draw_wrapped(
        draw,
        _bounded(instruction, "instruction", 240),
        (86, 173, 938, 236),
        font=_font(23),
        fill=MUTED_INK,
        align="center",
    )

    panel_top = 840
    _panel(draw, (54, panel_top, 970, 1490))
    draw.text((88, panel_top + 34), "Marque quando encontrar:", font=_font(28, bold=True), fill=INK)
    y = panel_top + 94
    item_height = min(92, (1450 - y) // len(normalized_clues))
    for clue in normalized_clues:
        draw.rounded_rectangle(
            (88, y + 7, 126, y + 45), radius=5, outline=INK, width=4, fill="white"
        )
        _draw_wrapped(
            draw,
            clue,
            (150, y, 922, y + item_height - 6),
            font=_font(24),
            fill=INK,
        )
        y += item_height
    return _atomic_save(image, output_path)


def compose_word_search_page(
    artwork_path: Path,
    output_path: Path,
    *,
    landmark_name: str,
    instruction: str,
    grid: Sequence[str],
    words: Sequence[str],
) -> Path:
    normalized_grid, normalized_words = _validate_word_search(grid, words)
    image = _load_artwork(artwork_path)
    draw = ImageDraw.Draw(image)
    _panel(draw, (38, 30, 986, 230))
    _draw_centered(draw, WORD_SEARCH_TITLE, 49, 55, bold=True)
    _draw_centered(draw, _bounded(landmark_name, "landmark_name", 100), 116, 30, bold=True)
    _draw_wrapped(
        draw,
        _bounded(instruction, "instruction", 240),
        (90, 163, 934, 218),
        font=_font(21),
        fill=MUTED_INK,
        align="center",
    )

    size = len(normalized_grid)
    cell = min(67, 700 // size)
    grid_width = cell * size
    left = (PAGE_IMAGE_SIZE[0] - grid_width) // 2
    top = 270
    _panel(draw, (left - 26, top - 26, left + grid_width + 26, top + grid_width + 26), radius=22)
    letter_font = _font(max(23, int(cell * 0.48)), bold=True)
    for row_index, row in enumerate(normalized_grid):
        for column_index, letter in enumerate(row):
            x0 = left + column_index * cell
            y0 = top + row_index * cell
            draw.rectangle((x0, y0, x0 + cell, y0 + cell), outline="#7898af", width=2)
            bbox = draw.textbbox((0, 0), letter, font=letter_font)
            x = x0 + (cell - (bbox[2] - bbox[0])) / 2
            y = y0 + (cell - (bbox[3] - bbox[1])) / 2 - bbox[1]
            draw.text((x, y), letter, font=letter_font, fill=INK)

    list_top = top + grid_width + 52
    list_bottom = min(1450, list_top + 260)
    _panel(draw, (78, list_top, 946, list_bottom))
    draw.text((112, list_top + 27), "Palavras para encontrar", font=_font(27, bold=True), fill=INK)
    word_font = _font(25, bold=True)
    columns = 2 if len(normalized_words) > 3 else 1
    column_width = 390 if columns == 2 else 760
    for index, word in enumerate(normalized_words):
        column = index % columns
        word_row = index // columns
        draw.text(
            (120 + column * column_width, list_top + 82 + word_row * 52),
            f"• {word}",
            font=word_font,
            fill=INK,
        )
    return _atomic_save(image, output_path)


def compose_drawing_page(
    artwork_path: Path,
    output_path: Path,
    *,
    landmark_name: str,
    prompt: str,
) -> Path:
    image = _load_artwork(artwork_path)
    draw = ImageDraw.Draw(image)
    _panel(draw, (38, 34, 986, 294))
    _draw_centered(draw, DRAWING_TITLE, 52, 53, bold=True)
    _draw_centered(draw, _bounded(landmark_name, "landmark_name", 100), 116, 30, bold=True)
    _draw_wrapped(
        draw,
        _bounded(prompt, "prompt", 300),
        (82, 166, 942, 274),
        font=_font(25),
        fill=MUTED_INK,
        align="center",
    )
    draw.rounded_rectangle((70, 330, 954, 1297), radius=28, fill="white", outline=INK, width=5)
    _panel(draw, (70, 1310, 954, 1488), radius=20)
    draw.text((96, 1325), "Título do meu desenho:", font=_font(24, bold=True), fill=INK)
    draw.line((354, 1356, 928, 1356), fill=INK, width=3)
    draw.text((96, 1401), "Data:", font=_font(23, bold=True), fill=INK)
    draw.line((172, 1431, 430, 1431), fill=INK, width=3)
    return _atomic_save(image, output_path, blank_regions=[DRAWING_BLANK_REGION])


def compose_best_memory_page(
    artwork_path: Path,
    output_path: Path,
    *,
    family_title: str,
    trip_date: str,
) -> Path:
    image = _load_artwork(artwork_path)
    draw = ImageDraw.Draw(image)
    _panel(draw, (38, 32, 986, 238))
    _draw_centered(draw, BEST_MEMORY_REQUIRED_COPY[0], 54, 57, bold=True)
    subtitle = " • ".join(part for part in (family_title, trip_date) if part)
    if subtitle:
        _draw_centered(draw, _bounded(subtitle, "trip subtitle", 180), 139, 27, bold=True)
    _draw_centered(draw, "Guarde aqui o momento mais especial da viagem.", 187, 22)

    _memory_line(draw, 278, BEST_MEMORY_REQUIRED_COPY[1])
    _memory_line(draw, 382, BEST_MEMORY_REQUIRED_COPY[2])
    _memory_line(draw, 486, BEST_MEMORY_REQUIRED_COPY[3])
    draw.rounded_rectangle((70, 590, 954, 1230), radius=28, fill="white", outline=INK, width=5)
    draw.text((96, 610), BEST_MEMORY_REQUIRED_COPY[4], font=_font(25, bold=True), fill=INK)
    _panel(draw, (55, 1255, 969, 1352), radius=20)
    draw.text((82, 1283), BEST_MEMORY_REQUIRED_COPY[5], font=_font(24, bold=True), fill=INK)
    draw.line((226, 1315, 600, 1315), fill=INK, width=3)
    draw.text((640, 1283), BEST_MEMORY_REQUIRED_COPY[6], font=_font(24, bold=True), fill=INK)
    draw.line((710, 1315, 940, 1315), fill=INK, width=3)
    _panel(draw, (170, 1370, 854, 1465), radius=20)
    _draw_centered(draw, "Uma lembrança para guardar para sempre.", 1400, 23, bold=True)
    return _atomic_save(image, output_path, blank_regions=[MEMORY_BLANK_REGION])


def validate_activity_page(
    path: Path,
    *,
    blank_regions: Sequence[tuple[int, int, int, int]] = (),
    monochrome: bool = False,
) -> None:
    """Validate the final output, including measurable writable space."""

    try:
        with Image.open(path) as opened:
            opened.verify()
        with Image.open(path) as opened:
            if opened.format != "PNG" or opened.size != PAGE_IMAGE_SIZE:
                raise ActivityPageCompositionError(
                    "A página de atividade não possui PNG 1024x1536."
                )
            image = opened.convert("RGB")
    except (UnidentifiedImageError, OSError) as error:
        raise ActivityPageCompositionError(
            "A página de atividade contém imagem inválida."
        ) from error

    if monochrome:
        colors = image.getcolors(maxcolors=PAGE_IMAGE_SIZE[0] * PAGE_IMAGE_SIZE[1])
        valid_colors = {(0, 0, 0), (255, 255, 255)}
        if colors is None or any(color not in valid_colors for _count, color in colors):
            raise ActivityPageCompositionError("A página de colorir não está em preto e branco.")
        color_counts = {color: count for count, color in colors}
        total = image.width * image.height
        black_fraction = color_counts.get((0, 0, 0), 0) / total
        white_fraction = color_counts.get((255, 255, 255), 0) / total
        if not 0.001 <= black_fraction <= 0.40 or white_fraction < 0.60:
            raise ActivityPageCompositionError(
                "A página de colorir não preservou áreas imprimíveis utilizáveis."
            )

    for region in blank_regions:
        _validate_blank_region(image, region)


def _memory_line(draw: ImageDraw.ImageDraw, top: int, label: str) -> None:
    draw.rounded_rectangle(
        (70, top, 954, top + 82),
        radius=18,
        fill="white",
        outline=PANEL_OUTLINE,
        width=4,
    )
    draw.text((92, top + 20), label, font=_font(23, bold=True), fill=INK)
    label_width = draw.textlength(label, font=_font(23, bold=True))
    draw.line((112 + label_width, top + 54, 924, top + 54), fill=INK, width=2)


def _validate_blank_region(image: Image.Image, region: tuple[int, int, int, int]) -> None:
    left, top, right, bottom = region
    if not (0 <= left < right <= image.width and 0 <= top < bottom <= image.height):
        raise ActivityPageCompositionError("A área de resposta está fora da página.")
    crop = image.crop(region)
    total = crop.width * crop.height
    colors = cast(
        list[tuple[int, tuple[int, int, int]]] | None,
        crop.getcolors(maxcolors=total),
    )
    white = (
        sum(
            count
            for count, (red, green, blue) in colors
            if red >= 248 and green >= 248 and blue >= 248
        )
        if colors is not None
        else 0
    )
    if not total or white / total < 0.98:
        raise ActivityPageCompositionError("A página não preservou espaço branco suficiente.")


def _validate_word_search(grid: Sequence[str], words: Sequence[str]) -> tuple[list[str], list[str]]:
    rows = [str(row).strip().upper() for row in grid]
    if not 8 <= len(rows) <= 14 or any(len(row) != len(rows) for row in rows):
        raise ActivityPageCompositionError("A grade do caça-palavras é inválida.")
    if any(not row.isascii() or not row.isalpha() for row in rows):
        raise ActivityPageCompositionError("A grade contém caracteres inválidos.")
    normalized_words = _validated_items(words, label="words", minimum=1, maximum=8, item_max=14)
    normalized_words = [word.upper() for word in normalized_words]
    columns = ["".join(row[index] for row in rows) for index in range(len(rows))]
    searchable = rows + columns
    if any(not any(word in line for line in searchable) for word in normalized_words):
        raise ActivityPageCompositionError("O caça-palavras contém palavra sem solução.")
    return rows, normalized_words


def _validated_items(
    items: Sequence[str], *, label: str, minimum: int, maximum: int, item_max: int
) -> list[str]:
    normalized = [" ".join(str(item).split()) for item in items]
    if not minimum <= len(normalized) <= maximum:
        raise ActivityPageCompositionError(f"Quantidade inválida em {label}.")
    if any(not item or len(item) > item_max for item in normalized):
        raise ActivityPageCompositionError(f"Conteúdo inválido em {label}.")
    if len(set(normalized)) != len(normalized):
        raise ActivityPageCompositionError(f"Itens duplicados em {label}.")
    return normalized


def _load_artwork(path: Path) -> Image.Image:
    try:
        with Image.open(path) as opened:
            if opened.format != "PNG" or opened.size != PAGE_IMAGE_SIZE:
                raise ActivityPageCompositionError("A arte-base não possui PNG 1024x1536.")
            return opened.convert("RGB")
    except (UnidentifiedImageError, OSError) as error:
        raise ActivityPageCompositionError("A arte-base da atividade é inválida.") from error


def _atomic_save(
    image: Image.Image,
    output_path: Path,
    *,
    blank_regions: Sequence[tuple[int, int, int, int]] = (),
    monochrome: bool = False,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_name(f".{output_path.name}.tmp")
    temporary.unlink(missing_ok=True)
    try:
        image.save(temporary, "PNG", optimize=True)
        validate_activity_page(temporary, blank_regions=blank_regions, monochrome=monochrome)
        temporary.replace(output_path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return output_path


def _panel(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    *,
    radius: int = 28,
) -> None:
    draw.rounded_rectangle(box, radius=radius, fill=PAPER, outline=PANEL_OUTLINE, width=4)


def _draw_centered(
    draw: ImageDraw.ImageDraw,
    text: str,
    y: int,
    size: int,
    *,
    bold: bool = False,
) -> None:
    font = _font(size, bold=bold)
    bbox = draw.textbbox((0, 0), text, font=font)
    x = (PAGE_IMAGE_SIZE[0] - (bbox[2] - bbox[0])) / 2
    draw.text((x, y), text, font=font, fill=INK)


def _draw_wrapped(
    draw: ImageDraw.ImageDraw,
    text: str,
    box: tuple[int, int, int, int],
    *,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    fill: str,
    align: str = "left",
) -> None:
    left, top, right, bottom = box
    lines = _wrap_text(draw, text, font, right - left)
    line_height = max(1, font.getbbox("Ág")[3] - font.getbbox("Ág")[1] + 8)
    if top + len(lines) * line_height > bottom:
        raise ActivityPageCompositionError("O texto não cabe na área reservada.")
    y: float = top
    for line in lines:
        line_width = draw.textlength(line, font=font)
        x = left if align == "left" else left + ((right - left) - line_width) / 2
        draw.text((x, y), line, font=font, fill=fill)
        y += line_height


def _wrap_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    max_width: int,
) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if draw.textlength(candidate, font=font) <= max_width:
            current = candidate
            continue
        if not current or draw.textlength(word, font=font) > max_width:
            raise ActivityPageCompositionError("Uma palavra não cabe na área reservada.")
        lines.append(current)
        current = word
    if current:
        lines.append(current)
    return lines


def _font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    names = ["DejaVuSans-Bold.ttf", "Arial Bold.ttf"] if bold else ["DejaVuSans.ttf", "Arial.ttf"]
    for name in names:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    # Pillow's built-in fallback is Unicode-capable in supported releases.
    return ImageFont.load_default(size=size)


def _bounded(value: str, label: str, maximum: int) -> str:
    normalized = " ".join(str(value).split())
    if not normalized or len(normalized) > maximum:
        raise ActivityPageCompositionError(f"Conteúdo inválido em {label}.")
    return normalized
