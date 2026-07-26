from pathlib import Path

import pytest
from PIL import Image

from minerva_travel.activity_page_compositor import (
    NEWSPAPER_HEADLINE_TITLE,
    PAGE_IMAGE_SIZE,
    ActivityPageCompositionError,
    compose_writing_page,
)


def _artwork(tmp_path: Path, color: tuple[int, int, int] = (255, 255, 255)) -> Path:
    path = tmp_path / "artwork.png"
    Image.new("RGB", PAGE_IMAGE_SIZE, color).save(path, "PNG")
    return path


def test_writing_page_prints_every_label_and_keeps_room_to_write(tmp_path: Path):
    output = tmp_path / "page.png"

    compose_writing_page(
        _artwork(tmp_path),
        output,
        title=NEWSPAPER_HEADLINE_TITLE,
        subtitle="Torre Eiffel",
        instruction="Escreva a manchete do jornal sobre a sua visita.",
        fields=[("A manchete de hoje é:", 2), ("O que aconteceu:", 3)],
    )

    with Image.open(output) as page:
        assert page.size == PAGE_IMAGE_SIZE


def test_writing_page_refuses_a_layout_that_would_not_fit(tmp_path: Path):
    # Cortar o último campo em silêncio deixaria a criança sem onde escrever.
    with pytest.raises(ActivityPageCompositionError):
        compose_writing_page(
            _artwork(tmp_path),
            tmp_path / "page.png",
            title="Diário do dia",
            subtitle="Torre Eiffel",
            instruction="Conte como foi o dia.",
            fields=[(f"Campo {index}", 6) for index in range(5)],
        )


def test_writing_page_rejects_duplicated_and_empty_labels(tmp_path: Path):
    artwork = _artwork(tmp_path)
    for fields in (
        [("Igual", 2), ("Igual", 2)],
        [("", 2)],
        [("Sem linhas", 0)],
    ):
        with pytest.raises(ActivityPageCompositionError):
            compose_writing_page(
                artwork,
                tmp_path / "page.png",
                title="Diário do dia",
                subtitle="Torre Eiffel",
                instruction="Conte como foi o dia.",
                fields=fields,
            )


def test_writing_page_keeps_white_paper_even_over_dark_artwork(tmp_path: Path):
    # A arte é moldura, não fundo de texto: sobre um fundo escuro a criança
    # não leria o que escreveu, então o painel entra opaco por cima.
    output = tmp_path / "page.png"

    compose_writing_page(
        _artwork(tmp_path, color=(18, 22, 30)),
        output,
        title="Diário do dia",
        subtitle="Torre Eiffel",
        instruction="Conte como foi o dia.",
        fields=[("Melhor momento:", 3), ("Palavra nova:", 2)],
    )

    with Image.open(output) as page:
        band = page.convert("RGB").crop((120, 400, 900, 420))
    assert all(minimum >= 248 for minimum, _maximum in band.getextrema())


def test_every_activity_artwork_asks_for_the_same_house_style():
    """Uma identidade só para o caderno inteiro.

    Sem contrato compartilhado, cada atividade saía com fundo próprio e o
    guia parecia uma colagem de fontes diferentes.
    """

    from minerva_travel.models import OPTIONAL_LANDMARK_ACTIVITY_TYPES
    from minerva_travel.page_generation import activity_artwork_prompt

    visual_types = [
        activity_type
        for activity_type in OPTIONAL_LANDMARK_ACTIVITY_TYPES
        if activity_type not in {"family_coloring", "investigator"}
    ]
    for activity_type in visual_types:
        prompt = activity_artwork_prompt(
            activity_type=activity_type,
            landmark_name="Coliseu",
            city="Roma",
            country="Itália",
            age_complexity="early_reader",
            has_landmark_reference=False,
            has_revision_reference=False,
        )
        assert "HOUSE STYLE" in prompt, activity_type
        # Paleta e traço são o que faz o caderno parecer um caderno só.
        assert "vintage children's storybook watercolour" in prompt, activity_type
        assert "aged cream, golden ochre, muted navy blue" in prompt, activity_type
        # O texto exato continua sendo composto por código, nunca desenhado.
        assert "text-free" in prompt.lower(), activity_type

        # A moldura ornamentada é a variante padrão; o "ache os erros" recorta
        # a arte em painéis e a moldura seria descartada.
        framed = "ornate double-rule border frame" in prompt
        assert framed is (activity_type != "spot_the_difference"), activity_type
