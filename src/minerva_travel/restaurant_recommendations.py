from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

import httpx

from minerva_travel.models import GuideDestination, RestaurantRecommendation
from minerva_travel.place_discovery import GOOGLE_TEXT_SEARCH_URL

RESTAURANT_TEXT_SEARCH_FIELD_MASK = (
    "places.id,"
    "places.displayName,"
    "places.formattedAddress,"
    "places.types,"
    "places.primaryType,"
    "places.rating,"
    "places.userRatingCount,"
    "places.googleMapsUri"
)

RESTAURANT_PLACE_TYPES = {"restaurant", "cafe", "bakery", "meal_takeaway"}
EXCLUDED_RESTAURANT_TYPES = {"bar", "night_club", "casino", "liquor_store"}
MAX_RESTAURANTS_PER_DESTINATION = 2


@dataclass(frozen=True)
class RestaurantAnchor:
    destination_id: str
    query: str
    nearby_context: str


def discover_restaurants_for_guide(
    guide_destinations: list[GuideDestination],
    *,
    api_key: str | None = None,
    client: httpx.Client | None = None,
) -> list[RestaurantRecommendation]:
    if not api_key or not guide_destinations:
        return []

    owns_client = client is None
    http_client = client or httpx.Client(timeout=20)
    try:
        recommendations: list[RestaurantRecommendation] = []
        seen_place_ids: set[str] = set()
        per_destination_counts: dict[str, int] = {}
        for anchor in restaurant_anchors(guide_destinations):
            if (
                per_destination_counts.get(anchor.destination_id, 0)
                >= MAX_RESTAURANTS_PER_DESTINATION
            ):
                continue
            for place in _search_restaurants(http_client, api_key, anchor.query):
                place_id = str(place.get("id") or "")
                if not place_id or place_id in seen_place_ids:
                    continue
                if not _is_family_restaurant_candidate(place):
                    continue
                recommendation = _restaurant_recommendation(place, anchor)
                if not recommendation:
                    continue
                recommendations.append(recommendation)
                seen_place_ids.add(place_id)
                per_destination_counts[anchor.destination_id] = (
                    per_destination_counts.get(anchor.destination_id, 0) + 1
                )
                break
        return recommendations
    finally:
        if owns_client:
            http_client.close()


def restaurant_anchors(guide_destinations: Iterable[GuideDestination]) -> list[RestaurantAnchor]:
    anchors: list[RestaurantAnchor] = []
    for item in guide_destinations:
        destination = item.destination
        if item.landmarks:
            for landmark in item.landmarks:
                query = " ".join(
                    part
                    for part in [
                        "restaurante familiar perto de",
                        landmark.name,
                        destination.city,
                        destination.country,
                    ]
                    if part
                )
                anchors.append(
                    RestaurantAnchor(
                        destination_id=destination.id,
                        query=query,
                        nearby_context=f"perto de {landmark.name}",
                    )
                )
            continue
        query = f"restaurante familiar em {destination.city} {destination.country}".strip()
        anchors.append(
            RestaurantAnchor(
                destination_id=destination.id,
                query=query,
                nearby_context=f"em {destination.city}",
            )
        )
    return anchors


def _search_restaurants(
    client: httpx.Client,
    api_key: str,
    query: str,
) -> list[dict[str, Any]]:
    response = client.post(
        GOOGLE_TEXT_SEARCH_URL,
        headers={
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": RESTAURANT_TEXT_SEARCH_FIELD_MASK,
        },
        json={
            "textQuery": query,
            "languageCode": "pt-BR",
            "maxResultCount": 4,
        },
    )
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError:
        return []
    return response.json().get("places", [])


def _is_family_restaurant_candidate(place: dict[str, Any]) -> bool:
    place_types = set(place.get("types", []))
    if place_types & EXCLUDED_RESTAURANT_TYPES:
        return False
    return bool(place_types & RESTAURANT_PLACE_TYPES)


def _restaurant_recommendation(
    place: dict[str, Any],
    anchor: RestaurantAnchor,
) -> RestaurantRecommendation | None:
    name = str(place.get("displayName", {}).get("text") or "").strip()
    if not name:
        return None
    cuisine = _cuisine_note(place)
    notes = _suitability_notes(place)
    reason = f"Opção {anchor.nearby_context} para uma pausa em família."
    rating = place.get("rating")
    if isinstance(rating, int | float) and rating >= 4.4:
        reason = f"Opção bem avaliada {anchor.nearby_context} para uma pausa em família."

    return RestaurantRecommendation(
        destination_id=anchor.destination_id,
        name=name,
        nearby_context=anchor.nearby_context,
        reason=reason,
        cuisine=cuisine,
        suitability_notes=notes,
        google_maps_uri=place.get("googleMapsUri"),
        formatted_address=place.get("formattedAddress"),
    )


def _cuisine_note(place: dict[str, Any]) -> str | None:
    primary_type = str(place.get("primaryType") or "")
    if primary_type in {"cafe", "bakery"}:
        return "cafes e lanches"
    if primary_type == "meal_takeaway":
        return "refeicao rapida"
    return None


def _suitability_notes(place: dict[str, Any]) -> list[str]:
    notes: list[str] = []
    rating_count = place.get("userRatingCount")
    if isinstance(rating_count, int) and rating_count >= 500:
        notes.append("Popular entre visitantes; vale checar horarios de pico.")
    return notes
