from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

RUNTIME_DIR = Path("runtime")


def ensure_runtime_dirs() -> None:
    for name in ("uploads", "generated", "pdfs"):
        (RUNTIME_DIR / name).mkdir(parents=True, exist_ok=True)


async def save_upload(upload: UploadFile) -> Path:
    ensure_runtime_dirs()
    suffix = Path(upload.filename or "family.png").suffix.lower() or ".png"
    path = RUNTIME_DIR / "uploads" / f"{uuid4().hex}{suffix}"
    content = await upload.read()
    path.write_bytes(content)
    return path


def generated_path(filename: str) -> Path:
    ensure_runtime_dirs()
    return RUNTIME_DIR / "generated" / filename


def pdf_path(filename: str) -> Path:
    ensure_runtime_dirs()
    return RUNTIME_DIR / "pdfs" / filename
