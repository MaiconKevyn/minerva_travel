from pathlib import Path

import pytest
from pydantic import ValidationError

from minerva_travel.models import Destination, GuideRequest, Landmark


def test_guide_request_builds_display_names():
    request = GuideRequest(
        title="Pequenos Exploradores pela Europa",
        children_names=["Alice", "Antonio"],
        children_ages=[5, 9],
        parents_names=["Ana", "Otavio"],
        year=2026,
        selected_landmarks=["paris:eiffel-tower", "london:big-ben"],
    )

    assert request.children_display == "Alice e Antonio"
    assert request.children_ages == [5, 9]
    assert request.parents_display == "mamae Ana e papai Otavio"


def test_guide_request_allows_name_only_child_compatibility():
    request = GuideRequest(
        title="Pequenos Exploradores pela Europa",
        children_names=["Alice"],
        parents_names=["Ana"],
        year=2026,
        selected_landmarks=["paris:eiffel-tower"],
    )

    assert request.children_ages == []


def test_guide_request_requires_at_least_one_landmark():
    with pytest.raises(ValidationError):
        GuideRequest(
            title="Pequenos Exploradores pela Europa",
            children_names=["Alice"],
            parents_names=["Ana"],
            year=2026,
            selected_landmarks=[],
        )


def test_guide_request_accepts_up_to_ten_children_names():
    request = GuideRequest(
        title="Pequenos Exploradores pela Europa",
        children_names=[f"Crianca {index}" for index in range(1, 11)],
        parents_names=["Ana"],
        year=2026,
        selected_landmarks=["paris:eiffel-tower"],
    )

    assert len(request.children_names) == 10


def _sample_landmark() -> Landmark:
    return Landmark(
        id="sample-landmark",
        name="Sample Landmark",
        description=["Um lugar especial para observar com calma."],
        image=Path("assets/landmarks/sample.png"),
        lineart_image=Path("assets/lineart/sample.png"),
        sort_order=1,
        categories=["parks", "slow-walk"],
        duration_minutes=45,
        family_tip="Bom para uma pausa tranquila entre passeios.",
    )


def test_destination_supports_language_tips_and_phase_activities():
    destination = Destination(
        id="paris",
        country="Franca",
        city="Paris",
        display_title="FRANCA - PARIS",
        intro=["Paris e uma cidade cheia de historias."],
        favorites_prompt="Meus lugares favoritos em Paris foram...",
        coloring_title="DESENHOS PARA COLORIR",
        coloring_subtitle="Para colorir e desenhar",
        language_name="frances",
        language_tips=[
            {
                "phrase": "Bonjour",
                "pronunciation": "bon-ZHUR",
                "meaning": "Oi / bom dia",
                "use_case": "Use ao entrar em uma loja ou restaurante.",
            }
        ],
        phase_activities={
            "before": "No aviao, encontre Paris no mapa.",
            "during": "Procure uma forma triangular neste lugar.",
            "after": "Desenhe a lembranca mais bonita de Paris.",
        },
        landmarks=[_sample_landmark()],
    )

    assert destination.language_name == "frances"
    assert destination.language_tips[0].phrase == "Bonjour"
    assert destination.language_tips[0].use_case == "Use ao entrar em uma loja ou restaurante."
    assert destination.phase_activities.before == "No aviao, encontre Paris no mapa."
    assert destination.phase_activities.during == "Procure uma forma triangular neste lugar."
    assert destination.phase_activities.after == "Desenhe a lembranca mais bonita de Paris."


def test_landmark_supports_recommendation_metadata():
    landmark = _sample_landmark()

    assert landmark.categories == ["parks", "slow-walk"]
    assert landmark.duration_minutes == 45
    assert landmark.family_tip == "Bom para uma pausa tranquila entre passeios."


def test_destination_phase_content_has_safe_defaults_for_custom_destinations():
    destination = Destination(
        id="custom-rome",
        country="Italy",
        city="Rome",
        display_title="ITALY - ROME",
        intro=["Os lugares abaixo foram escolhidos pela familia."],
        favorites_prompt="Meus lugares favoritos em Rome foram...",
        coloring_title="DESENHOS PARA COLORIR",
        coloring_subtitle="Para colorir e desenhar",
        landmarks=[_sample_landmark()],
    )

    assert destination.language_name is None
    assert destination.language_tips == []
    assert destination.phase_activities.before == (
        "No caminho, procure esta cidade no mapa e imagine o que voces vao encontrar."
    )
    assert destination.phase_activities.during == (
        "Durante a visita, escolha um detalhe para observar com calma."
    )
    assert destination.phase_activities.after == (
        "Depois da visita, desenhe ou escreva uma lembranca importante."
    )
