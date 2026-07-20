from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from minerva_travel.contract_limits import (
    MAX_GUIDE_CHILDREN,
    MAX_GUIDE_DESTINATIONS,
    MAX_GUIDE_LANDMARKS,
    MAX_GUIDE_PARENTS,
    MAX_GUIDE_YEAR,
    MAX_VISIBLE_FAMILY_MEMBERS,
    MIN_GUIDE_YEAR,
)
from minerva_travel.wikimedia_assets import ImageCredit

ActivityType = Literal[
    "coloring",
    "word_search",
    "spot_the_difference",
    "detail_hunt",
    "drawing",
    "short_prompt",
    "checklist",
    "language_learning",
]
ActivityComplexity = Literal["preschool", "early_reader", "older_child", "family"]
OptionalLandmarkActivityType = Literal[
    "coloring",
    "detail_hunt",
    "word_search",
    "drawing",
]

OPTIONAL_LANDMARK_ACTIVITY_TYPES: tuple[OptionalLandmarkActivityType, ...] = (
    "coloring",
    "detail_hunt",
    "word_search",
    "drawing",
)
MAX_OPTIONAL_ACTIVITIES_PER_LANDMARK = 2
MAX_OPTIONAL_ACTIVITY_PAGES_PER_GUIDE = 8
MAX_ACTIVITY_SELECTIONS_JSON_BYTES = 20_000


class StrictRequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LandmarkActivitySelection(StrictRequestModel):
    """One explicit optional page selected for one server-resolved landmark."""

    landmark_selection_id: Annotated[
        str,
        Field(strict=True, min_length=1, max_length=200),
    ]
    activity_type: OptionalLandmarkActivityType
    order: Annotated[
        int,
        Field(strict=True, ge=1, le=MAX_OPTIONAL_ACTIVITIES_PER_LANDMARK),
    ]


class LandmarkActivityContext(BaseModel):
    """Immutable, private landmark context used by progressive activity pages."""

    destination_id: str = Field(min_length=1, max_length=120)
    selection_id: str = Field(min_length=1, max_length=200)
    name: str = Field(min_length=1, max_length=200)
    city: str = Field(default="", max_length=160)
    country: str = Field(default="", max_length=160)
    description: str = Field(min_length=1, max_length=500)
    curiosity: str = Field(min_length=1, max_length=300)
    curiosity_kind: Literal["trusted", "observation"]
    place_id: str | None = Field(default=None, max_length=256)
    source_image: str | None = Field(default=None, max_length=1000)
    source_image_available: bool = False
    itinerary_order: int = Field(ge=1, le=MAX_GUIDE_LANDMARKS)
    landmark_page_id: str = Field(min_length=1, max_length=120)
    age_complexity: ActivityComplexity


class DestinationLearningContext(BaseModel):
    """Immutable, private copy contract for one progressive destination introduction."""

    destination_id: str = Field(min_length=1, max_length=120)
    title: str = Field(min_length=1, max_length=160)
    city: str = Field(default="", max_length=160)
    country: str = Field(default="", max_length=160)
    learning_points: list[str] = Field(min_length=1, max_length=2)
    curiosity: str = Field(min_length=1, max_length=300)
    curiosity_kind: Literal["trusted", "observation"]
    curiosity_label: str = Field(min_length=1, max_length=80)
    landmark_names: list[str] = Field(min_length=1, max_length=MAX_GUIDE_LANDMARKS)
    itinerary_order: int = Field(ge=1, le=MAX_GUIDE_DESTINATIONS)
    destination_page_id: str = Field(min_length=1, max_length=120)


class GuideDestinationPlan(StrictRequestModel):
    id: str = Field(min_length=1, max_length=120)
    place: str = Field(min_length=1, max_length=160)
    timing: str = Field(min_length=1, max_length=160)
    days: int = Field(ge=1, le=30)
    order: int = Field(ge=1, le=10)


class GuideItineraryStopPlan(StrictRequestModel):
    selection_id: str = Field(min_length=1, max_length=200)
    name: str = Field(min_length=1, max_length=200)
    destination_id: str | None = Field(default=None, max_length=120)


class GuideItineraryDayPlan(StrictRequestModel):
    day: int = Field(ge=1, le=30)
    title: str = Field(min_length=1, max_length=200)
    theme: str = Field(default="", max_length=300)
    stops: list[GuideItineraryStopPlan] = Field(default_factory=list, max_length=30)


class GuideItineraryPlan(StrictRequestModel):
    mode: Literal["known", "freeform", "suggested"] = "known"
    pace: Literal["light", "balanced", "full"] = "balanced"
    interests: list[str] = Field(default_factory=list, max_length=12)
    destinations: list[GuideDestinationPlan] = Field(
        min_length=1, max_length=MAX_GUIDE_DESTINATIONS
    )
    days: list[GuideItineraryDayPlan] = Field(default_factory=list, max_length=MAX_GUIDE_LANDMARKS)
    unplanned_stops: list[GuideItineraryStopPlan] = Field(
        default_factory=list, max_length=MAX_GUIDE_LANDMARKS
    )

    @property
    def pace_label(self) -> str:
        return {
            "light": "leve",
            "balanced": "equilibrado",
            "full": "intenso",
        }[self.pace]

    @property
    def mode_label(self) -> str:
        return {
            "known": "roteiro definido pela família",
            "freeform": "roteiro organizado a partir da ideia da família",
            "suggested": "roteiro sugerido e confirmado pela família",
        }[self.mode]

    @property
    def total_days(self) -> int:
        return sum(destination.days for destination in self.destinations)


class GuideRequest(StrictRequestModel):
    title: str = Field(min_length=1, max_length=160)
    children_names: list[Annotated[str, Field(min_length=1, max_length=100)]] = Field(
        min_length=1,
        max_length=MAX_GUIDE_CHILDREN,
    )
    children_ages: list[Annotated[int, Field(ge=0, le=17)]] = Field(
        default_factory=list,
        max_length=MAX_GUIDE_CHILDREN,
    )
    parents_names: list[Annotated[str, Field(min_length=1, max_length=100)]] = Field(
        min_length=1,
        max_length=MAX_GUIDE_PARENTS,
    )
    year: int = Field(ge=MIN_GUIDE_YEAR, le=MAX_GUIDE_YEAR)
    selected_landmarks: list[Annotated[str, Field(min_length=1, max_length=200)]] = Field(
        min_length=1,
        max_length=MAX_GUIDE_LANDMARKS,
    )
    expected_visible_family_member_count: int | None = Field(
        default=None, ge=1, le=MAX_VISIBLE_FAMILY_MEMBERS
    )
    restaurant_recommendations_extra: bool = False
    itinerary: GuideItineraryPlan | None = None

    @property
    def children_display(self) -> str:
        return join_pt(self.children_names)

    @property
    def parents_display(self) -> str:
        return join_pt(self.parents_names)


class Landmark(BaseModel):
    id: str
    selection_id: str | None = Field(default=None, min_length=1, max_length=200)
    name: str
    description: list[str] = Field(min_length=1)
    image: Path | str
    lineart_image: Path | str
    sort_order: int
    place_id: str | None = None
    representative_query: str | None = None
    required_terms: list[str] = Field(default_factory=list)
    rejected_terms: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    duration_minutes: int = Field(default=60, ge=15, le=240)
    family_tip: str | None = None
    curiosity: str | None = Field(default=None, max_length=300)


class LanguageTip(BaseModel):
    phrase: str = Field(min_length=1)
    pronunciation: str = Field(min_length=1)
    meaning: str = Field(min_length=1)
    use_case: str = Field(min_length=1)


class PhaseActivities(BaseModel):
    before: str = "No caminho, procure esta cidade no mapa e imagine o que voces vao encontrar."
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
    curiosities: list[str] = Field(default_factory=list)
    language_name: str | None = None
    language_tips: list[LanguageTip] = Field(default_factory=list)
    phase_activities: PhaseActivities = Field(default_factory=PhaseActivities)
    landmarks: list[Landmark] = Field(min_length=1)

    @property
    def location_label(self) -> str:
        parts = [self.city.strip(), self.country.strip()]
        return ", ".join(part for part in parts if part)

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


class GuideSummaryLandmark(BaseModel):
    number: int
    selection_id: str
    destination: Destination
    landmark: Landmark


class RestaurantRecommendation(BaseModel):
    destination_id: str
    name: str = Field(min_length=1)
    nearby_context: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    cuisine: str | None = None
    suitability_notes: list[str] = Field(default_factory=list)
    google_maps_uri: str | None = None
    formatted_address: str | None = None


class GuideActivity(BaseModel):
    destination_id: str
    type: ActivityType
    title: str
    prompt: str
    complexity: ActivityComplexity
    phase: Literal["before", "during", "after"] = "during"
    landmark_name: str | None = None
    lineart_image: Path | str | None = None
    words: list[str] = Field(default_factory=list)
    word_search_grid: list[str] = Field(default_factory=list)
    checklist_items: list[str] = Field(default_factory=list)
    extension_prompt: str | None = None
    language_name: str | None = None
    language_phrase: str | None = None
    language_pronunciation: str | None = None
    language_meaning: str | None = None


class GuideContext(BaseModel):
    request: GuideRequest
    cover_image: Path | str
    summary_image: Path | str | None = None
    destinations: list[GuideDestination]
    activity_plan: list[GuideActivity] = Field(default_factory=list)
    image_credits: list[ImageCredit] = Field(default_factory=list)
    restaurant_recommendations: list[RestaurantRecommendation] = Field(default_factory=list)

    @property
    def summary_landmarks(self) -> list[GuideSummaryLandmark]:
        items: list[GuideSummaryLandmark] = []
        for item in self.destinations:
            for landmark in item.landmarks:
                items.append(
                    GuideSummaryLandmark(
                        number=len(items) + 1,
                        selection_id=f"{item.destination.id}:{landmark.id}",
                        destination=item.destination,
                        landmark=landmark,
                    )
                )
        return items

    @property
    def summary_density(self) -> Literal["airy", "compact", "dense"]:
        count = len(self.summary_landmarks)
        if count <= 6:
            return "airy"
        if count <= 12:
            return "compact"
        return "dense"

    @property
    def summary_headline(self) -> str:
        items = self.summary_landmarks
        if not items:
            return self.request.title
        if len(items) == 1:
            return items[0].landmark.name
        return f"{items[0].landmark.name} + {items[1].landmark.name}"

    @property
    def summary_primary_city(self) -> str:
        items = self.summary_landmarks
        if not items:
            return "sua viagem"
        return items[0].destination.location_label or "sua viagem"

    @property
    def summary_map_columns(self) -> int:
        if self.summary_density == "airy":
            return 3
        if self.summary_density == "compact":
            return 4
        return 6

    @property
    def summary_map_rows(self) -> list[list[GuideSummaryLandmark | None]]:
        columns = self.summary_map_columns
        items = self.summary_landmarks
        rows: list[list[GuideSummaryLandmark | None]] = []
        for index in range(0, len(items), columns):
            row: list[GuideSummaryLandmark | None] = list(items[index : index + columns])
            missing = columns - len(row)
            leading_empty = missing // 2
            trailing_empty = missing - leading_empty
            rows.append([None] * leading_empty + row + [None] * trailing_empty)
        return rows


class ItineraryRecommendationRequest(StrictRequestModel):
    destination_ids: list[str] = Field(min_length=1, max_length=MAX_GUIDE_DESTINATIONS)
    days: int = Field(ge=1, le=14)
    interests: list[str] = Field(default_factory=list, max_length=12)
    pace: Literal["light", "balanced", "full"] = "balanced"
    children_ages: list[int] = Field(default_factory=list, max_length=MAX_GUIDE_CHILDREN)
    must_see_landmarks: list[str] = Field(default_factory=list, max_length=MAX_GUIDE_LANDMARKS)


class DynamicItineraryRequest(StrictRequestModel):
    destination: str = Field(min_length=2, max_length=500)
    days: int = Field(ge=1, le=14)
    interests: list[str] = Field(default_factory=list, max_length=12)
    pace: Literal["light", "balanced", "full"] = "balanced"
    children_ages: list[int] = Field(default_factory=list, max_length=MAX_GUIDE_CHILDREN)
    must_see: list[str] = Field(default_factory=list, max_length=MAX_GUIDE_LANDMARKS)


class StructuredDestinationInput(StrictRequestModel):
    id: str | None = None
    place: str = Field(min_length=1, max_length=160)
    timing: str = Field(default="", max_length=160)
    days: int = Field(default=0, ge=0, le=30)


class RouteSuggestionRequest(StrictRequestModel):
    trip_idea: str = Field(default="", max_length=1000)
    days: int = Field(default=3, ge=1, le=30)
    interests: list[str] = Field(default_factory=list, max_length=12)
    pace: Literal["light", "balanced", "full"] = "balanced"
    children_ages: list[int] = Field(default_factory=list, max_length=10)
    structured_destinations: list[StructuredDestinationInput] = Field(
        default_factory=list,
        max_length=MAX_GUIDE_DESTINATIONS,
    )


class RouteSuggestionOption(BaseModel):
    id: str
    title: str
    summary: str
    structured_destinations: list[StructuredDestinationInput]


class RouteSuggestionResponse(BaseModel):
    options: list[RouteSuggestionOption]


class ItineraryStop(BaseModel):
    selection_id: str
    destination_id: str
    landmark_id: str
    name: str
    city: str
    country: str
    description: list[str]
    image: Path
    category: str | None = None
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
