from html import unescape
from pathlib import Path

from minerva_travel.catalog import load_catalog
from minerva_travel.guide_builder import build_guide_context
from minerva_travel.models import GuideRequest
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
    context = build_guide_context(request, catalog, Path("runtime/generated/cover.png"))

    html = render_guide_html(context)

    assert "Alice e Antonio" in html
    assert "Torre Eiffel" in html
    assert "JA VISITEI" in html
    assert "@page" in html


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

    assert "Creditos das imagens" in html
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
    assert "Caca ao detalhe" in html
    assert "O que eu aprendi" in html
    assert ".phase-badge" in html
    assert ".language-tip-card" in html
    assert ".observation-card" in html
    assert ".memory-boxes" in html


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


def test_render_guide_html_trip_summary_lists_all_confirmed_landmarks():
    catalog = load_catalog(Path("data/destinations/europe_2026.json"))
    paris_landmarks = [
        f"paris:{landmark.id}"
        for landmark in catalog.find_destination("paris").landmarks
    ]
    request = GuideRequest(
        title="Pequenos Exploradores pela Europa",
        children_names=["Alice"],
        parents_names=["Ana"],
        year=2026,
        selected_landmarks=paris_landmarks,
    )
    context = build_guide_context(request, catalog, Path("runtime/generated/cover.png"))

    html = render_guide_html(context)
    summary = html.split('<section class="page trip-summary-page', maxsplit=1)[1].split(
        '<section class="page letter-page', maxsplit=1
    )[0]

    assert 'data-summary-count="10"' in summary
    assert "summary-density-compact" in summary
    assert summary.count("summary-legend-item") == 10
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
    context = build_guide_context(request, catalog, Path("runtime/generated/cover.png"))

    html = render_guide_html(context)
    summary = html.split('<section class="page trip-summary-page', maxsplit=1)[1].split(
        '<section class="page letter-page', maxsplit=1
    )[0]

    assert 'data-summary-count="17"' in summary
    assert "summary-density-dense" in summary
    assert summary.count("summary-legend-item") == 17
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
