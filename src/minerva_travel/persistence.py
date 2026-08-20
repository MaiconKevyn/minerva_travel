from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

from minerva_travel import storage
from minerva_travel.config import guide_draft_retention_days, guide_retention_days

SCHEMA_VERSION = 1
TEMPLATE_VERSION = "2026-07-09"
JOB_STAGES = {
    "queued",
    "validating",
    "preparing_assets",
    "generating_cover",
    "generating_content",
    "rendering_pdf",
    "persisting",
    "finalizing",
    "complete",
}
JOB_STATUSES = {"queued", "running", "succeeded", "failed", "cancelled"}
PAYMENT_STATUSES = {
    "pending",
    "authorized",
    "paid",
    "failed",
    "refunded",
    "cancelled",
}


@dataclass(frozen=True)
class GuideRecord:
    id: str
    user_id: str
    title: str
    status: str
    pdf_filename: str | None
    created_at: str
    updated_at: str
    expires_at: str | None
    deleted_at: str | None
    cover_fallback_used: bool
    metadata: dict[str, Any]

    @property
    def is_expired(self) -> bool:
        if not self.expires_at:
            return False
        return datetime.fromisoformat(self.expires_at) <= datetime.now(UTC)

    def public_payload(self) -> dict[str, object]:
        return {
            "id": self.id,
            "title": self.title,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "expires_at": self.expires_at,
            "cover_fallback_used": self.cover_fallback_used,
            "destinations": self.metadata.get("destinations", []),
            "download_url": (
                f"/download/{self.pdf_filename}"
                if self.status == "succeeded" and self.pdf_filename and not self.is_expired
                else None
            ),
            # Guias gerados antes da miniatura existir não têm capa; o painel
            # cai no placeholder ilustrado em vez de mostrar imagem quebrada.
            "cover_url": (
                f"/guides/{self.id}/cover"
                if self.status == "succeeded"
                and not self.is_expired
                and self.metadata.get("cover_thumbnail")
                else None
            ),
        }

    def export_payload(self) -> dict[str, object]:
        """Return the portable, user-facing subset of a persisted guide.

        Persistence metadata is deliberately allow-listed here. This keeps
        filenames, storage paths, provider details, and any future internal
        metadata out of account exports by default.
        """

        destinations: list[dict[str, object]] = []
        raw_destinations = self.metadata.get("destinations")
        if isinstance(raw_destinations, list):
            for raw_destination in raw_destinations:
                if not isinstance(raw_destination, dict):
                    continue
                destination: dict[str, object] = {}
                for key in ("id", "place"):
                    value = raw_destination.get(key)
                    if isinstance(value, str):
                        destination[key] = value
                landmarks = raw_destination.get("landmarks")
                if isinstance(landmarks, list):
                    destination["landmarks"] = [
                        landmark for landmark in landmarks if isinstance(landmark, str)
                    ]
                if destination:
                    destinations.append(destination)

        privacy_consent: dict[str, str] | None = None
        raw_privacy_consent = self.metadata.get("privacy_consent")
        if isinstance(raw_privacy_consent, dict):
            allowed_consent = {
                key: value
                for key in ("version", "granted_at")
                if isinstance((value := raw_privacy_consent.get(key)), str)
            }
            privacy_consent = allowed_consent or None

        payload: dict[str, object] = {
            "id": self.id,
            "title": self.title,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "expires_at": self.expires_at,
            "deleted_at": self.deleted_at,
            "cover_fallback_used": self.cover_fallback_used,
            "destinations": destinations,
            "privacy_consent": privacy_consent,
            "pdf_available": bool(
                self.status == "succeeded" and self.pdf_filename and not self.is_expired
            ),
        }
        year = self.metadata.get("year")
        if isinstance(year, int) and not isinstance(year, bool):
            payload["year"] = year
        return payload


@dataclass(frozen=True)
class GuideAssetRecord:
    guide_id: str
    user_id: str
    kind: str
    local_path: Path


@dataclass(frozen=True)
class GuideDraftRecord:
    id: str
    user_id: str
    title: str
    payload: dict[str, Any]
    revision: int
    status: str
    created_at: str
    updated_at: str
    expires_at: str | None

    def public_payload(self) -> dict[str, object]:
        return {
            "id": self.id,
            "title": self.title,
            "payload": self.payload,
            "revision": self.revision,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "expires_at": self.expires_at,
        }

    def export_payload(self) -> dict[str, object]:
        return self.public_payload()


@dataclass(frozen=True)
class FamilyProfileRecord:
    """Os dados reutilizáveis da família, um registro por dono.

    Guarda o ano de nascimento, não a idade: uma idade salva envelhece em
    silêncio e o guia é calibrado por faixa etária — a criança de 6 anos
    voltaria como criança de 6 anos na viagem do ano seguinte.

    Nada de foto, consentimento, destino ou roteiro entra aqui: cada guia
    pede a foto e o consentimento de novo, de propósito.
    """

    user_id: str
    family_name: str
    parents: list[dict[str, Any]]
    children: list[dict[str, Any]]
    revision: int
    created_at: str
    updated_at: str

    def public_payload(self) -> dict[str, object]:
        return {
            "family_name": self.family_name,
            "parents": self.parents,
            "children": self.children,
            "revision": self.revision,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def export_payload(self) -> dict[str, object]:
        return self.public_payload()


@dataclass(frozen=True)
class GuideJobRecord:
    id: str
    user_id: str
    idempotency_key: str
    status: str
    stage: str
    progress: int
    request_snapshot: dict[str, Any]
    photo_path: Path
    result: dict[str, Any] | None
    error_code: str | None
    error_message_safe: str | None
    attempt_count: int
    max_attempts: int
    cancel_requested: bool
    created_at: str
    updated_at: str
    started_at: str | None
    completed_at: str | None
    lease_expires_at: str | None
    next_attempt_at: str | None

    @property
    def terminal(self) -> bool:
        return self.status in {"succeeded", "failed", "cancelled"}

    def public_payload(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "id": self.id,
            "status": self.status,
            "stage": self.stage,
            "progress": self.progress,
            "attempt_count": self.attempt_count,
            "max_attempts": self.max_attempts,
            "cancel_requested": self.cancel_requested,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "error": (
                {
                    "code": self.error_code or "generation_failed",
                    "message": self.error_message_safe or "Não foi possível gerar o guia.",
                }
                if self.status == "failed"
                else None
            ),
        }
        if self.status == "succeeded" and self.result:
            payload["result"] = self.result
        return payload


@dataclass(frozen=True)
class PaymentRecord:
    id: str
    user_id: str
    builder_session_id: str
    provider: str
    provider_preference_id: str | None
    provider_payment_id: str | None
    idempotency_key: str
    status: str
    amount_minor: int
    currency: str
    product_code: str
    checkout_url: str | None
    created_at: str
    updated_at: str
    paid_at: str | None

    def public_payload(self) -> dict[str, object]:
        return {
            "payment_id": self.id,
            "builder_session_id": self.builder_session_id,
            "status": self.status,
            "amount_minor": self.amount_minor,
            "currency": self.currency,
            "product_code": self.product_code,
            "checkout_url": self.checkout_url,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "paid_at": self.paid_at,
        }


@dataclass(frozen=True)
class EntitlementRecord:
    id: str
    user_id: str
    builder_session_id: str
    source_payment_id: str
    status: str
    product_code: str
    created_at: str
    consumed_at: str | None
    revoked_at: str | None


class GuideRepository:
    """Small durable repository used by the API and local worker.

    Production migrations target Supabase Postgres. SQLite remains the hermetic
    development/test adapter so the complete owner/download flow works offline.
    """

    def __init__(self, database_path: Path | None = None) -> None:
        self.database_path = database_path or storage.RUNTIME_DIR / "minerva.sqlite3"
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 10000")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._connection() as connection:
            connection.executescript(
                """
                PRAGMA journal_mode = WAL;
                CREATE TABLE IF NOT EXISTS guides (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    status TEXT NOT NULL CHECK (
                        status IN ('queued', 'running', 'succeeded', 'failed', 'cancelled')
                    ),
                    pdf_filename TEXT UNIQUE,
                    cover_fallback_used INTEGER NOT NULL DEFAULT 0,
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    schema_version INTEGER NOT NULL,
                    template_version TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    expires_at TEXT,
                    deleted_at TEXT
                );
                CREATE INDEX IF NOT EXISTS guides_owner_created_idx
                    ON guides(user_id, created_at DESC);
                CREATE TABLE IF NOT EXISTS guide_assets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guide_id TEXT NOT NULL REFERENCES guides(id) ON DELETE CASCADE,
                    user_id TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    local_path TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(guide_id, local_path)
                );
                CREATE INDEX IF NOT EXISTS guide_assets_owner_idx
                    ON guide_assets(user_id, guide_id);
                CREATE TABLE IF NOT EXISTS guide_drafts (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    title TEXT NOT NULL DEFAULT '',
                    payload_json TEXT NOT NULL DEFAULT '{}',
                    revision INTEGER NOT NULL DEFAULT 1 CHECK (revision > 0),
                    status TEXT NOT NULL DEFAULT 'active' CHECK (
                        status IN ('active', 'submitted', 'abandoned', 'deleted')
                    ),
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    expires_at TEXT
                );
                CREATE INDEX IF NOT EXISTS guide_drafts_owner_updated_idx
                    ON guide_drafts(user_id, status, updated_at DESC);
                CREATE TABLE IF NOT EXISTS family_profiles (
                    user_id TEXT PRIMARY KEY,
                    family_name TEXT NOT NULL DEFAULT '',
                    members_json TEXT NOT NULL DEFAULT '{}',
                    revision INTEGER NOT NULL DEFAULT 1 CHECK (revision > 0),
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS guide_jobs (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL,
                    status TEXT NOT NULL CHECK (
                        status IN ('queued', 'running', 'succeeded', 'failed', 'cancelled')
                    ),
                    stage TEXT NOT NULL,
                    progress INTEGER NOT NULL CHECK (progress BETWEEN 0 AND 100),
                    request_snapshot_json TEXT NOT NULL,
                    photo_path TEXT NOT NULL,
                    result_json TEXT,
                    error_code TEXT,
                    error_message_safe TEXT,
                    attempt_count INTEGER NOT NULL DEFAULT 0,
                    max_attempts INTEGER NOT NULL DEFAULT 3,
                    cancel_requested INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    started_at TEXT,
                    completed_at TEXT,
                    lease_expires_at TEXT,
                    next_attempt_at TEXT,
                    UNIQUE(user_id, idempotency_key)
                );
                CREATE INDEX IF NOT EXISTS guide_jobs_owner_created_idx
                    ON guide_jobs(user_id, created_at DESC);
                CREATE INDEX IF NOT EXISTS guide_jobs_queue_idx
                    ON guide_jobs(status, next_attempt_at, lease_expires_at, created_at);
                CREATE TABLE IF NOT EXISTS payments (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    builder_session_id TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    provider_preference_id TEXT,
                    provider_payment_id TEXT,
                    idempotency_key TEXT NOT NULL,
                    status TEXT NOT NULL CHECK (
                        status IN (
                            'pending', 'authorized', 'paid', 'failed', 'refunded', 'cancelled'
                        )
                    ),
                    amount_minor INTEGER NOT NULL CHECK (amount_minor > 0),
                    currency TEXT NOT NULL CHECK (length(currency) = 3),
                    product_code TEXT NOT NULL,
                    checkout_url TEXT,
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    paid_at TEXT,
                    UNIQUE(provider, idempotency_key),
                    UNIQUE(provider, provider_preference_id),
                    UNIQUE(provider, provider_payment_id)
                );
                CREATE INDEX IF NOT EXISTS payments_owner_created_idx
                    ON payments(user_id, created_at DESC);
                CREATE INDEX IF NOT EXISTS payments_builder_idx
                    ON payments(user_id, builder_session_id, created_at DESC);
                CREATE UNIQUE INDEX IF NOT EXISTS payments_active_builder_uidx
                    ON payments(user_id, builder_session_id)
                    WHERE status IN ('pending', 'authorized', 'paid');
                CREATE TABLE IF NOT EXISTS entitlements (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    builder_session_id TEXT NOT NULL UNIQUE,
                    source_payment_id TEXT NOT NULL UNIQUE
                        REFERENCES payments(id) ON DELETE CASCADE,
                    status TEXT NOT NULL CHECK (status IN ('active', 'consumed', 'revoked')),
                    product_code TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    consumed_at TEXT,
                    revoked_at TEXT
                );
                CREATE INDEX IF NOT EXISTS entitlements_owner_builder_idx
                    ON entitlements(user_id, builder_session_id, status);
                """
            )
            # SQLite does not support ADD COLUMN inside CREATE TABLE IF NOT
            # EXISTS. Keep existing local installations forward-compatible.
            columns = {row["name"] for row in connection.execute("PRAGMA table_info(guide_jobs)")}
            if "next_attempt_at" not in columns:
                connection.execute("ALTER TABLE guide_jobs ADD COLUMN next_attempt_at TEXT")
            draft_columns = {
                row["name"] for row in connection.execute("PRAGMA table_info(guide_drafts)")
            }
            if "expires_at" not in draft_columns:
                connection.execute("ALTER TABLE guide_drafts ADD COLUMN expires_at TEXT")

    def create_draft(
        self,
        *,
        user_id: str,
        title: str,
        payload: dict[str, object],
    ) -> GuideDraftRecord:
        serialized = _serialized_draft_payload(payload)
        now = datetime.now(UTC)
        now_value = now.isoformat()
        expires_at = (now + timedelta(days=guide_draft_retention_days())).isoformat()
        draft_id = uuid4().hex
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO guide_drafts (
                    id, user_id, title, payload_json, revision, status,
                    created_at, updated_at, expires_at
                ) VALUES (?, ?, ?, ?, 1, 'active', ?, ?, ?)
                """,
                (draft_id, user_id, title[:200], serialized, now_value, now_value, expires_at),
            )
        record = self.get_draft_for_owner(draft_id, user_id)
        if record is None:  # pragma: no cover - database invariant
            raise RuntimeError("Guide draft persistence failed.")
        return record

    def create_or_get_payment(
        self,
        *,
        payment_id: str,
        user_id: str,
        builder_session_id: str,
        provider: str,
        idempotency_key: str,
        amount_minor: int,
        currency: str,
        product_code: str,
    ) -> tuple[PaymentRecord, bool]:
        """Create a local pending payment or return the safe reusable record."""

        now = datetime.now(UTC).isoformat()
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT * FROM payments
                WHERE user_id = ? AND builder_session_id = ?
                  AND status IN ('pending', 'authorized', 'paid')
                ORDER BY created_at DESC LIMIT 1
                """,
                (user_id, builder_session_id),
            ).fetchone()
            if row is not None:
                return self._payment_from_row(row), False
            row = connection.execute(
                "SELECT * FROM payments WHERE provider = ? AND idempotency_key = ?",
                (provider, idempotency_key),
            ).fetchone()
            if row is not None:
                record = self._payment_from_row(row)
                if record.user_id != user_id or record.builder_session_id != builder_session_id:
                    raise ValueError("Idempotency key already used for another checkout.")
                return record, False
            connection.execute(
                """
                INSERT INTO payments (
                    id, user_id, builder_session_id, provider, idempotency_key,
                    status, amount_minor, currency, product_code, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, 'pending', ?, ?, ?, ?, ?)
                """,
                (
                    payment_id,
                    user_id,
                    builder_session_id,
                    provider,
                    idempotency_key,
                    amount_minor,
                    currency,
                    product_code,
                    now,
                    now,
                ),
            )
        record = self.get_payment_for_owner(payment_id, user_id)
        if record is None:  # pragma: no cover - database invariant
            raise RuntimeError("Payment persistence failed.")
        return record, True

    def set_payment_preference(
        self,
        *,
        payment_id: str,
        provider_preference_id: str,
        checkout_url: str,
    ) -> PaymentRecord:
        now = datetime.now(UTC).isoformat()
        with self._connection() as connection:
            result = connection.execute(
                """
                UPDATE payments
                SET provider_preference_id = ?, checkout_url = ?, updated_at = ?
                WHERE id = ? AND status = 'pending'
                """,
                (provider_preference_id, checkout_url, now, payment_id),
            )
        if result.rowcount != 1:
            raise ValueError("Payment can no longer receive a checkout preference.")
        record = self.get_payment(payment_id)
        if record is None:  # pragma: no cover - database invariant
            raise RuntimeError("Payment persistence failed.")
        return record

    def fail_payment_checkout(self, payment_id: str) -> bool:
        now = datetime.now(UTC).isoformat()
        with self._connection() as connection:
            result = connection.execute(
                """
                UPDATE payments SET status = 'failed', updated_at = ?
                WHERE id = ? AND status = 'pending' AND provider_payment_id IS NULL
                """,
                (now, payment_id),
            )
        return result.rowcount == 1

    def get_payment(self, payment_id: str) -> PaymentRecord | None:
        return self._one_payment("SELECT * FROM payments WHERE id = ?", (payment_id,))

    def get_payment_for_owner(self, payment_id: str, user_id: str) -> PaymentRecord | None:
        return self._one_payment(
            "SELECT * FROM payments WHERE id = ? AND user_id = ?",
            (payment_id, user_id),
        )

    def payment_for_builder_owner(
        self,
        builder_session_id: str,
        user_id: str,
    ) -> PaymentRecord | None:
        return self._one_payment(
            """
            SELECT * FROM payments
            WHERE builder_session_id = ? AND user_id = ?
            ORDER BY CASE status
                WHEN 'paid' THEN 0 WHEN 'authorized' THEN 1 WHEN 'pending' THEN 2 ELSE 3 END,
                created_at DESC
            LIMIT 1
            """,
            (builder_session_id, user_id),
        )

    def apply_provider_payment(
        self,
        *,
        payment_id: str,
        provider_payment_id: str,
        status: str,
        amount_minor: int,
        currency: str,
    ) -> PaymentRecord:
        if status not in PAYMENT_STATUSES:
            raise ValueError("Unsupported payment status.")
        now = datetime.now(UTC).isoformat()
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM payments WHERE id = ?", (payment_id,)
            ).fetchone()
            if row is None:
                raise LookupError("Payment not found.")
            current = self._payment_from_row(row)
            if current.amount_minor != amount_minor or current.currency != currency:
                raise ValueError("Provider payment amount or currency mismatch.")
            collision = connection.execute(
                """
                SELECT id FROM payments
                WHERE provider = ? AND provider_payment_id = ? AND id != ?
                """,
                (current.provider, provider_payment_id, current.id),
            ).fetchone()
            if collision is not None:
                raise ValueError("Provider payment is already linked to another order.")

            final_status = status
            if current.status == "refunded":
                final_status = "refunded"
            elif current.status == "paid" and status not in {"refunded"}:
                final_status = "paid"
            paid_at = current.paid_at or (now if final_status == "paid" else None)
            connection.execute(
                """
                UPDATE payments
                SET provider_payment_id = ?, status = ?, updated_at = ?, paid_at = ?
                WHERE id = ?
                """,
                (provider_payment_id, final_status, now, paid_at, current.id),
            )
            if final_status == "paid":
                connection.execute(
                    """
                    INSERT OR IGNORE INTO entitlements (
                        id, user_id, builder_session_id, source_payment_id,
                        status, product_code, created_at
                    ) VALUES (?, ?, ?, ?, 'active', ?, ?)
                    """,
                    (
                        uuid4().hex,
                        current.user_id,
                        current.builder_session_id,
                        current.id,
                        current.product_code,
                        now,
                    ),
                )
            elif final_status == "refunded":
                connection.execute(
                    """
                    UPDATE entitlements
                    SET status = 'revoked', revoked_at = ?
                    WHERE source_payment_id = ? AND status != 'revoked'
                    """,
                    (now, current.id),
                )
        record = self.get_payment(payment_id)
        if record is None:  # pragma: no cover - database invariant
            raise RuntimeError("Payment persistence failed.")
        return record

    def claim_builder_entitlement(self, *, user_id: str, builder_session_id: str) -> bool:
        now = datetime.now(UTC).isoformat()
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT * FROM entitlements
                WHERE user_id = ? AND builder_session_id = ?
                  AND status IN ('active', 'consumed')
                LIMIT 1
                """,
                (user_id, builder_session_id),
            ).fetchone()
            if row is None:
                return False
            if row["status"] == "active":
                connection.execute(
                    """
                    UPDATE entitlements SET status = 'consumed', consumed_at = ?
                    WHERE id = ? AND status = 'active'
                    """,
                    (now, row["id"]),
                )
        return True

    def entitlement_for_builder(
        self,
        *,
        user_id: str,
        builder_session_id: str,
    ) -> EntitlementRecord | None:
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT * FROM entitlements
                WHERE user_id = ? AND builder_session_id = ? LIMIT 1
                """,
                (user_id, builder_session_id),
            ).fetchone()
        return self._entitlement_from_row(row) if row else None

    def update_draft(
        self,
        *,
        draft_id: str,
        user_id: str,
        title: str,
        payload: dict[str, object],
        expected_revision: int,
    ) -> GuideDraftRecord | None:
        if expected_revision < 1:
            raise ValueError("expected_revision must be positive")
        serialized = _serialized_draft_payload(payload)
        now = datetime.now(UTC)
        now_value = now.isoformat()
        expires_at = (now + timedelta(days=guide_draft_retention_days())).isoformat()
        with self._connection() as connection:
            result = connection.execute(
                """
                UPDATE guide_drafts
                SET title = ?, payload_json = ?, revision = revision + 1,
                    updated_at = ?, expires_at = ?
                WHERE id = ? AND user_id = ? AND status = 'active' AND revision = ?
                """,
                (
                    title[:200],
                    serialized,
                    now_value,
                    expires_at,
                    draft_id,
                    user_id,
                    expected_revision,
                ),
            )
        if result.rowcount != 1:
            return None
        return self.get_draft_for_owner(draft_id, user_id)

    def get_draft_for_owner(self, draft_id: str, user_id: str) -> GuideDraftRecord | None:
        return self._one_draft(
            """
            SELECT * FROM guide_drafts
            WHERE id = ? AND user_id = ? AND status = 'active'
              AND (expires_at IS NULL OR expires_at > ?)
            """,
            (draft_id, user_id, datetime.now(UTC).isoformat()),
        )

    def latest_draft_for_owner(self, user_id: str) -> GuideDraftRecord | None:
        return self._one_draft(
            """
            SELECT * FROM guide_drafts
            WHERE user_id = ? AND status = 'active'
              AND (expires_at IS NULL OR expires_at > ?)
            ORDER BY updated_at DESC LIMIT 1
            """,
            (user_id, datetime.now(UTC).isoformat()),
        )

    def list_drafts_for_export(self, user_id: str) -> list[GuideDraftRecord]:
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT * FROM guide_drafts
                WHERE user_id = ?
                ORDER BY updated_at DESC
                """,
                (user_id,),
            ).fetchall()
        return [self._draft_from_row(row) for row in rows]

    def discard_draft(self, draft_id: str, user_id: str) -> bool:
        with self._connection() as connection:
            result = connection.execute(
                """
                DELETE FROM guide_drafts
                WHERE id = ? AND user_id = ? AND status = 'active'
                """,
                (draft_id, user_id),
            )
        return result.rowcount == 1

    def delete_expired_drafts(self, *, now: datetime | None = None) -> int:
        now_value = (now or datetime.now(UTC)).isoformat()
        with self._connection() as connection:
            result = connection.execute(
                "DELETE FROM guide_drafts WHERE expires_at IS NOT NULL AND expires_at <= ?",
                (now_value,),
            )
        return result.rowcount

    def family_profile_for_owner(self, user_id: str) -> FamilyProfileRecord | None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM family_profiles WHERE user_id = ?",
                (user_id,),
            ).fetchone()
        return self._family_profile_from_row(row) if row else None

    def save_family_profile(
        self,
        *,
        user_id: str,
        family_name: str,
        parents: list[dict[str, object]],
        children: list[dict[str, object]],
        expected_revision: int | None,
    ) -> FamilyProfileRecord | None:
        """Grava o perfil inteiro de uma vez. Devolve ``None`` em conflito.

        O perfil é sempre lido e escrito como um bloco só, então uma escrita
        parcial não existe: ou a lista de membros nova entra inteira, ou a
        anterior fica como está. ``expected_revision`` ausente significa "não
        havia perfil"; se outra aba já criou um, isso é conflito e não
        sobrescrita.
        """

        serialized = _serialized_family_members(parents, children)
        now_value = datetime.now(UTC).isoformat()
        with self._connection() as connection:
            current = connection.execute(
                "SELECT revision FROM family_profiles WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            if current is None:
                if expected_revision is not None:
                    return None
                connection.execute(
                    """
                    INSERT INTO family_profiles (
                        user_id, family_name, members_json, revision, created_at, updated_at
                    ) VALUES (?, ?, ?, 1, ?, ?)
                    """,
                    (user_id, family_name[:160], serialized, now_value, now_value),
                )
            else:
                if expected_revision != int(current["revision"]):
                    return None
                connection.execute(
                    """
                    UPDATE family_profiles
                    SET family_name = ?, members_json = ?, revision = revision + 1,
                        updated_at = ?
                    WHERE user_id = ? AND revision = ?
                    """,
                    (family_name[:160], serialized, now_value, user_id, expected_revision),
                )
        record = self.family_profile_for_owner(user_id)
        if record is None:  # pragma: no cover - database invariant
            raise RuntimeError("Family profile persistence failed.")
        return record

    def delete_family_profile(self, user_id: str) -> bool:
        with self._connection() as connection:
            result = connection.execute(
                "DELETE FROM family_profiles WHERE user_id = ?",
                (user_id,),
            )
        return result.rowcount == 1

    def save_succeeded_guide(
        self,
        *,
        guide_id: str,
        user_id: str,
        title: str,
        pdf_filename: str,
        cover_fallback_used: bool,
        metadata: dict[str, object],
        assets: Iterable[tuple[str, Path]],
    ) -> GuideRecord:
        now = datetime.now(UTC)
        now_value = now.isoformat()
        expires_at = (now + timedelta(days=guide_retention_days())).isoformat()
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO guides (
                    id, user_id, title, status, pdf_filename,
                    cover_fallback_used, metadata_json, schema_version,
                    template_version, created_at, updated_at, expires_at
                ) VALUES (?, ?, ?, 'succeeded', ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    guide_id,
                    user_id,
                    title,
                    pdf_filename,
                    int(cover_fallback_used),
                    json.dumps(metadata, ensure_ascii=False, separators=(",", ":")),
                    SCHEMA_VERSION,
                    TEMPLATE_VERSION,
                    now_value,
                    now_value,
                    expires_at,
                ),
            )
            for kind, local_path in assets:
                connection.execute(
                    """
                    INSERT OR IGNORE INTO guide_assets (
                        guide_id, user_id, kind, local_path, created_at
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (guide_id, user_id, kind, str(local_path), now_value),
                )
        record = self.get_for_owner(guide_id, user_id)
        if record is None:  # pragma: no cover - defensive database invariant
            raise RuntimeError("Guide persistence failed.")
        return record

    def get_for_owner(self, guide_id: str, user_id: str) -> GuideRecord | None:
        return self._one(
            """
            SELECT * FROM guides
            WHERE id = ? AND user_id = ? AND deleted_at IS NULL
            """,
            (guide_id, user_id),
        )

    def get_by_pdf_for_owner(self, pdf_filename: str, user_id: str) -> GuideRecord | None:
        return self._one(
            """
            SELECT * FROM guides
            WHERE pdf_filename = ? AND user_id = ? AND deleted_at IS NULL
            """,
            (pdf_filename, user_id),
        )

    def list_for_owner(self, user_id: str, *, limit: int = 50) -> list[GuideRecord]:
        safe_limit = min(max(limit, 1), 100)
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT * FROM guides
                WHERE user_id = ? AND deleted_at IS NULL
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (user_id, safe_limit),
            ).fetchall()
        return [self._from_row(row) for row in rows]

    def list_all_for_owner(self, user_id: str) -> list[GuideRecord]:
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT * FROM guides
                WHERE user_id = ? AND deleted_at IS NULL
                ORDER BY created_at DESC
                """,
                (user_id,),
            ).fetchall()
        return [self._from_row(row) for row in rows]

    def list_for_export(self, user_id: str) -> list[GuideRecord]:
        """List all retained owner data, including previously soft-deleted guides."""

        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT * FROM guides
                WHERE user_id = ?
                ORDER BY created_at DESC
                """,
                (user_id,),
            ).fetchall()
        return [self._from_row(row) for row in rows]

    def create_job(
        self,
        *,
        job_id: str,
        user_id: str,
        idempotency_key: str,
        request_snapshot: dict[str, object],
        photo_path: Path,
        max_attempts: int = 3,
    ) -> GuideJobRecord:
        if not 1 <= max_attempts <= 10:
            raise ValueError("max_attempts must be between 1 and 10")
        now = datetime.now(UTC).isoformat()
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO guide_jobs (
                    id, user_id, idempotency_key, status, stage, progress,
                    request_snapshot_json, photo_path, max_attempts, created_at, updated_at
                ) VALUES (?, ?, ?, 'queued', 'queued', 0, ?, ?, ?, ?, ?)
                """,
                (
                    job_id,
                    user_id,
                    idempotency_key,
                    json.dumps(request_snapshot, ensure_ascii=False, separators=(",", ":")),
                    str(photo_path),
                    max_attempts,
                    now,
                    now,
                ),
            )
        record = self.get_job_for_owner(job_id, user_id)
        if record is None:  # pragma: no cover - database invariant
            raise RuntimeError("Guide job persistence failed.")
        return record

    def get_job_for_owner(self, job_id: str, user_id: str) -> GuideJobRecord | None:
        return self._one_job(
            "SELECT * FROM guide_jobs WHERE id = ? AND user_id = ?",
            (job_id, user_id),
        )

    def get_job(self, job_id: str) -> GuideJobRecord | None:
        return self._one_job("SELECT * FROM guide_jobs WHERE id = ?", (job_id,))

    def get_job_for_idempotency(self, user_id: str, idempotency_key: str) -> GuideJobRecord | None:
        return self._one_job(
            "SELECT * FROM guide_jobs WHERE user_id = ? AND idempotency_key = ?",
            (user_id, idempotency_key),
        )

    def list_jobs_for_owner(self, user_id: str, *, limit: int = 50) -> list[GuideJobRecord]:
        safe_limit = min(max(limit, 1), 100)
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT * FROM guide_jobs
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (user_id, safe_limit),
            ).fetchall()
        return [self._job_from_row(row) for row in rows]

    def claim_next_job(self, *, lease_seconds: int = 15 * 60) -> GuideJobRecord | None:
        if lease_seconds <= 0:
            raise ValueError("lease_seconds must be positive")
        now = datetime.now(UTC)
        now_value = now.isoformat()
        lease_value = (now + timedelta(seconds=lease_seconds)).isoformat()
        with self._connection() as connection:
            connection.execute(
                """
                UPDATE guide_jobs
                SET status = 'failed', stage = 'complete', completed_at = ?,
                    lease_expires_at = NULL, next_attempt_at = NULL,
                    error_code = 'worker_lease_expired',
                    error_message_safe = 'A geração excedeu o limite de tentativas.',
                    updated_at = ?
                WHERE status = 'running' AND lease_expires_at IS NOT NULL
                  AND lease_expires_at <= ? AND cancel_requested = 0
                  AND attempt_count >= max_attempts
                """,
                (now_value, now_value, now_value),
            )
            connection.execute(
                """
                UPDATE guide_jobs
                SET status = 'queued', stage = 'queued', progress = 0,
                    lease_expires_at = NULL, next_attempt_at = NULL, updated_at = ?
                WHERE status = 'running' AND lease_expires_at IS NOT NULL
                  AND lease_expires_at <= ? AND cancel_requested = 0
                  AND attempt_count < max_attempts
                """,
                (now_value, now_value),
            )
            row = connection.execute(
                """
                SELECT * FROM guide_jobs
                WHERE status = 'queued' AND cancel_requested = 0
                  AND attempt_count < max_attempts
                  AND (next_attempt_at IS NULL OR next_attempt_at <= ?)
                ORDER BY created_at ASC
                LIMIT 1
                """,
                (now_value,),
            ).fetchone()
            if row is None:
                return None
            cursor = connection.execute(
                """
                UPDATE guide_jobs
                SET status = 'running', stage = 'validating', progress = 5,
                    attempt_count = attempt_count + 1, started_at = COALESCE(started_at, ?),
                    lease_expires_at = ?, next_attempt_at = NULL, updated_at = ?
                WHERE id = ? AND status = 'queued' AND cancel_requested = 0
                """,
                (now_value, lease_value, now_value, row["id"]),
            )
            if cursor.rowcount != 1:  # pragma: no cover - transaction invariant
                return None
            claimed = connection.execute(
                "SELECT * FROM guide_jobs WHERE id = ?", (row["id"],)
            ).fetchone()
        return self._job_from_row(claimed) if claimed else None

    def update_job_progress(
        self,
        job_id: str,
        *,
        stage: str,
        progress: int,
        lease_seconds: int = 15 * 60,
    ) -> bool:
        if stage not in JOB_STAGES:
            raise ValueError(f"Unknown job stage: {stage}")
        if not 0 <= progress <= 100:
            raise ValueError("progress must be between 0 and 100")
        now = datetime.now(UTC)
        with self._connection() as connection:
            result = connection.execute(
                """
                UPDATE guide_jobs
                SET stage = ?, progress = ?, lease_expires_at = ?, updated_at = ?
                WHERE id = ? AND status = 'running' AND cancel_requested = 0
                """,
                (
                    stage,
                    progress,
                    (now + timedelta(seconds=lease_seconds)).isoformat(),
                    now.isoformat(),
                    job_id,
                ),
            )
        return result.rowcount == 1

    def finish_job(self, job_id: str, *, result_payload: dict[str, object]) -> bool:
        now_value = datetime.now(UTC).isoformat()
        with self._connection() as connection:
            result = connection.execute(
                """
                UPDATE guide_jobs
                SET status = 'succeeded', stage = 'complete', progress = 100,
                    result_json = ?, completed_at = ?, lease_expires_at = NULL,
                    updated_at = ?
                WHERE id = ? AND status = 'running' AND cancel_requested = 0
                """,
                (
                    json.dumps(result_payload, ensure_ascii=False, separators=(",", ":")),
                    now_value,
                    now_value,
                    job_id,
                ),
            )
        return result.rowcount == 1

    def fail_job(
        self,
        job_id: str,
        *,
        error_code: str,
        error_message_safe: str,
    ) -> bool:
        now_value = datetime.now(UTC).isoformat()
        with self._connection() as connection:
            result = connection.execute(
                """
                UPDATE guide_jobs
                SET status = CASE WHEN cancel_requested = 1 THEN 'cancelled' ELSE 'failed' END,
                    stage = 'complete', completed_at = ?, lease_expires_at = NULL,
                    next_attempt_at = NULL,
                    error_code = ?, error_message_safe = ?, updated_at = ?
                WHERE id = ? AND status = 'running'
                """,
                (now_value, error_code[:80], error_message_safe[:500], now_value, job_id),
            )
        return result.rowcount == 1

    def retry_or_fail_job(
        self,
        job_id: str,
        *,
        error_code: str,
        error_message_safe: str,
    ) -> str:
        """Schedule a bounded retry with exponential backoff, or finish safely."""

        now = datetime.now(UTC)
        now_value = now.isoformat()
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT attempt_count, max_attempts, cancel_requested
                FROM guide_jobs WHERE id = ? AND status = 'running'
                """,
                (job_id,),
            ).fetchone()
            if row is None:
                return "cancelled"
            if row["cancel_requested"]:
                connection.execute(
                    """
                    UPDATE guide_jobs
                    SET status = 'cancelled', stage = 'complete', completed_at = ?,
                        lease_expires_at = NULL, next_attempt_at = NULL, updated_at = ?
                    WHERE id = ? AND status = 'running'
                    """,
                    (now_value, now_value, job_id),
                )
                return "cancelled"
            if row["attempt_count"] >= row["max_attempts"]:
                connection.execute(
                    """
                    UPDATE guide_jobs
                    SET status = 'failed', stage = 'complete', completed_at = ?,
                        lease_expires_at = NULL, next_attempt_at = NULL,
                        error_code = ?, error_message_safe = ?, updated_at = ?
                    WHERE id = ? AND status = 'running'
                    """,
                    (
                        now_value,
                        error_code[:80],
                        error_message_safe[:500],
                        now_value,
                        job_id,
                    ),
                )
                return "failed"

            backoff_seconds = min(30 * (2 ** max(row["attempt_count"] - 1, 0)), 15 * 60)
            connection.execute(
                """
                UPDATE guide_jobs
                SET status = 'queued', stage = 'queued', progress = 0,
                    lease_expires_at = NULL, next_attempt_at = ?,
                    error_code = ?, error_message_safe = ?, updated_at = ?
                WHERE id = ? AND status = 'running' AND cancel_requested = 0
                """,
                (
                    (now + timedelta(seconds=backoff_seconds)).isoformat(),
                    error_code[:80],
                    error_message_safe[:500],
                    now_value,
                    job_id,
                ),
            )
        return "retrying"

    def request_job_cancellation(self, job_id: str, user_id: str) -> GuideJobRecord | None:
        now_value = datetime.now(UTC).isoformat()
        with self._connection() as connection:
            connection.execute(
                """
                UPDATE guide_jobs
                SET cancel_requested = 1,
                    status = CASE WHEN status = 'queued' THEN 'cancelled' ELSE status END,
                    stage = CASE WHEN status = 'queued' THEN 'complete' ELSE stage END,
                    completed_at = CASE WHEN status = 'queued' THEN ? ELSE completed_at END,
                    lease_expires_at = CASE
                        WHEN status = 'queued' THEN NULL ELSE lease_expires_at
                    END,
                    next_attempt_at = CASE
                        WHEN status = 'queued' THEN NULL ELSE next_attempt_at
                    END,
                    updated_at = ?
                WHERE id = ? AND user_id = ? AND status IN ('queued', 'running')
                """,
                (now_value, now_value, job_id, user_id),
            )
        return self.get_job_for_owner(job_id, user_id)

    def assets_for_owner(self, guide_id: str, user_id: str) -> list[GuideAssetRecord]:
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT guide_id, user_id, kind, local_path
                FROM guide_assets
                WHERE guide_id = ? AND user_id = ?
                """,
                (guide_id, user_id),
            ).fetchall()
        return [
            GuideAssetRecord(
                guide_id=row["guide_id"],
                user_id=row["user_id"],
                kind=row["kind"],
                local_path=Path(row["local_path"]),
            )
            for row in rows
        ]

    def all_assets_for_owner(self, user_id: str) -> list[GuideAssetRecord]:
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT ga.guide_id, g.user_id, ga.kind, ga.local_path
                FROM guide_assets AS ga
                JOIN guides AS g ON g.id = ga.guide_id
                WHERE g.user_id = ?
                """,
                (user_id,),
            ).fetchall()
        return [
            GuideAssetRecord(
                guide_id=row["guide_id"],
                user_id=row["user_id"],
                kind=row["kind"],
                local_path=Path(row["local_path"]),
            )
            for row in rows
        ]

    def is_private_path_referenced_by_another_owner(self, path: Path, user_id: str) -> bool:
        """Avoid deleting a shared/corrupt private path that belongs to another user.

        Normal generation writes unique request-scoped names. This guard makes
        cleanup safe even if a buggy migration or worker ever records the same
        path for two owners.
        """

        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT 1
                FROM (
                    SELECT g.user_id AS owner_id, ga.local_path AS path
                    FROM guide_assets AS ga
                    JOIN guides AS g ON g.id = ga.guide_id
                    UNION ALL
                    SELECT user_id AS owner_id, photo_path AS path
                    FROM guide_jobs
                ) AS private_paths
                WHERE path = ? AND owner_id != ?
                LIMIT 1
                """,
                (str(path), user_id),
            ).fetchone()
        return row is not None

    def all_job_photo_paths_for_owner(self, user_id: str) -> list[Path]:
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT photo_path FROM guide_jobs WHERE user_id = ?",
                (user_id,),
            ).fetchall()
        return [Path(row["photo_path"]) for row in rows]

    def purge_for_owner(self, user_id: str) -> int:
        """Hard-delete every guide row (including soft-deleted rows) for an owner."""

        with self._connection() as connection:
            result = connection.execute(
                "DELETE FROM guides WHERE user_id = ?",
                (user_id,),
            )
            connection.execute("DELETE FROM guide_jobs WHERE user_id = ?", (user_id,))
            connection.execute("DELETE FROM guide_drafts WHERE user_id = ?", (user_id,))
            connection.execute("DELETE FROM family_profiles WHERE user_id = ?", (user_id,))
            connection.execute("DELETE FROM entitlements WHERE user_id = ?", (user_id,))
            connection.execute("DELETE FROM payments WHERE user_id = ?", (user_id,))
        return result.rowcount

    def mark_deleted(self, guide_id: str, user_id: str) -> bool:
        now_value = datetime.now(UTC).isoformat()
        with self._connection() as connection:
            result = connection.execute(
                """
                UPDATE guides
                SET status = 'cancelled', deleted_at = ?, updated_at = ?
                WHERE id = ? AND user_id = ? AND deleted_at IS NULL
                """,
                (now_value, now_value, guide_id, user_id),
            )
        return result.rowcount == 1

    def expired_guides(self, *, now: datetime | None = None) -> list[GuideRecord]:
        current = (now or datetime.now(UTC)).isoformat()
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT * FROM guides
                WHERE deleted_at IS NULL AND expires_at IS NOT NULL AND expires_at <= ?
                """,
                (current,),
            ).fetchall()
        return [self._from_row(row) for row in rows]

    def healthcheck(self) -> bool:
        with self._connection() as connection:
            row = connection.execute("SELECT 1 AS healthy").fetchone()
        return bool(row and row["healthy"] == 1)

    def _one(self, query: str, parameters: tuple[object, ...]) -> GuideRecord | None:
        with self._connection() as connection:
            row = connection.execute(query, parameters).fetchone()
        return self._from_row(row) if row else None

    def _one_job(self, query: str, parameters: tuple[object, ...]) -> GuideJobRecord | None:
        with self._connection() as connection:
            row = connection.execute(query, parameters).fetchone()
        return self._job_from_row(row) if row else None

    def _one_draft(self, query: str, parameters: tuple[object, ...]) -> GuideDraftRecord | None:
        with self._connection() as connection:
            row = connection.execute(query, parameters).fetchone()
        return self._draft_from_row(row) if row else None

    def _one_payment(self, query: str, parameters: tuple[object, ...]) -> PaymentRecord | None:
        with self._connection() as connection:
            row = connection.execute(query, parameters).fetchone()
        return self._payment_from_row(row) if row else None

    @staticmethod
    def _from_row(row: sqlite3.Row) -> GuideRecord:
        try:
            metadata = json.loads(row["metadata_json"])
        except (json.JSONDecodeError, TypeError):
            metadata = {}
        if not isinstance(metadata, dict):
            metadata = {}
        return GuideRecord(
            id=row["id"],
            user_id=row["user_id"],
            title=row["title"],
            status=row["status"],
            pdf_filename=row["pdf_filename"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            expires_at=row["expires_at"],
            deleted_at=row["deleted_at"],
            cover_fallback_used=bool(row["cover_fallback_used"]),
            metadata=metadata,
        )

    @staticmethod
    def _job_from_row(row: sqlite3.Row) -> GuideJobRecord:
        try:
            request_snapshot = json.loads(row["request_snapshot_json"])
        except (json.JSONDecodeError, TypeError):
            request_snapshot = {}
        try:
            result = json.loads(row["result_json"]) if row["result_json"] else None
        except (json.JSONDecodeError, TypeError):
            result = None
        return GuideJobRecord(
            id=row["id"],
            user_id=row["user_id"],
            idempotency_key=row["idempotency_key"],
            status=row["status"],
            stage=row["stage"],
            progress=int(row["progress"]),
            request_snapshot=request_snapshot if isinstance(request_snapshot, dict) else {},
            photo_path=Path(row["photo_path"]),
            result=result if isinstance(result, dict) else None,
            error_code=row["error_code"],
            error_message_safe=row["error_message_safe"],
            attempt_count=int(row["attempt_count"]),
            max_attempts=int(row["max_attempts"]),
            cancel_requested=bool(row["cancel_requested"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            started_at=row["started_at"],
            completed_at=row["completed_at"],
            lease_expires_at=row["lease_expires_at"],
            next_attempt_at=row["next_attempt_at"],
        )

    @staticmethod
    def _draft_from_row(row: sqlite3.Row) -> GuideDraftRecord:
        try:
            payload = json.loads(row["payload_json"])
        except (json.JSONDecodeError, TypeError):
            payload = {}
        return GuideDraftRecord(
            id=row["id"],
            user_id=row["user_id"],
            title=row["title"],
            payload=payload if isinstance(payload, dict) else {},
            revision=int(row["revision"]),
            status=row["status"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            expires_at=row["expires_at"],
        )

    @staticmethod
    def _family_profile_from_row(row: sqlite3.Row) -> FamilyProfileRecord:
        try:
            members = json.loads(row["members_json"])
        except (json.JSONDecodeError, TypeError):
            members = {}
        if not isinstance(members, dict):
            members = {}

        def _member_list(key: str) -> list[dict[str, Any]]:
            values = members.get(key)
            if not isinstance(values, list):
                return []
            return [item for item in values if isinstance(item, dict)]

        return FamilyProfileRecord(
            user_id=row["user_id"],
            family_name=row["family_name"],
            parents=_member_list("parents"),
            children=_member_list("children"),
            revision=int(row["revision"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    @staticmethod
    def _payment_from_row(row: sqlite3.Row) -> PaymentRecord:
        return PaymentRecord(
            id=row["id"],
            user_id=row["user_id"],
            builder_session_id=row["builder_session_id"],
            provider=row["provider"],
            provider_preference_id=row["provider_preference_id"],
            provider_payment_id=row["provider_payment_id"],
            idempotency_key=row["idempotency_key"],
            status=row["status"],
            amount_minor=int(row["amount_minor"]),
            currency=row["currency"],
            product_code=row["product_code"],
            checkout_url=row["checkout_url"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            paid_at=row["paid_at"],
        )

    @staticmethod
    def _entitlement_from_row(row: sqlite3.Row) -> EntitlementRecord:
        return EntitlementRecord(
            id=row["id"],
            user_id=row["user_id"],
            builder_session_id=row["builder_session_id"],
            source_payment_id=row["source_payment_id"],
            status=row["status"],
            product_code=row["product_code"],
            created_at=row["created_at"],
            consumed_at=row["consumed_at"],
            revoked_at=row["revoked_at"],
        )


def _serialized_family_members(
    parents: list[dict[str, object]],
    children: list[dict[str, object]],
) -> str:
    members = {"parents": parents, "children": children}
    try:
        serialized = json.dumps(members, ensure_ascii=False, separators=(",", ":"))
    except (TypeError, ValueError) as error:
        raise ValueError("Family profile members must be JSON serializable.") from error
    if len(serialized.encode()) > 16 * 1024:
        raise ValueError("Family profile members exceed 16 KiB.")
    return serialized


def _serialized_draft_payload(payload: dict[str, object]) -> str:
    try:
        serialized = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    except (TypeError, ValueError) as error:
        raise ValueError("Guide draft payload must be JSON serializable.") from error
    if len(serialized.encode()) > 64 * 1024:
        raise ValueError("Guide draft payload exceeds 64 KiB.")
    return serialized


def guide_repository() -> GuideRepository:
    return GuideRepository()


def delete_private_asset(path: Path) -> bool:
    """Delete only files rooted below the active private runtime directory."""

    runtime_root = storage.RUNTIME_DIR.resolve()
    try:
        if path.is_symlink():
            return False
        resolved = path.resolve(strict=False)
        resolved.relative_to(runtime_root)
    except (OSError, ValueError):
        return False
    if not resolved.is_file() or resolved.is_symlink():
        return False
    resolved.unlink(missing_ok=True)
    return True


def delete_guide_and_assets(repository: GuideRepository, guide_id: str, user_id: str) -> bool:
    if repository.get_for_owner(guide_id, user_id) is None:
        return False
    assets = repository.assets_for_owner(guide_id, user_id)
    for asset in assets:
        if not repository.is_private_path_referenced_by_another_owner(asset.local_path, user_id):
            delete_private_asset(asset.local_path)
    return repository.mark_deleted(guide_id, user_id)


def delete_all_guides_for_owner(repository: GuideRepository, user_id: str) -> int:
    deleted = 0
    for record in repository.list_all_for_owner(user_id):
        deleted += int(delete_guide_and_assets(repository, record.id, user_id))
    return deleted


@dataclass(frozen=True)
class OwnerDataDeletionResult:
    guides_deleted: int
    private_files_deleted: int


def purge_all_data_for_owner(
    repository: GuideRepository,
    user_id: str,
) -> OwnerDataDeletionResult:
    """Remove an owner's private assets and hard-delete all persisted guide data.

    Asset paths are obtained through the guide-owner relationship rather than
    trusting the denormalized owner column on ``guide_assets``. Files outside
    the private runtime root are never removed.
    """

    private_files_deleted = 0
    seen_paths: set[Path] = set()
    private_paths = [
        *(asset.local_path for asset in repository.all_assets_for_owner(user_id)),
        *repository.all_job_photo_paths_for_owner(user_id),
    ]
    for path in private_paths:
        if path in seen_paths:
            continue
        seen_paths.add(path)
        if not repository.is_private_path_referenced_by_another_owner(path, user_id):
            private_files_deleted += int(delete_private_asset(path))
    guides_deleted = repository.purge_for_owner(user_id)
    return OwnerDataDeletionResult(
        guides_deleted=guides_deleted,
        private_files_deleted=private_files_deleted,
    )


def cleanup_expired_guides(
    repository: GuideRepository | None = None,
    *,
    now: datetime | None = None,
) -> int:
    active_repository = repository or guide_repository()
    deleted = 0
    for record in active_repository.expired_guides(now=now):
        deleted += int(delete_guide_and_assets(active_repository, record.id, record.user_id))
    return deleted


def cleanup_expired_drafts(
    repository: GuideRepository | None = None,
    *,
    now: datetime | None = None,
) -> int:
    return (repository or guide_repository()).delete_expired_drafts(now=now)
