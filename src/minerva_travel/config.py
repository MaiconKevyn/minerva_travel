import os
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv

# O site em produção. Serve de padrão para o link do e-mail e para o CORS,
# então uma variável de ambiente esquecida no deploy degrada para o endereço
# certo em vez de para um domínio que não existe mais.
PRODUCTION_SITE_URL = "https://guiadememorias.com.br"
# A Hostinger atende o apex e o www; o CORS é comparado por igualdade exata,
# então quem entrar pelo www ficaria sem API nenhuma.
PRODUCTION_SITE_ORIGINS = (PRODUCTION_SITE_URL, "https://www.guiadememorias.com.br")


def load_project_env() -> None:
    load_dotenv(Path(".env"))


def app_environment() -> str:
    load_project_env()
    return os.getenv("APP_ENV", "development").strip().lower()


def frontend_base_url() -> str:
    load_project_env()
    default = PRODUCTION_SITE_URL if app_environment() == "production" else "http://127.0.0.1:3000"
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


def openai_api_base_url() -> str:
    load_project_env()
    return os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")


def openai_api_key() -> str:
    load_project_env()
    return os.getenv("OPENAI_API_KEY", "").strip()


def openai_image_model() -> str:
    load_project_env()
    return os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-2").strip() or "gpt-image-2"


def openai_activity_model() -> str:
    load_project_env()
    return (
        os.getenv("OPENAI_ACTIVITY_MODEL")
        or os.getenv("OPENAI_LANDMARK_MODEL")
        or "gpt-4o-2024-08-06"
    ).strip()


def openai_image_quality() -> str:
    load_project_env()
    quality = os.getenv("OPENAI_IMAGE_QUALITY", "medium").strip().lower()
    return quality if quality in {"low", "medium", "high", "auto"} else "medium"


def openai_image_timeout_seconds() -> float:
    load_project_env()
    try:
        value = float(os.getenv("OPENAI_IMAGE_TIMEOUT_SECONDS", "180"))
    except ValueError:
        return 180.0
    return min(max(value, 30.0), 600.0)


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
        production = ",".join(PRODUCTION_SITE_ORIGINS)
        raw_origins = (
            production
            if app_environment() == "production"
            else f"http://localhost:3000,http://127.0.0.1:3000,{production}"
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


def supabase_bucket_generated_covers() -> str:
    load_project_env()
    return os.getenv("SUPABASE_BUCKET_GENERATED_COVERS", "generated-covers")


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


def in_process_guide_worker_enabled() -> bool:
    """Run the durable queue beside the API when both share one mounted disk.

    Render disks are attached to a single service. Until the queue and builder
    assets move to shared object storage/database infrastructure, keeping the
    worker in the web service is what lets queued jobs survive deploys *and*
    see the same private files.
    """

    load_project_env()
    raw_value = os.getenv(
        "IN_PROCESS_GUIDE_WORKER_ENABLED",
        "true" if app_environment() == "production" else "false",
    )
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def guide_worker_poll_seconds() -> float:
    load_project_env()
    try:
        value = float(os.getenv("GUIDE_WORKER_POLL_SECONDS", "1"))
    except ValueError:
        return 1.0
    return min(max(value, 0.25), 30.0)


def guide_job_max_attempts() -> int:
    load_project_env()
    raw_value = os.getenv("GUIDE_JOB_MAX_ATTEMPTS", "3")
    try:
        attempts = int(raw_value)
    except ValueError:
        return 3
    return min(max(attempts, 1), 10)


def payments_enabled() -> bool:
    """Enable checkout and entitlement enforcement explicitly.

    Leaving this off preserves the existing pilot flow and prevents a deploy
    with incomplete credentials from accidentally presenting a real checkout.
    """

    load_project_env()
    raw_value = os.getenv("PAYMENTS_ENABLED", "false")
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def mercado_pago_access_token() -> str:
    load_project_env()
    return os.getenv("MERCADO_PAGO_ACCESS_TOKEN", "").strip()


def mercado_pago_webhook_secret() -> str:
    load_project_env()
    return os.getenv("MERCADO_PAGO_WEBHOOK_SECRET", "").strip()


def mercado_pago_api_base_url() -> str:
    load_project_env()
    return os.getenv("MERCADO_PAGO_API_BASE_URL", "https://api.mercadopago.com").rstrip("/")


def mercado_pago_environment() -> Literal["test", "production"]:
    load_project_env()
    value = os.getenv("MERCADO_PAGO_ENVIRONMENT", "test").strip().lower()
    if value == "test":
        return "test"
    if value == "production":
        return "production"
    raise RuntimeError("MERCADO_PAGO_ENVIRONMENT must be test or production.")


def mercado_pago_webhook_url() -> str:
    load_project_env()
    value = os.getenv("MERCADO_PAGO_WEBHOOK_URL", "").strip()
    if value and not value.startswith("https://"):
        raise RuntimeError("MERCADO_PAGO_WEBHOOK_URL must use HTTPS.")
    return value


def guide_product_code() -> str:
    load_project_env()
    return os.getenv("GUIDE_PRODUCT_CODE", "guide_generation_v1").strip() or "guide_generation_v1"


def guide_product_title() -> str:
    load_project_env()
    return os.getenv("GUIDE_PRODUCT_TITLE", "Guia de Memórias personalizado").strip()


def guide_product_currency() -> str:
    load_project_env()
    value = os.getenv("GUIDE_PRODUCT_CURRENCY", "BRL").strip().upper()
    if len(value) != 3 or not value.isalpha():
        raise RuntimeError("GUIDE_PRODUCT_CURRENCY must be a three-letter ISO currency code.")
    return value


def guide_product_price_minor() -> int:
    load_project_env()
    raw_value = os.getenv("GUIDE_PRODUCT_PRICE_MINOR", "1999")
    try:
        value = int(raw_value)
    except ValueError as error:
        raise RuntimeError("GUIDE_PRODUCT_PRICE_MINOR must be an integer.") from error
    if not 100 <= value <= 10_000_000:
        raise RuntimeError("GUIDE_PRODUCT_PRICE_MINOR must be between 100 and 10000000.")
    return value


def validate_payment_configuration() -> None:
    """Fail closed when checkout is enabled with an incomplete environment."""

    if not payments_enabled():
        return
    if not mercado_pago_access_token():
        raise RuntimeError("MERCADO_PAGO_ACCESS_TOKEN is required when payments are enabled.")
    guide_product_price_minor()
    guide_product_currency()
    webhook_url = mercado_pago_webhook_url()
    if app_environment() == "production":
        if mercado_pago_environment() != "production":
            raise RuntimeError("MERCADO_PAGO_ENVIRONMENT must be production in APP_ENV=production.")
        if not mercado_pago_webhook_secret():
            raise RuntimeError("MERCADO_PAGO_WEBHOOK_SECRET is required in production.")
        if not webhook_url:
            raise RuntimeError("MERCADO_PAGO_WEBHOOK_URL is required in production.")
