import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from minerva_travel.request_control import (
    ConcurrencyLimitExceededError,
    IdempotencyConflictError,
    RateLimitExceededError,
    RatePolicy,
    RequestControlUnavailableError,
    SQLiteRequestControl,
    idempotency_key_required,
    request_control_fail_closed,
    request_controls_enabled,
    stable_request_hash,
)


class MutableClock:
    def __init__(self, value: float = 1_000.0) -> None:
        self.value = value

    def __call__(self) -> float:
        return self.value

    def advance(self, seconds: float) -> None:
        self.value += seconds


def _guard(tmp_path: Path, clock: MutableClock | None = None) -> SQLiteRequestControl:
    return SQLiteRequestControl(
        tmp_path / "request-control.sqlite3",
        fail_closed=True,
        clock=clock or MutableClock(),
    )


def test_rate_limit_enforces_user_and_ip_bursts_independently(tmp_path):
    guard = _guard(tmp_path)
    user_policy = RatePolicy("user-burst", user_limit=2, ip_limit=20, window_seconds=60)
    ip_policy = RatePolicy("ip-burst", user_limit=20, ip_limit=2, window_seconds=60)

    first = guard.consume_rate(user_policy, user_id="user-a", ip_address="203.0.113.10")
    second = guard.consume_rate(user_policy, user_id="user-a", ip_address="203.0.113.10")
    with pytest.raises(RateLimitExceededError) as user_blocked:
        guard.consume_rate(user_policy, user_id="user-a", ip_address="203.0.113.10")

    guard.consume_rate(ip_policy, user_id="user-a", ip_address="203.0.113.20")
    guard.consume_rate(ip_policy, user_id="user-b", ip_address="203.0.113.20")
    with pytest.raises(RateLimitExceededError) as ip_blocked:
        guard.consume_rate(ip_policy, user_id="user-c", ip_address="203.0.113.20")

    assert first.remaining_user == 1
    assert second.remaining_user == 0
    assert user_blocked.value.details["reason"] == "user_rate_limit"
    assert ip_blocked.value.details["reason"] == "ip_rate_limit"
    assert user_blocked.value.response_headers() == {"Retry-After": "20"}
    assert user_blocked.value.as_detail()["retry_after_seconds"] == 20


def test_rate_window_and_quota_reset_after_period(tmp_path):
    clock = MutableClock(1_000)
    guard = _guard(tmp_path, clock)
    policy = RatePolicy("reset", user_limit=1, ip_limit=1, window_seconds=10)

    guard.consume_rate(policy, user_id="user-a", ip_address="203.0.113.1")
    with pytest.raises(RateLimitExceededError):
        guard.consume_rate(policy, user_id="user-a", ip_address="203.0.113.1")
    guard.consume_quota(scope="guides", user_id="user-a", limit=1, period_seconds=100)
    with pytest.raises(RateLimitExceededError):
        guard.consume_quota(scope="guides", user_id="user-a", limit=1, period_seconds=100)

    clock.advance(100)

    assert (
        guard.consume_rate(
            policy,
            user_id="user-a",
            ip_address="203.0.113.1",
        ).remaining_user
        == 0
    )
    assert (
        guard.consume_quota(
            scope="guides",
            user_id="user-a",
            limit=1,
            period_seconds=100,
        ).remaining_user
        == 0
    )


def test_parallel_rate_consumption_is_atomic_across_connections(tmp_path):
    guard = _guard(tmp_path)
    policy = RatePolicy("atomic-burst", user_limit=5, ip_limit=100, window_seconds=60)

    def consume() -> str:
        try:
            guard.consume_rate(policy, user_id="same-user", ip_address="198.51.100.2")
        except RateLimitExceededError:
            return "blocked"
        return "allowed"

    with ThreadPoolExecutor(max_workers=20) as executor:
        outcomes = list(executor.map(lambda _index: consume(), range(20)))

    assert outcomes.count("allowed") == 5
    assert outcomes.count("blocked") == 15


def test_concurrency_limits_user_and_each_provider_globally(tmp_path):
    guard = _guard(tmp_path)
    first = guard.acquire_concurrency(
        scope="generate",
        user_id="user-a",
        provider="replicate",
        user_limit=1,
        provider_limit=2,
        lease_seconds=60,
    )
    with pytest.raises(ConcurrencyLimitExceededError) as user_blocked:
        guard.acquire_concurrency(
            scope="parse",
            user_id="user-a",
            provider="openai",
            user_limit=1,
            provider_limit=10,
            lease_seconds=60,
        )
    second = guard.acquire_concurrency(
        scope="generate",
        user_id="user-b",
        provider="replicate",
        user_limit=1,
        provider_limit=2,
        lease_seconds=60,
    )
    with pytest.raises(ConcurrencyLimitExceededError) as provider_blocked:
        guard.acquire_concurrency(
            scope="generate",
            user_id="user-c",
            provider="replicate",
            user_limit=1,
            provider_limit=2,
            lease_seconds=60,
        )

    assert user_blocked.value.details["reason"] == "user_concurrency"
    assert provider_blocked.value.details["reason"] == "provider_concurrency"
    first.release()
    replacement = guard.acquire_concurrency(
        scope="generate",
        user_id="user-c",
        provider="replicate",
        user_limit=1,
        provider_limit=2,
        lease_seconds=60,
    )
    second.release()
    replacement.release()


def test_expired_concurrency_lease_is_reclaimed_after_process_failure(tmp_path):
    clock = MutableClock()
    guard = _guard(tmp_path, clock)
    abandoned = guard.acquire_concurrency(
        scope="generate",
        user_id="user-a",
        provider="replicate",
        user_limit=1,
        provider_limit=1,
        lease_seconds=10,
    )
    with pytest.raises(ConcurrencyLimitExceededError):
        guard.acquire_concurrency(
            scope="generate",
            user_id="user-b",
            provider="replicate",
            user_limit=1,
            provider_limit=1,
            lease_seconds=10,
        )

    clock.advance(11)
    replacement = guard.acquire_concurrency(
        scope="generate",
        user_id="user-b",
        provider="replicate",
        user_limit=1,
        provider_limit=1,
        lease_seconds=10,
    )

    assert replacement.token != abandoned.token
    replacement.release()


def test_repeated_idempotency_key_reuses_operation_and_completed_response(tmp_path):
    guard = _guard(tmp_path)
    request_hash = stable_request_hash({"title": "Paris", "days": 3})
    first = guard.reserve_idempotency(
        namespace="guide-generation",
        user_id="user-a",
        key="request-key-123",
        request_hash=request_hash,
        required=True,
        pending_ttl_seconds=60,
    )
    assert first is not None
    second = guard.reserve_idempotency(
        namespace="guide-generation",
        user_id="user-a",
        key="request-key-123",
        request_hash=request_hash,
        required=True,
        pending_ttl_seconds=60,
    )
    assert second is not None
    guard.complete_idempotency(
        first,
        response_payload={"request_id": "guide-1", "download_url": "/download/guide-1.pdf"},
        response_status=200,
        ttl_seconds=3_600,
    )
    replay = guard.reserve_idempotency(
        namespace="guide-generation",
        user_id="user-a",
        key="request-key-123",
        request_hash=request_hash,
        required=True,
        pending_ttl_seconds=60,
    )

    assert second.state == "in_progress"
    assert second.operation_id == first.operation_id
    assert replay is not None
    assert replay.state == "completed"
    assert replay.operation_id == first.operation_id
    assert replay.response_payload == {
        "request_id": "guide-1",
        "download_url": "/download/guide-1.pdf",
    }
    persisted_bytes = (tmp_path / "request-control.sqlite3").read_bytes()
    assert b"request-key-123" not in persisted_bytes


def test_same_idempotency_key_with_different_payload_is_rejected(tmp_path):
    guard = _guard(tmp_path)
    guard.reserve_idempotency(
        namespace="guide-generation",
        user_id="user-a",
        key="request-key-123",
        request_hash=stable_request_hash({"title": "Paris"}),
        required=True,
        pending_ttl_seconds=60,
    )

    with pytest.raises(IdempotencyConflictError):
        guard.reserve_idempotency(
            namespace="guide-generation",
            user_id="user-a",
            key="request-key-123",
            request_hash=stable_request_hash({"title": "London"}),
            required=True,
            pending_ttl_seconds=60,
        )


def test_parallel_idempotency_reservation_creates_exactly_one_operation(tmp_path):
    guard = _guard(tmp_path)
    request_hash = stable_request_hash({"title": "Paris"})

    def reserve():
        return guard.reserve_idempotency(
            namespace="guide-generation",
            user_id="user-a",
            key="parallel-key-123",
            request_hash=request_hash,
            required=True,
            pending_ttl_seconds=60,
        )

    with ThreadPoolExecutor(max_workers=12) as executor:
        reservations = list(executor.map(lambda _index: reserve(), range(12)))

    assert all(reservation is not None for reservation in reservations)
    assert sum(reservation.state == "new" for reservation in reservations if reservation) == 1
    assert {reservation.operation_id for reservation in reservations if reservation} == {
        reservations[0].operation_id
    }


def test_expired_idempotency_reservation_can_be_started_again(tmp_path):
    clock = MutableClock()
    guard = _guard(tmp_path, clock)
    request_hash = stable_request_hash({"title": "Paris"})
    first = guard.reserve_idempotency(
        namespace="guide-generation",
        user_id="user-a",
        key="expiring-key-123",
        request_hash=request_hash,
        required=True,
        pending_ttl_seconds=10,
    )
    clock.advance(11)
    replacement = guard.reserve_idempotency(
        namespace="guide-generation",
        user_id="user-a",
        key="expiring-key-123",
        request_hash=request_hash,
        required=True,
        pending_ttl_seconds=10,
    )

    assert first is not None
    assert replacement is not None
    assert replacement.state == "new"
    assert replacement.operation_id != first.operation_id


def test_storage_failure_is_fail_closed_or_open_according_to_configuration(tmp_path):
    blocker = tmp_path / "not-a-directory"
    blocker.write_text("blocked", encoding="utf-8")
    database_path = blocker / "request-control.sqlite3"

    with pytest.raises(RequestControlUnavailableError):
        SQLiteRequestControl(database_path, fail_closed=True)

    fail_open = SQLiteRequestControl(database_path, fail_closed=False)
    rate = fail_open.consume_rate(
        RatePolicy("fallback", user_limit=1, ip_limit=1, window_seconds=60),
        user_id="user-a",
        ip_address="127.0.0.1",
    )
    lease = fail_open.acquire_concurrency(
        scope="fallback",
        user_id="user-a",
        provider="openai",
        user_limit=1,
        provider_limit=1,
        lease_seconds=60,
    )
    reservation = fail_open.reserve_idempotency(
        namespace="fallback",
        user_id="user-a",
        key="fallback-key-123",
        request_hash=stable_request_hash({"request": 1}),
        required=True,
        pending_ttl_seconds=60,
    )

    assert rate.bypassed is True
    assert lease.durable is False
    assert reservation is not None and reservation.durable is False


def test_production_defaults_enable_controls_and_fail_closed(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("REQUEST_CONTROL_ENABLED", raising=False)
    monkeypatch.delenv("REQUEST_CONTROL_FAIL_CLOSED", raising=False)
    monkeypatch.delenv("IDEMPOTENCY_KEY_REQUIRED", raising=False)

    assert request_controls_enabled() is True
    assert request_control_fail_closed() is True
    assert idempotency_key_required() is True

    monkeypatch.setenv("REQUEST_CONTROL_FAIL_CLOSED", "false")
    assert request_control_fail_closed() is False

    monkeypatch.setenv("REQUEST_CONTROL_ENABLED", "false")
    with pytest.raises(RuntimeError, match="cannot be disabled"):
        request_controls_enabled()
    monkeypatch.setenv("REQUEST_CONTROL_ENABLED", "true")
    monkeypatch.setenv("IDEMPOTENCY_KEY_REQUIRED", "false")
    with pytest.raises(RuntimeError, match="cannot be disabled"):
        idempotency_key_required()


def test_database_schema_keeps_subjects_as_hashes(tmp_path):
    guard = _guard(tmp_path)
    guard.consume_rate(
        RatePolicy("privacy", user_limit=2, ip_limit=2, window_seconds=60),
        user_id="person@example.com",
        ip_address="203.0.113.99",
    )

    with sqlite3.connect(tmp_path / "request-control.sqlite3") as connection:
        user_values = [
            row[0] for row in connection.execute("SELECT subject_hash FROM rate_windows")
        ]

    assert "person@example.com" not in user_values
    assert "203.0.113.99" not in user_values
    assert all(len(value) == 64 for value in user_values)
