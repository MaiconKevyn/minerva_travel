from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from minerva_travel.wikimedia_assets import ImageCredit


class GuideRequest(BaseModel):
    title: str = Field(min_length=1)
    children_names: list[str] = Field(min_length=1, max_length=10)
    parents_names: list[str] = Field(min_length=1, max_length=2)
    year: int = Field(ge=2024, le=2100)
    selected_landmarks: list[str] = Field(min_length=1, max_length=30)

    @property
    def children_display(self) -> str:
        return join_pt(self.children_names)

    @property
    def parents_display(self) -> str:
        if len(self.parents_names) == 1:
            return f"mamae/papai {self.parents_names[0]}"
        return f"mamae {self.parents_names[0]} e papai {self.parents_names[1]}"


class Landmark(BaseModel):
    id: str
    name: str
    description: list[str] = Field(min_length=1)
    image: Path | str
    lineart_image: Path
    sort_order: int
    representative_query: str | None = None
    required_terms: list[str] = Field(default_factory=list)
    rejected_terms: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    duration_minutes: int = Field(default=60, ge=15, le=240)
    family_tip: str | None = None


class LanguageTip(BaseModel):
    phrase: str = Field(min_length=1)
    pronunciation: str = Field(min_length=1)
    meaning: str = Field(min_length=1)
    use_case: str = Field(min_length=1)


class PhaseActivities(BaseModel):
    before: str = (
        "No caminho, procure esta cidade no mapa e imagine o que voces vao encontrar."
    )
    during: str = "Durante a visita, escolha um detalhe para observar com calma."
    after: str = "Depois da visita, desenhe ou escreva uma lembranca importante."


class Destination(BaseModel):
    id: str
    country: str
    city: str
    display_title: str
    intro: list[str] = Field(min_length=1)
    favorites_prompt: str
    coloring_title: str
    coloring_subtitle: str
    language_name: str | None = None
    language_tips: list[LanguageTip] = Field(default_factory=list)
    phase_activities: PhaseActivities = Field(default_factory=PhaseActivities)
    landmarks: list[Landmark] = Field(min_length=1)

    def sorted_landmarks(self) -> list[Landmark]:
        return sorted(self.landmarks, key=lambda landmark: landmark.sort_order)


class Catalog(BaseModel):
    id: str
    title: str
    destinations: list[Destination] = Field(min_length=1)

    def find_destination(self, destination_id: str) -> Destination:
        for destination in self.destinations:
            if destination.id == destination_id:
                return destination
        raise KeyError(f"Unknown destination: {destination_id}")

    def find_landmark(self, destination_id: str, landmark_id: str) -> Landmark:
        destination = self.find_destination(destination_id)
        for landmark in destination.landmarks:
            if landmark.id == landmark_id:
                return landmark
        raise KeyError(f"Unknown landmark: {destination_id}:{landmark_id}")


class GuideDestination(BaseModel):
    destination: Destination
    landmarks: list[Landmark]


class GuideContext(BaseModel):
    request: GuideRequest
    cover_image: Path
    destinations: list[GuideDestination]
    image_credits: list[ImageCredit] = Field(default_factory=list)


class ItineraryRecommendationRequest(BaseModel):
    destination_ids: list[str] = Field(min_length=1, max_length=10)
    days: int = Field(ge=1, le=14)
    interests: list[str] = Field(default_factory=list, max_length=12)
    pace: Literal["light", "balanced", "full"] = "balanced"
    children_ages: list[int] = Field(default_factory=list, max_length=10)
    must_see_landmarks: list[str] = Field(default_factory=list, max_length=30)


class DynamicItineraryRequest(BaseModel):
    destination: str = Field(min_length=2, max_length=500)
    days: int = Field(ge=1, le=14)
    interests: list[str] = Field(default_factory=list, max_length=12)
    pace: Literal["light", "balanced", "full"] = "balanced"
    children_ages: list[int] = Field(default_factory=list, max_length=10)
    must_see: list[str] = Field(default_factory=list, max_length=30)


class ItineraryStop(BaseModel):
    selection_id: str
    destination_id: str
    landmark_id: str
    name: str
    city: str
    country: str
    description: list[str]
    image: Path
    categories: list[str] = Field(default_factory=list)
    duration_minutes: int
    family_tip: str | None = None
    match_score: int
    match_reasons: list[str] = Field(default_factory=list)
    editable: bool = True


class ItineraryDay(BaseModel):
    day: int
    title: str
    theme: str
    destination_ids: list[str]
    stops: list[ItineraryStop]
    family_prompt: str


class ItineraryRecommendation(BaseModel):
    summary: str
    recommendation_source: str = "curated_catalog"
    selected_landmarks: list[str]
    days: list[ItineraryDay]
    alternatives: list[ItineraryStop] = Field(default_factory=list)


def join_pt(values: list[str]) -> str:
    if len(values) == 1:
        return values[0]
    return f"{', '.join(values[:-1])} e {values[-1]}"
