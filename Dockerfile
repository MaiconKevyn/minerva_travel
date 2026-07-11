# syntax=docker/dockerfile:1.7

ARG PYTHON_VERSION=3.11.15
ARG UV_VERSION=0.11.28

FROM ghcr.io/astral-sh/uv:${UV_VERSION} AS uv

FROM python:${PYTHON_VERSION}-slim-bookworm AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

COPY --from=uv /uv /uvx /usr/local/bin/
COPY pyproject.toml uv.lock README.md ./
COPY src ./src

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-editable


FROM python:${PYTHON_VERSION}-slim-bookworm AS runtime

ARG APP_UID=10001
ARG APP_GID=10001

ENV PATH="/app/.venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

RUN apt-get update \
    && apt-get install --yes --no-install-recommends \
        fonts-dejavu-core \
        libcairo2 \
        libffi8 \
        libfontconfig1 \
        libfreetype6 \
        libgdk-pixbuf-2.0-0 \
        libglib2.0-0 \
        libharfbuzz-subset0 \
        libharfbuzz0b \
        libjpeg62-turbo \
        libopenjp2-7 \
        libpango-1.0-0 \
        libpangocairo-1.0-0 \
        libpangoft2-1.0-0 \
        poppler-utils \
        qpdf \
        shared-mime-info \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid "${APP_GID}" app \
    && useradd --uid "${APP_UID}" --gid "${APP_GID}" --create-home \
        --shell /usr/sbin/nologin app

# Build tooling is unnecessary at runtime. Removing it also removes vendored
# package metadata that would otherwise expose fixed HIGH vulnerabilities.
RUN python -m pip uninstall --yes setuptools wheel

WORKDIR /app

COPY --from=builder --chown=app:app /app/.venv /app/.venv
COPY --chown=app:app data ./data
COPY --chown=app:app assets ./assets
COPY --chown=app:app scripts/run_guide_worker.py ./scripts/run_guide_worker.py

RUN mkdir --parents \
        runtime/custom-images \
        runtime/generated \
        runtime/pdfs \
        runtime/uploads \
        runtime/wikimedia \
    && chown --recursive app:app runtime

USER app

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=5s --start-period=15s --retries=5 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/catalog', timeout=3).read()" || exit 1

STOPSIGNAL SIGTERM

CMD ["sh", "-c", "exec uvicorn minerva_travel.app:app --host 0.0.0.0 --port \"${PORT:-8000}\""]


FROM runtime AS worker

CMD ["sh", "-c", "trap 'exit 0' TERM INT; while :; do python scripts/run_guide_worker.py; sleep 1; done"]
