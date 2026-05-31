import json
import os
from typing import Any

import httpx
from pydantic import BaseModel, Field, ValidationError

from minerva_travel.config import load_project_env

OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"


class ParsedLandmark(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    city: str = Field(min_length=2, max_length=80)
    country: str = Field(min_length=2, max_length=80)
    confidence: float = Field(ge=0, le=1)


class ParsedLandmarksResponse(BaseModel):
    landmarks: list[ParsedLandmark] = Field(default_factory=list, max_length=30)


def parse_landmarks_from_message(message: str) -> list[ParsedLandmark]:
    cleaned = message.strip()
    if len(cleaned) < 3:
        raise ValueError("Informe os pontos turisticos em uma frase ou lista.")

    load_project_env()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY nao configurada no backend.")

    model = os.getenv("OPENAI_LANDMARK_MODEL", "gpt-4o-2024-08-06")
    response = _create_structured_response(api_key=api_key, model=model, message=cleaned)
    return _parse_response_payload(response).landmarks


def _create_structured_response(api_key: str, model: str, message: str) -> dict[str, Any]:
    payload = {
        "model": model,
        "input": [
            {
                "role": "system",
                "content": (
                    "Voce extrai pontos turisticos de mensagens em portugues, ingles "
                    "ou espanhol. Retorne apenas locais turisticos visitaveis. "
                    "Agrupe cada item com cidade e pais quando puder inferir pelo texto. "
                    "Quando a cidade ou pais nao estiver claro, use "
                    "'Roteiro personalizado' e 'Personalizado'. Preserve nomes conhecidos "
                    "em uma forma clara para o usuario confirmar."
                ),
            },
            {"role": "user", "content": message},
        ],
        "text": {
            "format": {
                "type": "json_schema",
                "name": "travel_landmarks",
                "strict": True,
                "schema": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "landmarks": {
                            "type": "array",
                            "maxItems": 30,
                            "items": {
                                "type": "object",
                                "additionalProperties": False,
                                "properties": {
                                    "name": {"type": "string"},
                                    "city": {"type": "string"},
                                    "country": {"type": "string"},
                                    "confidence": {
                                        "type": "number",
                                        "minimum": 0,
                                        "maximum": 1,
                                    },
                                },
                                "required": [
                                    "name",
                                    "city",
                                    "country",
                                    "confidence",
                                ],
                            },
                        }
                    },
                    "required": ["landmarks"],
                },
            }
        },
        "max_output_tokens": 1500,
    }
    with httpx.Client(timeout=45) as client:
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


def _parse_response_payload(response: dict[str, Any]) -> ParsedLandmarksResponse:
    output_text = _extract_output_text(response)
    try:
        payload = json.loads(output_text)
    except json.JSONDecodeError as error:
        raise ValueError("A OpenAI retornou uma resposta que nao era JSON valido.") from error
    try:
        return ParsedLandmarksResponse.model_validate(payload)
    except ValidationError as error:
        raise ValueError("A OpenAI retornou pontos turisticos em formato invalido.") from error


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
