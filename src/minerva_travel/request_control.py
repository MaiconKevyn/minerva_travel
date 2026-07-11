from __future__ import annotations

import hashlib
import json
import math
import os
import re
import sqlite3
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Literal
from uuid import uuid4

from minerva_travel import storage
from minerva_travel.config import app_environment

_SAFE_NAME = re.compile(r"[^a-z0-9_:-]+")


class RequestControlError(RuntimeError):
    status_code = 429
    code = "request_control_rejected"

    def __init__(
        self,
        message: str,
        *,
        retry_after: int | None = None,
        **details: object,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.retry_after = retry_after
        self.details = details

    def as_detail(self) -> dict[str, object]:
        detail: dict[str, object] = {
            "code": self.code,
            "message": self.message,
            **self.details,
        }
        if self.retry_after is not None:
            detail["retry_after_seconds"] = self.retry_after
        return detail

    def response_headers(self) -> dict[str, str]:
        if self.retry_after is None:
            return {}
        return {"Retry-After": str(self.retry_after)}


class RateLimitExceededError(RequestControlError):
    code = "rate_limit_exceeded"

    def __init__(self, *, scope: str, reason: str, retry_after: int) -> None:
        super().__init__(
            "Muitas solicitacoes. Aguarde antes de tentar novamente.",
            retry_after=retry_after,
            scope=scope,
            reason=reason,
        )


class ConcurrencyLimitExceededError(RequestControlError):
    code = "concurrency_limit_exceeded"

    def __init__(
        self,
        *,
        scope: str,
        provider: str,
        reason: str,
        retry_after: int,
    ) -> None:
        super().__init__(
            "Ja existem trabalhos demais em andamento. Tente novamente em instantes.",
            retry_after=retry_after,
            scope=scope,
            provider=provider,
            reason=reason,
        )


class RequestControlUnavailableError(RequestControlError):
    status_code = 503
    code = "request_control_unavailable"

    def __init__(self) -> None:
        super().__init__(
            "O controle de solicitacoes esta temporariamente indisponivel.",
            retry_after=5,
        )


class IdempotencyKeyRequiredError(RequestControlError):
    status_code = 428
    code = "idempotency_key_required"

    def __init__(self) -> None:
        super().__init__(
            "Envie o header Idempotency-Key para criar uma geracao.",
        )


class InvalidIdempotencyKeyError(RequestControlError):
    status_code = 400
    code = "invalid_idempotency_key"

    def __init__(self) -> None:
        super().__init__(
            "Idempotency-Key deve ter entre 8 e 200 caracteres ASCII visiveis.",
        )


class IdempotencyConflictError(RequestControlError):
    status_code = 409
    code = "idempotency_key_conflict"

    def __init__(self) -> None:
        super().__init__(
            "Esta Idempotency-Key ja foi usada com outro payload.",
        )


class IdempotencyInProgressError(RequestControlError):
    status_code = 409
    code = "idempotency_in_progress"

    def __init__(self, *, operation_id: str, retry_after: int) -> None:
        super().__init__(
            "A solicitacao com esta Idempotency-Key ainda esta em andamento.",
            retry_after=retry_after,
            operation_id=operation_id,
        )


class IdempotencyOwnershipError(RequestControlError):
    status_code = 409
    code = "idempotency_reservation_lost"

    def __init__(self) -> None:
        super().__init__(
            "A reserva idempotente expirou ou pertence a outra operacao.",
        )


@dataclass(frozen=True)
class RatePolicy:
    scope: str
    user_limit: int | None
    ip_limit: int | None
    window_seconds: int

    def __post_init__(self) -> None:
        if self.window_seconds <= 0:
            raise ValueError("window_seconds must be positive")
        if self.user_limit is not None and self.user_limit <= 0:
            raise ValueError("user_limit must be positive")
        if self.ip_limit is not None and self.ip_limit <= 0:
            raise ValueError("ip_limit must be positive")


@dataclass(frozen=True)
class RateLimitResult:
    scope: str
    reset_at: int
    remaining_user: int | None
    remaining_ip: int | None
    bypassed: bool = False


@dataclass(frozen=True)
class IdempotencyReservation:
    state: Literal["new", "in_progress", "completed"]
    operation_id: str
    request_hash: str
    response_payload: dict[str, object] | None = None
    response_status: int | None = None
    retry_after: int | None = None
    durable: bool = True
    _namespace: str = field(default="", repr=False)
    _user_hash: str = field(default="", repr=False)
    _key_hash: str = field(default="", repr=False)


class ConcurrencyLease:
    def __init__(
        self,
        guard: SQLiteRequestControl | None,
        *,
        token: str,
        expires_at: float,
        durable: bool,
    ) -> None:
        self.guard = guard
        self.token = token
        self.expires_at = expires_at
        self.durable = durable
        self.released = False

    def release(self) -> None:
        if self.released:
            return
        self.released = True
        if self.guard is not None and self.durable:
            self.guard._release_lease(self.token)

    def __enter__(self) -> ConcurrencyLease:
        return self

    def __exit__(self, *_args: object) -> None:
        self.release()


class SQLiteRequestControl:
    """Atomic request controls shared by processes through SQLite."""

    def __init__(
        self,
        database_path: Path,
        *,
        fail_closed: bool,
        clock: Callable[[], float] = time.time,
        sqlite_timeout_seconds: float = 5.0,
    ) -> None:
        self.database_path = database_path
        self.fail_closed = fail_closed
        self.clock = clock
        self.sqlite_timeout_seconds = sqlite_timeout_seconds
        self._available = False
        try:
            self.database_path.parent.mkdir(parents=True, exist_ok=True)
            self._initialize()
            self._available = True
        except (OSError, sqlite3.Error) as error:
            if self.fail_closed:
                raise RequestControlUnavailableError() from error

    def consume_rate(
        self,
        policy: RatePolicy,
        *,
        user_id: str,
        ip_address: str,
    ) -> RateLimitResult:
        now = self.clock()
        reset_at = (int(now) // policy.window_seconds + 1) * policy.window_seconds
        if not self._available:
            return RateLimitResult(
                scope=policy.scope,
                reset_at=reset_at,
                remaining_user=None,
                remaining_ip=None,
                bypassed=True,
            )

        window_start = reset_at - policy.window_seconds
        subjects: list[tuple[str, str, int]] = []
        if policy.user_limit is not None:
            subjects.append(("user", _subject_hash("user", user_id), policy.user_limit))
        if policy.ip_limit is not None:
            subjects.append(("ip", _subject_hash("ip", ip_address), policy.ip_limit))

        try:
            blocked_reason: str | None = None
            counts: dict[str, int] = {}
            with self._transaction() as connection:
                connection.execute("DELETE FROM rate_windows WHERE reset_at <= ?", (now,))
                for subject_type, subject_hash, limit in subjects:
                    row = connection.execute(
                        """
                        SELECT count FROM rate_windows
                        WHERE scope = ? AND subject_type = ? AND subject_hash = ?
                          AND window_start = ?
                        """,
                        (policy.scope, subject_type, subject_hash, window_start),
                    ).fetchone()
                    current_count = int(row["count"]) if row else 0
                    counts[subject_type] = current_count
                    if current_count >= limit and blocked_reason is None:
                        blocked_reason = f"{subject_type}_rate_limit"

                if blocked_reason is None:
                    for subject_type, subject_hash, _limit in subjects:
                        connection.execute(
                            """
                            INSERT INTO rate_windows (
                                scope, subject_type, subject_hash,
                                window_start, reset_at, count
                            ) VALUES (?, ?, ?, ?, ?, 1)
                            ON CONFLICT(scope, subject_type, subject_hash, window_start)
                            DO UPDATE SET count = count + 1
                            """,
                            (
                                policy.scope,
                                subject_type,
                                subject_hash,
                                window_start,
                                reset_at,
                            ),
                        )
                        counts[subject_type] = counts.get(subject_type, 0) + 1
                    self._record_event(
                        connection,
                        kind="rate",
                        scope=policy.scope,
                        subject_hash=_subject_hash("user", user_id),
                        outcome="allowed",
                        reason="consumed",
                        created_at=now,
                    )
                else:
                    self._record_event(
                        connection,
                        kind="rate",
                        scope=policy.scope,
                        subject_hash=_subject_hash("user", user_id),
                        outcome="blocked",
                        reason=blocked_reason,
                        created_at=now,
                    )
        except (OSError, sqlite3.Error) as error:
            return self._rate_store_failure(policy.scope, reset_at, error)

        if blocked_reason is not None:
            raise RateLimitExceededError(
                scope=policy.scope,
                reason=blocked_reason,
                retry_after=max(1, math.ceil(reset_at - now)),
            )
        return RateLimitResult(
            scope=policy.scope,
            reset_at=reset_at,
            remaining_user=(
                policy.user_limit - counts.get("user", 0) if policy.user_limit is not None else None
            ),
            remaining_ip=(
                policy.ip_limit - counts.get("ip", 0) if policy.ip_limit is not None else None
            ),
        )

    def consume_quota(
        self,
        *,
        scope: str,
        user_id: str,
        limit: int,
        period_seconds: int,
    ) -> RateLimitResult:
        return self.consume_rate(
            RatePolicy(
                scope=f"quota:{scope}",
                user_limit=limit,
                ip_limit=None,
                window_seconds=period_seconds,
            ),
            user_id=user_id,
            ip_address="quota-not-applicable",
        )

    def acquire_concurrency(
        self,
        *,
        scope: str,
        user_id: str,
        provider: str,
        user_limit: int,
        provider_limit: int,
        lease_seconds: int,
    ) -> ConcurrencyLease:
        if min(user_limit, provider_limit, lease_seconds) <= 0:
            raise ValueError("Concurrency limits and lease must be positive")
        now = self.clock()
        expires_at = now + lease_seconds
        token = uuid4().hex
        if not self._available:
            return ConcurrencyLease(
                None,
                token=token,
                expires_at=expires_at,
                durable=False,
            )

        provider_name = _normalized_name(provider, fallback="unknown")
        user_hash = _subject_hash("user", user_id)
        try:
            blocked_reason: str | None = None
            retry_at = expires_at
            with self._transaction() as connection:
                connection.execute("DELETE FROM concurrency_leases WHERE expires_at <= ?", (now,))
                user_row = connection.execute(
                    """
                    SELECT COUNT(*) AS total, MIN(expires_at) AS retry_at
                    FROM concurrency_leases WHERE user_hash = ?
                    """,
                    (user_hash,),
                ).fetchone()
                provider_row = connection.execute(
                    """
                    SELECT COUNT(*) AS total, MIN(expires_at) AS retry_at
                    FROM concurrency_leases WHERE provider = ?
                    """,
                    (provider_name,),
                ).fetchone()
                if int(user_row["total"]) >= user_limit:
                    blocked_reason = "user_concurrency"
                    retry_at = float(user_row["retry_at"] or expires_at)
                elif int(provider_row["total"]) >= provider_limit:
                    blocked_reason = "provider_concurrency"
                    retry_at = float(provider_row["retry_at"] or expires_at)

                if blocked_reason is None:
                    connection.execute(
                        """
                        INSERT INTO concurrency_leases (
                            token, scope, user_hash, provider, created_at, expires_at
                        ) VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (token, scope, user_hash, provider_name, now, expires_at),
                    )
                    self._record_event(
                        connection,
                        kind="concurrency",
                        scope=scope,
                        subject_hash=user_hash,
                        outcome="allowed",
                        reason=provider_name,
                        created_at=now,
                    )
                else:
                    self._record_event(
                        connection,
                        kind="concurrency",
                        scope=scope,
                        subject_hash=user_hash,
                        outcome="blocked",
                        reason=blocked_reason,
                        created_at=now,
                    )
        except (OSError, sqlite3.Error) as error:
            if self.fail_closed:
                raise RequestControlUnavailableError() from error
            self._available = False
            return ConcurrencyLease(
                None,
                token=token,
                expires_at=expires_at,
                durable=False,
            )

        if blocked_reason is not None:
            raise ConcurrencyLimitExceededError(
                scope=scope,
                provider=provider_name,
                reason=blocked_reason,
                retry_after=max(1, math.ceil(retry_at - now)),
            )
        return ConcurrencyLease(
            self,
            token=token,
            expires_at=expires_at,
            durable=True,
        )

    def reserve_idempotency(
        self,
        *,
        namespace: str,
        user_id: str,
        key: str | None,
        request_hash: str,
        required: bool,
        pending_ttl_seconds: int,
    ) -> IdempotencyReservation | None:
        normalized_key = _validated_idempotency_key(key, required=required)
        if normalized_key is None:
            return None
        if pending_ttl_seconds <= 0:
            raise ValueError("pending_ttl_seconds must be positive")

        namespace_value = _normalized_name(namespace, fallback="operation")
        user_hash = _subject_hash("user", user_id)
        key_hash = hashlib.sha256(normalized_key.encode("utf-8")).hexdigest()
        operation_id = uuid4().hex
        now = self.clock()
        expires_at = now + pending_ttl_seconds
        if not self._available:
            return IdempotencyReservation(
                state="new",
                operation_id=operation_id,
                request_hash=request_hash,
                durable=False,
                _namespace=namespace_value,
                _user_hash=user_hash,
                _key_hash=key_hash,
            )

        try:
            conflict = False
            reservation: IdempotencyReservation | None = None
            with self._transaction() as connection:
                connection.execute("DELETE FROM idempotency_records WHERE expires_at <= ?", (now,))
                row = connection.execute(
                    """
                    SELECT request_hash, operation_id, status, response_json,
                           response_status, expires_at
                    FROM idempotency_records
                    WHERE namespace = ? AND user_hash = ? AND key_hash = ?
                    """,
                    (namespace_value, user_hash, key_hash),
                ).fetchone()
                if row is not None and row["request_hash"] != request_hash:
                    conflict = True
                    self._record_event(
                        connection,
                        kind="idempotency",
                        scope=namespace_value,
                        subject_hash=user_hash,
                        outcome="blocked",
                        reason="payload_conflict",
                        created_at=now,
                    )
                elif row is not None and row["status"] == "completed":
                    payload = json.loads(row["response_json"] or "{}")
                    reservation = IdempotencyReservation(
                        state="completed",
                        operation_id=row["operation_id"],
                        request_hash=request_hash,
                        response_payload=payload,
                        response_status=int(row["response_status"] or 200),
                        durable=True,
                        _namespace=namespace_value,
                        _user_hash=user_hash,
                        _key_hash=key_hash,
                    )
                elif row is not None:
                    reservation = IdempotencyReservation(
                        state="in_progress",
                        operation_id=row["operation_id"],
                        request_hash=request_hash,
                        retry_after=max(1, math.ceil(float(row["expires_at"]) - now)),
                        durable=True,
                        _namespace=namespace_value,
                        _user_hash=user_hash,
                        _key_hash=key_hash,
                    )
                else:
                    connection.execute(
                        """
                        INSERT INTO idempotency_records (
                            namespace, user_hash, key_hash, request_hash,
                            operation_id, status, created_at, updated_at, expires_at
                        ) VALUES (?, ?, ?, ?, ?, 'pending', ?, ?, ?)
                        """,
                        (
                            namespace_value,
                            user_hash,
                            key_hash,
                            request_hash,
                            operation_id,
                            now,
                            now,
                            expires_at,
                        ),
                    )
                    reservation = IdempotencyReservation(
                        state="new",
                        operation_id=operation_id,
                        request_hash=request_hash,
                        durable=True,
                        _namespace=namespace_value,
                        _user_hash=user_hash,
                        _key_hash=key_hash,
                    )
                    self._record_event(
                        connection,
                        kind="idempotency",
                        scope=namespace_value,
                        subject_hash=user_hash,
                        outcome="allowed",
                        reason="reserved",
                        created_at=now,
                    )
        except (OSError, sqlite3.Error, json.JSONDecodeError) as error:
            if self.fail_closed:
                raise RequestControlUnavailableError() from error
            self._available = False
            return IdempotencyReservation(
                state="new",
                operation_id=operation_id,
                request_hash=request_hash,
                durable=False,
                _namespace=namespace_value,
                _user_hash=user_hash,
                _key_hash=key_hash,
            )

        if conflict:
            raise IdempotencyConflictError()
        if reservation is None:  # pragma: no cover - defensive transaction invariant
            raise RequestControlUnavailableError()
        return reservation

    def complete_idempotency(
        self,
        reservation: IdempotencyReservation,
        *,
        response_payload: dict[str, object],
        response_status: int,
        ttl_seconds: int,
    ) -> None:
        if not reservation.durable:
            return
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        now = self.clock()
        try:
            with self._transaction() as connection:
                cursor = connection.execute(
                    """
                    UPDATE idempotency_records
                    SET status = 'completed', response_json = ?, response_status = ?,
                        updated_at = ?, expires_at = ?
                    WHERE namespace = ? AND user_hash = ? AND key_hash = ?
                      AND operation_id = ? AND status = 'pending'
                    """,
                    (
                        json.dumps(
                            response_payload,
                            ensure_ascii=False,
                            sort_keys=True,
                            separators=(",", ":"),
                        ),
                        response_status,
                        now,
                        now + ttl_seconds,
                        reservation._namespace,
                        reservation._user_hash,
                        reservation._key_hash,
                        reservation.operation_id,
                    ),
                )
                if cursor.rowcount != 1:
                    raise IdempotencyOwnershipError()
                self._record_event(
                    connection,
                    kind="idempotency",
                    scope=reservation._namespace,
                    subject_hash=reservation._user_hash,
                    outcome="allowed",
                    reason="completed",
                    created_at=now,
                )
        except RequestControlError:
            raise
        except (OSError, sqlite3.Error, TypeError, ValueError) as error:
            if self.fail_closed:
                raise RequestControlUnavailableError() from error
            self._available = False

    def abandon_idempotency(self, reservation: IdempotencyReservation) -> None:
        if reservation.state != "new" or not reservation.durable:
            return
        try:
            with self._transaction() as connection:
                connection.execute(
                    """
                    DELETE FROM idempotency_records
                    WHERE namespace = ? AND user_hash = ? AND key_hash = ?
                      AND operation_id = ? AND status = 'pending'
                    """,
                    (
                        reservation._namespace,
                        reservation._user_hash,
                        reservation._key_hash,
                        reservation.operation_id,
                    ),
                )
        except (OSError, sqlite3.Error) as error:
            if self.fail_closed:
                raise RequestControlUnavailableError() from error
            self._available = False

    def audit_events(self, *, scope: str | None = None) -> list[dict[str, object]]:
        if not self._available:
            return []
        try:
            with self._connection() as connection:
                if scope is None:
                    rows = connection.execute(
                        "SELECT * FROM request_control_events ORDER BY id"
                    ).fetchall()
                else:
                    rows = connection.execute(
                        "SELECT * FROM request_control_events WHERE scope = ? ORDER BY id",
                        (scope,),
                    ).fetchall()
            return [dict(row) for row in rows]
        except (OSError, sqlite3.Error) as error:
            if self.fail_closed:
                raise RequestControlUnavailableError() from error
            self._available = False
            return []

    def _rate_store_failure(
        self,
        scope: str,
        reset_at: int,
        error: Exception,
    ) -> RateLimitResult:
        if self.fail_closed:
            raise RequestControlUnavailableError() from error
        self._available = False
        return RateLimitResult(
            scope=scope,
            reset_at=reset_at,
            remaining_user=None,
            remaining_ip=None,
            bypassed=True,
        )

    def _release_lease(self, token: str) -> None:
        if not self._available:
            return
        try:
            with self._transaction() as connection:
                connection.execute("DELETE FROM concurrency_leases WHERE token = ?", (token,))
        except (OSError, sqlite3.Error) as error:
            if self.fail_closed:
                raise RequestControlUnavailableError() from error
            self._available = False

    def _initialize(self) -> None:
        with self._connection() as connection:
            connection.executescript(
                """
                PRAGMA journal_mode = WAL;
                CREATE TABLE IF NOT EXISTS rate_windows (
                    scope TEXT NOT NULL,
                    subject_type TEXT NOT NULL,
                    subject_hash TEXT NOT NULL,
                    window_start INTEGER NOT NULL,
                    reset_at INTEGER NOT NULL,
                    count INTEGER NOT NULL,
                    PRIMARY KEY (scope, subject_type, subject_hash, window_start)
                );
                CREATE INDEX IF NOT EXISTS rate_windows_reset_idx
                    ON rate_windows(reset_at);

                CREATE TABLE IF NOT EXISTS concurrency_leases (
                    token TEXT PRIMARY KEY,
                    scope TEXT NOT NULL,
                    user_hash TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    expires_at REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS concurrency_user_idx
                    ON concurrency_leases(user_hash, expires_at);
                CREATE INDEX IF NOT EXISTS concurrency_provider_idx
                    ON concurrency_leases(provider, expires_at);

                CREATE TABLE IF NOT EXISTS idempotency_records (
                    namespace TEXT NOT NULL,
                    user_hash TEXT NOT NULL,
                    key_hash TEXT NOT NULL,
                    request_hash TEXT NOT NULL,
                    operation_id TEXT NOT NULL,
                    status TEXT NOT NULL CHECK (status IN ('pending', 'completed')),
                    response_json TEXT,
                    response_status INTEGER,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    expires_at REAL NOT NULL,
                    PRIMARY KEY (namespace, user_hash, key_hash)
                );
                CREATE INDEX IF NOT EXISTS idempotency_expiry_idx
                    ON idempotency_records(expires_at);

                CREATE TABLE IF NOT EXISTS request_control_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    kind TEXT NOT NULL,
                    scope TEXT NOT NULL,
                    subject_hash TEXT NOT NULL,
                    outcome TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    created_at REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS request_control_events_scope_idx
                    ON request_control_events(scope, created_at);
                """
            )

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(
            self.database_path,
            timeout=self.sqlite_timeout_seconds,
            isolation_level=None,
            check_same_thread=False,
        )
        connection.row_factory = sqlite3.Row
        connection.execute(f"PRAGMA busy_timeout = {int(self.sqlite_timeout_seconds * 1000)}")
        try:
            yield connection
        finally:
            connection.close()

    @contextmanager
    def _transaction(self) -> Iterator[sqlite3.Connection]:
        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                yield connection
                connection.commit()
            except Exception:
                connection.rollback()
                raise

    @staticmethod
    def _record_event(
        connection: sqlite3.Connection,
        *,
        kind: str,
        scope: str,
        subject_hash: str,
        outcome: str,
        reason: str,
        created_at: float,
    ) -> None:
        connection.execute(
            """
            INSERT INTO request_control_events (
                kind, scope, subject_hash, outcome, reason, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (kind, scope, subject_hash, outcome, reason, created_at),
        )


def request_controls_enabled() -> bool:
    production = app_environment() == "production"
    enabled = _environment_bool(
        "REQUEST_CONTROL_ENABLED",
        default=production,
    )
    if production and not enabled:
        raise RuntimeError("REQUEST_CONTROL_ENABLED cannot be disabled in production.")
    return enabled


def request_control_fail_closed() -> bool:
    return _environment_bool(
        "REQUEST_CONTROL_FAIL_CLOSED",
        default=app_environment() == "production",
    )


def idempotency_key_required() -> bool:
    production = app_environment() == "production"
    required = _environment_bool(
        "IDEMPOTENCY_KEY_REQUIRED",
        default=production,
    )
    if production and not required:
        raise RuntimeError("IDEMPOTENCY_KEY_REQUIRED cannot be disabled in production.")
    return required


def configured_rate_policy(
    scope: str,
    *,
    default_user_limit: int,
    default_ip_limit: int,
    default_window_seconds: int = 60,
) -> RatePolicy:
    prefix = _environment_prefix(scope)
    return RatePolicy(
        scope=scope,
        user_limit=_positive_environment_integer(
            f"RATE_LIMIT_{prefix}_USER",
            default_user_limit,
        ),
        ip_limit=_positive_environment_integer(
            f"RATE_LIMIT_{prefix}_IP",
            default_ip_limit,
        ),
        window_seconds=_positive_environment_integer(
            f"RATE_LIMIT_{prefix}_WINDOW_SECONDS",
            default_window_seconds,
        ),
    )


def configured_user_concurrency_limit(scope: str, *, default: int = 2) -> int:
    prefix = _environment_prefix(scope)
    scoped_name = f"CONCURRENCY_{prefix}_USER_LIMIT"
    if os.getenv(scoped_name) is not None:
        return _positive_environment_integer(scoped_name, default)
    return _positive_environment_integer("CONCURRENCY_USER_LIMIT", default)


def configured_provider_concurrency_limit(provider: str) -> int:
    provider_name = _environment_prefix(provider)
    defaults = {
        "REPLICATE": 2,
        "OPENAI": 4,
        "GOOGLE": 8,
        "PLACEHOLDER": 8,
    }
    return _positive_environment_integer(
        f"CONCURRENCY_PROVIDER_{provider_name}_LIMIT",
        defaults.get(provider_name, 4),
    )


def configured_user_quota(scope: str, *, default: int) -> int:
    return _positive_environment_integer(
        f"QUOTA_{_environment_prefix(scope)}_USER",
        default,
    )


def configured_quota_period_seconds(scope: str, *, default: int) -> int:
    return _positive_environment_integer(
        f"QUOTA_{_environment_prefix(scope)}_PERIOD_SECONDS",
        default,
    )


def configured_concurrency_lease_seconds() -> int:
    return _positive_environment_integer("CONCURRENCY_LEASE_SECONDS", 15 * 60)


def configured_idempotency_pending_ttl_seconds() -> int:
    return _positive_environment_integer("IDEMPOTENCY_PENDING_TTL_SECONDS", 15 * 60)


def configured_idempotency_ttl_seconds() -> int:
    return _positive_environment_integer("IDEMPOTENCY_TTL_SECONDS", 24 * 60 * 60)


def get_request_control() -> SQLiteRequestControl:
    configured_path = os.getenv("REQUEST_CONTROL_DB_PATH")
    database_path = (
        Path(configured_path).expanduser()
        if configured_path
        else storage.RUNTIME_DIR / "request-control.sqlite3"
    )
    return _cached_request_control(str(database_path.resolve()), request_control_fail_closed())


@lru_cache(maxsize=8)
def _cached_request_control(
    database_path: str,
    fail_closed: bool,
) -> SQLiteRequestControl:
    return SQLiteRequestControl(Path(database_path), fail_closed=fail_closed)


def reset_request_control_cache() -> None:
    _cached_request_control.cache_clear()


def stable_request_hash(payload: object) -> str:
    serialized = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _validated_idempotency_key(key: str | None, *, required: bool) -> str | None:
    if key is None or not key.strip():
        if required:
            raise IdempotencyKeyRequiredError()
        return None
    normalized = key.strip()
    if (
        len(normalized) < 8
        or len(normalized) > 200
        or any(ord(character) < 33 or ord(character) > 126 for character in normalized)
    ):
        raise InvalidIdempotencyKeyError()
    return normalized


def _subject_hash(subject_type: str, value: str) -> str:
    return hashlib.sha256(f"{subject_type}\0{value}".encode()).hexdigest()


def _normalized_name(value: str, *, fallback: str) -> str:
    normalized = _SAFE_NAME.sub("_", value.strip().lower()).strip("_:")
    return normalized[:80] or fallback


def _environment_prefix(value: str) -> str:
    return _normalized_name(value, fallback="DEFAULT").replace(":", "_").upper()


def _environment_bool(name: str, *, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() not in {"0", "false", "no", "off"}


def _positive_environment_integer(name: str, default: int) -> int:
    raw_value = os.getenv(name, str(default))
    try:
        value = int(raw_value)
    except ValueError:
        return default
    return value if value > 0 else default
