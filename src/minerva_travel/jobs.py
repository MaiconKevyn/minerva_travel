"""Durable local worker for guide generation.

The production database schema has the same job states. This SQLite adapter is
intentionally small but preserves the important operational contract: the API
persists a request and returns quickly; a separately started worker claims,
leases, resumes and finalizes the work.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from time import perf_counter
from typing import Any, cast

from fastapi import HTTPException

from minerva_travel.observability import EventOutcome, emit_event
from minerva_travel.persistence import GuideJobRecord, GuideRepository, delete_private_asset
from minerva_travel.privacy import PrivacyConsentError, validate_photo_processing_consent


@dataclass(frozen=True)
class JobRunResult:
    job_id: str | None
    outcome: str


class GuideJobWorker:
    def __init__(self, repository: GuideRepository, *, lease_seconds: int = 15 * 60) -> None:
        self.repository = repository
        self.lease_seconds = lease_seconds

    async def run_once(self) -> JobRunResult:
        job = self.repository.claim_next_job(lease_seconds=self.lease_seconds)
        if job is None:
            return JobRunResult(job_id=None, outcome="idle")
        emit_event(
            "guide_job_started",
            job_id=job.id,
            user_id=job.user_id,
            stage=job.stage,
            attempt_count=job.attempt_count,
            outcome="accepted",
        )
        return await self._run_claimed_job(job)

    async def _run_claimed_job(self, job: GuideJobRecord) -> JobRunResult:
        started_at = perf_counter()
        if job.cancel_requested:
            delete_private_asset(job.photo_path)
            emit_event(
                "guide_job_finished",
                job_id=job.id,
                user_id=job.user_id,
                outcome="cancelled",
                duration_ms=round((perf_counter() - started_at) * 1000),
                attempt_count=job.attempt_count,
            )
            return JobRunResult(job_id=job.id, outcome="cancelled")
        try:
            payload = _validated_snapshot(job.request_snapshot)
            consent = validate_photo_processing_consent(
                granted=bool(payload["photo_processing_consent"]),
                version=_optional_string(payload.get("privacy_consent_version")),
                granted_at=_optional_string(payload.get("privacy_consent_at")),
            )
            if not self.repository.update_job_progress(
                job.id,
                stage="preparing_assets",
                progress=20,
                lease_seconds=self.lease_seconds,
            ):
                delete_private_asset(job.photo_path)
                return JobRunResult(job_id=job.id, outcome="cancelled")

            # Import lazily so the FastAPI module can use persistence without a
            # circular import at application startup.
            from minerva_travel.app import generate_pdf_from_saved_photo

            self.repository.update_job_progress(
                job.id,
                stage="generating_cover",
                progress=40,
                lease_seconds=self.lease_seconds,
            )
            result = await generate_pdf_from_saved_photo(
                title=payload["title"],
                children_names=payload["children_names"],
                children_ages=payload["children_ages"],
                expected_visible_family_member_count=payload[
                    "expected_visible_family_member_count"
                ],
                parents_names=payload["parents_names"],
                year=payload["year"],
                selected_landmarks=payload["selected_landmarks"],
                family_photo_path=job.photo_path,
                owner_id=job.user_id,
                custom_landmarks=_optional_string(payload.get("custom_landmarks")),
                itinerary_json=_optional_string(payload.get("itinerary_json")),
                restaurant_recommendations_extra=bool(
                    payload.get("restaurant_recommendations_extra")
                ),
                privacy_consent=consent,
                guide_id=job.id,
            )
            self.repository.update_job_progress(
                job.id,
                stage="persisting",
                progress=90,
                lease_seconds=self.lease_seconds,
            )
            result_payload = {
                "request_id": result["request_id"],
                "download_url": result["download_url"],
                "preview_url": result.get("preview_url"),
                "filename": result["filename"],
                "cover_status": result["cover_status"],
            }
            if self.repository.finish_job(job.id, result_payload=result_payload):
                emit_event(
                    "guide_job_finished",
                    job_id=job.id,
                    user_id=job.user_id,
                    stage="complete",
                    outcome="succeeded",
                    duration_ms=round((perf_counter() - started_at) * 1000),
                    attempt_count=job.attempt_count,
                )
                return JobRunResult(job_id=job.id, outcome="succeeded")

            # A cancellation requested while the PDF was rendering wins. The
            # guide has already been persisted, so delete its private assets.
            from minerva_travel.persistence import delete_guide_and_assets

            delete_guide_and_assets(self.repository, job.id, job.user_id)
            emit_event(
                "guide_job_finished",
                job_id=job.id,
                user_id=job.user_id,
                outcome="cancelled",
                duration_ms=round((perf_counter() - started_at) * 1000),
                attempt_count=job.attempt_count,
            )
            return JobRunResult(job_id=job.id, outcome="cancelled")
        except Exception as error:
            code, message = _safe_job_error(error)
            if _is_retryable_job_error(error):
                outcome = self.repository.retry_or_fail_job(
                    job.id,
                    error_code=code,
                    error_message_safe=message,
                )
            else:
                self.repository.fail_job(job.id, error_code=code, error_message_safe=message)
                outcome = "failed"
            if outcome != "retrying":
                delete_private_asset(job.photo_path)
            emit_event(
                "guide_job_finished",
                job_id=job.id,
                user_id=job.user_id,
                outcome=cast(
                    EventOutcome,
                    outcome if outcome in {"failed", "retrying", "cancelled"} else "failed",
                ),
                error_code=code,
                duration_ms=round((perf_counter() - started_at) * 1000),
                attempt_count=job.attempt_count,
            )
            return JobRunResult(job_id=job.id, outcome=outcome)


def run_once(repository: GuideRepository | None = None) -> JobRunResult:
    """Synchronous worker entrypoint used by the process script and tests."""

    active_repository = repository or GuideRepository()
    return asyncio.run(GuideJobWorker(active_repository).run_once())


def _validated_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    required_strings = ("title", "children_names", "parents_names")
    for key in required_strings:
        value = snapshot.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"job_snapshot_invalid_{key}")
    selected = snapshot.get("selected_landmarks")
    ages = snapshot.get("children_ages", [])
    if not isinstance(selected, list) or not all(isinstance(item, str) for item in selected):
        raise ValueError("job_snapshot_invalid_selected_landmarks")
    if not isinstance(ages, list) or not all(isinstance(age, int) for age in ages):
        raise ValueError("job_snapshot_invalid_children_ages")
    year = snapshot.get("year")
    if not isinstance(year, int):
        raise ValueError("job_snapshot_invalid_year")
    expected = snapshot.get("expected_visible_family_member_count")
    if expected is not None and (not isinstance(expected, int) or isinstance(expected, bool)):
        raise ValueError("job_snapshot_invalid_expected_visible_family_member_count")
    return {
        "title": snapshot["title"],
        "children_names": snapshot["children_names"],
        "children_ages": ages,
        "expected_visible_family_member_count": expected,
        "parents_names": snapshot["parents_names"],
        "year": year,
        "selected_landmarks": selected,
        "custom_landmarks": snapshot.get("custom_landmarks"),
        "itinerary_json": snapshot.get("itinerary_json"),
        "restaurant_recommendations_extra": bool(snapshot.get("restaurant_recommendations_extra")),
        "photo_processing_consent": bool(snapshot.get("photo_processing_consent")),
        "privacy_consent_version": snapshot.get("privacy_consent_version"),
        "privacy_consent_at": snapshot.get("privacy_consent_at"),
    }


def _optional_string(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _safe_job_error(error: Exception) -> tuple[str, str]:
    if isinstance(error, PrivacyConsentError):
        return error.code, error.message
    if isinstance(error, HTTPException):
        detail = error.detail
        if isinstance(detail, dict):
            code = str(detail.get("code") or "generation_failed")
            message = str(detail.get("message") or "Não foi possível gerar o guia.")
            return code[:80], message[:500]
        return "generation_failed", "Não foi possível gerar o guia."
    if isinstance(error, ValueError) and str(error).startswith("job_snapshot_invalid_"):
        return str(error)[:80], "Os dados salvos para este guia são inválidos."
    return "generation_failed", "Não foi possível gerar o guia. Tente novamente."


def _is_retryable_job_error(error: Exception) -> bool:
    """Only retry errors that could reasonably recover without user action."""

    if isinstance(error, (PrivacyConsentError, ValueError)):
        return False
    if isinstance(error, HTTPException):
        return error.status_code == 429 or error.status_code >= 500
    return True
