"""Layout determinístico de cruzadinha a partir do vocabulário da viagem.

Cada palavra entra cruzando uma já colocada. Palavras soltas transformariam a
cruzadinha numa lista de lacunas, então uma palavra que não encontra
cruzamento é descartada em vez de flutuar no canto da grade.
"""

from dataclasses import dataclass

from minerva_travel.puzzles import normalize_puzzle_word

CROSSWORD_MIN_ENTRIES = 4
CROSSWORD_MAX_ENTRIES = 8
CROSSWORD_MIN_LENGTH = 3
CROSSWORD_MAX_LENGTH = 12
CROSSWORD_MAX_SIDE = 15


class CrosswordGenerationError(ValueError):
    """The supplied clues cannot produce a connected crossword."""


@dataclass(frozen=True)
class CrosswordEntry:
    number: int
    answer: str
    clue: str
    column: int
    row: int
    across: bool


@dataclass(frozen=True)
class Crossword:
    columns: int
    rows: int
    entries: tuple[CrosswordEntry, ...]

    @property
    def letters(self) -> dict[tuple[int, int], str]:
        placed: dict[tuple[int, int], str] = {}
        for entry in self.entries:
            for offset, letter in enumerate(entry.answer):
                column = entry.column + (offset if entry.across else 0)
                row = entry.row + (0 if entry.across else offset)
                placed[(column, row)] = letter
        return placed

    @property
    def across(self) -> tuple[CrosswordEntry, ...]:
        return tuple(entry for entry in self.entries if entry.across)

    @property
    def down(self) -> tuple[CrosswordEntry, ...]:
        return tuple(entry for entry in self.entries if not entry.across)


def build_crossword(clues: list[tuple[str, str]]) -> Crossword:
    """Interlock the answers into one connected grid, numbered top-left first."""

    candidates: list[tuple[str, str]] = []
    seen: set[str] = set()
    for word, clue in clues:
        answer = normalize_puzzle_word(word)
        cleaned_clue = " ".join(str(clue).split())
        if not CROSSWORD_MIN_LENGTH <= len(answer) <= CROSSWORD_MAX_LENGTH:
            continue
        if answer in seen or not cleaned_clue:
            continue
        seen.add(answer)
        candidates.append((answer, cleaned_clue))
    candidates.sort(key=lambda item: len(item[0]), reverse=True)
    if len(candidates) < CROSSWORD_MIN_ENTRIES:
        raise CrosswordGenerationError("Não há palavras suficientes para montar a cruzadinha.")

    first_answer, first_clue = candidates[0]
    placements: list[tuple[str, str, int, int, bool]] = [(first_answer, first_clue, 0, 0, True)]
    occupied = {(offset, 0): letter for offset, letter in enumerate(first_answer)}

    for answer, clue in candidates[1:]:
        if len(placements) == CROSSWORD_MAX_ENTRIES:
            break
        placement = _find_placement(answer, placements, occupied)
        if placement is None:
            continue
        column, row, across = placement
        placements.append((answer, clue, column, row, across))
        for offset, letter in enumerate(answer):
            occupied[(column + (offset if across else 0), row + (0 if across else offset))] = letter

    if len(placements) < CROSSWORD_MIN_ENTRIES:
        raise CrosswordGenerationError("As palavras não se cruzam o suficiente para a cruzadinha.")
    return _normalized(placements)


def _find_placement(
    answer: str,
    placements: list[tuple[str, str, int, int, bool]],
    occupied: dict[tuple[int, int], str],
) -> tuple[int, int, bool] | None:
    for placed_answer, _clue, placed_column, placed_row, placed_across in placements:
        for placed_offset, placed_letter in enumerate(placed_answer):
            for offset, letter in enumerate(answer):
                if letter != placed_letter:
                    continue
                across = not placed_across
                if across:
                    column = placed_column + (placed_offset if not placed_across else 0) - offset
                    row = placed_row + (placed_offset if placed_across else 0)
                else:
                    column = placed_column + (placed_offset if placed_across else 0)
                    row = placed_row + (placed_offset if not placed_across else 0) - offset
                if _fits(answer, column, row, across, occupied):
                    return column, row, across
    return None


def _fits(
    answer: str,
    column: int,
    row: int,
    across: bool,
    occupied: dict[tuple[int, int], str],
) -> bool:
    # Antes do início e depois do fim precisa haver vazio, senão duas palavras
    # se emendam e formam uma terceira que não está nas dicas.
    before = (column - 1, row) if across else (column, row - 1)
    after = (column + len(answer), row) if across else (column, row + len(answer))
    if before in occupied or after in occupied:
        return False

    for offset, letter in enumerate(answer):
        cell = (column + offset, row) if across else (column, row + offset)
        existing = occupied.get(cell)
        if existing is not None:
            if existing != letter:
                return False
            continue
        # Célula nova não pode encostar em outra palavra pelo lado: isso
        # criaria uma palavra colada que ninguém pediu.
        sides = (
            [(cell[0], cell[1] - 1), (cell[0], cell[1] + 1)]
            if across
            else [(cell[0] - 1, cell[1]), (cell[0] + 1, cell[1])]
        )
        if any(side in occupied for side in sides):
            return False
    return True


def _normalized(placements: list[tuple[str, str, int, int, bool]]) -> Crossword:
    columns = [column for _a, _c, column, _r, _across in placements]
    rows = [row for _a, _c, _column, row, _across in placements]
    ends_column = [
        column + (len(answer) if across else 1)
        for answer, _c, column, _r, across in placements
    ]
    ends_row = [
        row + (1 if across else len(answer)) for answer, _c, _column, row, across in placements
    ]
    left, top = min(columns), min(rows)
    width, height = max(ends_column) - left, max(ends_row) - top
    if width > CROSSWORD_MAX_SIDE or height > CROSSWORD_MAX_SIDE:
        raise CrosswordGenerationError("A cruzadinha ficou maior do que a página comporta.")

    shifted = [
        (answer, clue, column - left, row - top, across)
        for answer, clue, column, row, across in placements
    ]
    # Numeração de palavra cruzada: varre de cima para baixo, esquerda para
    # direita, e cada início de palavra ganha o próximo número.
    starts = sorted({(row, column) for _a, _c, column, row, _across in shifted})
    numbers = {start: index + 1 for index, start in enumerate(starts)}
    entries = tuple(
        CrosswordEntry(
            number=numbers[(row, column)],
            answer=answer,
            clue=clue,
            column=column,
            row=row,
            across=across,
        )
        for answer, clue, column, row, across in shifted
    )
    return Crossword(
        columns=width,
        rows=height,
        entries=tuple(sorted(entries, key=lambda entry: (entry.number, not entry.across))),
    )
