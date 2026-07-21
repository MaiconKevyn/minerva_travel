import json

import pytest

from minerva_travel.investigator_activity import (
    InvestigatorMissionError,
    investigator_mission_prompt,
    investigator_mission_response_schema,
    normalize_investigator_children,
    parse_investigator_missions,
)


def _response(missions):
    return {"output_text": json.dumps({"missions": missions}, ensure_ascii=False)}


def test_investigator_prompt_preserves_order_context_age_and_visit_safety():
    children = normalize_investigator_children(["Lia", "Ravi"], [4, 11])
    prompt = investigator_mission_prompt(
        landmark_context={
            "name": "Museu do Louvre",
            "city": "Paris",
            "country": "França",
            "description": "Museu de arte instalado em um antigo palácio.",
            "curiosity": "A entrada mais conhecida tem formato de pirâmide.",
            "curiosity_kind": "trusted",
        },
        children=children,
        revision_instruction="Inclua uma missão de observar formas.",
    )

    system = prompt[0]["content"]
    user = json.loads(prompt[1]["content"])
    assert "0-5 anos" in system
    assert "9-17" in system
    assert "não afirme que uma obra" in system
    assert "Nunca peça para tocar obras" in system
    assert user["tourist_point"]["name"] == "Museu do Louvre"
    assert user["children_in_required_order"] == [
        {"name": "Lia", "age": 4},
        {"name": "Ravi", "age": 11},
    ]
    assert user["parent_revision_request"] == "Inclua uma missão de observar formas."


def test_investigator_schema_and_parser_accept_one_distinct_mission_per_child():
    children = normalize_investigator_children(["Lia", "Ravi"], [4, 11])
    schema = investigator_mission_response_schema()
    assert schema["properties"]["missions"]["maxItems"] == 10

    missions = parse_investigator_missions(
        _response(
            [
                {
                    "child_index": 1,
                    "child_name": "Lia",
                    "clue": "Procure uma forma de triângulo.",
                    "mission": "Aponte para ela e desenhe a forma no ar.",
                },
                {
                    "child_index": 2,
                    "child_name": "Ravi",
                    "clue": "Observe uma obra com muitas cores.",
                    "mission": "Compare duas cores e anote a diferença principal.",
                },
            ]
        ),
        children,
    )
    assert [mission.child_name for mission in missions] == ["Lia", "Ravi"]


@pytest.mark.parametrize(
    "missions",
    [
        [
            {
                "child_index": 1,
                "child_name": "Outra criança",
                "clue": "Procure uma forma.",
                "mission": "Aponte para a forma.",
            }
        ],
        [
            {
                "child_index": 1,
                "child_name": "Lia",
                "clue": "Procure uma forma.",
                "mission": "Aponte para a forma.",
            },
            {
                "child_index": 2,
                "child_name": "Ravi",
                "clue": "Procure uma forma.",
                "mission": "Aponte para a forma.",
            },
        ],
    ],
)
def test_investigator_parser_rejects_renamed_or_duplicate_assignments(missions):
    children = normalize_investigator_children(["Lia", "Ravi"], [4, 11])
    with pytest.raises(InvestigatorMissionError):
        parse_investigator_missions(_response(missions), children)


def test_investigator_parser_rejects_unsafe_visit_instruction():
    children = normalize_investigator_children(["Lia"], [4])
    with pytest.raises(InvestigatorMissionError, match="não é segura"):
        parse_investigator_missions(
            _response(
                [
                    {
                        "child_index": 1,
                        "child_name": "Lia",
                        "clue": "Procure uma escultura.",
                        "mission": "Toque na obra quando o adulto não estiver olhando.",
                    }
                ]
            ),
            children,
        )


def test_investigator_children_support_the_full_ten_child_guide_contract():
    children = normalize_investigator_children(
        [f"Criança {index}" for index in range(1, 11)],
        list(range(4, 14)),
    )
    assert len(children) == 10
    assert children[-1].name == "Criança 10"
    assert children[-1].age == 13
