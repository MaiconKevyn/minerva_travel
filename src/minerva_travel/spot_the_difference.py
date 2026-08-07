"""Validação das diferenças entre as duas artes do "ache os erros".

O gerador de imagens não promete quantas alterações fez nem onde. Sem
conferir, a página sairia dizendo "ache 6 diferenças" com 2 achaveis — ou
com o desenho inteiro trocado, que também não é o jogo.

Aqui comparamos as duas artes numa grade grossa, agrupamos as células que
mudaram e a página imprime o número de manchas que realmente existem — nunca
um número prometido de antemão.

A comparação olha para COR, não para brilho. O modelo não devolve um remendo:
devolve a cena inteira redesenhada, e o monumento sai com o traço levemente
diferente a cada vez. Medido numa Torre Eiffel de verdade, esse tremor tinha
|Δ| de luminância 22–30 — mais alto que a árvore que de fato mudou de verde
para rosa (28) — e a página prometia 7 diferenças com 2 achaveis, quatro delas
em cima da própria torre. Na saturação do delta os dois grupos se separam sem
ambiguidade: 5–7 no tremor contra 20–32 nas mudanças reais, porque redesenhar
o mesmo objeto na mesma paleta desloca linhas sem trocar a cor.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from PIL import Image, ImageChops

# O editor de imagens não entrega um número exato de alterações: em testes
# repetidos ele produziu 1, 3 e uma cena inteira redesenhada. Em vez de
# prometer seis e imprimir menos, a página conta o que foi medido — e três
# diferenças achaveis já são um jogo. Abaixo disso não é.
MIN_DIFFERENCES = 3
# Uma linha só de quadradinhos na página impressa comporta oito.
MAX_DIFFERENCES = 8
# Célula grossa: mudanças menores que isso não seriam achadas por uma criança
# na página impressa, e ruído de compressão viraria falso positivo.
CELL = 32
# Saturação média do delta dentro da célula. Fica no meio do vão medido entre
# o tremor do redesenho (5–7) e uma troca de cor de verdade (20–32).
CHROMA_THRESHOLD = 14
# Uma mancha precisa de área para ser um "erro"; uma célula solta é ruído.
MIN_REGION_CELLS = 2
# Um objeto repintado raramente muda num bloco só: a árvore roxa mudou na copa
# e, dois quadros abaixo, na grama caída ao pé dela. Contar isso como dois
# erros faz a página prometer mais do que a criança acha. Colar as manchas
# vizinhas às vezes junta dois objetos próximos num só — e tudo bem: errar
# para menos vira uma diferença de brinde, errar para mais vira promessa
# quebrada. Raio 1 fecha vãos de até duas células e foi o limite medido em
# arte real: com raio 2, seis diferenças bem separadas viravam quatro.
MERGE_RADIUS_CELLS = 1
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
    """Group the recoloured cells into separate findable differences."""

    with Image.open(base_path) as opened:
        base = opened.convert("RGB")
    with Image.open(variant_path) as opened:
        variant = opened.convert("RGB")
    if base.size != variant.size:
        raise SpotTheDifferenceError("As duas artes não têm o mesmo tamanho.")

    width, height = base.size
    columns, rows = width // CELL, height // CELL
    if columns < 4 or rows < 4:
        raise SpotTheDifferenceError("As artes são pequenas demais para comparar.")

    delta = cast(Any, ImageChops.difference(base, variant).load())
    changed: set[tuple[int, int]] = set()
    samples = (CELL // 4) ** 2
    for row in range(rows):
        for column in range(columns):
            total = 0
            for y in range(row * CELL, (row + 1) * CELL, 4):
                for x in range(column * CELL, (column + 1) * CELL, 4):
                    red, green, blue = delta[x, y]
                    total += max(red, green, blue) - min(red, green, blue)
            if total / samples >= CHROMA_THRESHOLD:
                changed.add((column, row))

    if len(changed) > columns * rows * MAX_CHANGED_FRACTION:
        raise SpotTheDifferenceError("A segunda arte mudou demais para ser a mesma cena.")

    # O ruído sai antes de colar as manchas: dilatar primeiro transformaria uma
    # célula solta numa mancha de nove e ela passaria pelo filtro.
    solid = {
        cell
        for cluster in _clusters(changed)
        if len(cluster) >= MIN_REGION_CELLS
        for cell in cluster
    }
    regions = [_bounds(cluster) for cluster in _clusters(_dilate(solid))]
    if not MIN_DIFFERENCES <= len(regions) <= MAX_DIFFERENCES:
        raise SpotTheDifferenceError(
            f"A arte gerou {len(regions)} diferenças utilizáveis; "
            f"o esperado é entre {MIN_DIFFERENCES} e {MAX_DIFFERENCES}."
        )
    return sorted(regions, key=lambda region: (region.top, region.left))


def _clusters(changed: set[tuple[int, int]]) -> list[set[tuple[int, int]]]:
    """Flood fill neighbouring changed cells into one cluster each."""

    remaining = set(changed)
    clusters: list[set[tuple[int, int]]] = []
    while remaining:
        start = remaining.pop()
        stack = [start]
        cluster = {start}
        while stack:
            column, row = stack.pop()
            for delta_column in (-1, 0, 1):
                for delta_row in (-1, 0, 1):
                    neighbour = (column + delta_column, row + delta_row)
                    if neighbour in remaining:
                        remaining.discard(neighbour)
                        stack.append(neighbour)
                        cluster.add(neighbour)
        clusters.append(cluster)
    return clusters


def _dilate(cells: set[tuple[int, int]]) -> set[tuple[int, int]]:
    """Grow every cell so pieces of the same repainted object touch."""

    radius = MERGE_RADIUS_CELLS
    return {
        (column + delta_column, row + delta_row)
        for column, row in cells
        for delta_column in range(-radius, radius + 1)
        for delta_row in range(-radius, radius + 1)
    }


def _bounds(cluster: set[tuple[int, int]]) -> DifferenceRegion:
    columns = [column for column, _row in cluster]
    rows = [row for _column, row in cluster]
    return DifferenceRegion(
        left=min(columns) * CELL,
        top=min(rows) * CELL,
        right=(max(columns) + 1) * CELL,
        bottom=(max(rows) + 1) * CELL,
    )
