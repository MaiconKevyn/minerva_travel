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
