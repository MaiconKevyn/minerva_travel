from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from minerva_travel.activity_page_compositor import (
    BEST_MEMORY_REQUIRED_COPY,
    COLORING_ART_REGION,
    COLORING_INSTRUCTION_TEMPLATE,
    COLORING_MIN_WHITE_FRACTION,
    COLORING_TITLE,
    DETAIL_HUNT_TITLE,
    DRAWING_BLANK_REGION,
    HOMECOMING_REQUIRED_COPY,
    HOMECOMING_WRITING_BLANK_REGIONS,
    LANDMARK_VISITED_CHECKBOX,
    LANDMARK_VISITED_LABEL,
    MEMORY_BLANK_REGION,
    PAINTING_TITLE,
    WORD_SEARCH_TITLE,
    ActivityPageCompositionError,
    coloring_instruction_for,
    compose_best_memory_page,
    compose_coloring_page,
    compose_detail_hunt_page,
    compose_drawing_page,
    compose_homecoming_page,
    compose_landmark_visited_checkbox,
    compose_word_search_page,
    validate_activity_page,
)
from minerva_travel.word_search import build_word_search_grid


def _artwork(path: Path, color: str = "#d9eaf2") -> Path:
    image = Image.new("RGB", (1024, 1536), color)
    draw = ImageDraw.Draw(image)
    draw.ellipse((330, 290, 694, 780), fill="#7ca6bd", outline="#31566c", width=16)
    image.save(path, "PNG")
    return path


def _lineart(path: Path) -> Path:
    image = Image.new("RGB", (1024, 1536), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((250, 310, 774, 1260), outline="black", width=12)
    draw.polygon([(260, 310), (512, 115), (764, 310)], outline="black", fill="white")
    for x in range(320, 741, 105):
        draw.rectangle((x, 480, x + 55, 570), outline="black", width=8)
    image.save(path, "PNG")
    return path


def _white_fraction(path: Path, region: tuple[int, int, int, int]) -> float:
    with Image.open(path) as image:
        crop = image.convert("RGB").crop(region)
    colors = crop.getcolors(maxcolors=crop.width * crop.height)
    assert colors is not None
    white = next((count for count, color in colors if color == (255, 255, 255)), 0)
    return white / (crop.width * crop.height)


def test_compositor_exact_copy_contract_matches_builder_required_copy():
    assert (COLORING_TITLE, DETAIL_HUNT_TITLE, WORD_SEARCH_TITLE, PAINTING_TITLE) == (
        "Atividade para colorir",
        "Caça aos detalhes",
        "Caça-palavras",
        "Minha pintura",
    )
    assert BEST_MEMORY_REQUIRED_COPY == (
        "Minha melhor memória",
        "Meu lugar favorito foi...",
        "O que eu mais gostei foi...",
        "Eu descobri que...",
        "Desenhe sua melhor lembrança",
        "Assinatura",
        "Data",
    )
    assert LANDMARK_VISITED_LABEL == "Já visitei"
    assert HOMECOMING_REQUIRED_COPY == (
        "Hora de voltar para casa",
        "Nossa grande aventura está chegando ao fim.",
        "Depois de conhecer lugares incríveis, chegou a hora de voltar para casa.",
        "Mas todas essas lembranças vão continuar com a gente.",
        "Uma coisa que quero contar quando chegar em casa:",
    )
    assert COLORING_INSTRUCTION_TEMPLATE == (
        "Agora é a vez de colorir {landmark_name} do seu jeito."
    )


def test_coloring_instruction_is_exact_point_specific_copy():
    assert coloring_instruction_for("  Torre   Eiffel ") == (
        "Agora é a vez de colorir Torre Eiffel do seu jeito."
    )


def test_landmark_compositor_adds_one_empty_printable_visited_checkbox(tmp_path):
    output = tmp_path / "landmark.png"
    compose_landmark_visited_checkbox(_artwork(tmp_path / "art.png"), output)

    validate_activity_page(output)
    left, top, right, bottom = LANDMARK_VISITED_CHECKBOX
    with Image.open(output) as image:
        rgb = image.convert("RGB")
        assert rgb.getpixel(((left + right) // 2, (top + bottom) // 2)) == (255, 255, 255)
        assert rgb.getpixel((left, (top + bottom) // 2)) == (21, 52, 81)
        label_crop = rgb.crop((438, 1418, 650, 1480))
        colors = label_crop.getcolors(maxcolors=label_crop.width * label_crop.height)
        assert colors is not None
        assert any(color == (21, 52, 81) for _count, color in colors)


def test_coloring_compositor_outputs_binary_printable_page(tmp_path):
    output = tmp_path / "coloring.png"
    compose_coloring_page(
        _lineart(tmp_path / "art.png"),
        output,
        landmark_name="Torre Eiffel",
    )

    validate_activity_page(output, monochrome=True)
    with Image.open(output) as image:
        assert image.size == (1024, 1536)
        assert image.format == "PNG"
        colors = image.convert("RGB").getcolors(maxcolors=1024 * 1536)
        assert colors is not None
        assert {color for _count, color in colors} <= {(0, 0, 0), (255, 255, 255)}
        white = next((count for count, color in colors if color == (255, 255, 255)), 0)
        assert white / (1024 * 1536) >= COLORING_MIN_WHITE_FRACTION
        # Provider artwork is fitted below the code-owned heading and instruction.
        art_ink = (
            image.convert("L")
            .crop(COLORING_ART_REGION)
            .point(lambda value: 255 if value < 128 else 0)
        )
        assert art_ink.getbbox() is not None


def test_coloring_compositor_rejects_unusable_solid_artwork_atomically(tmp_path):
    output = tmp_path / "coloring.png"
    output.write_bytes(b"previous-attempt")

    with pytest.raises(ActivityPageCompositionError, match="traços infantis"):
        compose_coloring_page(
            _artwork(tmp_path / "solid.png", color="black"),
            output,
            landmark_name="Torre Eiffel",
        )

    assert output.read_bytes() == b"previous-attempt"
    assert not (tmp_path / ".coloring.png.tmp").exists()


def test_detail_hunt_composites_bounded_exact_checklist(tmp_path):
    output = tmp_path / "detail.png"
    compose_detail_hunt_page(
        _artwork(tmp_path / "art.png"),
        output,
        landmark_name="Torre Eiffel",
        instruction="Observe a ilustração e marque suas descobertas.",
        clues=[
            "Encontre o contorno principal.",
            "Ache uma forma que se repete.",
            "Observe um detalhe perto do topo.",
        ],
    )

    validate_activity_page(output)
    with Image.open(output) as image:
        # Interior of the first deterministic checkbox is white.
        assert image.convert("RGB").getpixel((107, 951)) == (255, 255, 255)


def test_detail_hunt_rejects_unvalidated_clues(tmp_path):
    with pytest.raises(ActivityPageCompositionError, match="Quantidade"):
        compose_detail_hunt_page(
            _artwork(tmp_path / "art.png"),
            tmp_path / "detail.png",
            landmark_name="Torre Eiffel",
            instruction="Observe.",
            clues=["Somente uma pista"],
        )


def test_word_search_composites_only_a_solvable_seeded_grid(tmp_path):
    grid, words = build_word_search_grid(
        ["TORRE", "EIFFEL", "PARIS", "VIAGEM"], seed="paris:eiffel"
    )
    output = tmp_path / "words.png"
    compose_word_search_page(
        _artwork(tmp_path / "art.png"),
        output,
        landmark_name="Torre Eiffel",
        instruction="Encontre as palavras na horizontal ou vertical.",
        grid=grid,
        words=words,
    )

    validate_activity_page(output)
    with Image.open(output) as image:
        # The code-owned grid panel is opaque and independent from model artwork.
        assert image.convert("RGB").getpixel((170, 258)) == (255, 253, 248)


def test_word_search_rejects_a_word_missing_from_the_grid(tmp_path):
    grid, words = build_word_search_grid(["TORRE", "PARIS"], seed="stable")
    with pytest.raises(ActivityPageCompositionError, match="sem solução"):
        compose_word_search_page(
            _artwork(tmp_path / "art.png"),
            tmp_path / "words.png",
            landmark_name="Torre Eiffel",
            instruction="Encontre.",
            grid=grid,
            words=[*words, "LONDRES"],
        )


def test_drawing_and_memory_preserve_measurable_blank_response_areas(tmp_path):
    artwork = _artwork(tmp_path / "art.png", color="#427a8f")
    drawing = tmp_path / "drawing.png"
    memory = tmp_path / "memory.png"

    compose_drawing_page(
        artwork,
        drawing,
        landmark_name="Torre Eiffel",
        prompt="Agora é a sua vez de criar uma pintura da Torre Eiffel do seu jeito.",
    )
    compose_best_memory_page(
        artwork,
        memory,
        family_title="Família Moraes",
        trip_date="Julho de 2026",
    )

    assert _white_fraction(drawing, DRAWING_BLANK_REGION) == 1
    assert _white_fraction(memory, MEMORY_BLANK_REGION) == 1
    with Image.open(drawing) as drawing_image:
        assert drawing_image.convert("RGB").getpixel((80, 1320)) == (255, 253, 248)
    with Image.open(memory) as memory_image:
        assert memory_image.convert("RGB").getpixel((65, 1265)) == (255, 253, 248)
    validate_activity_page(drawing, blank_regions=[DRAWING_BLANK_REGION])
    validate_activity_page(memory, blank_regions=[MEMORY_BLANK_REGION])


def test_homecoming_compositor_adds_exact_closing_copy_and_blank_writing_lines(tmp_path):
    output = tmp_path / "homecoming.png"
    compose_homecoming_page(_artwork(tmp_path / "homecoming-art.png"), output)

    validate_activity_page(output, blank_regions=HOMECOMING_WRITING_BLANK_REGIONS)
    with Image.open(output) as image:
        rgb = image.convert("RGB")
        assert rgb.size == (1024, 1536)
        assert rgb.getpixel((80, 1200)) == (255, 253, 248)
        assert rgb.getpixel((200, 1340)) == (21, 52, 81)
        for left, top, right, bottom in HOMECOMING_WRITING_BLANK_REGIONS:
            assert rgb.getpixel(((left + right) // 2, (top + bottom) // 2)) == (255, 253, 248)


def test_compositor_rejects_wrong_size_provider_artwork(tmp_path):
    source = tmp_path / "small.png"
    Image.new("RGB", (512, 512), "white").save(source, "PNG")

    with pytest.raises(ActivityPageCompositionError, match="1024x1536"):
        compose_drawing_page(
            source,
            tmp_path / "drawing.png",
            landmark_name="Torre Eiffel",
            prompt="Desenhe.",
        )
