"""O número impresso tem de ser o número que a criança acha.

As cenas aqui imitam o que o provedor devolve de verdade: aquarela colorida
sobre papel creme, com grão, e um monumento de traço fino que muda um pouco a
cada geração porque o modelo redesenha a cena inteira em vez de remendá-la.
A fixture antiga era de elipses pretas sólidas sobre cinza liso — passava com
folga enquanto a página impressa prometia sete erros e tinha dois.
"""

from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from minerva_travel.spot_the_difference import (
    MAX_DIFFERENCES,
    MIN_DIFFERENCES,
    SpotTheDifferenceError,
    find_difference_regions,
)

SIZE = (1536, 1024)
PAPER = (247, 240, 222)
LANDMARK_INK = (150, 116, 74)
# Seis objetos bem separados, como o prompt pede da cena base.
OBJECTS = [
    ((180, 180), (108, 148, 196)),
    ((520, 200), (196, 132, 96)),
    ((1180, 210), (176, 96, 108)),
    ((200, 780), (120, 156, 108)),
    ((640, 800), (198, 168, 92)),
    ((1240, 790), (96, 132, 168)),
]


def _grain(draw: ImageDraw.ImageDraw) -> None:
    """Grão do papel: variação fraca e acromática por toda a cena."""

    for y in range(0, SIZE[1], 8):
        shade = 244 + (y // 8) % 5
        draw.line((0, y, SIZE[0], y), fill=(shade, shade - 6, shade - 24))


def _landmark(draw: ImageDraw.ImageDraw, *, jitter: int = 0) -> None:
    """Torre de treliça fina. O jitter imita o redesenho do provedor."""

    for step in range(14):
        half = 150 - step * 9
        top = 120 + step * 58
        draw.line(
            (768 - half + jitter, top, 768 + half - jitter, top + 58),
            fill=LANDMARK_INK,
            width=5,
        )
        draw.line(
            (768 + half - jitter, top, 768 - half + jitter, top + 58),
            fill=LANDMARK_INK,
            width=5,
        )


def _scene(
    path: Path,
    *,
    recolored: dict[int, tuple[int, int, int]] | None = None,
    removed: set[int] | None = None,
    jitter: int = 0,
) -> Path:
    image = Image.new("RGB", SIZE, PAPER)
    draw = ImageDraw.Draw(image)
    _grain(draw)
    _landmark(draw, jitter=jitter)
    for index, ((x, y), color) in enumerate(OBJECTS):
        if removed and index in removed:
            continue
        fill = (recolored or {}).get(index, color)
        draw.ellipse((x - 90, y - 90, x + 90, y + 90), fill=fill)
    image.save(path, "PNG")
    return path


def test_three_recolored_objects_are_found_as_three_differences(tmp_path: Path):
    base = _scene(tmp_path / "base.png")
    variant = _scene(
        tmp_path / "variant.png",
        recolored={0: (206, 104, 96), 2: (104, 168, 120), 4: (112, 108, 190)},
    )

    regions = find_difference_regions(base, variant)

    assert len(regions) == 3
    assert MIN_DIFFERENCES <= len(regions) <= MAX_DIFFERENCES
    # Cada diferença precisa de um centro próprio para virar um item da lista.
    assert len({region.center for region in regions}) == 3


def test_the_landmark_being_redrawn_is_not_counted_as_a_difference(tmp_path: Path):
    """O defeito que a família viu: sete erros impressos, dois achaveis.

    Quatro das sete manchas eram a própria torre, redesenhada com o traço um
    pouco deslocado. Em brilho isso é indistinguível de uma troca de cor; em
    cor, não é.
    """

    base = _scene(tmp_path / "base.png")
    variant = _scene(
        tmp_path / "variant.png",
        recolored={0: (206, 104, 96), 2: (104, 168, 120), 4: (112, 108, 190)},
        jitter=6,
    )

    assert len(find_difference_regions(base, variant)) == 3


def test_only_the_landmark_redrawn_is_refused_instead_of_printing_a_non_puzzle(tmp_path: Path):
    base = _scene(tmp_path / "base.png")
    jittered = _scene(tmp_path / "jitter.png", jitter=6)

    # Nada mudou de propósito: a página não sai prometendo erros inexistentes.
    with pytest.raises(SpotTheDifferenceError):
        find_difference_regions(base, jittered)


def test_two_patches_of_one_repainted_object_count_as_a_single_difference(tmp_path: Path):
    """A copa roxa e a grama roxa ao pé dela são a mesma árvore.

    Contadas em separado, a página prometia sete diferenças num Coliseu que
    tinha cinco.
    """

    def scene(path: Path, tree: tuple[int, int, int]) -> Path:
        image = Image.new("RGB", SIZE, PAPER)
        draw = ImageDraw.Draw(image)
        _grain(draw)
        draw.ellipse((110, 300, 470, 560), fill=tree)
        # A sombra caída fica separada da copa por uma faixa de papel.
        draw.ellipse((200, 620, 380, 680), fill=tree)
        for (x, y), color in OBJECTS[2:5]:
            draw.ellipse((x - 90, y - 90, x + 90, y + 90), fill=color)
        image.save(path, "PNG")
        return path

    base = scene(tmp_path / "base.png", (120, 156, 108))
    variant = scene(tmp_path / "variant.png", (168, 104, 190))

    with pytest.raises(SpotTheDifferenceError) as raised:
        find_difference_regions(base, variant)
    # Uma árvore só: não chega ao mínimo, em vez de virar duas diferenças.
    assert "1 diferenças" in str(raised.value)


def test_a_removed_object_counts_as_one_difference(tmp_path: Path):
    base = _scene(tmp_path / "base.png")
    variant = _scene(
        tmp_path / "variant.png",
        removed={1},
        recolored={3: (198, 108, 168), 5: (214, 156, 84)},
    )

    assert len(find_difference_regions(base, variant)) == 3


def test_nudging_the_shade_of_an_object_is_not_counted(tmp_path: Path):
    """Um verde 8% mais escuro não é um erro que a criança ache lado a lado.

    O limiar separa matiz de tom com folga larga — uma troca verde/vermelho
    mede 74 e esta variação mede 9 — mas não é um corte absoluto: escurecer um
    objeto em 20% ou mais volta a contar, e tudo bem, porque a essa altura a
    diferença de fato aparece na página impressa.
    """

    base = _scene(tmp_path / "base.png")
    darker = _scene(
        tmp_path / "darker.png",
        recolored={
            index: tuple(round(channel * 0.92) for channel in OBJECTS[index][1])
            for index in (0, 2, 4)
        },
    )

    with pytest.raises(SpotTheDifferenceError):
        find_difference_regions(base, darker)


def test_too_few_differences_are_refused_instead_of_printing_a_non_puzzle(tmp_path: Path):
    base = _scene(tmp_path / "base.png")
    variant = _scene(tmp_path / "variant.png", recolored={0: (206, 104, 96)})

    # Uma diferença não é um jogo; a página não sai.
    with pytest.raises(SpotTheDifferenceError):
        find_difference_regions(base, variant)


def test_the_printed_count_is_whatever_was_actually_measured(tmp_path: Path):
    base = _scene(tmp_path / "base.png")
    variant = _scene(
        tmp_path / "variant.png",
        recolored={0: (206, 104, 96), 1: (104, 168, 120), 3: (112, 108, 190)},
        removed={5},
    )

    # A instrução impressa vem daqui, então nunca promete mais do que existe.
    assert len(find_difference_regions(base, variant)) == 4


def test_a_completely_redrawn_scene_is_refused(tmp_path: Path):
    base = _scene(tmp_path / "base.png")
    redrawn = tmp_path / "redrawn.png"
    Image.new("RGB", SIZE, (40, 90, 170)).save(redrawn, "PNG")

    with pytest.raises(SpotTheDifferenceError):
        find_difference_regions(base, redrawn)


def test_identical_artworks_are_refused(tmp_path: Path):
    base = _scene(tmp_path / "base.png")
    same = _scene(tmp_path / "same.png")

    with pytest.raises(SpotTheDifferenceError):
        find_difference_regions(base, same)


def test_mismatched_sizes_are_refused(tmp_path: Path):
    base = _scene(tmp_path / "base.png")
    small = tmp_path / "small.png"
    Image.new("RGB", (512, 512), PAPER).save(small, "PNG")

    with pytest.raises(SpotTheDifferenceError):
        find_difference_regions(base, small)
