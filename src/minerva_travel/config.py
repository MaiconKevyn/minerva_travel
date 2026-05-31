import os
from pathlib import Path

from dotenv import load_dotenv


def load_project_env() -> None:
    load_dotenv(Path(".env"))


def image_provider() -> str:
    load_project_env()
    return os.getenv("IMAGE_PROVIDER", "placeholder")
