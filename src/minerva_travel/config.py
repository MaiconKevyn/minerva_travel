import os
from pathlib import Path

from dotenv import load_dotenv


def load_project_env() -> None:
    load_dotenv(Path(".env"))


def image_provider() -> str:
    load_project_env()
    return os.getenv("IMAGE_PROVIDER", "placeholder")


def cors_allowed_origins() -> list[str]:
    load_project_env()
    raw_origins = os.getenv("CORS_ALLOW_ORIGINS", "*")
    origins = [origin.strip() for origin in raw_origins.split(",") if origin.strip()]
    return origins or ["*"]
