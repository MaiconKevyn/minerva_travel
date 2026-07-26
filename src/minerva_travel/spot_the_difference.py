"""Validação das diferenças entre as duas artes do "ache os erros".

O gerador de imagens não promete quantas alterações fez nem onde. Sem
conferir, a página sairia dizendo "ache 6 diferenças" com 2 achaveis — ou
com o desenho inteiro trocado, que também não é o jogo.

Aqui comparamos as duas artes numa grade grossa, agrupamos as células que
mudaram e a página imprime o número de manchas que realmente existem — nunca
um número prometido de antemão.
"""

from dataclasses import dataclass
from pathlib import Path

from PIL import Image

# O editor de imagens não entrega um número exato de alterações: em testes
# repetidos ele produziu 1, 3 e uma cena inteira redesenhada. Em vez de
# prometer seis e imprimir menos, a página conta o que foi medido — e três
# diferenças achaveis já são um jogo. Abaixo disso não é.
MIN_DIFFERENCES = 3
MAX_DIFFERENCES = 8
# Célula grossa: mudanças menores que isso não seriam achadas por uma criança
# na página impressa, e ruído de compressão viraria falso positivo.
CELL = 32
CELL_DIFFERENCE_THRESHOLD = 26
# Uma mancha precisa de área para ser um "erro"; um pixel isolado é ruído.
MIN_REGION_CELLS = 2
# Acima disso a arte inteira mudou e não é mais a mesma cena.
MAX_CHANGED_FRACTION = 0.22


class SpotTheDifferenceError(ValueError):
    """The two artworks do not differ in a countable, findable way."""


@dataclass(frozen=True)
class DifferenceRegion:
    """Box in source-image pixels, used to print the answer key."""

    left: int
    top: int
    right: int
    bottom: int

    @property
    def center(self) -> tuple[int, int]:
        return ((self.left + self.right) // 2, (self.top + self.bottom) // 2)


def find_difference_regions(base_path: Path, variant_path: Path) -> list[DifferenceRegion]:
    """Group the changed cells into separate findable differences."""

    with Image.open(base_path) as opened:
        base = opened.convert("L")
    with Image.open(variant_path) as opened:
        variant = opened.convert("L")
    if base.size != variant.size:
        raise SpotTheDifferenceError("As duas artes não têm o mesmo tamanho.")

    width, height = base.size
    columns, rows = width // CELL, height // CELL
    if columns < 4 or rows < 4:
        raise SpotTheDifferenceError("As artes são pequenas demais para comparar.")

    base_pixels, variant_pixels = base.load(), variant.load()
    changed: set[tuple[int, int]] = set()
    for row in range(rows):
        for column in range(columns):
            total = 0
            for y in range(row * CELL, (row + 1) * CELL, 4):
                for x in range(column * CELL, (column + 1) * CELL, 4):
                    total += abs(base_pixels[x, y] - variant_pixels[x, y])
            samples = (CELL // 4) ** 2
            if total / samples >= CELL_DIFFERENCE_THRESHOLD:
                changed.add((column, row))

    if len(changed) > columns * rows * MAX_CHANGED_FRACTION:
        raise SpotTheDifferenceError("A segunda arte mudou demais para ser a mesma cena.")
    regions = [region for region in _group(changed) if _cells_in(region) >= MIN_REGION_CELLS]
    if not MIN_DIFFERENCES <= len(regions) <= MAX_DIFFERENCES:
        raise SpotTheDifferenceError(
            f"A arte gerou {len(regions)} diferenças utilizáveis; "
            f"o esperado é entre {MIN_DIFFERENCES} e {MAX_DIFFERENCES}."
        )
    return sorted(regions, key=lambda region: (region.top, region.left))


def _group(changed: set[tuple[int, int]]) -> list[DifferenceRegion]:
    """Flood fill neighbouring changed cells into one region each."""

    remaining = set(changed)
    regions: list[DifferenceRegion] = []
    while remaining:
        stack = [remaining.pop()]
        cells = [stack[0]]
        while stack:
            column, row = stack.pop()
            for delta_column in (-1, 0, 1):
                for delta_row in (-1, 0, 1):
                    neighbour = (column + delta_column, row + delta_row)
                    if neighbour in remaining:
                        remaining.discard(neighbour)
                        stack.append(neighbour)
                        cells.append(neighbour)
        columns = [column for column, _row in cells]
        rows = [row for _column, row in cells]
        regions.append(
            DifferenceRegion(
                left=min(columns) * CELL,
                top=min(rows) * CELL,
                right=(max(columns) + 1) * CELL,
                bottom=(max(rows) + 1) * CELL,
            )
        )
    return regions


def _cells_in(region: DifferenceRegion) -> int:
    return ((region.right - region.left) // CELL) * ((region.bottom - region.top) // CELL)
