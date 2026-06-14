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


def landmark_art_generation_enabled() -> bool:
    load_project_env()
    raw_value = os.getenv("LANDMARK_ART_GENERATION", "false")
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def coloring_lineart_generation_enabled() -> bool:
    load_project_env()
    raw_value = os.getenv("COLORING_LINEART_GENERATION", "true")
    return raw_value.strip().lower() not in {"0", "false", "no", "off"}


def cors_allowed_origins() -> list[str]:
    load_project_env()
    raw_origins = os.getenv("CORS_ALLOW_ORIGINS", "*")
    origins = [origin.strip() for origin in raw_origins.split(",") if origin.strip()]
    return origins or ["*"]


def google_maps_api_key() -> str | None:
    load_project_env()
    return os.getenv("GOOGLE_MAPS_API_KEY")


def supabase_url() -> str | None:
    load_project_env()
    return os.getenv("SUPABASE_URL")


def supabase_service_role_key() -> str | None:
    load_project_env()
    return os.getenv("SUPABASE_SERVICE_ROLE_KEY")


def supabase_bucket_landmark_assets() -> str:
    load_project_env()
    return os.getenv("SUPABASE_BUCKET_LANDMARK_ASSETS", "landmark-assets")


def supabase_storage_enabled() -> bool:
    load_project_env()
    raw_value = os.getenv("SUPABASE_STORAGE_ENABLED", "true")
    return raw_value.strip().lower() not in {"0", "false", "no", "off"}
