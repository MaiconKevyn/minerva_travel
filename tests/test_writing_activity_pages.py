from pathlib import Path

import pytest
from PIL import Image

from minerva_travel.activity_page_compositor import (
    NEWSPAPER_HEADLINE_TITLE,
    PAGE_IMAGE_SIZE,
    PAPER,
    ActivityPageCompositionError,
    compose_writing_page,
)
from minerva_travel.visual_identity import PALETA_PROSA

# A frase que so existe na identidade vigente. O teste protege que TODAS as
# paginas pecam o MESMO estilo — nao qual estilo e.
MARCA_DO_ESTILO = "crayon and chalk brush"
PAPEL_RGB = tuple(int(PAPER[i : i + 2], 16) for i in (1, 3, 5))


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
    piso = min(PAPEL_RGB) - 4
    assert all(minimum >= piso for minimum, _maximum in band.getextrema())


def test_every_activity_artwork_asks_for_the_same_house_style():
    """Uma identidade só para o caderno, em três variantes de meio.

    Aplicar a moldura a tudo quebrou duas páginas: em colorir ela virou borda
    preta torta na conversão monocromática, e no ligue os pontos o traçador
    seguiu a moldura em vez do monumento.
    """

    from minerva_travel.models import OPTIONAL_LANDMARK_ACTIVITY_TYPES
    from minerva_travel.page_generation import activity_artwork_prompt

    lineart = {"coloring", "dot_to_dot"}
    for activity_type in OPTIONAL_LANDMARK_ACTIVITY_TYPES:
        if activity_type in {"investigator", "family_coloring"}:
            continue  # têm prompt próprio, cobertos abaixo
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
        assert "text-free" in prompt.lower(), activity_type

        if activity_type in lineart:
            # Traço puro: sem contorno fechado a criança não tem onde pintar,
            # e no ligue os pontos o traçador seguiria a textura em vez do
            # monumento.
            assert "pure black line art" in prompt, activity_type
            assert "no border frame" in prompt.lower(), activity_type
            assert MARCA_DO_ESTILO not in prompt, activity_type
        else:
            assert MARCA_DO_ESTILO in prompt, activity_type
            assert PALETA_PROSA in prompt, activity_type


def test_the_two_family_activities_share_the_house_style_too():
    """Elas têm prompt próprio e ficaram de fora na primeira passada."""

    from minerva_travel.page_generation import (
        family_coloring_artwork_prompt,
        investigator_artwork_prompt,
    )

    coloring = family_coloring_artwork_prompt(
        landmark_name="Coliseu",
        city="Roma",
        country="Itália",
        age_complexity="early_reader",
        expected_visible_family_member_count=3,
        has_family_cover=True,
        has_landmark_reference=False,
        has_landmark_page_reference=False,
        has_revision_reference=False,
    )
    assert "pure black line art" in coloring

    investigator = investigator_artwork_prompt(
        child_count=2,
        landmark_name="Coliseu",
        city="Roma",
        country="Itália",
        age_complexity="early_reader",
        expected_visible_family_member_count=3,
        has_family_cover=True,
        has_landmark_reference=False,
        has_landmark_page_reference=False,
        has_revision_reference=False,
    )
    assert MARCA_DO_ESTILO in investigator


def test_every_page_of_the_guide_shares_the_house_style():
    """Capa, sumário, destino, ponto turístico e as duas páginas finais.

    Um livro em que só as atividades compartilham a linguagem continua sendo
    uma colagem — e as páginas dos pontos turísticos são as mais numerosas
    depois delas.
    """

    from minerva_travel import page_generation as generation

    family = {
        "family_title": "Família Lima",
        "trip_date": "Julho de 2026",
        "landmark_names": ["Coliseu"],
        "has_revision_reference": False,
    }
    pages = {
        "capa": generation.cover_page_prompt(
            **family, expected_visible_family_member_count=3
        ),
        "sumario": generation.summary_page_prompt(
            family_title="Família Lima",
            trip_date="Julho de 2026",
            landmark_names=["Coliseu"],
            has_revision_reference=False,
        ),
        "destino": generation.destination_intro_page_prompt(
            title="Roma",
            city="Roma",
            country="Itália",
            learning_points=["Roma tem muitas fontes."],
            curiosity="O Coliseu recebia jogos.",
            curiosity_label="Você sabia?",
            landmark_names=["Coliseu"],
            has_revision_reference=False,
        ),
        "ponto": generation.landmark_page_prompt(
            family_title="Família Lima",
            trip_date="Julho de 2026",
            landmark_name="Coliseu",
            city="Roma",
            country="Itália",
            description="Um anfiteatro romano.",
            curiosity="Cabiam milhares de pessoas.",
            curiosity_label="Você sabia?",
            include_family=False,
            expected_visible_family_member_count=None,
            has_revision_reference=False,
        ),
        "melhor_memoria": generation.best_memory_artwork_prompt(
            **family, age_complexity="early_reader"
        ),
        "volta_para_casa": generation.homecoming_page_prompt(
            **family, age_complexity="early_reader", expected_visible_family_member_count=3
        ),
    }
    for page, prompt in pages.items():
        assert "HOUSE STYLE" in prompt, page
        assert MARCA_DO_ESTILO in prompt, page
        assert PALETA_PROSA in prompt, page
