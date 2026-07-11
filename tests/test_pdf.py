from html import unescape
from pathlib import Path

from minerva_travel.catalog import load_catalog
from minerva_travel.guide_builder import build_guide_context
from minerva_travel.models import (
    Catalog,
    Destination,
    GuideRequest,
    Landmark,
    RestaurantRecommendation,
)
from minerva_travel.pdf import render_guide_html, write_pdf


def test_render_guide_html_contains_selected_content():
    catalog = load_catalog(Path("data/destinations/europe_2026.json"))
    request = GuideRequest(
        title="Pequenos Exploradores pela Europa",
        children_names=["Alice", "Antonio"],
        parents_names=["Ana", "Otavio"],
        year=2026,
        selected_landmarks=["paris:eiffel-tower"],
    )
    context = build_guide_context(
        request,
        catalog,
        Path("runtime/generated/cover.png"),
        summary_image=Path("runtime/generated/summary.png"),
    )

    html = render_guide_html(context)

    assert "Alice e Antonio" in html
    assert "Torre Eiffel" in html
    assert "JÁ VISITEI" in html
    assert "@page" in html
    assert "size: A4" in html
    assert '<meta name="author" content="Minerva Travel">' in html


def test_render_guide_html_contains_image_credits_when_present():
    catalog = load_catalog(Path("data/destinations/europe_2026.json"))
    request = GuideRequest(
        title="Pequenos Exploradores pela Europa",
        children_names=["Alice"],
        parents_names=["Ana"],
        year=2026,
        selected_landmarks=["paris:eiffel-tower"],
    )
    context = build_guide_context(request, catalog, Path("runtime/generated/cover.png"))
    context.image_credits = [
        {
            "landmark_name": "Torre Eiffel",
            "source_url": "https://commons.wikimedia.org/wiki/File:Eiffel_Tower.jpg",
            "author": "Jane Doe",
            "license_short_name": "CC BY-SA 4.0",
            "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
            "credit": "Jane Doe / Wikimedia Commons",
        }
    ]

    html = render_guide_html(context)

    assert "Créditos das imagens" in html
    assert "Jane Doe / Wikimedia Commons" in html


def test_render_guide_html_contains_trip_phases_language_tips_and_reflection_prompts():
    catalog = load_catalog(Path("data/destinations/europe_2026.json"))
    request = GuideRequest(
        title="Pequenos Exploradores pela Europa",
        children_names=["Alice"],
        parents_names=["Ana"],
        year=2026,
        selected_landmarks=[
            "paris:eiffel-tower",
            "london:big-ben",
            "lisbon:oceanario",
        ],
    )
    context = build_guide_context(request, catalog, Path("runtime/generated/cover.png"))

    html = render_guide_html(context)

    assert "Antes da viagem" in html
    assert "Durante a viagem" in html
    assert "Depois da viagem" in html
    assert "Palavras para usar" in html
    assert "Bonjour" in html
    assert "Thank you" in html
    assert "Obrigado/obrigada" in html
    assert "Caça ao detalhe" in html
    assert "O que eu aprendi" in html
    assert ".phase-badge" in html
    assert ".language-tip-card" in html
    assert ".observation-card" in html
    assert ".memory-boxes" in html


def test_render_guide_html_places_structured_language_activity_before_trip():
    catalog = load_catalog(Path("data/destinations/europe_2026.json"))
    request = GuideRequest(
        title="Pequenos Exploradores pela Europa",
        children_names=["Alice"],
        children_ages=[6],
        parents_names=["Ana"],
        year=2026,
        selected_landmarks=["paris:eiffel-tower"],
    )
    context = build_guide_context(request, catalog, Path("runtime/generated/cover.png"))

    html = render_guide_html(context)
    language_section = html.split('class="page language-page phase-before"', maxsplit=1)[1].split(
        '<section class="page landmark-page"', maxsplit=1
    )[0]

    assert "Palavras para usar" in language_section
    assert "Bonjour" in language_section
    assert "Leia a palavra" in language_section
    assert "language-learning-activity" in language_section


def test_render_guide_html_omits_uncertain_language_content_and_pdf_still_builds(tmp_path):
    catalog = Catalog(
        id="custom",
        title="Custom",
        destinations=[
            Destination(
                id="custom-atlantida",
                country="Atlantida",
                city="Cidade Misteriosa",
                display_title="Atlantida - Cidade Misteriosa",
                intro=["Um destino inventado pela familia."],
                favorites_prompt="Minha lembranca favorita foi...",
                coloring_title="Desenho da viagem",
                coloring_subtitle="Para colorir depois.",
                landmarks=[
                    Landmark(
                        id="portal",
                        name="Portal",
                        description=["Um lugar especial para imaginar."],
                        image=Path("assets/landmarks/sample.png"),
                        lineart_image=Path("assets/lineart/sample.png"),
                        sort_order=1,
                    )
                ],
            )
        ],
    )
    request = GuideRequest(
        title="Guia Misterioso",
        children_names=["Alice"],
        parents_names=["Ana"],
        year=2026,
        selected_landmarks=["custom-atlantida:portal"],
    )
    context = build_guide_context(request, catalog, Path("runtime/generated/cover.png"))
    output = tmp_path / "guide-without-language.pdf"

    html = render_guide_html(context)
    pdf = write_pdf(context, output)

    assert 'class="page language-page' not in html
    assert "language-learning-activity" not in html
    assert "Palavras para usar" not in html
    assert pdf.exists()
    assert pdf.stat().st_size > 1000


def test_render_guide_html_omits_restaurants_without_entitlement():
    catalog = load_catalog(Path("data/destinations/europe_2026.json"))
    request = GuideRequest(
        title="Pequenos Exploradores pela Europa",
        children_names=["Alice"],
        parents_names=["Ana"],
        year=2026,
        selected_landmarks=["paris:eiffel-tower"],
    )
    context = build_guide_context(
        request,
        catalog,
        Path("runtime/generated/cover.png"),
        restaurant_recommendations=[
            RestaurantRecommendation(
                destination_id="paris",
                name="Bistro Familiar",
                nearby_context="perto de Torre Eiffel",
                reason="Boa pausa para familia entre passeios.",
            )
        ],
    )

    html = render_guide_html(context)

    assert "Onde comer perto do roteiro" not in html
    assert "Bistro Familiar" not in html


def test_render_guide_html_includes_optional_restaurants_with_freshness_note():
    catalog = load_catalog(Path("data/destinations/europe_2026.json"))
    request = GuideRequest(
        title="Pequenos Exploradores pela Europa",
        children_names=["Alice"],
        parents_names=["Ana"],
        year=2026,
        selected_landmarks=["paris:eiffel-tower"],
        restaurant_recommendations_extra=True,
    )
    context = build_guide_context(
        request,
        catalog,
        Path("runtime/generated/cover.png"),
        restaurant_recommendations=[
            RestaurantRecommendation(
                destination_id="paris",
                name="Bistro Familiar",
                nearby_context="perto de Torre Eiffel",
                reason="Boa pausa para familia entre passeios.",
                cuisine="francesa",
                suitability_notes=["Cardapio simples para criancas"],
            )
        ],
    )

    html = render_guide_html(context)

    assert "Onde comer perto do roteiro" in html
    assert "Bistro Familiar" in html
    assert "perto de Torre Eiffel" in html
    assert "Cardapio simples para criancas" in html
    assert "Confira horários, reservas e funcionamento antes de visitar" in html


def test_render_guide_html_adds_trip_summary_after_cover():
    catalog = load_catalog(Path("data/destinations/europe_2026.json"))
    request = GuideRequest(
        title="Pequenos Exploradores pela Europa",
        children_names=["Alice"],
        parents_names=["Ana"],
        year=2026,
        selected_landmarks=["paris:eiffel-tower", "paris:louvre"],
    )
    context = build_guide_context(request, catalog, Path("runtime/generated/cover.png"))

    html = render_guide_html(context)

    assert html.index("cover-page") < html.index("trip-summary-page")
    assert html.index("trip-summary-page") < html.index("journey-phase-page")
    assert 'data-summary-count="2"' in html
    assert "Resumo da viagem" in html
    assert ">2</strong>" in html
    assert "paradas confirmadas" in html
    assert "summary-illustration-image" in html
    assert "summary-infographic-layout" in html
    assert "summary-map-card" in html
    assert "summary-details-panel" in html
    assert "summary-terminal-start" in html
    assert "summary-terminal-finish" in html
    assert "Torre Eiffel + Museu do Louvre" in html


def test_render_guide_html_trip_summary_lists_all_confirmed_landmarks():
    catalog = load_catalog(Path("data/destinations/europe_2026.json"))
    paris_landmarks = [
        f"paris:{landmark.id}" for landmark in catalog.find_destination("paris").landmarks
    ]
    request = GuideRequest(
        title="Pequenos Exploradores pela Europa",
        children_names=["Alice"],
        parents_names=["Ana"],
        year=2026,
        selected_landmarks=paris_landmarks,
    )
    context = build_guide_context(
        request,
        catalog,
        Path("runtime/generated/cover.png"),
        summary_image=Path("runtime/generated/summary.png"),
    )

    html = render_guide_html(context)
    # A carta de boas-vindas abre o guia; o resumo do roteiro vem em seguida.
    assert html.index('<section class="page letter-page') < html.index(
        '<section class="page trip-summary-page'
    )
    summary = html.split('<section class="page trip-summary-page', maxsplit=1)[1].split(
        '<section class="page city-page', maxsplit=1
    )[0]

    assert 'data-summary-count="10"' in summary
    assert "summary-density-compact" in summary
    assert summary.count("summary-stop-card") == 10
    # Com ilustracao gerada, a rota pontilhada e os marcadores ficam de fora.
    assert summary.count('class="summary-map-marker summary-route-marker"') == 0
    assert "summary-route-svg" not in summary
    assert '<img src="assets/landmarks' not in summary
    assert "summary-legend-photo" not in summary
    assert "runtime/generated/summary.png" in summary
    readable_summary = unescape(summary)
    for landmark in catalog.find_destination("paris").landmarks:
        assert landmark.name in readable_summary


def test_render_guide_html_trip_summary_uses_dense_layout_for_many_landmarks():
    catalog = load_catalog(Path("data/destinations/europe_2026.json"))
    selected_landmarks = [
        *[f"paris:{landmark.id}" for landmark in catalog.find_destination("paris").landmarks],
        *[f"london:{landmark.id}" for landmark in catalog.find_destination("london").landmarks],
    ]
    request = GuideRequest(
        title="Pequenos Exploradores pela Europa",
        children_names=["Alice"],
        parents_names=["Ana"],
        year=2026,
        selected_landmarks=selected_landmarks,
    )
    context = build_guide_context(
        request,
        catalog,
        Path("runtime/generated/cover.png"),
        summary_image=Path("runtime/generated/summary.png"),
    )

    html = render_guide_html(context)
    summary = html.split('<section class="page trip-summary-page', maxsplit=1)[1].split(
        '<section class="page city-page', maxsplit=1
    )[0]

    assert 'data-summary-count="17"' in summary
    assert "summary-density-dense" in summary
    assert summary.count("summary-stop-card") == 17
    assert summary.count('class="summary-map-marker summary-route-marker"') == 0
    assert "Torre Eiffel" in summary
    assert "Big Ben" in summary


def test_write_pdf_creates_non_empty_file(tmp_path):
    catalog = load_catalog(Path("data/destinations/europe_2026.json"))
    request = GuideRequest(
        title="Pequenos Exploradores pela Europa",
        children_names=["Alice"],
        parents_names=["Ana"],
        year=2026,
        selected_landmarks=["paris:eiffel-tower"],
    )
    context = build_guide_context(request, catalog, Path("runtime/generated/cover.png"))
    output = tmp_path / "guide.pdf"

    result = write_pdf(context, output)

    assert result == output
    assert output.exists()
    assert output.stat().st_size > 1000


def test_render_guide_html_skips_static_coloring_page_when_activity_plan_has_coloring():
    catalog = load_catalog(Path("data/destinations/europe_2026.json"))
    request = GuideRequest(
        title="Pequenos Exploradores pela Europa",
        children_names=["Alice"],
        children_ages=[4],
        parents_names=["Ana"],
        year=2026,
        selected_landmarks=["paris:eiffel-tower", "paris:louvre"],
    )
    context = build_guide_context(request, catalog, Path("runtime/generated/cover.png"))

    assert any(activity.type == "coloring" for activity in context.activity_plan)
    html = render_guide_html(context)

    # A atividade de colorir ja entrega a pagina de pintura; a pagina estatica
    # duplicada nao deve ser impressa de novo para o mesmo destino.
    assert 'class="page activity-page activity-coloring"' in html
    assert 'class="page coloring-page"' not in html
