"""Minimal structured telemetry with an explicit no-PII boundary.

The application can ship these JSON records to the platform log drain without
adding a tracking SDK or leaking family names, emails, free-form itineraries,
photos, storage paths, or provider responses.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from collections import Counter
from datetime import UTC, datetime
from threading import Lock
from typing import Literal

LOGGER = logging.getLogger("minerva.events")
LOGGER.setLevel(logging.INFO)
if not LOGGER.handlers:
    _event_handler = logging.StreamHandler()
    _event_handler.setFormatter(logging.Formatter("%(message)s"))
    LOGGER.addHandler(_event_handler)
# Uvicorn commonly configures the root logger at WARNING.  Keep this dedicated
# JSON stream independent so production drains receive the events consistently.
LOGGER.propagate = False
_METRICS: Counter[str] = Counter()
_METRICS_LOCK = Lock()

EventOutcome = Literal["accepted", "succeeded", "failed", "retrying", "cancelled"]


def user_pseudonym(user_id: str) -> str:
    """Return a stable non-reversible identifier suitable for logs."""

    salt = os.getenv("OBSERVABILITY_HASH_SALT", "minerva-observability-v1")
    value = f"{salt}:{user_id}".encode()
    return hashlib.sha256(value).hexdigest()[:16]


def emit_event(
    event: str,
    *,
    request_id: str | None = None,
    job_id: str | None = None,
    user_id: str | None = None,
    stage: str | None = None,
    outcome: EventOutcome | None = None,
    error_code: str | None = None,
    duration_ms: int | None = None,
    attempt_count: int | None = None,
    pdf_bytes: int | None = None,
    http_status: int | None = None,
    route: str | None = None,
) -> None:
    """Emit an allow-listed event and update small in-process counters."""

    payload: dict[str, object] = {
        "event": event[:80],
        "timestamp": datetime.now(UTC).isoformat(),
    }
    for key, value in {
        "request_id": request_id,
        "job_id": job_id,
        "stage": stage,
        "outcome": outcome,
        "error_code": error_code,
        "duration_ms": duration_ms,
        "attempt_count": attempt_count,
        "pdf_bytes": pdf_bytes,
        "http_status": http_status,
        "route": route,
    }.items():
        if value is not None:
            payload[key] = value
    if user_id:
        payload["user_hash"] = user_pseudonym(user_id)

    with _METRICS_LOCK:
        _METRICS[f"events.{event[:80]}"] += 1
        if outcome:
            _METRICS[f"outcomes.{outcome}"] += 1
    LOGGER.info(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))


def metrics_snapshot() -> dict[str, int]:
    """Return counters for a health/debug integration without exposing PII."""

    with _METRICS_LOCK:
        return dict(_METRICS)


def reset_metrics_for_tests() -> None:
    with _METRICS_LOCK:
        _METRICS.clear()
