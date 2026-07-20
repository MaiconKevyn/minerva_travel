import os
from pathlib import Path

from dotenv import load_dotenv


def load_project_env() -> None:
    load_dotenv(Path(".env"))


def app_environment() -> str:
    load_project_env()
    return os.getenv("APP_ENV", "development").strip().lower()


def frontend_base_url() -> str:
    load_project_env()
    default = (
        "https://minerva-travel.hostingerapp.com"
        if app_environment() == "production"
        else "http://127.0.0.1:3000"
    )
    value = os.getenv("FRONTEND_BASE_URL", default).rstrip("/")
    if app_environment() == "production" and not value.startswith("https://"):
        raise RuntimeError("FRONTEND_BASE_URL must use HTTPS in production.")
    return value


def auth_required() -> bool:
    load_project_env()
    raw_value = os.getenv("AUTH_REQUIRED", "true")
    required = raw_value.strip().lower() not in {"0", "false", "no", "off"}
    if app_environment() == "production" and not required:
        raise RuntimeError("AUTH_REQUIRED cannot be disabled in production.")
    return required


def supabase_publishable_key() -> str | None:
    load_project_env()
    return os.getenv("SUPABASE_PUBLISHABLE_KEY")


def supabase_jwt_audience() -> str:
    load_project_env()
    return os.getenv("SUPABASE_JWT_AUDIENCE", "authenticated")


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


def landmark_stylized_art_enabled() -> bool:
    """Arte aquarela dos pontos turisticos a partir da foto real (com cache global)."""
    load_project_env()
    raw_value = os.getenv("LANDMARK_STYLIZED_ART", "true")
    return raw_value.strip().lower() not in {"0", "false", "no", "off"}


def coloring_lineart_generation_enabled() -> bool:
    load_project_env()
    raw_value = os.getenv("COLORING_LINEART_GENERATION", "true")
    return raw_value.strip().lower() not in {"0", "false", "no", "off"}


def cors_allowed_origins() -> list[str]:
    load_project_env()
    raw_origins = os.getenv("CORS_ALLOW_ORIGINS")
    if not raw_origins:
        raw_origins = (
            "https://minerva-travel.hostingerapp.com"
            if app_environment() == "production"
            else (
                "http://localhost:3000,http://127.0.0.1:3000,"
                "https://minerva-travel.hostingerapp.com"
            )
        )
    origins = [origin.strip() for origin in raw_origins.split(",") if origin.strip()]
    if app_environment() == "production":
        if "*" in origins:
            raise RuntimeError("CORS wildcard is not allowed in production.")
        if any(not origin.startswith("https://") for origin in origins):
            raise RuntimeError("Production CORS origins must use HTTPS.")
    return origins


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


def guide_retention_days() -> int:
    load_project_env()
    raw_value = os.getenv("GUIDE_RETENTION_DAYS", "30")
    try:
        value = int(raw_value)
    except ValueError:
        return 30
    return min(max(value, 1), 365)


def guide_draft_retention_days() -> int:
    load_project_env()
    raw_value = os.getenv("GUIDE_DRAFT_RETENTION_DAYS", "14")
    try:
        value = int(raw_value)
    except ValueError:
        return 14
    return min(max(value, 1), 90)


def photo_processing_consent_required() -> bool:
    load_project_env()
    raw_value = os.getenv("PHOTO_PROCESSING_CONSENT_REQUIRED", "true")
    required = raw_value.strip().lower() not in {"0", "false", "no", "off"}
    if app_environment() == "production" and not required:
        raise RuntimeError("PHOTO_PROCESSING_CONSENT_REQUIRED cannot be disabled in production.")
    return required


def pilot_restaurant_recommendations_enabled() -> bool:
    """Server-side release control for the pilot-only restaurant content.

    The client may request the content, but cannot activate this feature in a
    production environment where it has not been explicitly approved.
    """

    load_project_env()
    raw_value = os.getenv(
        "PILOT_RESTAURANT_RECOMMENDATIONS_ENABLED",
        "true" if app_environment() != "production" else "false",
    )
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def async_guide_jobs_enabled() -> bool:
    """Require the durable queue path in production without disrupting local demos."""

    load_project_env()
    raw_value = os.getenv(
        "ASYNC_GUIDE_JOBS_ENABLED",
        "true" if app_environment() == "production" else "false",
    )
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def guide_job_max_attempts() -> int:
    load_project_env()
    raw_value = os.getenv("GUIDE_JOB_MAX_ATTEMPTS", "3")
    try:
        attempts = int(raw_value)
    except ValueError:
        return 3
    return min(max(attempts, 1), 10)
