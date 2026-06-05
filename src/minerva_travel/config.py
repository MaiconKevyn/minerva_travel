import os
from pathlib import Path

from dotenv import load_dotenv


def load_project_env() -> None:
    load_dotenv(Path(".env"))


def image_provider() -> str:
    load_project_env()
    return os.getenv("IMAGE_PROVIDER", "placeholder")


def image_generation_concurrency() -> int:
    load_project_env()
    raw_value = os.getenv("IMAGE_GENERATION_CONCURRENCY", "2")
    try:
        value = int(raw_value)
    except ValueError:
        return 2
    return max(1, value)


def cors_allowed_origins() -> list[str]:
    load_project_env()
    raw_origins = os.getenv("CORS_ALLOW_ORIGINS", "*")
    origins = [origin.strip() for origin in raw_origins.split(",") if origin.strip()]
    return origins or ["*"]


def google_maps_api_key() -> str | None:
    load_project_env()
    return os.getenv("GOOGLE_MAPS_API_KEY")
