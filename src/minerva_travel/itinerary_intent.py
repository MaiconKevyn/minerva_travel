import json
import os
import unicodedata
from collections.abc import Callable, Iterable
from typing import Any, Literal

import httpx
from pydantic import BaseModel, Field, ValidationError

from minerva_travel.config import load_project_env

OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"

INTEREST_ALIASES = {
    "animal": "animals",
    "animais": "animals",
    "aquario": "animals",
    "arte": "art",
    "artes": "art",
    "comida": "food",
    "gastronomia": "food",
    "almoco": "food",
    "almoço": "food",
    "jantar": "food",
    "restaurante": "food",
    "historia": "history",
    "história": "history",
    "ciencia": "science",
    "ciência": "science",
    "descobertas": "science",
    "educativo": "education",
    "educacao": "education",
    "educação": "education",
    "lojas": "local_stores",
    "lojas locais": "local_stores",
    "mercados": "local_stores",
    "compras": "shopping",
    "museu": "museums",
    "museus": "museums",
    "outdoor": "outdoor",
    "ar livre": "outdoor",
    "atividade ao ar livre": "outdoor",
    "atividades ao ar livre": "outdoor",
    "parque": "parks",
    "parques": "parks",
    "praca": "squares",
    "praça": "squares",
    "pracas": "squares",
    "praças": "squares",
    "brincar": "play",
    "rio": "river",
    "teatro": "theaters",
    "teatros": "theaters",
    "vistas": "views",
}

KNOWN_INTERESTS = {
    "animals",
    "art",
    "education",
    "family",
    "food",
    "history",
    "local_stores",
    "museums",
    "outdoor",
    "parks",
    "play",
    "river",
    "science",
    "shopping",
    "squares",
    "theaters",
    "views",
}

DISCOVERY_KIND_TO_CATEGORY = {
    "educational": "education",
    "restaurant": "food",
    "activity": "play",
    "nature": "parks",
    "museum": "museums",
    "shopping": "shopping",
    "food": "food",
    "general": "family",
}


class DiscoveryRequest(BaseModel):
    kind: Literal[
        "educational",
        "restaurant",
        "activity",
        "nature",
        "museum",
        "shopping",
        "food",
        "general",
    ] = "general"
    query: str = Field(default="", max_length=180)
    topic: str = Field(default="", max_length=80)
    near: str = Field(default="", max_length=120)
    meal: str = Field(default="", max_length=40)
    audience: Literal["children", "family", "general"] = "children"


class ItineraryIntent(BaseModel):
    destination: str = Field(default="", max_length=180)
    must_see_places: list[str] = Field(default_factory=list, max_length=20)
    discovery_requests: list[DiscoveryRequest] = Field(default_factory=list, max_length=12)
    inferred_interests: list[str] = Field(default_factory=list, max_length=12)


def parse_itinerary_intent(
    message: str,
    *,
    api_key: str | None = None,
    model: str | None = None,
    responder: Callable[..., dict[str, Any]] | None = None,
) -> ItineraryIntent:
    cleaned = message.strip()
    if len(cleaned) < 2:
        return ItineraryIntent(destination=cleaned)

    load_project_env()
    effective_api_key = api_key or os.getenv("OPENAI_API_KEY")
    if responder or effective_api_key:
        try:
            effective_model = model or os.getenv("OPENAI_LANDMARK_MODEL") or "gpt-4o-2024-08-06"
            response = (responder or _create_structured_response)(
                api_key=effective_api_key,
                model=effective_model,
                message=cleaned,
            )
            intent = _parse_response_payload(response)
            if intent.destination:
                return intent
        except (ValueError, httpx.HTTPError, ValidationError):
            pass

    return _fallback_intent(cleaned)


def search_profiles_from_intent(
    intent: ItineraryIntent,
    *,
    explicit_interests: Iterable[str],
) -> list[tuple[str, str]]:
    destination = intent.destination.strip()
    profiles: list[tuple[str, str]] = []

    for place in intent.must_see_places:
        profiles.append(("must_see", _query_with_destination(place, destination)))

    for request in intent.discovery_requests:
        base_query = request.query.strip() or request.topic.strip() or request.kind
        if request.audience == "children" and "crianca" not in _normalize_text(base_query):
            base_query = f"{base_query} para criancas"
        if request.near.strip():
            base_query = f"{base_query} perto de {request.near.strip()}"
        category = _request_category(request)
        profiles.append((category, _query_with_destination(base_query, destination)))

    normalized_interests = [
        _normalize_interest(interest)
        for interest in [*explicit_interests, *intent.inferred_interests]
    ]
    for interest in normalized_interests:
        if interest and interest != "unknown":
            profiles.append((interest, _interest_query(interest, destination)))

    return _dedupe_profiles(profiles)


def _create_structured_response(api_key: str | None, model: str, message: str) -> dict[str, Any]:
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY nao configurada no backend.")
    payload = {
        "model": model,
        "input": [
            {
                "role": "system",
                "content": (
                    "Voce entende pedidos de pais planejando viagem com filhos. "
                    "Extraia o destino principal, pontos turisticos ja citados como "
                    "obrigatorios, pedidos de descoberta para criancas e interesses "
                    "inferidos. Nao invente locais. Preserve pedidos contextuais como "
                    "'almoco perto da Torre Eiffel'. Use portugues do Brasil. "
                    "Quando algo nao existir, use string vazia ou lista vazia."
                ),
            },
            {"role": "user", "content": message},
        ],
        "text": {
            "format": {
                "type": "json_schema",
                "name": "family_trip_intent",
                "strict": True,
                "schema": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "destination": {"type": "string"},
                        "must_see_places": {
                            "type": "array",
                            "maxItems": 20,
                            "items": {"type": "string"},
                        },
                        "discovery_requests": {
                            "type": "array",
                            "maxItems": 12,
                            "items": {
                                "type": "object",
                                "additionalProperties": False,
                                "properties": {
                                    "kind": {
                                        "type": "string",
                                        "enum": [
                                            "educational",
                                            "restaurant",
                                            "activity",
                                            "nature",
                                            "museum",
                                            "shopping",
                                            "food",
                                            "general",
                                        ],
                                    },
                                    "query": {"type": "string"},
                                    "topic": {"type": "string"},
                                    "near": {"type": "string"},
                                    "meal": {"type": "string"},
                                    "audience": {
                                        "type": "string",
                                        "enum": ["children", "family", "general"],
                                    },
                                },
                                "required": [
                                    "kind",
                                    "query",
                                    "topic",
                                    "near",
                                    "meal",
                                    "audience",
                                ],
                            },
                        },
                        "inferred_interests": {
                            "type": "array",
                            "maxItems": 12,
                            "items": {"type": "string"},
                        },
                    },
                    "required": [
                        "destination",
                        "must_see_places",
                        "discovery_requests",
                        "inferred_interests",
                    ],
                },
            }
        },
        "max_output_tokens": 2000,
    }
    with httpx.Client(timeout=30) as client:
        response = client.post(
            OPENAI_RESPONSES_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        response.raise_for_status()
        return response.json()


def _parse_response_payload(response: dict[str, Any]) -> ItineraryIntent:
    output_text = _extract_output_text(response)
    try:
        payload = json.loads(output_text)
    except json.JSONDecodeError as error:
        raise ValueError("A OpenAI retornou uma intencao que nao era JSON valido.") from error
    return ItineraryIntent.model_validate(payload)


def _extract_output_text(response: dict[str, Any]) -> str:
    direct_output = response.get("output_text")
    if isinstance(direct_output, str) and direct_output.strip():
        return direct_output

    chunks: list[str] = []
    for output_item in response.get("output", []):
        for content_item in output_item.get("content", []):
            text = content_item.get("text")
            if isinstance(text, str):
                chunks.append(text)
    output_text = "".join(chunks).strip()
    if not output_text:
        raise ValueError("A OpenAI nao retornou conteudo para interpretar.")
    return output_text


def _fallback_intent(message: str) -> ItineraryIntent:
    inferred_interests = [
        value for key, value in INTEREST_ALIASES.items() if key in _normalize_text(message)
    ]
    return ItineraryIntent(
        destination=message,
        inferred_interests=list(dict.fromkeys(inferred_interests)),
    )


def _request_category(request: DiscoveryRequest) -> str:
    topic_category = _normalize_interest(request.topic)
    if topic_category != "unknown":
        return topic_category
    return DISCOVERY_KIND_TO_CATEGORY.get(request.kind, "family")


def _normalize_interest(value: str) -> str:
    key = _normalize_text(value)
    candidate = INTEREST_ALIASES.get(key, key)
    return candidate if candidate in KNOWN_INTERESTS else "unknown"


def _interest_query(interest: str, destination: str) -> str:
    queries = {
        "animals": "zoologicos aquarios e experiencias com animais para criancas",
        "art": "lugares para criancas aprenderem sobre arte",
        "education": "atividades educativas para criancas",
        "family": "lugares bons para ir com criancas",
        "food": "restaurantes familiares para comer com criancas",
        "history": "lugares historicos interessantes para criancas",
        "local_stores": "lojas locais mercados livrarias brinquedos para familias",
        "museums": "museus interativos e educativos para criancas",
        "outdoor": "atividades ao ar livre trilhas jardins para familias",
        "parks": "parques pracas e atividades ao ar livre para criancas",
        "play": "atividades divertidas para criancas",
        "science": "museus de ciencia e descobertas para criancas",
        "shopping": "lojas e mercados legais para familias",
        "squares": "pracas largos espacos publicos para familias",
        "theaters": "teatros infantis espetaculos e centros culturais para familias",
        "river": "passeios de barco e rio para familias",
        "views": "mirantes e vistas bonitas para familias",
    }
    return _query_with_destination(queries.get(interest, f"{interest} para criancas"), destination)


def _query_with_destination(query: str, destination: str) -> str:
    cleaned_query = " ".join(query.split())
    cleaned_destination = " ".join(destination.split())
    if not cleaned_destination:
        return cleaned_query
    if _normalize_text(cleaned_destination) in _normalize_text(cleaned_query):
        return cleaned_query
    return f"{cleaned_query} em {cleaned_destination}"


def _dedupe_profiles(profiles: list[tuple[str, str]]) -> list[tuple[str, str]]:
    deduped: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for category, query in profiles:
        key = (category, _normalize_text(query))
        if key in seen:
            continue
        seen.add(key)
        deduped.append((category, query))
    return deduped[:8]


def _normalize_text(value: str) -> str:
    ascii_value = unicodedata.normalize("NFKD", value)
    ascii_value = "".join(
        character for character in ascii_value if not unicodedata.combining(character)
    )
    return " ".join(ascii_value.strip().casefold().split())
