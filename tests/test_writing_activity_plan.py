"""As páginas de escrever precisam citar o lugar certo, não pautas genéricas."""

import pytest

from minerva_travel.app import WRITING_ACTIVITY_TYPES, _builder_page_plan
from minerva_travel.catalog import load_catalog


def _writing_pages(activity_type: str, selected: list[str]):
    catalog = load_catalog()
    pages, normalized = _builder_page_plan(
        {
            "title": "Família Lima",
            "year": 2026,
            "children_ages": [9],
            "activity_selections": [
                {
                    "landmark_selection_id": selection_id,
                    "activity_type": activity_type,
                    "order": 1,
                }
                for selection_id in selected
            ],
        },
        catalog.destinations,
        selected,
    )
    assert len(normalized) == len(selected)
    return [page for page in pages if page.kind == "landmark_activity"]


@pytest.mark.parametrize("activity_type", sorted(WRITING_ACTIVITY_TYPES))
def test_every_writing_activity_names_its_landmark_and_prints_its_fields(activity_type):
    pages = _writing_pages(activity_type, ["paris:eiffel-tower"])

    assert len(pages) == 1
    page = pages[0]
    fields = page.metadata["activity_spec"]["fields"]
    assert 1 <= len(fields) <= 5
    # Cada rótulo impresso precisa estar no contrato de texto da página.
    assert all(str(field["label"]) in page.required_copy for field in fields)
    assert all(1 <= int(field["lines"]) <= 6 for field in fields)
    assert page.metadata["name"] in page.required_copy


def test_writing_prompts_change_with_the_destination():
    paris = _writing_pages("here_vs_home", ["paris:eiffel-tower"])[0]
    london = _writing_pages("here_vs_home", ["london:tower-bridge"])[0]

    paris_labels = [field["label"] for field in paris.metadata["activity_spec"]["fields"]]
    london_labels = [field["label"] for field in london.metadata["activity_spec"]["fields"]]

    assert any("Paris" in label for label in paris_labels)
    assert any("Londres" in label or "London" in label for label in london_labels)
    assert paris_labels != london_labels


def test_headline_asks_about_the_landmark_and_diary_about_the_city():
    headline = _writing_pages("newspaper_headline", ["paris:eiffel-tower"])[0]
    diary = _writing_pages("travel_diary", ["paris:eiffel-tower"])[0]

    headline_labels = " ".join(
        str(field["label"]) for field in headline.metadata["activity_spec"]["fields"]
    )
    diary_labels = " ".join(
        str(field["label"]) for field in diary.metadata["activity_spec"]["fields"]
    )

    # A manchete é sobre o monumento; o diário fecha o dia inteiro na cidade.
    assert headline.metadata["name"] in headline_labels
    assert "Paris" in diary_labels
