from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from minerva_travel.spot_the_difference import (
    MAX_DIFFERENCES,
    MIN_DIFFERENCES,
    SpotTheDifferenceError,
    find_difference_regions,
)

SIZE = (1024, 1024)


def _scene(path: Path, *, blobs: list[tuple[int, int]]) -> Path:
    image = Image.new("L", SIZE, 240)
    draw = ImageDraw.Draw(image)
    draw.rectangle((100, 100, 900, 900), outline=60, width=8)
    for x, y in blobs:
        draw.ellipse((x - 40, y - 40, x + 40, y + 40), fill=20)
    image.save(path, "PNG")
    return path


def test_six_added_shapes_are_found_as_six_separate_differences(tmp_path: Path):
    base = _scene(tmp_path / "base.png", blobs=[])
    variant = _scene(
        tmp_path / "variant.png",
        blobs=[(200, 200), (500, 200), (800, 200), (200, 600), (500, 600), (800, 600)],
    )

    regions = find_difference_regions(base, variant)

    assert len(regions) == 6
    assert MIN_DIFFERENCES <= len(regions) <= MAX_DIFFERENCES
    # Cada diferença precisa ter um centro próprio para virar círculo no gabarito.
    centers = {region.center for region in regions}
    assert len(centers) == 6


def test_too_few_differences_are_refused_instead_of_printing_a_non_puzzle(tmp_path: Path):
    base = _scene(tmp_path / "base.png", blobs=[])
    variant = _scene(tmp_path / "variant.png", blobs=[(200, 200), (500, 200)])

    # Duas diferenças não são um jogo; a página não sai.
    with pytest.raises(SpotTheDifferenceError):
        find_difference_regions(base, variant)


def test_the_printed_count_is_whatever_was_actually_measured(tmp_path: Path):
    base = _scene(tmp_path / "base.png", blobs=[])
    variant = _scene(
        tmp_path / "variant.png", blobs=[(200, 200), (500, 200), (800, 200), (200, 600)]
    )

    # A instrução impressa vem daqui, então nunca promete mais do que existe.
    assert len(find_difference_regions(base, variant)) == 4


def test_a_completely_redrawn_scene_is_refused(tmp_path: Path):
    base = _scene(tmp_path / "base.png", blobs=[])
    redrawn = tmp_path / "redrawn.png"
    Image.new("L", SIZE, 10).save(redrawn, "PNG")

    with pytest.raises(SpotTheDifferenceError):
        find_difference_regions(base, redrawn)


def test_identical_artworks_are_refused(tmp_path: Path):
    base = _scene(tmp_path / "base.png", blobs=[(300, 300)])
    same = _scene(tmp_path / "same.png", blobs=[(300, 300)])

    with pytest.raises(SpotTheDifferenceError):
        find_difference_regions(base, same)


def test_mismatched_sizes_are_refused(tmp_path: Path):
    base = _scene(tmp_path / "base.png", blobs=[])
    small = tmp_path / "small.png"
    Image.new("L", (512, 512), 240).save(small, "PNG")

    with pytest.raises(SpotTheDifferenceError):
        find_difference_regions(base, small)
