import pytest
from pydantic import ValidationError

from minerva_travel.models import GuideRequest


def test_guide_request_builds_display_names():
    request = GuideRequest(
        title="Pequenos Exploradores pela Europa",
        children_names=["Alice", "Antonio"],
        parents_names=["Ana", "Otavio"],
        year=2026,
        selected_landmarks=["paris:eiffel-tower", "london:big-ben"],
    )

    assert request.children_display == "Alice e Antonio"
    assert request.parents_display == "mamae Ana e papai Otavio"


def test_guide_request_requires_at_least_one_landmark():
    with pytest.raises(ValidationError):
        GuideRequest(
            title="Pequenos Exploradores pela Europa",
            children_names=["Alice"],
            parents_names=["Ana"],
            year=2026,
            selected_landmarks=[],
        )
