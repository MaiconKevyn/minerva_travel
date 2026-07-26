"""Deterministic overlays for printable progressive-guide activity pages.

OpenAI supplies the landmark-specific visual layer.  This module owns every
functional element whose spelling, geometry, or blank space must be exact.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from pathlib import Path
from typing import cast

from PIL import Image, ImageDraw, ImageFont, UnidentifiedImageError

from minerva_travel.child_phrasebook import PHRASES_PER_PAGE, ChildPhrasebook
from minerva_travel.crossword import Crossword
from minerva_travel.dot_to_dot import DotToDot
from minerva_travel.investigator_activity import (
    InvestigatorChildProfile,
    InvestigatorMission,
)
from minerva_travel.maze import Maze
from minerva_travel.puzzles import (
    ANAGRAM_MAX_WORDS,
    ANAGRAM_MIN_WORDS,
    AnagramEntry,
    Cryptogram,
)

PAGE_IMAGE_SIZE = (1024, 1536)
INK = "#153451"
MUTED_INK = "#42617a"
ACCENT = "#db8b45"
PAPER = "#fffdf8"
PANEL_OUTLINE = "#b9ccda"
COLORING_TITLE = "Atividade para colorir"
COLORING_INSTRUCTION_TEMPLATE = "Agora é a vez de colorir {landmark_name} do seu jeito."
FAMILY_COLORING_TITLE = "Família de férias para colorir"
FAMILY_COLORING_INSTRUCTION_TEMPLATE = (
    "Agora é a vez de colorir a aventura da sua família em {landmark_name}."
)
DETAIL_HUNT_TITLE = "Caça aos detalhes"
WORD_SEARCH_TITLE = "Caça-palavras"
PAINTING_TITLE = "Minha pintura"
INVESTIGATOR_TITLE = "Investigador"
LANGUAGE_TITLE = "Sobrevivência no idioma"
POSTCARD_TITLE = "Cartão-postal"
POSTCARD_REGION = (600, 1480)
PASSPORT_TITLE = "Passaporte de viagem"
DOT_TO_DOT_TITLE = "Ligue os pontos"
CROSSWORD_TITLE = "Cruzadinha da viagem"
CROSSWORD_CLUE_HEIGHT = 84
MAZE_TITLE = "Labirinto"
MAZE_START_LABEL = "A"
MAZE_GOAL_LABEL = "B"
MAZE_WALL_WIDTH = 5
MAZE_PADDING = 26
ANAGRAM_TITLE = "Palavras embaralhadas"
CRYPTOGRAM_TITLE = "Código secreto"
NEWSPAPER_HEADLINE_TITLE = "Manchete do jornal"
TRAVEL_DIARY_TITLE = "Diário do dia"
HERE_VS_HOME_TITLE = "Aqui e na minha rua"

# Geometria única das páginas de escrever. Manchete, diário e comparação só
# diferem no texto: repetir três layouts quase iguais desalinharia as pautas
# entre as páginas do mesmo caderno.
WRITING_BODY_REGION = (54, 290, 970, 1496)
WRITING_LABEL_OFFSET = 22
WRITING_LABEL_BAND = 52
# Entre ~1,1 cm e ~1,8 cm impressos. A folga cresce até preencher a página:
# pauta apertada com um terço da folha vazio parece página inacabada.
WRITING_MIN_RULE_SPACING = 58
WRITING_MAX_RULE_SPACING = 104
WRITING_FIELD_PADDING = 16
WRITING_MIN_FIELD_GAP = 18
# Folga maior que isso solta os painéis uns dos outros e a página deixa de
# parecer uma folha só.
WRITING_MAX_FIELD_GAP = 56
WRITING_MAX_FIELDS = 5
INVESTIGATOR_INSTRUCTION = (
    "Cada criança tem uma missão secreta. Observem com atenção e trabalhem em equipe!"
)
BEST_MEMORY_REQUIRED_COPY = (
    "Minha melhor memória",
    "Meu lugar favorito foi...",
    "O que eu mais gostei foi...",
    "Eu descobri que...",
    "Desenhe sua melhor lembrança",
    "Assinatura",
    "Data",
)
HOMECOMING_REQUIRED_COPY = (
    "Hora de voltar para casa",
    "Nossa grande aventura está chegando ao fim.",
    "Depois de conhecer lugares incríveis, chegou a hora de voltar para casa.",
    "Mas todas essas lembranças vão continuar com a gente.",
    "Uma coisa que quero contar quando chegar em casa:",
)
LANDMARK_VISITED_LABEL = "Já visitei"
LANDMARK_VISITED_PANEL = (326, 1392, 698, 1500)
LANDMARK_VISITED_CHECKBOX = (366, 1423, 414, 1471)
COLORING_ART_REGION = (68, 342, 956, 1492)
COLORING_MIN_WHITE_FRACTION = 0.72

# These inner rectangles intentionally exclude captions and borders.  They are
# exported for semantic tests and for the final output validator.
DRAWING_BLANK_REGION = (106, 366, 918, 1260)
MEMORY_BLANK_REGION = (106, 670, 918, 1190)
HOMECOMING_WRITING_BLANK_REGIONS = (
    (92, 1295, 932, 1330),
    (92, 1350, 932, 1394),
    (92, 1415, 932, 1459),
)


class ActivityPageCompositionError(ValueError):
    """An activity specification or artwork cannot produce a usable page."""


def compose_landmark_visited_checkbox(artwork_path: Path, output_path: Path) -> Path:
    """Add the exact printable visit marker to a completed landmark page."""

    image = _load_artwork(artwork_path)
    draw = ImageDraw.Draw(image)
    _panel(draw, LANDMARK_VISITED_PANEL, radius=20)
    draw.rounded_rectangle(
        LANDMARK_VISITED_CHECKBOX,
        radius=5,
        fill="white",
        outline=INK,
        width=4,
    )
    draw.text((438, 1424), LANDMARK_VISITED_LABEL, font=_font(30, bold=True), fill=INK)
    return _atomic_save(image, output_path)


def compose_coloring_page(
    artwork_path: Path,
    output_path: Path,
    *,
    landmark_name: str,
) -> Path:
    normalized_name = _bounded(landmark_name, "landmark_name", 100)
    instruction = coloring_instruction_for(normalized_name)
    image = _layout_coloring_artwork(_load_artwork(artwork_path))
    _validate_coloring_artwork_density(image)
    draw = ImageDraw.Draw(image)
    _panel(draw, (38, 34, 986, 320))
    _draw_centered(draw, COLORING_TITLE, 54, 48, bold=True)
    _draw_centered_fit(draw, normalized_name, 116, 38, 22, 884, bold=True)
    _draw_wrapped(
        draw,
        instruction,
        (82, 180, 942, 302),
        font=_font(28),
        fill=INK,
        align="center",
    )
    # The simplifier emits pure black and white; thresholding after the exact
    # overlay also removes font antialiasing and guarantees printer-safe output.
    image = image.convert("L").point(lambda value: 0 if value < 210 else 255).convert("RGB")
    return _atomic_save(image, output_path, monochrome=True)


def coloring_instruction_for(landmark_name: str) -> str:
    """Return the exact child-facing instruction for a server-resolved point."""

    normalized_name = _bounded(landmark_name, "landmark_name", 100)
    return COLORING_INSTRUCTION_TEMPLATE.format(landmark_name=normalized_name)


def compose_family_coloring_page(
    artwork_path: Path,
    output_path: Path,
    *,
    family_title: str,
    landmark_name: str,
) -> Path:
    """Compose exact family-vacation copy over validated printable line art."""

    normalized_family = _bounded(family_title, "family_title", 100)
    normalized_landmark = _bounded(landmark_name, "landmark_name", 100)
    instruction = family_coloring_instruction_for(normalized_landmark)
    image = _layout_coloring_artwork(_load_artwork(artwork_path))
    _validate_coloring_artwork_density(image)
    draw = ImageDraw.Draw(image)
    _panel(draw, (38, 34, 986, 320))
    _draw_centered_fit(draw, FAMILY_COLORING_TITLE, 50, 50, 28, 884, bold=True)
    _draw_centered_fit(draw, normalized_family, 116, 34, 22, 884, bold=True)
    _draw_wrapped(
        draw,
        instruction,
        (82, 180, 942, 302),
        font=_font(27),
        fill=INK,
        align="center",
    )
    image = image.convert("L").point(lambda value: 0 if value < 210 else 255).convert("RGB")
    return _atomic_save(image, output_path, monochrome=True)


def family_coloring_instruction_for(landmark_name: str) -> str:
    """Return exact child-facing copy for the family vacation coloring page."""

    normalized_name = _bounded(landmark_name, "landmark_name", 100)
    return FAMILY_COLORING_INSTRUCTION_TEMPLATE.format(landmark_name=normalized_name)


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


def compose_investigator_page(
    artwork_path: Path,
    output_path: Path,
    *,
    family_title: str,
    landmark_name: str,
    children: Sequence[InvestigatorChildProfile],
    missions: Sequence[InvestigatorMission],
) -> Path:
    """Compose exact child-specific detective missions over a text-free visual layer."""

    if not 1 <= len(children) <= 10 or len(missions) != len(children):
        raise ActivityPageCompositionError("A página Investigador possui missões incompletas.")
    for index, (child, mission) in enumerate(zip(children, missions, strict=True), start=1):
        if mission.child_index != index or mission.child_name != child.name:
            raise ActivityPageCompositionError(
                "As missões não correspondem às crianças cadastradas."
            )

    family = _bounded(family_title, "family_title", 100)
    landmark = _bounded(landmark_name, "landmark_name", 100)
    image = _load_artwork(artwork_path)
    draw = ImageDraw.Draw(image)
    _panel(draw, (38, 30, 986, 300))
    _draw_centered(draw, INVESTIGATOR_TITLE, 46, 52, bold=True)
    _draw_centered_fit(draw, landmark, 111, 37, 22, 884, bold=True)
    _draw_centered_fit(draw, family, 163, 24, 17, 884, bold=True)
    _draw_wrapped(
        draw,
        INVESTIGATOR_INSTRUCTION,
        (86, 208, 938, 282),
        font=_font(21),
        fill=MUTED_INK,
        align="center",
    )

    columns = 1 if len(missions) == 1 else 2
    rows = math.ceil(len(missions) / columns)
    left = 54
    right = 970
    bottom = 1490
    gap_x = 16
    gap_y = 12
    available_height = 730
    row_height = min(240, (available_height - gap_y * (rows - 1)) // rows)
    grid_height = rows * row_height + gap_y * (rows - 1)
    top = bottom - grid_height
    column_width = (right - left - gap_x * (columns - 1)) // columns

    for index, (child, mission) in enumerate(zip(children, missions, strict=True)):
        row = index // columns
        column = index % columns
        x0 = left + column * (column_width + gap_x)
        y0 = top + row * (row_height + gap_y)
        _draw_investigator_mission_card(
            draw,
            (x0, y0, x0 + column_width, y0 + row_height),
            child=child,
            mission=mission,
            compact=rows >= 4,
        )
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
    _draw_centered(draw, PAINTING_TITLE, 52, 53, bold=True)
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
    draw.text((96, 1325), "Título da minha pintura:", font=_font(24, bold=True), fill=INK)
    draw.line((354, 1356, 928, 1356), fill=INK, width=3)
    draw.text((96, 1401), "Data:", font=_font(23, bold=True), fill=INK)
    draw.line((172, 1431, 430, 1431), fill=INK, width=3)
    return _atomic_save(image, output_path, blank_regions=[DRAWING_BLANK_REGION])


def compose_writing_page(
    artwork_path: Path,
    output_path: Path,
    *,
    title: str,
    subtitle: str,
    instruction: str,
    fields: Sequence[tuple[str, int]],
) -> Path:
    """Compose a ruled writing page from exact labels and line counts.

    ``fields`` pairs each printed label with how many ruled lines follow it.
    The page fails to build rather than silently cropping: a child who runs
    out of room mid-sentence is a worse outcome than a rejected layout.
    """

    normalized_fields = _validated_writing_fields(fields)
    image = _load_artwork(artwork_path)
    draw = ImageDraw.Draw(image)

    _panel(draw, (38, 34, 986, 262))
    _draw_centered_fit(draw, _bounded(title, "title", 60), 50, 52, 34, 884, bold=True)
    _draw_centered_fit(draw, _bounded(subtitle, "subtitle", 100), 122, 33, 20, 884, bold=True)
    _draw_wrapped(
        draw,
        _bounded(instruction, "instruction", 240),
        (82, 178, 942, 250),
        font=_font(24),
        fill=MUTED_INK,
        align="center",
    )

    left, top, right, bottom = WRITING_BODY_REGION
    spacing, gap = _writing_layout(normalized_fields)
    y = top
    blank_regions: list[tuple[int, int, int, int]] = []
    for label, rule_count in normalized_fields:
        height = _writing_field_height(rule_count, spacing)
        _panel(draw, (left, y, right, y + height), radius=22)
        draw.text((left + 34, y + WRITING_LABEL_OFFSET), label, font=_font(25, bold=True), fill=INK)
        first_rule = y + WRITING_LABEL_BAND + spacing
        for index in range(rule_count):
            rule_y = first_rule + index * spacing
            draw.line((left + 34, rule_y, right - 34, rule_y), fill=PANEL_OUTLINE, width=3)
        # Conferimos a faixa entre o rótulo e a primeira pauta: é escrita de
        # verdade e não contém régua, então dá para exigir branco puro ali.
        blank_regions.append((left + 40, y + WRITING_LABEL_BAND + 4, right - 40, first_rule - 6))
        y += height + gap

    if y - gap > bottom:
        raise ActivityPageCompositionError("Os campos de escrita não cabem na página.")
    return _atomic_save(image, output_path, blank_regions=blank_regions)


def _validated_writing_fields(fields: Sequence[tuple[str, int]]) -> list[tuple[str, int]]:
    normalized = [(" ".join(str(label).split()), int(count)) for label, count in fields]
    if not 1 <= len(normalized) <= WRITING_MAX_FIELDS:
        raise ActivityPageCompositionError("Quantidade inválida de campos de escrita.")
    if any(not label or len(label) > 90 for label, _count in normalized):
        raise ActivityPageCompositionError("Rótulo inválido em um campo de escrita.")
    if any(not 1 <= count <= 6 for _label, count in normalized):
        raise ActivityPageCompositionError("Número de linhas inválido em um campo de escrita.")
    if len({label for label, _count in normalized}) != len(normalized):
        raise ActivityPageCompositionError("Rótulos duplicados nos campos de escrita.")
    _writing_layout(normalized)
    return normalized


def _writing_layout(fields: Sequence[tuple[str, int]]) -> tuple[int, int]:
    """Pick the rule spacing and field gap that fill the page without overflowing.

    Linhas mais largas cabem letras maiores, então a folga cresce até o teto
    antes de sobrar espaço em branco no rodapé.
    """

    _left, top, _right, bottom = WRITING_BODY_REGION
    available = bottom - top
    rules = sum(count for _label, count in fields)
    fixed = len(fields) * (WRITING_LABEL_BAND + WRITING_FIELD_PADDING)
    slack = available - fixed - WRITING_MIN_FIELD_GAP * (len(fields) - 1)
    if slack < rules * WRITING_MIN_RULE_SPACING:
        raise ActivityPageCompositionError("Os campos de escrita não cabem na página.")

    spacing = min(WRITING_MAX_RULE_SPACING, slack // rules)
    used = fixed + rules * spacing
    gaps = max(1, len(fields) - 1)
    gap = min(WRITING_MAX_FIELD_GAP, (available - used) // gaps)
    return spacing, max(WRITING_MIN_FIELD_GAP, gap)


def _writing_field_height(rule_count: int, spacing: int) -> int:
    return WRITING_LABEL_BAND + rule_count * spacing + WRITING_FIELD_PADDING


def compose_language_page(
    artwork_path: Path,
    output_path: Path,
    *,
    country: str,
    instruction: str,
    phrasebook: ChildPhrasebook,
) -> Path:
    """One card per phrase: what to say, how to read it, and what it means."""

    if len(phrasebook.phrases) != PHRASES_PER_PAGE:
        raise ActivityPageCompositionError("O guia de frases está incompleto.")

    image = _load_artwork(artwork_path)
    draw = ImageDraw.Draw(image)
    _panel(draw, (38, 30, 986, 268))
    _draw_centered_fit(draw, LANGUAGE_TITLE, 46, 50, 30, 884, bold=True)
    _draw_centered_fit(
        draw,
        f"{phrasebook.language} • {_bounded(country, 'country', 90)}",
        118,
        32,
        20,
        884,
        bold=True,
    )
    _draw_wrapped(
        draw,
        _bounded(instruction, "instruction", 240),
        (82, 178, 942, 256),
        font=_font(23),
        fill=MUTED_INK,
        align="center",
    )

    top, bottom = 306, 1490
    height = (bottom - top) // PHRASES_PER_PAGE
    for index, phrase in enumerate(phrasebook.phrases):
        y = top + index * height
        _panel(draw, (54, y, 970, y + height - 16), radius=20)
        _draw_wrapped(
            draw,
            phrase.phrase,
            (92, y + 20, 932, y + 78),
            font=_font(36, bold=True),
            fill=INK,
        )
        # A pronúncia é o que a criança realmente fala; fica destacada.
        draw.text((92, y + 92), f"fale assim: {phrase.pronunciation}",
                  font=_font(25, bold=True), fill=ACCENT)
        draw.text((92, y + 142), phrase.meaning, font=_font(23), fill=MUTED_INK)
    return _atomic_save(image, output_path)


def compose_postcard_page(
    artwork_path: Path,
    output_path: Path,
    *,
    landmark_name: str,
    instruction: str,
    sender: str,
) -> Path:
    """Lay out a real postcard back: message on the left, address on the right.

    A arte do ponto turístico fica na metade de cima como a frente do cartão;
    a criança escreve embaixo, recorta e o cartão pode ser postado de verdade.
    """

    image = _load_artwork(artwork_path)
    draw = ImageDraw.Draw(image)
    _panel(draw, (38, 30, 986, 252))
    _draw_centered_fit(draw, POSTCARD_TITLE, 46, 50, 32, 884, bold=True)
    _draw_centered_fit(draw, _bounded(landmark_name, "landmark_name", 100), 116, 31, 20, 884,
                       bold=True)
    _draw_wrapped(
        draw,
        _bounded(instruction, "instruction", 240),
        (82, 170, 942, 242),
        font=_font(23),
        fill=MUTED_INK,
        align="center",
    )

    # Linha de corte: o cartão precisa sair da folha para ser postado.
    top, bottom = POSTCARD_REGION
    for x in range(60, 964, 22):
        draw.line((x, top - 18, x + 12, top - 18), fill=MUTED_INK, width=2)
    draw.text((60, top - 46), "Recorte aqui", font=_font(19), fill=MUTED_INK)

    _panel(draw, (54, top, 970, bottom), radius=18)
    middle = 512
    draw.line((middle, top + 28, middle, bottom - 28), fill=PANEL_OUTLINE, width=3)

    draw.text((92, top + 26), "Mensagem:", font=_font(24, bold=True), fill=INK)
    for index in range(6):
        rule_y = top + 122 + index * 78
        draw.line((92, rule_y, middle - 40, rule_y), fill=PANEL_OUTLINE, width=3)
    draw.text((92, bottom - 66), f"De: {_bounded(sender, 'sender', 80)}",
              font=_font(21, bold=True), fill=MUTED_INK)

    stamp = (middle + 300, top + 30, middle + 430, top + 190)
    draw.rounded_rectangle(stamp, radius=8, outline=MUTED_INK, width=3)
    _draw_centered_fit_box(draw, "SELO", (stamp[0] + 8, stamp[1] + 60, stamp[2] - 8, stamp[3] - 60),
                           maximum_size=22, minimum_size=14, bold=True)
    draw.text((middle + 40, top + 232), "Para:", font=_font(24, bold=True), fill=INK)
    for index in range(4):
        rule_y = top + 322 + index * 78
        draw.line((middle + 40, rule_y, 932, rule_y), fill=PANEL_OUTLINE, width=3)
    return _atomic_save(image, output_path)


def compose_passport_page(
    artwork_path: Path,
    output_path: Path,
    *,
    country: str,
    instruction: str,
    child_name: str,
) -> Path:
    """A passport page per country, with a frame to glue the real ticket in."""

    image = _load_artwork(artwork_path)
    draw = ImageDraw.Draw(image)
    _panel(draw, (38, 30, 986, 268))
    _draw_centered_fit(draw, PASSPORT_TITLE, 46, 50, 32, 884, bold=True)
    _draw_centered_fit(draw, _bounded(country, "country", 100).upper(), 116, 40, 22, 884,
                       bold=True)
    _draw_wrapped(
        draw,
        _bounded(instruction, "instruction", 240),
        (82, 178, 942, 256),
        font=_font(23),
        fill=MUTED_INK,
        align="center",
    )

    _panel(draw, (54, 306, 970, 512), radius=22)
    draw.text((92, 332), "Passaporte de:", font=_font(24, bold=True), fill=INK)
    draw.text((92, 382), _bounded(child_name, "child_name", 90), font=_font(34, bold=True),
              fill=INK)
    draw.text((92, 452), "Cheguei no dia:", font=_font(22, bold=True), fill=MUTED_INK)
    draw.line((320, 482, 620, 482), fill=PANEL_OUTLINE, width=3)

    # Moldura tracejada: espaço declarado para colar o bilhete ou o carimbo real.
    frame = (54, 556, 970, 1240)
    _panel(draw, frame, radius=22)
    inner = (frame[0] + 40, frame[1] + 78, frame[2] - 40, frame[3] - 40)
    draw.text((frame[0] + 40, frame[1] + 26), "Cole aqui o bilhete ou o carimbo:",
              font=_font(24, bold=True), fill=INK)
    _draw_dashed_rectangle(draw, inner, dash=22, gap=16)

    _panel(draw, (54, 1284, 970, 1490), radius=22)
    draw.text((92, 1310), "O que eu mais gostei neste país:", font=_font(24, bold=True), fill=INK)
    for index in range(2):
        draw.line((92, 1396 + index * 74, 932, 1396 + index * 74), fill=PANEL_OUTLINE, width=3)
    return _atomic_save(image, output_path)


def _draw_dashed_rectangle(
    draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], *, dash: int, gap: int
) -> None:
    left, top, right, bottom = box
    step = dash + gap
    for x in range(left, right, step):
        end = min(x + dash, right)
        draw.line((x, top, end, top), fill=MUTED_INK, width=3)
        draw.line((x, bottom, end, bottom), fill=MUTED_INK, width=3)
    for y in range(top, bottom, step):
        end = min(y + dash, bottom)
        draw.line((left, y, left, end), fill=MUTED_INK, width=3)
        draw.line((right, y, right, end), fill=MUTED_INK, width=3)


def compose_dot_to_dot_page(
    artwork_path: Path,
    output_path: Path,
    *,
    landmark_name: str,
    instruction: str,
    puzzle: DotToDot,
) -> Path:
    """Print the numbered dots over a clean sheet, scaled into the page."""

    image = _load_artwork(artwork_path)
    draw = ImageDraw.Draw(image)
    _puzzle_header(draw, DOT_TO_DOT_TITLE, landmark_name, instruction)

    region = (70, 300, 954, 1470)
    left, top, right, bottom = region
    _panel(draw, region, radius=22)
    scale = min((right - left - 96) / puzzle.width, (bottom - top - 96) / puzzle.height)
    offset_x = left + ((right - left) - puzzle.width * scale) / 2
    offset_y = top + ((bottom - top) - puzzle.height * scale) / 2

    number_font = _font(24, bold=True)
    for index, (x, y) in enumerate(puzzle.points, start=1):
        center_x = offset_x + x * scale
        center_y = offset_y + y * scale
        draw.ellipse(
            (center_x - 5, center_y - 5, center_x + 5, center_y + 5), fill=INK, outline=INK
        )
        # Número deslocado para fora do ponto: em cima dele, o lápis da criança
        # apagaria a referência assim que ela começasse a ligar.
        draw.text((center_x + 10, center_y - 30), str(index), font=number_font, fill=MUTED_INK)
    return _atomic_save(image, output_path)


def compose_crossword_page(
    artwork_path: Path,
    output_path: Path,
    *,
    landmark_name: str,
    instruction: str,
    crossword: Crossword,
) -> Path:
    """Draw the interlocked grid with start numbers, then the two clue lists."""

    image = _load_artwork(artwork_path)
    draw = ImageDraw.Draw(image)
    _puzzle_header(draw, CROSSWORD_TITLE, landmark_name, instruction)

    letters = crossword.letters
    cell = min(62, 760 // max(crossword.columns, 1), 520 // max(crossword.rows, 1))
    if cell < 30:
        raise ActivityPageCompositionError("A cruzadinha não cabe na página impressa.")
    width, height = cell * crossword.columns, cell * crossword.rows
    left = (PAGE_IMAGE_SIZE[0] - width) // 2
    top = 300
    _panel(draw, (left - 24, top - 24, left + width + 24, top + height + 24), radius=22)

    numbers = {(entry.column, entry.row): entry.number for entry in crossword.entries}
    number_font = _font(max(11, cell // 4), bold=True)
    for (column, row) in letters:
        x, y = left + column * cell, top + row * cell
        draw.rectangle((x, y, x + cell, y + cell), fill="white", outline=INK, width=3)
        number = numbers.get((column, row))
        if number is not None:
            draw.text((x + 5, y + 3), str(number), font=number_font, fill=MUTED_INK)

    clues_top = top + height + 52
    tallest = max(len(crossword.across), len(crossword.down))
    clues_height = 96 + tallest * CROSSWORD_CLUE_HEIGHT
    if clues_top + clues_height > 1490:
        raise ActivityPageCompositionError("As dicas da cruzadinha não cabem na página.")
    _panel(draw, (54, clues_top, 970, clues_top + clues_height), radius=22)
    _draw_crossword_clues(draw, crossword, top=clues_top + 26)
    return _atomic_save(image, output_path)


def _draw_crossword_clues(draw: ImageDraw.ImageDraw, crossword: Crossword, *, top: int) -> None:
    label_font, clue_font = _font(24, bold=True), _font(21)
    for index, (title, entries) in enumerate(
        (("Horizontais", crossword.across), ("Verticais", crossword.down))
    ):
        column_left = 92 + index * 452
        draw.text((column_left, top), title, font=label_font, fill=INK)
        y = top + 44
        for entry in entries:
            _draw_wrapped(
                draw,
                f"{entry.number}. {entry.clue}",
                (column_left, y, column_left + 388, y + 78),
                font=clue_font,
                fill=INK,
            )
            y += CROSSWORD_CLUE_HEIGHT


def compose_maze_page(
    artwork_path: Path,
    output_path: Path,
    *,
    landmark_name: str,
    instruction: str,
    maze: Maze,
) -> Path:
    """Draw the maze walls plus the labelled start and finish."""

    image = _load_artwork(artwork_path)
    draw = ImageDraw.Draw(image)
    _puzzle_header(draw, MAZE_TITLE, landmark_name, instruction)

    region_top, region_bottom = 306, 1436
    cell = min(
        (970 - 54 - 2 * MAZE_PADDING) // maze.columns,
        (region_bottom - region_top - 2 * MAZE_PADDING) // maze.rows,
    )
    if cell < 24:
        raise ActivityPageCompositionError("O labirinto não cabe na página impressa.")
    width, height = cell * maze.columns, cell * maze.rows
    left = (PAGE_IMAGE_SIZE[0] - width) // 2
    top = region_top + (region_bottom - region_top - height) // 2
    _panel(
        draw,
        (
            left - MAZE_PADDING,
            top - MAZE_PADDING,
            left + width + MAZE_PADDING,
            top + height + MAZE_PADDING,
        ),
        radius=22,
    )

    for row in range(maze.rows):
        for column in range(maze.columns):
            x, y = left + column * cell, top + row * cell
            if maze.has_wall_right(column, row) and column < maze.columns - 1:
                draw.line((x + cell, y, x + cell, y + cell), fill=INK, width=MAZE_WALL_WIDTH)
            if maze.has_wall_down(column, row) and row < maze.rows - 1:
                draw.line((x, y + cell, x + cell, y + cell), fill=INK, width=MAZE_WALL_WIDTH)
    # A borda externa fecha o labirinto; as aberturas de entrada e saída são
    # desenhadas por cima para a criança ver por onde começar.
    draw.rectangle((left, top, left + width, top + height), outline=INK, width=MAZE_WALL_WIDTH)
    draw.line(
        (left, top + 3, left, top + cell - 3), fill=PAPER, width=MAZE_WALL_WIDTH + 2
    )
    draw.line(
        (
            left + width,
            top + height - cell + 3,
            left + width,
            top + height - 3,
        ),
        fill=PAPER,
        width=MAZE_WALL_WIDTH + 2,
    )

    _draw_maze_marker(draw, left, top, cell, maze.start, MAZE_START_LABEL)
    _draw_maze_marker(draw, left, top, cell, maze.goal, MAZE_GOAL_LABEL)
    return _atomic_save(image, output_path)


def _draw_maze_marker(
    draw: ImageDraw.ImageDraw,
    left: int,
    top: int,
    cell: int,
    position: tuple[int, int],
    label: str,
) -> None:
    column, row = position
    x, y = left + column * cell, top + row * cell
    draw.rounded_rectangle(
        (x + 4, y + 4, x + cell - 4, y + cell - 4), radius=6, fill=ACCENT, outline=ACCENT
    )
    _draw_centered_fit_box(
        draw,
        label,
        (x + 5, y + 5, x + cell - 5, y + cell - 5),
        maximum_size=max(12, cell // 2),
        minimum_size=10,
        bold=True,
    )


def compose_anagram_page(
    artwork_path: Path,
    output_path: Path,
    *,
    landmark_name: str,
    instruction: str,
    entries: Sequence[AnagramEntry],
) -> Path:
    """Print scrambled travel words with one lettered box per answer letter."""

    if not ANAGRAM_MIN_WORDS <= len(entries) <= ANAGRAM_MAX_WORDS:
        raise ActivityPageCompositionError("O anagrama não possui palavras suficientes.")

    image = _load_artwork(artwork_path)
    draw = ImageDraw.Draw(image)
    _puzzle_header(draw, ANAGRAM_TITLE, landmark_name, instruction)

    top, bottom = 300, 1490
    row_height = min(206, (bottom - top) // len(entries))
    for index, entry in enumerate(entries):
        y = top + index * row_height
        _panel(draw, (54, y, 970, y + row_height - 16), radius=22)
        draw.text((92, y + 22), entry.scrambled, font=_font(46, bold=True), fill=ACCENT)
        _draw_answer_boxes(draw, entry.answer, top=y + 88, hint=entry.hint)
    return _atomic_save(image, output_path)


def _draw_answer_boxes(draw: ImageDraw.ImageDraw, answer: str, *, top: int, hint: str) -> None:
    size = min(58, 820 // max(len(answer), 1))
    left = 92
    for position, _letter in enumerate(answer):
        x = left + position * (size + 8)
        draw.rounded_rectangle(
            (x, top, x + size, top + size), radius=6, fill="white", outline=INK, width=3
        )
    # A primeira letra vem impressa: sem ela a criança trava na palavra maior.
    bbox = draw.textbbox((0, 0), hint, font=_font(int(size * 0.62), bold=True))
    draw.text(
        (left + (size - (bbox[2] - bbox[0])) / 2, top + (size - (bbox[3] - bbox[1])) / 2 - bbox[1]),
        hint,
        font=_font(int(size * 0.62), bold=True),
        fill=MUTED_INK,
    )


def compose_cryptogram_page(
    artwork_path: Path,
    output_path: Path,
    *,
    landmark_name: str,
    instruction: str,
    puzzle: Cryptogram,
) -> Path:
    """Print the coded sentence plus the partial legend that unlocks it."""

    image = _load_artwork(artwork_path)
    draw = ImageDraw.Draw(image)
    _puzzle_header(draw, CRYPTOGRAM_TITLE, landmark_name, instruction)

    legend_top = 300
    revealed = set(puzzle.revealed)
    columns = 9
    cell = 92
    legend_rows = math.ceil(len(puzzle.legend) / columns)
    _panel(draw, (54, legend_top, 970, legend_top + 96 + legend_rows * 74), radius=22)
    draw.text(
        (92, legend_top + 22), "Chave secreta (algumas já vêm prontas):",
        font=_font(25, bold=True), fill=INK,
    )
    for index, (letter, code) in enumerate(puzzle.legend):
        column, row = index % columns, index // columns
        x = 92 + column * cell
        y = legend_top + 76 + row * 74
        draw.rounded_rectangle(
            (x, y, x + 62, y + 46), radius=6, fill="white", outline=PANEL_OUTLINE, width=3
        )
        _draw_centered_fit_box(
            draw,
            letter if letter in revealed else "?",
            (x + 4, y + 4, x + 58, y + 42),
            maximum_size=28,
            minimum_size=16,
            bold=True,
        )
        _draw_centered_fit_box(
            draw, str(code), (x, y + 48, x + 62, y + 70), maximum_size=22, minimum_size=14
        )

    phrase_top = legend_top + 96 + legend_rows * 74 + 40
    rows = _cryptogram_rows(puzzle)
    phrase_height = 96 + rows * CRYPTOGRAM_ROW_HEIGHT
    if phrase_top + phrase_height > 1490:
        raise ActivityPageCompositionError("A frase secreta não cabe na página.")
    _panel(draw, (54, phrase_top, 970, phrase_top + phrase_height), radius=22)
    draw.text((92, phrase_top + 26), "A frase secreta:", font=_font(25, bold=True), fill=INK)
    _draw_cryptogram_phrase(draw, puzzle, top=phrase_top + 96)

    # Decifrar letra por letra deixa a frase picotada; copiá-la inteira é o
    # fecho da atividade e ocupa o rodapé que sobraria em branco.
    answer_top = phrase_top + phrase_height + 40
    _panel(draw, (54, answer_top, 970, min(1490, answer_top + 300)), radius=22)
    draw.text(
        (92, answer_top + 26),
        "Agora escreva a frase inteira:",
        font=_font(25, bold=True),
        fill=INK,
    )
    for index in range(2):
        rule_y = answer_top + 152 + index * 84
        draw.line((92, rule_y, 932, rule_y), fill=PANEL_OUTLINE, width=3)
    return _atomic_save(image, output_path)


CRYPTOGRAM_CELL = 56
CRYPTOGRAM_CELL_GAP = 8
CRYPTOGRAM_ROW_HEIGHT = CRYPTOGRAM_CELL + 48
CRYPTOGRAM_LEFT = 92
CRYPTOGRAM_RIGHT = 932


def _cryptogram_cells(puzzle: Cryptogram) -> list[tuple[str, int, int, int]]:
    """Place every coded letter on a grid, breaking rows between words.

    Quebrar uma palavra no meio da linha faria a criança procurar a
    continuação; palavras inteiras mantêm a frase legível.
    """

    per_row = (CRYPTOGRAM_RIGHT - CRYPTOGRAM_LEFT + CRYPTOGRAM_CELL_GAP) // (
        CRYPTOGRAM_CELL + CRYPTOGRAM_CELL_GAP
    )
    placed: list[tuple[str, int, int, int]] = []
    column = row = 0
    for word in puzzle.phrase.split(" "):
        length = len(word)
        if length > per_row:
            raise ActivityPageCompositionError("Uma palavra da frase secreta é longa demais.")
        if column and column + length > per_row:
            column, row = 0, row + 1
        for letter in word:
            code = next(code for char, code in puzzle.legend if char == letter)
            placed.append((letter, code, column, row))
            column += 1
        column += 1  # espaço entre palavras
    return placed


def _cryptogram_rows(puzzle: Cryptogram) -> int:
    return max(row for _letter, _code, _column, row in _cryptogram_cells(puzzle)) + 1


def _draw_cryptogram_phrase(draw: ImageDraw.ImageDraw, puzzle: Cryptogram, *, top: int) -> None:
    revealed = set(puzzle.revealed)
    for letter, code, column, row in _cryptogram_cells(puzzle):
        x = CRYPTOGRAM_LEFT + column * (CRYPTOGRAM_CELL + CRYPTOGRAM_CELL_GAP)
        y = top + row * CRYPTOGRAM_ROW_HEIGHT
        draw.rounded_rectangle(
            (x, y, x + CRYPTOGRAM_CELL, y + CRYPTOGRAM_CELL),
            radius=6,
            fill="white",
            outline=INK,
            width=3,
        )
        if letter in revealed:
            _draw_centered_fit_box(
                draw,
                letter,
                (x + 4, y + 4, x + CRYPTOGRAM_CELL - 4, y + CRYPTOGRAM_CELL - 4),
                maximum_size=34,
                minimum_size=18,
                bold=True,
            )
        _draw_centered_fit_box(
            draw,
            str(code),
            (x, y + CRYPTOGRAM_CELL + 4, x + CRYPTOGRAM_CELL, y + CRYPTOGRAM_CELL + 34),
            maximum_size=24,
            minimum_size=14,
        )


def _puzzle_header(
    draw: ImageDraw.ImageDraw, title: str, landmark_name: str, instruction: str
) -> None:
    _panel(draw, (38, 30, 986, 268))
    _draw_centered_fit(draw, title, 48, 52, 34, 884, bold=True)
    _draw_centered_fit(draw, _bounded(landmark_name, "landmark_name", 100), 120, 32, 20, 884,
                       bold=True)
    _draw_wrapped(
        draw,
        _bounded(instruction, "instruction", 240),
        (82, 178, 942, 256),
        font=_font(23),
        fill=MUTED_INK,
        align="center",
    )


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


def compose_homecoming_page(artwork_path: Path, output_path: Path) -> Path:
    """Add exact closing copy and a writable reflection field to homecoming artwork."""

    image = _load_artwork(artwork_path)
    draw = ImageDraw.Draw(image)
    _panel(draw, (38, 34, 986, 388))
    _draw_centered(draw, HOMECOMING_REQUIRED_COPY[0], 54, 50, bold=True)
    _draw_wrapped(
        draw,
        HOMECOMING_REQUIRED_COPY[1],
        (82, 132, 942, 178),
        font=_font(25, bold=True),
        fill=INK,
        align="center",
    )
    _draw_wrapped(
        draw,
        HOMECOMING_REQUIRED_COPY[2],
        (82, 194, 942, 270),
        font=_font(23),
        fill=INK,
        align="center",
    )
    _draw_wrapped(
        draw,
        HOMECOMING_REQUIRED_COPY[3],
        (82, 286, 942, 354),
        font=_font(24, bold=True),
        fill=INK,
        align="center",
    )

    _panel(draw, (54, 1172, 970, 1492))
    _draw_wrapped(
        draw,
        HOMECOMING_REQUIRED_COPY[4],
        (84, 1203, 940, 1282),
        font=_font(25, bold=True),
        fill=INK,
        align="center",
    )
    for y in (1340, 1405, 1470):
        draw.line((92, y, 932, y), fill=INK, width=3)
    return _atomic_save(
        image,
        output_path,
        blank_regions=HOMECOMING_WRITING_BLANK_REGIONS,
    )


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
        if (
            not 0.001 <= black_fraction <= (1 - COLORING_MIN_WHITE_FRACTION)
            or white_fraction < COLORING_MIN_WHITE_FRACTION
        ):
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


def _draw_investigator_mission_card(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    *,
    child: InvestigatorChildProfile,
    mission: InvestigatorMission,
    compact: bool,
) -> None:
    left, top, right, bottom = box
    _panel(draw, box, radius=18 if compact else 24)
    age = f" • {child.age} anos" if child.age is not None else ""
    _draw_centered_fit_box(
        draw,
        f"Missão de {child.name}{age}",
        (left + 14, top + 7, right - 14, top + (32 if compact else 42)),
        maximum_size=18 if compact else 22,
        minimum_size=12,
        bold=True,
    )
    separator_y = top + (35 if compact else 47)
    draw.line((left + 18, separator_y, right - 18, separator_y), fill=PANEL_OUTLINE, width=2)
    task = f"Pista: {mission.clue} Missão: {mission.mission}"
    _draw_wrapped_fit(
        draw,
        task,
        (left + 18, separator_y + 7, right - 18, bottom - 31),
        maximum_size=18 if compact else 21,
        minimum_size=11,
        fill=INK,
    )
    checkbox_size = 18 if compact else 22
    checkbox_right = right - 86
    checkbox_top = bottom - checkbox_size - 7
    draw.rounded_rectangle(
        (
            checkbox_right - checkbox_size,
            checkbox_top,
            checkbox_right,
            checkbox_top + checkbox_size,
        ),
        radius=3,
        fill="white",
        outline=INK,
        width=2,
    )
    draw.text(
        (checkbox_right + 7, checkbox_top - 3),
        "Concluí",
        font=_font(13 if compact else 16, bold=True),
        fill=INK,
    )


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


def _layout_coloring_artwork(image: Image.Image) -> Image.Image:
    """Fit only the generated line art below the trusted heading area."""

    monochrome = image.convert("L").point(lambda value: 0 if value < 210 else 255)
    black_mask = monochrome.point(lambda value: 255 if value < 128 else 0)
    bbox = black_mask.getbbox()
    canvas = Image.new("L", PAGE_IMAGE_SIZE, 255)
    if bbox is None:
        return canvas.convert("RGB")

    padding = 24
    left = max(0, bbox[0] - padding)
    top = max(0, bbox[1] - padding)
    right = min(monochrome.width, bbox[2] + padding)
    bottom = min(monochrome.height, bbox[3] + padding)
    subject = monochrome.crop((left, top, right, bottom))
    region_left, region_top, region_right, region_bottom = COLORING_ART_REGION
    subject.thumbnail(
        (region_right - region_left, region_bottom - region_top),
        Image.Resampling.LANCZOS,
    )
    subject = subject.point(lambda value: 0 if value < 210 else 255)
    x = region_left + ((region_right - region_left) - subject.width) // 2
    y = region_top + ((region_bottom - region_top) - subject.height) // 2
    canvas.paste(subject, (x, y))
    return canvas.convert("RGB")


def _validate_coloring_artwork_density(image: Image.Image) -> None:
    region = image.crop(COLORING_ART_REGION).convert("L")
    total = region.width * region.height
    colors = cast(list[tuple[int, int]] | None, region.getcolors(maxcolors=256))
    black = sum(count for count, value in colors or [] if value < 128)
    black_fraction = black / total if total else 0
    if not 0.003 <= black_fraction <= 0.28:
        raise ActivityPageCompositionError(
            "O desenho para colorir não possui traços infantis utilizáveis."
        )


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


def _draw_centered_fit(
    draw: ImageDraw.ImageDraw,
    text: str,
    y: int,
    maximum_size: int,
    minimum_size: int,
    maximum_width: int,
    *,
    bold: bool = False,
) -> None:
    for size in range(maximum_size, minimum_size - 1, -1):
        font = _font(size, bold=bold)
        bbox = draw.textbbox((0, 0), text, font=font)
        width = bbox[2] - bbox[0]
        if width <= maximum_width:
            draw.text(((PAGE_IMAGE_SIZE[0] - width) / 2, y), text, font=font, fill=INK)
            return
    raise ActivityPageCompositionError("O nome do ponto turístico não cabe no título.")


def _draw_centered_fit_box(
    draw: ImageDraw.ImageDraw,
    text: str,
    box: tuple[int, int, int, int],
    *,
    maximum_size: int,
    minimum_size: int,
    bold: bool = False,
) -> None:
    left, top, right, bottom = box
    for size in range(maximum_size, minimum_size - 1, -1):
        font = _font(size, bold=bold)
        bbox = draw.textbbox((0, 0), text, font=font)
        width = bbox[2] - bbox[0]
        height = bbox[3] - bbox[1]
        if width <= right - left and height <= bottom - top:
            x = left + ((right - left) - width) / 2
            y = top + ((bottom - top) - height) / 2 - bbox[1]
            draw.text((x, y), text, font=font, fill=INK)
            return
    raise ActivityPageCompositionError("O nome da criança não cabe no cartão de missão.")


def _draw_wrapped_fit(
    draw: ImageDraw.ImageDraw,
    text: str,
    box: tuple[int, int, int, int],
    *,
    maximum_size: int,
    minimum_size: int,
    fill: str,
) -> None:
    left, top, right, bottom = box
    for size in range(maximum_size, minimum_size - 1, -1):
        font = _font(size)
        try:
            lines = _wrap_text(draw, text, font, right - left)
        except ActivityPageCompositionError:
            continue
        line_height = max(1, font.getbbox("Ág")[3] - font.getbbox("Ág")[1] + 5)
        if top + len(lines) * line_height > bottom:
            continue
        y: float = top
        for line in lines:
            draw.text((left, y), line, font=font, fill=fill)
            y += line_height
        return
    raise ActivityPageCompositionError("A missão não cabe no cartão da criança.")


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
