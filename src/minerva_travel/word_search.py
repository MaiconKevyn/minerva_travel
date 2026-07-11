"""Gerador deterministico de grade de caca-palavras para as atividades do guia."""

import random
import unicodedata

GRID_SIZE = 10
FILLER_LETTERS = "ABCDEFGHIJLMNOPRSTUV"
MAX_WORDS = 6


def normalize_word_for_grid(word: str) -> str:
    decomposed = unicodedata.normalize("NFD", word)
    ascii_only = "".join(char for char in decomposed if not unicodedata.combining(char))
    return "".join(char for char in ascii_only.upper() if char.isalpha())


def build_word_search_grid(
    words: list[str],
    *,
    seed: str,
    size: int = GRID_SIZE,
) -> tuple[list[str], list[str]]:
    """Monta uma grade de letras com as palavras escondidas na horizontal e vertical.

    Retorna (linhas da grade, palavras efetivamente colocadas). Deterministico
    para um mesmo seed, entao o mesmo pedido gera sempre o mesmo caderno.
    """
    rng = random.Random(seed)
    normalized: list[str] = []
    for word in words:
        cleaned = normalize_word_for_grid(word)
        if 3 <= len(cleaned) <= size and cleaned not in normalized:
            normalized.append(cleaned)
    normalized = normalized[:MAX_WORDS]

    grid: list[list[str | None]] = [[None] * size for _ in range(size)]
    placed: list[str] = []
    for word in sorted(normalized, key=len, reverse=True):
        if _place_word(grid, word, rng, size):
            placed.append(word)

    for row in range(size):
        for column in range(size):
            if grid[row][column] is None:
                grid[row][column] = rng.choice(FILLER_LETTERS)

    rows = ["".join(cell or "" for cell in row) for row in grid]
    return rows, placed


def _place_word(
    grid: list[list[str | None]],
    word: str,
    rng: random.Random,
    size: int,
) -> bool:
    positions = [
        (row, column, direction)
        for direction in ("horizontal", "vertical")
        for row in range(size if direction == "horizontal" else size - len(word) + 1)
        for column in range(size - len(word) + 1 if direction == "horizontal" else size)
    ]
    rng.shuffle(positions)
    for row, column, direction in positions:
        if _fits(grid, word, row, column, direction):
            for index, letter in enumerate(word):
                if direction == "horizontal":
                    grid[row][column + index] = letter
                else:
                    grid[row + index][column] = letter
            return True
    return False


def _fits(
    grid: list[list[str | None]],
    word: str,
    row: int,
    column: int,
    direction: str,
) -> bool:
    for index, letter in enumerate(word):
        current = (
            grid[row][column + index] if direction == "horizontal" else grid[row + index][column]
        )
        if current is not None and current != letter:
            return False
    return True
