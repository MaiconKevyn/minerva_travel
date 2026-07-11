"""Fail when application environment variables are absent from example files."""

from __future__ import annotations

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND_SOURCES = [ROOT / "src", ROOT / "scripts"]
FRONTEND_SOURCE = ROOT / "frontend_atual" / "apps" / "web" / "src"
BACKEND_EXAMPLE = ROOT / ".env.example"
FRONTEND_EXAMPLE = ROOT / "frontend_atual" / "apps" / "web" / ".env.example"

# These names are assembled from a fixed endpoint scope/provider at runtime.
DYNAMIC_BACKEND_ENV = {
    "CONCURRENCY_GUIDE_GENERATE_USER_LIMIT",
    "CONCURRENCY_LEASE_SECONDS",
    "CONCURRENCY_PROVIDER_GOOGLE_LIMIT",
    "CONCURRENCY_PROVIDER_OPENAI_LIMIT",
    "CONCURRENCY_PROVIDER_REPLICATE_LIMIT",
    "CONCURRENCY_USER_LIMIT",
    "IDEMPOTENCY_KEY_REQUIRED",
    "IDEMPOTENCY_PENDING_TTL_SECONDS",
    "IDEMPOTENCY_TTL_SECONDS",
    "IMAGE_UPLOAD_MAX_BYTES",
    "IMAGE_UPLOAD_MAX_HEIGHT",
    "IMAGE_UPLOAD_MAX_PIXELS",
    "IMAGE_UPLOAD_MAX_WIDTH",
    "QUOTA_GUIDE_GENERATE_PERIOD_SECONDS",
    "QUOTA_GUIDE_GENERATE_USER",
    "RATE_LIMIT_GUIDE_GENERATE_IP",
    "RATE_LIMIT_GUIDE_GENERATE_USER",
    "RATE_LIMIT_GUIDE_GENERATE_WINDOW_SECONDS",
    "REQUEST_CONTROL_ENABLED",
    "REQUEST_CONTROL_FAIL_CLOSED",
}

FRONTEND_ENV_PATTERN = re.compile(
    r"(?:import\.meta\.env\?\.|runtimeConfig\(\)\.)(VITE_[A-Z][A-Z0-9_]*)"
)
EXAMPLE_KEY_PATTERN = re.compile(r"^([A-Z][A-Z0-9_]*)=", re.MULTILINE)


def _python_environment_names() -> set[str]:
    names = set(DYNAMIC_BACKEND_ENV)
    for source_root in BACKEND_SOURCES:
        for path in source_root.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call) or not node.args:
                    continue
                function = node.func
                if not (
                    isinstance(function, ast.Attribute)
                    and function.attr in {"getenv", "get"}
                    and isinstance(function.value, (ast.Name, ast.Attribute))
                ):
                    continue
                first_argument = node.args[0]
                if isinstance(first_argument, ast.Constant) and isinstance(
                    first_argument.value, str
                ):
                    value = first_argument.value
                    if re.fullmatch(r"[A-Z][A-Z0-9_]*", value):
                        names.add(value)
    return names


def _frontend_environment_names() -> set[str]:
    names: set[str] = set()
    for path in FRONTEND_SOURCE.rglob("*"):
        if path.suffix not in {".js", ".jsx"}:
            continue
        names.update(FRONTEND_ENV_PATTERN.findall(path.read_text(encoding="utf-8")))
    return names


def _example_names(path: Path) -> set[str]:
    return set(EXAMPLE_KEY_PATTERN.findall(path.read_text(encoding="utf-8")))


def main() -> int:
    checks = [
        ("backend", _python_environment_names(), _example_names(BACKEND_EXAMPLE)),
        ("frontend", _frontend_environment_names(), _example_names(FRONTEND_EXAMPLE)),
    ]
    failures: list[str] = []
    for label, used, documented in checks:
        missing = sorted(used - documented)
        if missing:
            failures.append(f"{label}: {', '.join(missing)}")
    if failures:
        print("Variáveis ausentes nos arquivos .env.example:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Environment examples cover all variables read by application code: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
