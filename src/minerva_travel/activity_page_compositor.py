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

from minerva_travel import visual_identity as identidade
from minerva_travel.child_phrasebook import PHRASES_PER_PAGE, ChildPhrasebook
from minerva_travel.crossword import Crossword
from minerva_travel.dot_to_dot import DotToDot
from minerva_travel.flight_vocabulary import WORDS_PER_PAGE, FlightVocabulary
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
from minerva_travel.spot_the_difference import DifferenceRegion
from minerva_travel.word_search import locate_words

PAGE_IMAGE_SIZE = (1024, 1536)
# As cores vem de `visual_identity`, que e a fonte unica da identidade.
INK = identidade.PETROLEO
MUTED_INK = identidade.SOMBRA
ACCENT = identidade.TERRACOTA
PAPER = identidade.PAPEL
# Ocre suave em vez do azul-acinzentado: as réguas e molduras passam a ser as
# mesmas do guia impresso que serve de referência do produto.
PANEL_OUTLINE = identidade.CREME
# A faixa chapada onde o tipo assenta, nas paginas ilustradas.
BAND = identidade.CREME
HIGHLIGHT = identidade.MOSTARDA
CARD_TINT = identidade.ROSA
_PAPEL_RGB = tuple(int(PAPER[i : i + 2], 16) for i in (1, 3, 5))
# Folga so para o antisserrilhado da tipografia, nao para deixar arte passar.
_TOLERANCIA_PAPEL = 4
# Vermelho do gabarito: nunca aparece na página que a criança recebe, só na
# versão resolvida que mostramos como exemplo no seletor.
SOLUTION_INK = identidade.TERRACOTA
SOLUTION_WIDTH = 7
# Faixa translúcida em vez de risco cheio: riscar por cima apagava as letras
# justamente na hora de conferir se a palavra está certa.
SOLUTION_HIGHLIGHT = (192, 57, 43, 76)
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
SPOT_DIFFERENCE_TITLE = "Ache os erros"
# A cena dos erros é a única arte gerada deitada, em 3:2, e o painel impresso
# tem exatamente a mesma proporção: nada é cortado. Antes a arte vinha em pé
# (1024x1536) e o painel largo obrigava um corte central que jogava fora 65%
# da altura — a Torre Eiffel saía sem pico e sem base, e quatro dos seis
# objetos plantados para o jogo nem chegavam à página.
SPOT_SCENE_SIZE = (1536, 1024)
SPOT_PANEL_SIZE = (780, 520)
SPOT_PANEL_GAP = 20
SPOT_PANEL_TOP = 288
SPOT_PANEL_LEFT = (PAGE_IMAGE_SIZE[0] - SPOT_PANEL_SIZE[0]) // 2
LANGUAGE_TITLE = "Sobrevivência no idioma"
# O idioma entra no título: "Primeiras palavras" sozinho não diz de qual país
# é a página, e num guia com dois países há duas delas.
FLIGHT_VOCABULARY_TITLE_PREFIX = "Primeiras palavras em"


def flight_vocabulary_title(language: str) -> str:
    return f"{FLIGHT_VOCABULARY_TITLE_PREFIX} {language}"


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
# A pagina ilustrada nao tem janela nem faixa: a arte cobre a folha inteira e
# o texto assenta em cima dela, nas zonas que o prompt mantem calmas. Foi a
# janela deitada que abriu os dois cortes horizontais na pagina.
SCENE_TEXT_LEFT = 76
SCENE_TEXT_RIGHT = PAGE_IMAGE_SIZE[0] - 76
SCENE_NOTES_TOP = 352
SCENE_TEXT_BOTTOM = 900
SCENE_CARD_RADIUS = 30
SCENE_STAR_RADIUS = 17
PAGE_TEXT_LEFT = 76
PAGE_TEXT_RIGHT = PAGE_IMAGE_SIZE[0] - 76
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


def _draw_visited_marker(draw: ImageDraw.ImageDraw) -> None:
    _panel(draw, LANDMARK_VISITED_PANEL, radius=20)
    draw.rounded_rectangle(
        LANDMARK_VISITED_CHECKBOX,
        radius=5,
        fill="white",
        outline=INK,
        width=4,
    )
    draw.text((438, 1424), LANDMARK_VISITED_LABEL, font=_font(30, bold=True), fill=INK)


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
    solution: bool = False,
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
            draw.rectangle((x0, y0, x0 + cell, y0 + cell), outline=PANEL_OUTLINE, width=2)
            bbox = draw.textbbox((0, 0), letter, font=letter_font)
            x = x0 + (cell - (bbox[2] - bbox[0])) / 2
            y = y0 + (cell - (bbox[3] - bbox[1])) / 2 - bbox[1]
            draw.text((x, y), letter, font=letter_font, fill=INK)

    if solution:
        image = _highlight_found_words(
            image, normalized_grid, normalized_words, left=left, top=top, cell=cell
        )
        draw = ImageDraw.Draw(image)

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


def _highlight_found_words(
    image: Image.Image,
    grid: Sequence[str],
    words: Sequence[str],
    *,
    left: int,
    top: int,
    cell: int,
) -> Image.Image:
    """Band each found word in translucent red, letters still readable through it."""

    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    painter = ImageDraw.Draw(overlay)
    inset = max(3, cell // 10)
    for row, column, row_end, column_end in locate_words(list(grid), list(words)):
        painter.rounded_rectangle(
            (
                left + column * cell + inset,
                top + row * cell + inset,
                left + (column_end + 1) * cell - inset,
                top + (row_end + 1) * cell - inset,
            ),
            radius=cell // 2,
            fill=SOLUTION_HIGHLIGHT,
        )
    return Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")


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


def compose_spot_the_difference_page(
    base_path: Path,
    variant_path: Path,
    output_path: Path,
    *,
    landmark_name: str,
    instruction: str,
    regions: Sequence[DifferenceRegion],
) -> Path:
    """Stack the two scenes with a counted checklist the child ticks off."""

    if not regions:
        raise ActivityPageCompositionError("A página de erros não tem diferenças confirmadas.")

    base = _load_panel_scene(base_path)
    variant = _load_panel_scene(variant_path)
    if base.size != variant.size:
        raise ActivityPageCompositionError("As duas cenas não têm o mesmo recorte.")
    image = Image.new("RGB", PAGE_IMAGE_SIZE, PAPER)
    draw = ImageDraw.Draw(image)
    _puzzle_header(draw, SPOT_DIFFERENCE_TITLE, landmark_name, instruction)

    panel_width, panel_height = SPOT_PANEL_SIZE
    left = SPOT_PANEL_LEFT
    for index, scene in enumerate((base, variant)):
        top = SPOT_PANEL_TOP + index * (panel_height + SPOT_PANEL_GAP)
        image.paste(scene.resize(SPOT_PANEL_SIZE, Image.LANCZOS), (left, top))
        draw.rectangle((left, top, left + panel_width, top + panel_height), outline=INK, width=4)
        badge = "1" if index == 0 else "2"
        draw.ellipse((left + 10, top + 10, left + 58, top + 58), fill=ACCENT, outline=ACCENT)
        _draw_centered_fit_box(
            draw,
            badge,
            (left + 14, top + 14, left + 54, top + 54),
            maximum_size=28,
            minimum_size=16,
            bold=True,
        )

    checklist_top = SPOT_PANEL_TOP + 2 * (panel_height + SPOT_PANEL_GAP)
    _panel(draw, (54, checklist_top, 970, 1500), radius=22)
    draw.text(
        (92, checklist_top + 22),
        f"Marque cada diferença que encontrar ({len(regions)} no total):",
        font=_font(24, bold=True),
        fill=INK,
    )
    # Uma linha só: com duas, a sétima caixa era desenhada abaixo da borda do
    # painel e saía cortada na página impressa.
    box_size = 44
    for index in range(len(regions)):
        x = 92 + index * 105
        y = checklist_top + 68
        draw.rounded_rectangle(
            (x, y, x + box_size, y + box_size), radius=6, outline=INK, width=4, fill="white"
        )
        draw.text((x + box_size + 10, y + 8), str(index + 1), font=_font(26, bold=True), fill=INK)
    return _atomic_save(image, output_path)


def _load_panel_scene(path: Path) -> Image.Image:
    """Load a scene already cropped to the panel aspect by crop_scene_for_panel."""

    try:
        with Image.open(path) as opened:
            if opened.format != "PNG":
                raise ActivityPageCompositionError("A cena dos erros não é PNG.")
            scene = opened.convert("RGB")
    except (UnidentifiedImageError, OSError) as error:
        raise ActivityPageCompositionError("A cena dos erros é inválida.") from error
    panel_width, panel_height = SPOT_PANEL_SIZE
    if abs(scene.width / scene.height - panel_width / panel_height) > 0.02:
        raise ActivityPageCompositionError("A cena dos erros não tem o recorte do painel.")
    return scene


def crop_scene_for_panel(artwork_path: Path, output_path: Path) -> Path:
    """Normalise the wide scene to the printed panel's aspect, before validation.

    A cena é pedida em 3:2, a mesma proporção do painel, então na prática nada
    é cortado. O corte continua aqui como rede: se o provedor devolver outra
    proporção, é melhor perder uma faixa do que imprimir a cena esticada.
    Validar antes de recortar contaria diferenças que a criança nunca veria.
    """

    try:
        with Image.open(artwork_path) as opened:
            if opened.format != "PNG" or opened.size != SPOT_SCENE_SIZE:
                raise ActivityPageCompositionError(
                    f"A cena dos erros não possui PNG {SPOT_SCENE_SIZE[0]}x{SPOT_SCENE_SIZE[1]}."
                )
            scene = opened.convert("RGB")
    except (UnidentifiedImageError, OSError) as error:
        raise ActivityPageCompositionError("A cena dos erros é inválida.") from error

    width, height = scene.size
    panel_width, panel_height = SPOT_PANEL_SIZE
    crop_height = min(height, round(width * panel_height / panel_width))
    top = (height - crop_height) // 2
    scene.crop((0, top, width, top + crop_height)).save(output_path, "PNG")
    return output_path


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
        draw.text(
            (92, y + 92),
            f"fale assim: {phrase.pronunciation}",
            font=_font(25, bold=True),
            fill=ACCENT,
        )
        draw.text((92, y + 142), phrase.meaning, font=_font(23), fill=MUTED_INK)
    return _atomic_save(image, output_path)


def compose_flight_vocabulary_page(
    artwork_path: Path,
    output_path: Path,
    *,
    vocabulary: FlightVocabulary,
    instruction: str,
) -> Path:
    """As primeiras palavras do país, para treinar antes de pousar.

    Uma linha por palavra: como se escreve, como se fala e o que quer dizer.
    O quadradinho no fim não é enfeite — é o que transforma a lista numa
    atividade, porque a criança volta à página para marcar o que já falou.
    """

    if len(vocabulary.words) != WORDS_PER_PAGE:
        raise ActivityPageCompositionError("A lista de palavras está incompleta.")

    image = _load_artwork(artwork_path)
    draw = ImageDraw.Draw(image)
    _panel(draw, (38, 30, 986, 268))
    _draw_centered_fit(
        draw,
        flight_vocabulary_title(vocabulary.language),
        46,
        50,
        28,
        884,
        bold=True,
    )
    _draw_centered_fit(
        draw,
        _bounded(vocabulary.country, "country", 90),
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
    height = (bottom - top) // WORDS_PER_PAGE
    for index, entry in enumerate(vocabulary.words):
        y = top + index * height
        _panel(draw, (54, y, 970, y + height - 14), radius=18)
        _draw_wrapped(
            draw,
            entry.word,
            (88, y + 14, 590, y + 70),
            font=_font(31, bold=True),
            fill=INK,
        )
        # A pronúncia é o que a criança realmente fala; fica destacada.
        draw.text(
            (88, y + 76),
            f"fale assim: {entry.pronunciation}",
            font=_font(23, bold=True),
            fill=ACCENT,
        )
        _draw_wrapped(
            draw,
            entry.meaning,
            (546, y + 30, 892, y + height - 30),
            font=_font(23),
            fill=MUTED_INK,
        )
        draw.rounded_rectangle(
            (912, y + 40, 950, y + 78), radius=5, outline=INK, width=4, fill="white"
        )
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
    _draw_centered_fit(
        draw, _bounded(landmark_name, "landmark_name", 100), 116, 31, 20, 884, bold=True
    )
    _draw_wrapped(
        draw,
        _bounded(instruction, "instruction", 240),
        (82, 170, 942, 242),
        font=_font(23),
        fill=MUTED_INK,
        align="center",
    )

    # Linha de corte: o cartão precisa sair da folha para ser postado. Ela cai
    # em cima da ilustração, então ganha uma tarja clara própria — sem isso a
    # instrução some contra a aquarela e ninguém sabe onde cortar.
    top, bottom = POSTCARD_REGION
    draw.rectangle((38, top - 56, 986, top - 8), fill=PAPER)
    for x in range(60, 964, 22):
        draw.line((x, top - 18, x + 12, top - 18), fill=MUTED_INK, width=3)
    draw.text((60, top - 50), "Recorte aqui", font=_font(19, bold=True), fill=MUTED_INK)

    _panel(draw, (54, top, 970, bottom), radius=18)
    middle = 512
    draw.line((middle, top + 28, middle, bottom - 28), fill=PANEL_OUTLINE, width=3)

    draw.text((92, top + 26), "Mensagem:", font=_font(24, bold=True), fill=INK)
    for index in range(6):
        rule_y = top + 122 + index * 78
        draw.line((92, rule_y, middle - 40, rule_y), fill=PANEL_OUTLINE, width=3)
    draw.text(
        (92, bottom - 66),
        f"De: {_bounded(sender, 'sender', 80)}",
        font=_font(21, bold=True),
        fill=MUTED_INK,
    )

    stamp = (middle + 300, top + 30, middle + 430, top + 190)
    draw.rounded_rectangle(stamp, radius=8, outline=MUTED_INK, width=3)
    _draw_centered_fit_box(
        draw,
        "SELO",
        (stamp[0] + 8, stamp[1] + 60, stamp[2] - 8, stamp[3] - 60),
        maximum_size=22,
        minimum_size=14,
        bold=True,
    )
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
    _draw_centered_fit(draw, _bounded(country, "country", 100).upper(), 116, 40, 22, 884, bold=True)
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
    draw.text(
        (92, 382), _bounded(child_name, "child_name", 90), font=_font(34, bold=True), fill=INK
    )
    draw.text((92, 452), "Cheguei no dia:", font=_font(22, bold=True), fill=MUTED_INK)
    draw.line((320, 482, 620, 482), fill=PANEL_OUTLINE, width=3)

    # Moldura tracejada: espaço declarado para colar o bilhete ou o carimbo real.
    frame = (54, 556, 970, 1240)
    _panel(draw, frame, radius=22)
    inner = (frame[0] + 40, frame[1] + 78, frame[2] - 40, frame[3] - 40)
    draw.text(
        (frame[0] + 40, frame[1] + 26),
        "Cole aqui o bilhete ou o carimbo:",
        font=_font(24, bold=True),
        fill=INK,
    )
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
    solution: bool = False,
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

    if solution:
        draw.line(
            [
                (offset_x + x * scale, offset_y + y * scale)
                for x, y in (*puzzle.points, puzzle.points[0])
            ],
            fill=SOLUTION_INK,
            width=SOLUTION_WIDTH,
            joint="curve",
        )

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
    solution: bool = False,
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
    for column, row in letters:
        x, y = left + column * cell, top + row * cell
        draw.rectangle((x, y, x + cell, y + cell), fill="white", outline=INK, width=3)
        number = numbers.get((column, row))
        if number is not None:
            draw.text((x + 5, y + 3), str(number), font=number_font, fill=MUTED_INK)
        if solution:
            _draw_centered_fit_box(
                draw,
                letters[(column, row)],
                (x + 6, y + int(cell * 0.28), x + cell - 6, y + cell - 6),
                maximum_size=max(16, int(cell * 0.5)),
                minimum_size=12,
                bold=True,
            )

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
    solution: bool = False,
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
    draw.line((left, top + 3, left, top + cell - 3), fill=PAPER, width=MAZE_WALL_WIDTH + 2)
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

    if solution:
        draw.line(
            [
                (left + column * cell + cell // 2, top + row * cell + cell // 2)
                for column, row in maze.solution
            ],
            fill=SOLUTION_INK,
            width=max(4, cell // 6),
            joint="curve",
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
        (92, legend_top + 22),
        "Chave secreta (algumas já vêm prontas):",
        font=_font(25, bold=True),
        fill=INK,
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
    _draw_centered_fit(
        draw, _bounded(landmark_name, "landmark_name", 100), 120, 32, 20, 884, bold=True
    )
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
    # "Limpo" e a cor do PAPEL desta identidade, nao branco puro. Fixar 248 em
    # cada canal amarrava a checagem ao creme antigo (#fffdf8) e reprovava
    # qualquer paleta mais quente — o que importa e que nada foi desenhado
    # aqui, e nao qual e o tom do papel.
    limpo = (
        sum(
            count
            for count, (red, green, blue) in colors
            if red >= _PAPEL_RGB[0] - _TOLERANCIA_PAPEL
            and green >= _PAPEL_RGB[1] - _TOLERANCIA_PAPEL
            and blue >= _PAPEL_RGB[2] - _TOLERANCIA_PAPEL
        )
        if colors is not None
        else 0
    )
    if not total or limpo / total < 0.98:
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
    fill: str = INK,
) -> None:
    font = _font(size, bold=bold)
    bbox = draw.textbbox((0, 0), text, font=font)
    x = (PAGE_IMAGE_SIZE[0] - (bbox[2] - bbox[0])) / 2
    draw.text((x, y), text, font=font, fill=fill)


def _draw_centered_fit(
    draw: ImageDraw.ImageDraw,
    text: str,
    y: int,
    maximum_size: int,
    minimum_size: int,
    maximum_width: int,
    *,
    bold: bool = False,
    maximum_height: int | None = None,
) -> None:
    """Titulo centrado, em uma linha; em duas quando o nome e comprido demais.

    Sem a segunda linha o titulo simplesmente estourava e a pagina virava
    impossivel de gerar — e nao para nomes inventados: "Santuario Nacional de
    Nossa Senhora da Conceicao Aparecida" nao cabe em uma linha, nem
    "Familia Wanderley Mendonca de Albuquerque Filho".
    """

    for size in range(maximum_size, minimum_size - 1, -1):
        font = _font(size, bold=bold)
        bbox = draw.textbbox((0, 0), text, font=font)
        width = bbox[2] - bbox[0]
        if width <= maximum_width:
            draw.text(((PAGE_IMAGE_SIZE[0] - width) / 2, y), text, font=font, fill=INK)
            return

    for size in range(maximum_size, minimum_size - 1, -1):
        font = _font(size, bold=bold)
        linhas = _split_in_two(draw, text, font, maximum_width)
        if linhas is None:
            continue
        altura = font.getbbox("Ág")[3] - font.getbbox("Ág")[1] + 8
        # A segunda linha precisa caber no espaco reservado, senao ela desce
        # em cima da linha em arco logo abaixo do titulo.
        if maximum_height is not None and 2 * altura > maximum_height:
            continue
        for indice, linha in enumerate(linhas):
            largura = draw.textbbox((0, 0), linha, font=font)[2]
            draw.text(
                ((PAGE_IMAGE_SIZE[0] - largura) / 2, y + indice * altura),
                linha,
                font=font,
                fill=INK,
            )
        return
    raise ActivityPageCompositionError("O nome não cabe no título nem em duas linhas.")


def _split_in_two(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    maximum_width: int,
) -> list[str] | None:
    """Quebra o titulo no espaco que deixa as duas linhas mais parecidas."""

    palavras = text.split()
    if len(palavras) < 2:
        return None
    melhor: tuple[float, list[str]] | None = None
    for corte in range(1, len(palavras)):
        primeira = " ".join(palavras[:corte])
        segunda = " ".join(palavras[corte:])
        larguras = [draw.textbbox((0, 0), linha, font=font)[2] for linha in (primeira, segunda)]
        if max(larguras) > maximum_width:
            continue
        desequilibrio = abs(larguras[0] - larguras[1])
        if melhor is None or desequilibrio < melhor[0]:
            melhor = (desequilibrio, [primeira, segunda])
    return melhor[1] if melhor else None


def _shared_fit_size(
    draw: ImageDraw.ImageDraw,
    textos: Sequence[str],
    *,
    maximum_size: int,
    minimum_size: int,
    maximum_width: int,
) -> int:
    """O maior corpo em que TODOS os textos cabem, para a lista falar igual."""

    for size in range(maximum_size, minimum_size - 1, -1):
        font = _font(size, bold=True)
        if all(draw.textlength(texto, font=font) <= maximum_width for texto in textos):
            return size
    raise ActivityPageCompositionError("O nome da parada não cabe no roteiro.")


def _draw_numbered_bullet(
    draw: ImageDraw.ImageDraw,
    numero: str,
    anchor: tuple[float, float],
) -> None:
    left, middle = anchor
    raio = SUMMARY_BULLET_RADIUS
    draw.ellipse((left, middle - raio, left + 2 * raio, middle + raio), fill=ACCENT)
    fonte = _font(24, bold=True)
    caixa = draw.textbbox((0, 0), numero, font=fonte)
    draw.text(
        (
            left + raio - (caixa[2] - caixa[0]) / 2 - caixa[0],
            middle - (caixa[3] - caixa[1]) / 2 - caixa[1],
        ),
        numero,
        font=fonte,
        fill=PAPER,
    )


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


def _wrapped_block(
    draw: ImageDraw.ImageDraw,
    text: str,
    width: int,
    *,
    maximum_size: int,
    minimum_size: int,
) -> tuple[int, list[str], int]:
    """Corpo, linhas e altura do texto embrulhado nesta largura."""

    for size in range(maximum_size, minimum_size - 1, -1):
        font = _font(size)
        try:
            linhas = _wrap_text(draw, text, font, width)
        except ActivityPageCompositionError:
            continue
        altura = int(max(1, font.getbbox("Ág")[3] - font.getbbox("Ág")[1] + 5))
        return size, linhas, len(linhas) * altura
    raise ActivityPageCompositionError("O texto não cabe no cartão.")


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
    """Zilla Slab, versionada no repositorio.

    Antes isto caia na DejaVu do sistema: sem relacao com a identidade e
    diferente de maquina para maquina, o que fazia a mesma pagina sair com
    metrica distinta em cada ambiente.
    """

    caminho = identidade.FONTE_SEMIBOLD if bold else identidade.FONTE_REGULAR
    try:
        return ImageFont.truetype(str(caminho), size)
    except OSError:
        pass
    names = ["DejaVuSans-Bold.ttf", "Arial Bold.ttf"] if bold else ["DejaVuSans.ttf", "Arial.ttf"]
    for name in names:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    # Pillow's built-in fallback is Unicode-capable in supported releases.
    return ImageFont.load_default(size=size)


def _draw_tracked(
    draw: ImageDraw.ImageDraw,
    text: str,
    y: int,
    *,
    size: int,
    fill: str,
    left: int | None = None,
    tracking: float = 0.16,
    maximum_width: int | None = None,
) -> float:
    """Caixa alta espacada, letra a letra, devolvendo a largura ocupada.

    Encolhe ate caber. Sem isso a sobrelinha de uma familia de nome longo com
    uma data longa saia pelos dois lados da pagina, cortada pela borda.
    """

    limite = maximum_width if maximum_width is not None else PAGE_TEXT_RIGHT - PAGE_TEXT_LEFT
    for corpo in range(size, 13, -1):
        fonte = _font(corpo, bold=True)
        larguras = [fonte.getlength(letra) + corpo * tracking for letra in text]
        if sum(larguras) <= limite:
            size = corpo
            break
    fonte = _font(size, bold=True)
    larguras = [fonte.getlength(letra) + size * tracking for letra in text]
    total = sum(larguras)
    x = float(left) if left is not None else (PAGE_IMAGE_SIZE[0] - total) / 2
    for letra, largura in zip(text, larguras, strict=True):
        draw.text((x, y), letra, font=fonte, fill=fill)
        x += largura
    return total


def _bounded(value: str, label: str, maximum: int) -> str:
    normalized = " ".join(str(value).split())
    if not normalized or len(normalized) > maximum:
        raise ActivityPageCompositionError(f"Conteúdo inválido em {label}.")
    return normalized


# O limite do arco e o quanto ele SOBE, nao o angulo. Com teto de 150 graus e
# raio 400, as pontas subiam 296 px: a data de uma viagem longa dava a volta no
# titulo da capa e saia pelas bordas. Medido em pixels, o arco continua arco.
_ARCO_SUBIDA_MAXIMA = 56
# Abaixo disto o texto em arco fica menor que o corpo do rodape e ilegivel.
_ARCO_CORPO_MINIMO = 15
# Teto do titulo em duas linhas nas paginas ilustradas. Medido: com 148 a
# segunda linha parava a 13 px do arco e encostava nele; com 120 sobram 41.
TITULO_ALTURA_MAXIMA = 120
# O brasao da capa mora no terco de cima, nao no meio. No meio ele atravessava
# a cabeca das pessoas: pedir que a familia inteira coubesse abaixo de 62% da
# altura espremia quatro pessoas no rodape, e o modelo cedia. Acima delas, o
# tipo tem ceu de sobra e a familia fica com dois tercos da folha.
COVER_LOCKUP_TOP = 300
COVER_LOCKUP_BOTTOM = 508


def _abertura_maxima(radius: int) -> float:
    """Angulo em que as pontas do arco sobem exatamente _ARCO_SUBIDA_MAXIMA."""

    if radius <= _ARCO_SUBIDA_MAXIMA:
        return math.pi
    return 2 * math.acos(1 - _ARCO_SUBIDA_MAXIMA / radius)


def _shrunk_to_arc(
    text: str,
    size: int,
    radius: int,
    tracking: float,
) -> tuple[int, ImageFont.FreeTypeFont | ImageFont.ImageFont, list[float]] | None:
    """Menor corpo em que o texto ainda cabe no arco, ou None se nem assim cabe."""

    limite = _abertura_maxima(radius)
    for corpo in range(size - 1, _ARCO_CORPO_MINIMO - 1, -1):
        fonte = _font(corpo, bold=True)
        larguras = [fonte.getlength(letra) + corpo * tracking for letra in text]
        if sum(larguras) / radius <= limite:
            return corpo, fonte, larguras
    return None


def _draw_straight_fallback(
    image: Image.Image,
    text: str,
    center: tuple[int, int],
    radius: int,
    size: int,
    fill: str,
    *,
    below: bool,
) -> None:
    """Ultimo recurso: a linha reta, na altura em que o arco seria lido."""

    linha = center[1] + radius if below else center[1] - radius
    draw = ImageDraw.Draw(image)
    for corpo in range(size, _ARCO_CORPO_MINIMO - 1, -1):
        fonte = _font(corpo, bold=True)
        largura = draw.textlength(text, font=fonte)
        if largura <= PAGE_IMAGE_SIZE[0] - 2 * 76:
            draw.text(((PAGE_IMAGE_SIZE[0] - largura) / 2, linha), text, font=fonte, fill=fill)
            return


def _arc_text(
    image: Image.Image,
    text: str,
    *,
    center: tuple[int, int],
    radius: int,
    size: int,
    fill: str,
    below: bool = False,
    tracking: float = 0.14,
) -> None:
    """Escreve o texto curvado sobre um arco, glifo a glifo.

    E o gesto que assina a referencia: a linha secundaria correndo em arco
    sobre e sob o titulo. O PIL nao tem texto em caminho, entao cada letra e
    desenhada isolada, girada para a tangente e colada na posicao.

    O angulo vem da LARGURA do texto, nunca de um valor fixo: com raio fixo,
    "Familia Knopp - Setembro de 2026" estourava o arco e saia cortada, o que
    ja aconteceu no primeiro esboco desta identidade.
    """

    fonte = _font(size, bold=True)
    letras = list(text)
    espaco = size * tracking
    larguras = [fonte.getlength(letra) + espaco for letra in letras]
    total = sum(larguras)
    if total <= 0 or radius <= 0:
        return

    # Comprimento de arco -> angulo. Texto largo abre mais o arco, e nunca
    # transborda porque o arco se ajusta a ele.
    abertura = total / radius
    if abertura > _abertura_maxima(radius):
        # Encolher antes de desistir. Sumir em silencio era o pior desfecho:
        # `timing` e texto livre do usuario, entao "Ultima semana de setembro
        # e primeira de outubro de 2026" apagava a data da capa sem erro.
        encolhido = _shrunk_to_arc(text, size, radius, tracking)
        if encolhido is None:
            _draw_straight_fallback(image, text, center, radius, size, fill, below=below)
            return
        size, fonte, larguras = encolhido
        espaco = size * tracking
        total = sum(larguras)
        abertura = total / radius

    cx, cy = center
    # Para cima o texto corre da esquerda para a direita sobre o topo do
    # circulo; para baixo, o sentido se inverte para as letras nao ficarem
    # de cabeca para baixo.
    sentido = 1 if not below else -1
    angulo = -abertura / 2

    for letra, largura in zip(letras, larguras, strict=True):
        meio = angulo + largura / (2 * radius)
        if letra.strip():
            caixa = fonte.getbbox(letra)
            largura_glifo = max(1, int(caixa[2] - caixa[0]))
            altura_glifo = max(1, int(caixa[3] - caixa[1]))
            selo = Image.new("RGBA", (largura_glifo + 4, altura_glifo + 4), (0, 0, 0, 0))
            ImageDraw.Draw(selo).text((-caixa[0] + 2, -caixa[1] + 2), letra, font=fonte, fill=fill)
            girado = selo.rotate(
                -math.degrees(meio) * sentido,
                resample=Image.Resampling.BICUBIC,
                expand=True,
            )
            x = cx + radius * math.sin(meio)
            y = cy - sentido * radius * math.cos(meio)
            image.paste(girado, (round(x - girado.width / 2), round(y - girado.height / 2)), girado)
        angulo += largura / radius


def compose_cover_page(
    artwork_path: Path,
    output_path: Path,
    *,
    family_title: str,
    trip_date: str,
) -> Path:
    """Imprime o brasao da capa sobre a arte, no lugar de deixar a IA escrever.

    A tipografia desenhada pelo modelo saia numa familia diferente a cada
    geracao, entao capa e paginas de atividade falavam com vozes distintas no
    mesmo livro. Aqui ela vem da mesma fonte que o resto do caderno.

    O arco de cima e o de baixo sao circunferencias DISTINTAS, cada uma com o
    proprio centro: o apice de uma e o fundo da outra precisam cair onde a
    linha deve ser lida. Derivar os dois de um centro so amontoava as tres
    linhas no mesmo ponto.
    """

    image = _load_artwork(artwork_path)
    titulo = _bounded(family_title, "family_title", 60)
    data = _bounded(trip_date, "trip_date", 60)

    centro_x = PAGE_IMAGE_SIZE[0] // 2
    LINHA_SUPERIOR = COVER_LOCKUP_TOP
    TOPO_DO_TITULO = COVER_LOCKUP_TOP + 44
    LINHA_INFERIOR = COVER_LOCKUP_BOTTOM
    RAIO_SUPERIOR = 430
    RAIO_INFERIOR = 400

    # Apice do circulo em LINHA_SUPERIOR: centro fica um raio abaixo.
    _arc_text(
        image,
        "GUIA DE MEMÓRIAS",
        center=(centro_x, LINHA_SUPERIOR + RAIO_SUPERIOR),
        radius=RAIO_SUPERIOR,
        size=30,
        fill=INK,
    )
    draw = ImageDraw.Draw(image)
    # Entre o topo do titulo e a linha do arco de baixo, com folga para as
    # letras do arco: e o teto que a segunda linha tem que respeitar.
    _draw_centered_fit(
        draw, titulo, TOPO_DO_TITULO, 96, 44, 880, bold=True, maximum_height=112
    )
    # Fundo do circulo em LINHA_INFERIOR: centro fica um raio acima.
    _arc_text(
        image,
        data.upper(),
        center=(centro_x, LINHA_INFERIOR - RAIO_INFERIOR),
        radius=RAIO_INFERIOR,
        size=26,
        fill=INK,
        below=True,
    )
    return _atomic_save(image, output_path)


def _tint(color: str, amount: float) -> str:
    """Mistura a cor com o papel: o cartao da referencia e um tom lavado."""

    alvo = tuple(int(color[i : i + 2], 16) for i in (1, 3, 5))
    papel = _PAPEL_RGB
    misturado = tuple(round(p + (a - p) * amount) for p, a in zip(papel, alvo, strict=True))
    return "#{:02X}{:02X}{:02X}".format(*misturado)


def _draw_star(
    draw: ImageDraw.ImageDraw,
    center: tuple[int, int],
    radius: float,
    fill: str,
) -> None:
    """A estrelinha que marca as notas de aprendizado, como nas pranchas."""

    cx, cy = center
    pontas = []
    for indice in range(10):
        raio = radius if indice % 2 == 0 else radius * 0.42
        angulo = -math.pi / 2 + indice * math.pi / 5
        pontas.append((cx + raio * math.cos(angulo), cy + raio * math.sin(angulo)))
    draw.polygon(pontas, fill=fill)


def _draw_scene_page_header(
    image: Image.Image,
    draw: ImageDraw.ImageDraw,
    *,
    overline: str,
    title: str,
    arched: str,
    compact: bool = False,
) -> None:
    """A cabeceira das paginas ilustradas: sobrelinha, titulo e a linha em arco.

    A versao compacta serve a pagina do roteiro, onde quem tem de ocupar a
    folha sao as ilustracoes das paradas — nao o letreiro.
    """

    if compact:
        y_sobrelinha, corpo_sobrelinha = 28, 19
        y_titulo, maior, menor, teto = 64, 60, 30, 88
        linha_do_arco, corpo_do_arco = 190, 22
    else:
        y_sobrelinha, corpo_sobrelinha = 44, 21
        y_titulo, maior, menor, teto = 100, 78, 34, TITULO_ALTURA_MAXIMA
        linha_do_arco, corpo_do_arco = 286, 25

    if overline:
        _draw_tracked(
            draw,
            overline.upper(),
            y_sobrelinha,
            size=corpo_sobrelinha,
            fill=MUTED_INK,
            maximum_width=880,
        )
    # O titulo vai do seu topo ate a linha em arco, menos a altura das letras
    # do arco. Em duas linhas, sem esse teto, a segunda descia sobre o arco.
    _draw_centered_fit(draw, title, y_titulo, maior, menor, 880, bold=True, maximum_height=teto)
    if arched:
        # Fundo do circulo na linha do arco: o centro fica um raio acima.
        RAIO = 430
        _arc_text(
            image,
            arched.upper(),
            center=(PAGE_IMAGE_SIZE[0] // 2, linha_do_arco - RAIO),
            radius=RAIO,
            size=corpo_do_arco,
            fill=ACCENT,
            below=True,
        )


def _draw_scene_notes(
    draw: ImageDraw.ImageDraw,
    *,
    label: str = "",
    notes: Sequence[str] = (),
    curiosity_label: str = "",
    curiosity: str = "",
) -> None:
    """Assenta o texto sobre a ilustracao, sem faixa por baixo.

    As notas vao direto no chao chapado, com a estrelinha da referencia; so a
    curiosidade ganha cartao, porque e o bloco mais longo e o unico que precisa
    de garantia de contraste. Faixa chapada atras de tudo abria dois cortes
    horizontais na folha — a pagina deixava de ser uma ilustracao so.
    """

    topo = SCENE_NOTES_TOP
    if label:
        _draw_tracked(
            draw,
            _bounded(label, "rótulo", 60).upper(),
            topo,
            size=21,
            fill=ACCENT,
            left=SCENE_TEXT_LEFT,
            maximum_width=SCENE_TEXT_RIGHT - SCENE_TEXT_LEFT,
        )
        topo += 40

    presentes = [" ".join(nota.split()) for nota in notes if " ".join(nota.split())]
    for nota in presentes:
        _draw_star(
            draw,
            (SCENE_TEXT_LEFT + SCENE_STAR_RADIUS, topo + 22),
            SCENE_STAR_RADIUS,
            HIGHLIGHT,
        )
        _draw_wrapped_fit(
            draw,
            nota,
            (SCENE_TEXT_LEFT + 2 * SCENE_STAR_RADIUS + 22, topo, SCENE_TEXT_RIGHT, topo + 96),
            maximum_size=27,
            minimum_size=18,
            fill=INK,
        )
        topo += 110

    texto = " ".join(curiosity.split())
    if not texto:
        return
    # O cartao veste o texto: com altura fixa ele sobrava vazio embaixo e
    # avancava sem precisar sobre a ilustracao.
    largura = SCENE_TEXT_RIGHT - SCENE_TEXT_LEFT - 72
    _corpo, _linhas, altura = _wrapped_block(
        draw, texto, largura, maximum_size=26, minimum_size=17
    )
    base = min(SCENE_TEXT_BOTTOM, topo + 82 + altura + 28)
    draw.rounded_rectangle(
        (SCENE_TEXT_LEFT, topo, SCENE_TEXT_RIGHT, base),
        radius=SCENE_CARD_RADIUS,
        fill=_tint(CARD_TINT, 0.34),
    )
    _draw_star(draw, (SCENE_TEXT_LEFT + 36, topo + 44), SCENE_STAR_RADIUS, HIGHLIGHT)
    _draw_tracked(
        draw,
        _bounded(curiosity_label or "Você sabia?", "curiosity_label", 60).upper(),
        topo + 30,
        size=21,
        fill=ACCENT,
        left=SCENE_TEXT_LEFT + 2 * SCENE_STAR_RADIUS + 44,
        maximum_width=SCENE_TEXT_RIGHT - SCENE_TEXT_LEFT - 120,
    )
    _draw_wrapped_fit(
        draw,
        texto,
        (SCENE_TEXT_LEFT + 36, topo + 82, SCENE_TEXT_RIGHT - 36, base - 24),
        maximum_size=26,
        minimum_size=17,
        fill=INK,
    )


def compose_landmark_page(
    artwork_path: Path,
    output_path: Path,
    *,
    landmark_name: str,
    location: str,
    family_title: str,
    trip_date: str,
    description: str = "",
    curiosity: str = "",
    curiosity_label: str = "Você sabia?",
) -> Path:
    """Escreve a pagina do ponto turistico sobre uma arte sem letra nenhuma.

    Esta e a pagina que mais se repete no livro — uma por parada. Enquanto o
    modelo desenhava o titulo, cada parada saia numa tipografia diferente da
    anterior e das paginas de atividade, que sempre vieram do compositor.

    A arte cobre a folha inteira e o tipo assenta em cima dela. A versao com
    janela deitada e faixas chapadas cortava a pagina em tres, e a pagina
    deixava de parecer uma ilustracao so.
    """

    nome = _bounded(landmark_name, "landmark_name", 100)
    lugar = " ".join(location.split())
    assinatura = " • ".join(
        parte for parte in (family_title.strip(), trip_date.strip()) if parte.strip()
    )

    image = _load_artwork(artwork_path)
    draw = ImageDraw.Draw(image)

    _draw_scene_page_header(
        image,
        draw,
        overline=_bounded(assinatura, "assinatura", 120) if assinatura else "",
        title=nome,
        arched=_bounded(lugar, "location", 80) if lugar else "",
    )
    _draw_scene_notes(
        draw,
        label="Conheça o lugar" if description.strip() else "",
        notes=[description],
        curiosity_label=curiosity_label,
        curiosity=curiosity,
    )
    _draw_visited_marker(draw)
    return _atomic_save(image, output_path)


DESTINATION_OVERLINE = "Descubra este destino"


def compose_destination_intro_page(
    artwork_path: Path,
    output_path: Path,
    *,
    title: str,
    subtitle: str = "",
    learning_points: Sequence[str] = (),
    curiosity: str = "",
    curiosity_label: str = "Você sabia?",
) -> Path:
    """Monta a abertura do destino na mesma grade da pagina do ponto turistico.

    As duas paginas abrem o mesmo capitulo e precisam abrir igual: cabeceira em
    cima, texto assentado sobre a ilustracao, cenario cobrindo a folha inteira.
    """

    destino = _bounded(title, "title", 80)
    image = _load_artwork(artwork_path)
    draw = ImageDraw.Draw(image)
    _draw_scene_page_header(
        image,
        draw,
        overline=DESTINATION_OVERLINE,
        title=destino,
        arched=_bounded(subtitle, "subtitle", 80) if subtitle.strip() else "",
    )
    _draw_scene_notes(
        draw,
        notes=list(learning_points)[:2],
        curiosity_label=curiosity_label,
        curiosity=curiosity,
    )
    return _atomic_save(image, output_path)


SUMMARY_TITLE = "Nosso roteiro"
SUMMARY_MAX_STOPS = 6
SUMMARY_BULLET_RADIUS = 22
SUMMARY_BULLET_GAP = 20
# A pagina do roteiro e uma serpentina: uma faixa por parada, a vinheta
# alternando de lado, e o nome na metade vazia da mesma faixa. O modelo so
# desenha as vinhetas; a rota pontilhada e os nomes sao do codigo, que assim
# sabe exatamente onde cada parada esta.
# O letreiro nao e o assunto da pagina: as paradas sao. Com 340 px de faixa a
# torre chegava a ser tapada pela cabeceira e saia sem a ponta.
SUMMARY_HEADER_HEIGHT = 232
# O prompt reserva MAIS do que o codigo pinta. A ponta da torre chegou a 200 e
# foi apagada pelo proprio retangulo da cabeceira; esta folga de 84 px entre o
# fim da pintura e o inicio da primeira faixa absorve o transbordo do modelo.
SUMMARY_ROUTE_TOP = 316
# Acima disto, o que a cabeceira ia cobrir nao e fundo: e monumento. Pintar por
# cima decapitaria a parada, e em silencio — o pior desfecho possivel. O numero
# vem de medicao: 3% e o degrau entre a antena que so encosta na linha (2,7%) e
# um corte que pega estrutura de verdade (a partir de 4,7%).
SUMMARY_HEADER_INTRUSION_LIMIT = 0.03
SUMMARY_HEADER_RETRIES = 3
# Margem de verdade no pe da folha: com a ultima faixa terminando a 58 px
# da borda, o modelo leu aquilo como permissao para sangrar, e o Louvre
# saiu sem base.
SUMMARY_ROUTE_BOTTOM = 1424
SUMMARY_HALF = PAGE_IMAGE_SIZE[0] // 2
SUMMARY_ROUTE_DOT = 7
SUMMARY_ROUTE_STEP = 34
# Quanto da curva fica de fora em cada ponta, para nao invadir a vinheta.
SUMMARY_ROUTE_MARGIN = 0.10
# Quao longe do eixo da pagina a rota se afasta, de cada lado.
SUMMARY_ROUTE_INSET = 96
# Folga entre o eixo da pagina e o rotulo. A vinheta transborda um pouco a
# metade dela — o Louvre passou do eixo e a bolinha encostou no predio.
SUMMARY_LABEL_INSET = 56


def summary_band(index: int, total: int) -> tuple[int, int, bool]:
    """Faixa da parada: topo, base e se a vinheta fica a direita.

    O codigo e o prompt derivam a geometria daqui, os dois. Foi a divergencia
    entre o que se pedia e o que se desenhava que cortou o monumento pelos pes
    na pagina do ponto turistico.
    """

    altura = (SUMMARY_ROUTE_BOTTOM - SUMMARY_ROUTE_TOP) // max(1, total)
    topo = SUMMARY_ROUTE_TOP + index * altura
    return topo, topo + altura, index % 2 == 0


def _ground_colour(image: Image.Image, boxes: Sequence[tuple[int, int, int, int]]) -> str:
    """A cor chapada que a arte usou, medida onde o contrato manda ficar vazio.

    Pintar a cabeceira com uma cor da paleta abria um corte visivel no meio da
    folha, como se fossem duas paginas coladas. Tirando a cor do proprio
    desenho, a emenda deixa de existir.

    A mediana por canal, e nao a media: um motivo que escape para a metade
    vazia puxaria a media para o lado dele, mas nao move a mediana.
    """

    canais: list[list[int]] = [[], [], []]
    for box in boxes:
        recorte = image.crop(box).resize((32, 32), Image.Resampling.BILINEAR).convert("RGB")
        pixels = recorte.load()
        if pixels is None:  # pragma: no cover - Pillow devolve None so em erro
            continue
        for x in range(32):
            for y in range(32):
                for indice, valor in enumerate(cast(tuple[int, ...], pixels[x, y])):
                    canais[indice].append(valor)
    if not canais[0]:
        return BAND
    mediana = tuple(sorted(canal)[len(canal) // 2] for canal in canais)
    return "#{:02X}{:02X}{:02X}".format(*mediana)


def _edge_crossing_fraction(
    image: Image.Image,
    y: int,
    ground: str,
    *,
    tolerance: int = 40,
    thickness: int = 8,
) -> float:
    """Fracao das colunas em que algo atravessa a linha onde o codigo vai pintar.

    Medir a AREA da faixa nao separa nada: o giz deixa 2 a 5% de ruido e a ponta
    fina de uma torre acrescenta pouco mais que isso. Na linha do corte o sinal
    e limpo. Medido nesta arte: coluna sem desenho da 0 a 1%, a antena da torre
    da 2,7%, e o corpo de um monumento passa de 30%.
    """

    alvo = tuple(int(ground[i : i + 2], 16) for i in (1, 3, 5))
    pixels = image.convert("RGB").load()
    if pixels is None:  # pragma: no cover - Pillow devolve None so em erro
        return 0.0
    largura, altura = image.size
    colunas = range(0, largura, 2)
    atravessadas = 0
    for x in colunas:
        for dy in range(-thickness, thickness + 1, 4):
            cor = cast(tuple[int, ...], pixels[x, max(0, min(altura - 1, y + dy))])
            if max(abs(cor[i] - alvo[i]) for i in range(3)) > tolerance:
                atravessadas += 1
                break
    return atravessadas / len(colunas)


def _draw_dotted_route(draw: ImageDraw.ImageDraw, pontos: Sequence[tuple[float, float]]) -> None:
    """Liga as paradas com a rota pontilhada, em curva e nao em reta."""

    ultimo = len(pontos) - 2
    for trecho, ((x0, y0), (x1, y1)) in enumerate(zip(pontos, pontos[1:], strict=False)):
        # Tangentes verticais nas duas pontas: a rota desce de uma parada, faz
        # a barriga e sobe na proxima. Com os controles na diagonal ela saia
        # reta, e reta nao parece caminho — parece regua.
        c0 = (x0, y0 + (y1 - y0) * 0.55)
        c1 = (x1, y1 - (y1 - y0) * 0.55)
        comprimento = abs(y1 - y0) + abs(x1 - x0)
        passos = max(4, int(comprimento / SUMMARY_ROUTE_STEP))
        # So as duas pontas do caminho inteiro ficam de fora — as internas nao,
        # senao a rota vira tracos soltos em vez de um caminho continuo.
        inicio = SUMMARY_ROUTE_MARGIN if trecho == 0 else 0.0
        fim = 1 - SUMMARY_ROUTE_MARGIN if trecho == ultimo else 1.0
        for passo in range(passos + 1):
            s = inicio + (passo / passos) * (fim - inicio)
            u = 1 - s
            x = u**3 * x0 + 3 * u**2 * s * c0[0] + 3 * u * s**2 * c1[0] + s**3 * x1
            y = u**3 * y0 + 3 * u**2 * s * c0[1] + 3 * u * s**2 * c1[1] + s**3 * y1
            raio = SUMMARY_ROUTE_DOT / 2
            draw.ellipse((x - raio, y - raio, x + raio, y + raio), fill=INK)


class SummaryHeaderIntrusionError(ActivityPageCompositionError):
    """A arte subiu ate a faixa do titulo; vale pedir outra em vez de decapitar."""


def compose_summary_page(
    artwork_path: Path,
    output_path: Path,
    *,
    family_title: str,
    trip_date: str,
    landmark_names: Sequence[str],
    enforce_header: bool = True,
) -> Path:
    """Monta o roteiro: vinhetas do modelo, rota e nomes do codigo.

    A lista numerada no rodape mostrava os nomes mas nao amarrava nenhum deles
    ao seu desenho — quem abria a pagina via as paradas de um lado e a lista do
    outro. Aqui cada nome fica na mesma faixa da sua vinheta, e a rota
    pontilhada passa por elas na ordem, sem que a IA precise escrever nada.
    """

    paradas = [" ".join(nome.split()) for nome in landmark_names if nome.strip()]
    if not paradas:
        raise ActivityPageCompositionError("O roteiro não tem paradas.")
    paradas = paradas[:SUMMARY_MAX_STOPS]

    image = _load_artwork(artwork_path)

    # As metades vazias sao a unica area que o contrato garante chapada: e de
    # la que sai a cor da cabeceira, para a pagina inteira ficar de uma cor so.
    metades_vazias = []
    for indice in range(len(paradas)):
        topo, base, vinheta_a_direita = summary_band(indice, len(paradas))
        metades_vazias.append(
            (0, topo, SUMMARY_HALF, base)
            if vinheta_a_direita
            else (SUMMARY_HALF, topo, PAGE_IMAGE_SIZE[0], base)
        )
    fundo = _ground_colour(image, metades_vazias)

    invasao = _edge_crossing_fraction(image, SUMMARY_HEADER_HEIGHT, fundo)
    if enforce_header and invasao > SUMMARY_HEADER_INTRUSION_LIMIT:
        raise SummaryHeaderIntrusionError(
            f"A arte do roteiro cruza a linha do título em {invasao:.0%} da largura; "
            "pintar por cima decapitaria a parada."
        )

    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, PAGE_IMAGE_SIZE[0], SUMMARY_HEADER_HEIGHT), fill=fundo)
    _draw_scene_page_header(
        image,
        draw,
        overline=_bounded(family_title, "family_title", 60),
        title=SUMMARY_TITLE,
        arched=_bounded(trip_date, "trip_date", 60) if trip_date.strip() else "",
        compact=True,
    )

    # Um corpo so para todas as paradas: deixar cada nome escolher o seu fazia
    # a parada de nome longo aparecer menor que a vizinha na mesma pagina.
    # A mesma largura dos dois lados: com a folga so de um lado, um nome longo
    # cabia a esquerda e estourava a margem a direita.
    largura_do_nome = (
        SUMMARY_HALF
        - PAGE_TEXT_LEFT
        - SUMMARY_LABEL_INSET
        - 2 * SUMMARY_BULLET_RADIUS
        - SUMMARY_BULLET_GAP
    )
    corpo = _shared_fit_size(
        draw, paradas, maximum_size=34, minimum_size=17, maximum_width=largura_do_nome
    )
    fonte = _font(corpo, bold=True)

    ancoras = []
    for indice, parada in enumerate(paradas):
        topo, base, vinheta_a_direita = summary_band(indice, len(paradas))
        meio = (topo + base) // 2
        # A rota corre pelo corredor central, nao pelo meio da vinheta: ancorada
        # no centro do desenho, os primeiros pontos caiam em cima do monumento.
        ancoras.append(
            (
                SUMMARY_HALF + (SUMMARY_ROUTE_INSET if vinheta_a_direita else -SUMMARY_ROUTE_INSET),
                meio,
            )
        )

        # O nome ocupa a metade que a vinheta deixou vazia.
        esquerda = (
            PAGE_TEXT_LEFT if vinheta_a_direita else SUMMARY_HALF + SUMMARY_LABEL_INSET
        )
        _draw_numbered_bullet(draw, str(indice + 1), (esquerda, meio))
        caixa = draw.textbbox((0, 0), parada, font=fonte)
        draw.text(
            (
                esquerda + 2 * SUMMARY_BULLET_RADIUS + SUMMARY_BULLET_GAP,
                meio - (caixa[3] - caixa[1]) / 2 - caixa[1],
            ),
            parada,
            font=fonte,
            fill=INK,
        )

    _draw_dotted_route(draw, ancoras)
    return _atomic_save(image, output_path)


WELCOME_OVERLINE = "O primeiro olá"
WELCOME_ROW_HEIGHT = 82
# A coluna da pronúncia. Alinhada à direita da página ela ficava a um vão de
# 700px da palavra — o olho perdia o par. Coluna fixa mantém o par junto.
WELCOME_SPEECH_COLUMN = 470
WELCOME_CARD_GAP = 26
# A faixa onde o pill da missão pousa, a mesma altura do "Já visitei".
WELCOME_PILL_TOP = 1392
WELCOME_PILL_BOTTOM = 1500


def _draw_mission_pill(draw: ImageDraw.ImageDraw, label: str) -> None:
    """O pill de missão com quadradinho, na gramática do "Já visitei".

    A largura veste o texto: o rótulo muda de idioma para idioma ("Eu disse
    Konnichiwa!" é bem mais largo que "Eu disse Ciao!"), e um painel fixo ou
    cortava ou sobrava.
    """

    fonte = _font(30, bold=True)
    caixa = draw.textbbox((0, 0), label, font=fonte)
    largura_texto = caixa[2] - caixa[0]
    lado = 48
    respiro = 40
    largura = int(respiro + lado + 24 + largura_texto + respiro)
    esquerda = (PAGE_IMAGE_SIZE[0] - largura) // 2
    _panel(draw, (esquerda, WELCOME_PILL_TOP, esquerda + largura, WELCOME_PILL_BOTTOM), radius=20)
    topo_caixa = WELCOME_PILL_TOP + 31
    draw.rounded_rectangle(
        (esquerda + respiro, topo_caixa, esquerda + respiro + lado, topo_caixa + lado),
        radius=5,
        fill="white",
        outline=INK,
        width=4,
    )
    draw.text(
        (esquerda + respiro + lado + 24, WELCOME_PILL_TOP + 32),
        label,
        font=fonte,
        fill=INK,
    )


def compose_language_welcome_page(
    artwork_path: Path,
    output_path: Path,
    *,
    language: str,
    greeting: str,
    words: Sequence[tuple[str, str, str]],
    curiosity: str,
    curiosity_label: str = "Você sabia?",
) -> Path:
    """A abertura de idioma do país, na gramática das páginas ilustradas.

    O título da página é a própria saudação nativa — a criança lê "Bonjour !"
    antes de qualquer explicação. As cinco linhas são o arco de uma conversa,
    com a pronúncia em destaque porque ela é o que a criança de fato fala; a
    curiosidade do idioma vai no cartão rosa; e a missão no rodapé é dizer a
    saudação para alguém de verdade.
    """

    if len(words) != 5:
        raise ActivityPageCompositionError("A abertura de idioma precisa de cinco palavras.")

    image = _load_artwork(artwork_path)
    draw = ImageDraw.Draw(image)

    _draw_scene_page_header(
        image,
        draw,
        overline=WELCOME_OVERLINE,
        title=_bounded(greeting, "greeting", 40),
        arched=_bounded(f"Olá, em {language}", "language", 40),
    )

    topo = SCENE_NOTES_TOP
    for palavra, pronuncia, significado in words:
        _draw_star(
            draw,
            (SCENE_TEXT_LEFT + SCENE_STAR_RADIUS, topo + 20),
            SCENE_STAR_RADIUS,
            HIGHLIGHT,
        )
        texto_x = SCENE_TEXT_LEFT + 2 * SCENE_STAR_RADIUS + 22
        draw.text(
            (texto_x, topo),
            _bounded(palavra, "palavra", 40),
            font=_font(31, bold=True),
            fill=INK,
        )
        # A pronúncia é o que a criança lê em voz alta — na voz que as páginas
        # de idioma já falam, em coluna fixa para o par palavra-fala ficar junto.
        fala = f"fale assim: {_bounded(pronuncia, 'pronúncia', 40)}"
        draw.text(
            (WELCOME_SPEECH_COLUMN, topo + 7),
            fala,
            font=_font(22, bold=True),
            fill=ACCENT,
        )
        draw.text(
            (texto_x, topo + 44),
            _bounded(significado, "significado", 60),
            font=_font(20),
            fill=MUTED_INK,
        )
        topo += WELCOME_ROW_HEIGHT

    texto = " ".join(curiosity.split())
    if texto:
        topo += WELCOME_CARD_GAP
        largura = SCENE_TEXT_RIGHT - SCENE_TEXT_LEFT - 72
        _corpo, _linhas, altura = _wrapped_block(
            draw, texto, largura, maximum_size=25, minimum_size=17
        )
        base = min(SCENE_TEXT_BOTTOM + 60, topo + 82 + altura + 28)
        draw.rounded_rectangle(
            (SCENE_TEXT_LEFT, topo, SCENE_TEXT_RIGHT, base),
            radius=SCENE_CARD_RADIUS,
            fill=_tint(CARD_TINT, 0.34),
        )
        _draw_star(draw, (SCENE_TEXT_LEFT + 36, topo + 44), SCENE_STAR_RADIUS, HIGHLIGHT)
        _draw_tracked(
            draw,
            _bounded(curiosity_label, "curiosity_label", 60).upper(),
            topo + 30,
            size=21,
            fill=ACCENT,
            left=SCENE_TEXT_LEFT + 2 * SCENE_STAR_RADIUS + 44,
            maximum_width=SCENE_TEXT_RIGHT - SCENE_TEXT_LEFT - 120,
        )
        _draw_wrapped_fit(
            draw,
            texto,
            (SCENE_TEXT_LEFT + 36, topo + 82, SCENE_TEXT_RIGHT - 36, base - 24),
            maximum_size=25,
            minimum_size=17,
            fill=INK,
        )

    saudacao_limpa = greeting.strip(" !¡?¿").strip()
    _draw_mission_pill(draw, f"Eu disse {saudacao_limpa}!")
    return _atomic_save(image, output_path)
