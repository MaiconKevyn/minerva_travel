"""As páginas de escrever precisam citar o lugar certo, não pautas genéricas."""

import pytest

from minerva_travel.app import WRITING_ACTIVITY_TYPES, _builder_page_plan
from minerva_travel.catalog import load_catalog
from minerva_travel.crossword import build_crossword
from minerva_travel.maze import maze_size_for
from minerva_travel.puzzles import build_anagrams, build_cryptogram


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


@pytest.mark.parametrize("activity_type", ["anagram", "cryptogram"])
def test_letter_puzzles_are_seeded_by_the_landmark_and_stay_solvable(activity_type):
    pages = _writing_pages(activity_type, ["paris:eiffel-tower"])
    spec = pages[0].metadata["activity_spec"]

    assert spec["seed"] == "paris:eiffel-tower"
    if activity_type == "anagram":
        entries = build_anagrams(spec["words"], seed=spec["seed"])
        assert all(sorted(item.scrambled) == sorted(item.answer) for item in entries)
    else:
        puzzle = build_cryptogram(spec["phrase"], seed=spec["seed"])
        # A frase precisa ser verdadeira e citar o lugar da página.
        assert "EIFFEL" in puzzle.phrase
        assert puzzle.revealed


def test_cryptogram_phrase_falls_back_when_the_landmark_name_is_too_long():
    from minerva_travel.app import _cryptogram_phrase
    from minerva_travel.models import LandmarkActivityContext

    landmark = LandmarkActivityContext(
        destination_id="d1",
        selection_id="s1",
        name="Basilica do Sagrado Coracao de Jesus de Montmartre em Paris",
        city="Paris",
        country="Franca",
        description="Uma basilica no alto de Montmartre.",
        curiosity="Fica no ponto mais alto da cidade.",
        curiosity_kind="trusted",
        itinerary_order=1,
        landmark_page_id="landmark-1",
        age_complexity="older_child",
    )

    phrase = _cryptogram_phrase(landmark)

    assert len(phrase) <= 62
    assert "Paris" in phrase


def test_maze_grid_grows_with_the_children_ages():
    catalog = load_catalog()

    def _grid(ages):
        pages, _ = _builder_page_plan(
            {
                "title": "Família Lima",
                "year": 2026,
                "children_ages": ages,
                "activity_selections": [
                    {
                        "landmark_selection_id": "paris:eiffel-tower",
                        "activity_type": "maze",
                        "order": 1,
                    }
                ],
            },
            catalog.destinations,
            ["paris:eiffel-tower"],
        )
        activity = next(page for page in pages if page.kind == "landmark_activity")
        return maze_size_for(activity.metadata["age_complexity"])

    # Uma grade de adulto frustra quem tem 4 anos; a de 4 anos entedia quem tem 11.
    assert _grid([4])[0] * _grid([4])[1] < _grid([11])[0] * _grid([11])[1]


def test_crossword_clues_come_from_this_trip_and_interlock():
    page = _writing_pages("crossword", ["paris:eiffel-tower"])[0]
    clues = page.metadata["activity_spec"]["clues"]

    joined = " ".join(item["clue"] for item in clues)
    assert "Paris" in " ".join(item["answer"] for item in clues)
    assert page.metadata["name"] in joined

    crossword = build_crossword([(item["answer"], item["clue"]) for item in clues])
    assert len(crossword.entries) >= 4
    assert crossword.across and crossword.down


@pytest.mark.parametrize(
    ("activity_type", "spec_key"),
    [("postcard", "sender"), ("passport_stamp", "child_name")],
)
def test_keepsake_pages_carry_the_child_name(activity_type, spec_key):
    catalog = load_catalog()
    pages, _ = _builder_page_plan(
        {
            "title": "Família Lima",
            "year": 2026,
            "children_ages": [9],
            "children_names": ["Aurora"],
            "activity_selections": [
                {
                    "landmark_selection_id": "paris:eiffel-tower",
                    "activity_type": activity_type,
                    "order": 1,
                }
            ],
        },
        catalog.destinations,
        ["paris:eiffel-tower"],
    )
    activity = next(page for page in pages if page.kind == "landmark_activity")

    # Cartão sem remetente e passaporte sem dono são papel em branco.
    assert activity.metadata["activity_spec"][spec_key] == "Aurora"


def test_a_guide_is_refused_when_no_selected_landmark_resolves():
    """Ids sem definição derrubavam a viagem inteira em silêncio.

    O guia saía com capa, sumário e páginas finais — nenhuma parada — e a
    capa, sem lugares confirmados no prompt, inventava um cenário: um roteiro
    no Japão voltava com a Torre Eiffel.
    """
    from minerva_travel.app import ActivitySelectionInputError

    catalog = load_catalog()
    with pytest.raises(ActivitySelectionInputError) as raised:
        _builder_page_plan(
            {
                "title": "Família Silva",
                "year": 2026,
                "children_ages": [7],
                "activity_selections": [],
            },
            catalog.destinations,
            ["custom-toquio:templo-sensoji", "custom-honshu:monte-fuji"],
        )

    assert raised.value.code == "landmark_selection_unresolved"
