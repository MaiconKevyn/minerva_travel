from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from minerva_travel.dot_to_dot import (
    DotToDotGenerationError,
    build_dot_to_dot,
    dot_count_for,
    minimum_dot_gap,
)


def _tower_lineart(tmp_path: Path) -> Path:
    """A silhueta simples de torre, como o lineart de colorir entrega."""
    path = tmp_path / "lineart.png"
    image = Image.new("L", (400, 600), 255)
    draw = ImageDraw.Draw(image)
    draw.polygon([(200, 60), (330, 540), (70, 540)], outline=0, width=6)
    draw.rectangle((60, 540, 340, 560), outline=0, width=6)
    image.save(path, "PNG")
    return path


def test_dots_follow_the_outline_and_stay_inside_the_drawing(tmp_path: Path):
    puzzle = build_dot_to_dot(_tower_lineart(tmp_path), dots=30)

    assert puzzle.width == 400
    assert puzzle.height == 600
    assert 10 <= len(puzzle.points) <= 30
    assert all(0 <= x < puzzle.width and 0 <= y < puzzle.height for x, y in puzzle.points)


def test_consecutive_dots_are_far_enough_apart_to_be_numbered(tmp_path: Path):
    puzzle = build_dot_to_dot(_tower_lineart(tmp_path), dots=30)

    gap = minimum_dot_gap(puzzle.width, puzzle.height)
    for (x0, y0), (x1, y1) in zip(puzzle.points, puzzle.points[1:], strict=False):
        # Dois números colados viram um borrão que a criança não consegue ligar.
        assert abs(x1 - x0) + abs(y1 - y0) >= gap


def test_the_outline_covers_the_whole_drawing_not_just_one_side(tmp_path: Path):
    puzzle = build_dot_to_dot(_tower_lineart(tmp_path), dots=40)

    xs = [x for x, _y in puzzle.points]
    ys = [_y for _x, _y in puzzle.points]
    # Se só o lado esquerdo fosse traçado, a torre sairia pela metade.
    assert max(xs) - min(xs) > puzzle.width * 0.5
    assert max(ys) - min(ys) > puzzle.height * 0.5


def test_dot_count_grows_with_the_age_band():
    assert dot_count_for("preschool") < dot_count_for("older_child")
    assert dot_count_for("desconhecido") == dot_count_for("early_reader")


def test_blank_line_art_is_refused_instead_of_printing_an_empty_puzzle(tmp_path: Path):
    blank = tmp_path / "blank.png"
    Image.new("L", (400, 600), 255).save(blank, "PNG")

    with pytest.raises(DotToDotGenerationError):
        build_dot_to_dot(blank, dots=30)


def test_impossible_dot_counts_are_refused(tmp_path: Path):
    lineart = _tower_lineart(tmp_path)
    for dots in (5, 200):
        with pytest.raises(DotToDotGenerationError):
            build_dot_to_dot(lineart, dots=dots)
