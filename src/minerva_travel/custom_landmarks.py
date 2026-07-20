import json
from collections import defaultdict
from pathlib import Path

from pydantic import BaseModel, Field, ValidationError

from minerva_travel.contract_limits import MAX_GUIDE_LANDMARKS
from minerva_travel.destination_facts import lookup_destination_facts
from minerva_travel.models import Destination, Landmark
from minerva_travel.wikimedia_client import normalize_search_text

DEFAULT_CITY = "Roteiro personalizado"
DEFAULT_COUNTRY = "Personalizado"
PLACEHOLDER_IMAGE = Path("assets/landmarks/paris/eiffel-tower.png")
PLACEHOLDER_LINEART = Path("assets/lineart/paris/eiffel-tower.png")
MAX_CUSTOM_LANDMARKS = MAX_GUIDE_LANDMARKS
MAX_CUSTOM_LANDMARKS_BYTES = 20_000
STOPWORDS = {
    "a",
    "as",
    "da",
    "das",
    "de",
    "del",
    "do",
    "dos",
    "e",
    "el",
    "la",
    "las",
    "le",
    "les",
    "of",
    "o",
    "os",
    "the",
}


class CustomLandmarkInput(BaseModel):
    selection_id: str | None = Field(default=None, min_length=1, max_length=200)
    name: str = Field(min_length=2, max_length=120)
    city: str = Field(default=DEFAULT_CITY, max_length=80)
    country: str = Field(default=DEFAULT_COUNTRY, max_length=80)
    description: list[str] = Field(default_factory=list, max_length=3)
    image: str | None = Field(default=None, max_length=1000)
    image_attributions: list[dict[str, str]] = Field(default_factory=list, max_length=8)
    place_id: str | None = Field(default=None, max_length=256)


def parse_custom_landmarks(raw: str | None) -> list[CustomLandmarkInput]:
    if not raw or not raw.strip():
        return []
    if len(raw.encode("utf-8")) > MAX_CUSTOM_LANDMARKS_BYTES:
        raise ValueError("custom_landmarks excede o limite de 20 KB.")
    stripped = raw.strip()
    if stripped.startswith("["):
        landmarks = _parse_json_landmarks(stripped)
    else:
        landmarks = _parse_text_landmarks(stripped)
    if len(landmarks) > MAX_CUSTOM_LANDMARKS:
        raise ValueError("Informe no maximo 30 pontos turisticos personalizados.")
    return landmarks


def build_custom_destinations(
    custom_landmarks: list[CustomLandmarkInput],
) -> tuple[list[Destination], list[str]]:
    grouped: dict[tuple[str, str], list[CustomLandmarkInput]] = defaultdict(list)
    for landmark in custom_landmarks:
        country = landmark.country.strip() or DEFAULT_COUNTRY
        city = landmark.city.strip() or DEFAULT_CITY
        grouped[(country, city)].append(landmark)

    destinations: list[Destination] = []
    selected_landmarks: list[str] = []
    used_destination_ids: set[str] = set()
    for destination_index, ((country, city), landmarks) in enumerate(grouped.items(), start=1):
        destination_id = unique_slug(f"custom-{city}", used_destination_ids)
        used_landmark_ids: set[str] = set()
        destination_landmarks: list[Landmark] = []
        for landmark_index, custom in enumerate(landmarks, start=1):
            landmark_id = unique_slug(custom.name, used_landmark_ids)
            selection_id = f"{destination_id}:{landmark_id}"
            selected_landmarks.append(selection_id)
            image = custom.image.strip() if custom.image else ""
            destination_landmarks.append(
                Landmark(
                    id=landmark_id,
                    selection_id=(custom.selection_id or "").strip() or None,
                    name=custom.name.strip(),
                    description=custom.description or default_description(custom.name),
                    image=image or PLACEHOLDER_IMAGE,
                    lineart_image=PLACEHOLDER_LINEART,
                    sort_order=landmark_index,
                    place_id=(custom.place_id or "").strip() or None,
                    representative_query=representative_query(custom),
                    required_terms=required_terms(custom.name),
                    rejected_terms=["map", "logo"],
                )
            )
        # "Personalizado" e apenas chave interna de agrupamento; nunca deve
        # aparecer no PDF. Sem pais real, o rotulo fica so com a cidade.
        visible_country = "" if country == DEFAULT_COUNTRY else country
        display_title = (
            f"{visible_country.upper()} - {city.upper()}" if visible_country else city.upper()
        )
        facts = lookup_destination_facts(city, visible_country)
        intro = (
            facts.intro
            if facts
            else [
                f"{city} faz parte do roteiro especial desta viagem.",
                "Os lugares abaixo foram escolhidos pela familia para explorar com calma.",
            ]
        )
        destinations.append(
            Destination(
                id=destination_id,
                country=visible_country,
                city=city,
                display_title=display_title,
                intro=intro,
                curiosities=facts.curiosities if facts else [],
                favorites_prompt=f"Meus lugares favoritos em {city} foram...",
                coloring_title="DESENHOS PARA COLORIR",
                coloring_subtitle="Para colorir e desenhar",
                landmarks=destination_landmarks,
            )
        )
        destination_index += 1
    return destinations, selected_landmarks


def merge_custom_destinations(
    base_destinations: list[Destination],
    custom_destinations: list[Destination],
) -> list[Destination]:
    if not custom_destinations:
        return base_destinations
    return [*base_destinations, *custom_destinations]


def representative_query(landmark: CustomLandmarkInput) -> str:
    parts = [landmark.name, landmark.city, landmark.country, "tourist attraction exterior"]
    return " ".join(part.strip() for part in parts if part and part.strip())


def required_terms(name: str) -> list[str]:
    terms = [
        term
        for term in normalize_search_text(name).split()
        if len(term) > 2 and term not in STOPWORDS
    ]
    return terms[:2] or [normalize_search_text(name)]


def default_description(name: str) -> list[str]:
    return [
        f"{name} e um ponto turistico escolhido para esta viagem.",
        "Observe os detalhes, tire fotos e marque quando visitar.",
    ]


def unique_slug(value: str, used: set[str]) -> str:
    base = slugify(value) or "item"
    slug = base
    index = 2
    while slug in used:
        slug = f"{base}-{index}"
        index += 1
    used.add(slug)
    return slug


def slugify(value: str) -> str:
    return "-".join(normalize_search_text(value).split())


def _parse_json_landmarks(raw: str) -> list[CustomLandmarkInput]:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as error:
        message = "custom_landmarks precisa ser JSON valido ou uma lista em texto."
        raise ValueError(message) from error
    if not isinstance(payload, list):
        raise ValueError("custom_landmarks em JSON precisa ser uma lista.")
    try:
        return [CustomLandmarkInput.model_validate(item) for item in payload]
    except ValidationError as error:
        raise ValueError("custom_landmarks contem itens invalidos.") from error


def _parse_text_landmarks(raw: str) -> list[CustomLandmarkInput]:
    landmarks: list[CustomLandmarkInput] = []
    for line in raw.splitlines():
        cleaned = line.strip()
        if not cleaned:
            continue
        parts = [part.strip() for part in cleaned.replace(";", ",").split(",")]
        name = parts[0]
        city = parts[1] if len(parts) > 1 and parts[1] else DEFAULT_CITY
        country = parts[2] if len(parts) > 2 and parts[2] else DEFAULT_COUNTRY
        landmarks.append(CustomLandmarkInput(name=name, city=city, country=country))
    return landmarks
