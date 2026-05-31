from pathlib import Path

from pydantic import BaseModel, Field

from minerva_travel.wikimedia_assets import ImageCredit


class GuideRequest(BaseModel):
    title: str = Field(min_length=1)
    children_names: list[str] = Field(min_length=1, max_length=3)
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
    image: Path
    lineart_image: Path
    sort_order: int
    representative_query: str | None = None
    required_terms: list[str] = Field(default_factory=list)
    rejected_terms: list[str] = Field(default_factory=list)


class Destination(BaseModel):
    id: str
    country: str
    city: str
    display_title: str
    intro: list[str] = Field(min_length=1)
    favorites_prompt: str
    coloring_title: str
    coloring_subtitle: str
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


def join_pt(values: list[str]) -> str:
    if len(values) == 1:
        return values[0]
    return f"{', '.join(values[:-1])} e {values[-1]}"
