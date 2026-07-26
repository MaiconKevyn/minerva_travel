"""Ligue os pontos a partir da silhueta do desenho já gerado para colorir.

Reaproveita o lineart do ponto turístico em vez de pedir arte nova: a criança
liga os números e reconhece o mesmo lugar que viu na página anterior.

Extrai a silhueta externa — por linha, o traço mais à esquerda e o mais à
direita — e amostra pontos igualmente espaçados ao longo dela. Detalhe interno
ficaria ilegível como número; o contorno é o que faz o desenho aparecer.
"""

from dataclasses import dataclass

from PIL import Image

DOT_COUNTS: dict[str, int] = {
    "preschool": 20,
    "early_reader": 30,
    "older_child": 45,
    "family": 30,
}
DEFAULT_DOT_COUNT = DOT_COUNTS["early_reader"]

INK_THRESHOLD = 128
MIN_SILHOUETTE_ROWS = 24


class DotToDotGenerationError(ValueError):
    """The line art has no usable silhouette to trace."""


@dataclass(frozen=True)
class DotToDot:
    """Numbered points in the source image's own pixel coordinates."""

    width: int
    height: int
    points: tuple[tuple[int, int], ...]


def dot_count_for(age_complexity: str) -> int:
    return DOT_COUNTS.get(age_complexity, DEFAULT_DOT_COUNT)


def build_dot_to_dot(lineart_path, *, dots: int) -> DotToDot:
    """Trace the outer silhouette of the line art into evenly spaced dots."""

    if not 10 <= dots <= 60:
        raise DotToDotGenerationError("A quantidade de pontos é inválida.")

    with Image.open(lineart_path) as opened:
        image = opened.convert("L")
    width, height = image.size
    pixels = image.load()

    left_edge: list[tuple[int, int]] = []
    right_edge: list[tuple[int, int]] = []
    for row in range(height):
        dark = [column for column in range(width) if pixels[column, row] < INK_THRESHOLD]
        if not dark:
            continue
        left_edge.append((dark[0], row))
        right_edge.append((dark[-1], row))
    if len(left_edge) < MIN_SILHOUETTE_ROWS:
        raise DotToDotGenerationError("O desenho não tem silhueta suficiente para ligar pontos.")

    # Sobe pelo lado direito para fechar o contorno num laço só.
    outline = left_edge + list(reversed(right_edge))
    return DotToDot(
        width=width,
        height=height,
        points=tuple(_sample(outline, dots, minimum_gap=minimum_dot_gap(width, height))),
    )


def minimum_dot_gap(width: int, height: int) -> int:
    """Separation that still reads as two dots after the page scales the art down.

    Um número tem ~24 px de altura na página impressa; pontos mais próximos
    que isso saem com os dois algarismos por cima um do outro.
    """

    return max(24, min(width, height) // 24)


def _sample(
    outline: list[tuple[int, int]], dots: int, *, minimum_gap: int
) -> list[tuple[int, int]]:
    """Pick `dots` points spread by distance along the traced outline."""

    lengths = [0.0]
    for (x0, y0), (x1, y1) in zip(outline, outline[1:], strict=False):
        lengths.append(lengths[-1] + ((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5)
    total = lengths[-1]
    if total <= 0:
        raise DotToDotGenerationError("O contorno do desenho não tem comprimento utilizável.")

    picked: list[tuple[int, int]] = []
    index = 0
    for step in range(dots):
        target = total * step / dots
        while index < len(lengths) - 1 and lengths[index + 1] < target:
            index += 1
        candidate = outline[index]
        # Pontos colados viram um borrão numerado; pula até separar.
        if (
            picked
            and abs(candidate[0] - picked[-1][0]) + abs(candidate[1] - picked[-1][1]) < minimum_gap
        ):
            continue
        picked.append(candidate)
    if len(picked) < 10:
        raise DotToDotGenerationError("O contorno do desenho gerou pontos demais no mesmo lugar.")
    return picked
