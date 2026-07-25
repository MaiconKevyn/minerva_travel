"""Sugestões de lugares para o preenchimento assistido do roteiro.

Antes, destino e ponto turístico eram texto livre: um erro de digitação
("Torre Eifel") era aceito e ia impresso no livro, mesmo quando o Google
já sabia qual era o lugar certo. Aqui a família escolhe de uma lista e o
nome oficial, a cidade, o país e o ``place_id`` entram estruturados.

A chave do Google fica sempre no servidor — o navegador nunca a vê.
"""

from dataclasses import dataclass
from typing import Any

import httpx

GOOGLE_TEXT_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"

SUGGESTION_FIELD_MASK = (
    "places.id,"
    "places.displayName,"
    "places.formattedAddress,"
    "places.addressComponents,"
    "places.location,"
    "places.types"
)

MAX_SUGGESTIONS = 6
MIN_QUERY_LENGTH = 3

# "cities" restringe a lugares administrativos; sem isso, buscar "Paris"
# devolveria também restaurantes e hotéis com Paris no nome.
CITY_TYPES = ("locality", "administrative_area_level_1", "country")


@dataclass(frozen=True)
class PlaceSuggestion:
    place_id: str
    name: str
    city: str
    country: str
    formatted_address: str
    latitude: float | None
    longitude: float | None

    @property
    def location_label(self) -> str:
        parts = [part for part in (self.city, self.country) if part]
        return ", ".join(parts)

    def as_payload(self) -> dict[str, Any]:
        return {
            "place_id": self.place_id,
            "name": self.name,
            "city": self.city,
            "country": self.country,
            "location_label": self.location_label,
            "formatted_address": self.formatted_address,
            "latitude": self.latitude,
            "longitude": self.longitude,
        }


def suggest_places(
    query: str,
    *,
    api_key: str | None,
    kind: str = "landmark",
    near: str = "",
    client: httpx.Client | None = None,
) -> list[PlaceSuggestion]:
    """Busca lugares para o autocomplete. Sem chave ou consulta curta, devolve vazio."""
    cleaned = " ".join(str(query or "").split())
    if not api_key or len(cleaned) < MIN_QUERY_LENGTH:
        return []

    text_query = f"{cleaned} {near}".strip() if near else cleaned
    body: dict[str, Any] = {
        "textQuery": text_query,
        "languageCode": "pt-BR",
        "maxResultCount": MAX_SUGGESTIONS,
    }
    if kind == "city":
        body["includedType"] = "locality"

    owns_client = client is None
    http_client = client or httpx.Client(timeout=10)
    try:
        response = http_client.post(
            GOOGLE_TEXT_SEARCH_URL,
            headers={"X-Goog-Api-Key": api_key, "X-Goog-FieldMask": SUGGESTION_FIELD_MASK},
            json=body,
        )
        response.raise_for_status()
        places = response.json().get("places", [])
    except httpx.HTTPError:
        # Autocomplete é conveniência: falha silenciosa mantém o campo
        # utilizável como texto livre em vez de bloquear o preenchimento.
        return []
    finally:
        if owns_client:
            http_client.close()

    suggestions = [_to_suggestion(place) for place in places if isinstance(place, dict)]
    return [item for item in suggestions if item is not None][:MAX_SUGGESTIONS]


def _to_suggestion(place: dict[str, Any]) -> PlaceSuggestion | None:
    place_id = str(place.get("id") or "")
    name = str((place.get("displayName") or {}).get("text") or "").strip()
    if not place_id or not name:
        return None
    city, country = _city_and_country(place)
    location = place.get("location") if isinstance(place.get("location"), dict) else {}
    return PlaceSuggestion(
        place_id=place_id,
        name=name,
        city=city,
        country=country,
        formatted_address=str(place.get("formattedAddress") or ""),
        latitude=_coordinate(location.get("latitude")),
        longitude=_coordinate(location.get("longitude")),
    )


def _city_and_country(place: dict[str, Any]) -> tuple[str, str]:
    components = place.get("addressComponents")
    city = ""
    country = ""
    if isinstance(components, list):
        for component in components:
            if not isinstance(component, dict):
                continue
            types = component.get("types") or []
            label = str(component.get("longText") or "").strip()
            if not label:
                continue
            if not city and "locality" in types:
                city = label
            elif not city and "administrative_area_level_2" in types:
                city = label
            if not country and "country" in types:
                country = label
    if not city:
        # Endereços sem "locality" (ilhas, regiões) ainda trazem a cidade no
        # texto formatado; usar a penúltima parte é melhor que ficar vazio.
        parts = [part.strip() for part in str(place.get("formattedAddress") or "").split(",")]
        parts = [part for part in parts if part]
        if len(parts) >= 2:
            city = parts[-2]
    return city, country


def _coordinate(value: Any) -> float | None:
    return float(value) if isinstance(value, int | float) else None
