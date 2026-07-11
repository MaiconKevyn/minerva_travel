import json
from io import StringIO

from minerva_travel.observability import (
    LOGGER,
    emit_event,
    metrics_snapshot,
    reset_metrics_for_tests,
    user_pseudonym,
)


def test_structured_events_pseudonymize_users_and_only_include_safe_fields():
    reset_metrics_for_tests()
    stream = StringIO()
    handler = LOGGER.handlers[0]
    original_stream = handler.stream
    handler.setStream(stream)

    try:
        emit_event(
            "guide_job_finished",
            request_id="request-123",
            job_id="job-123",
            user_id="family@example.com",
            stage="complete",
            outcome="succeeded",
            duration_ms=123,
            pdf_bytes=456,
        )
    finally:
        handler.setStream(original_stream)

    log_line = stream.getvalue().strip().splitlines()[-1]
    payload = json.loads(log_line)
    assert payload["user_hash"] == user_pseudonym("family@example.com")
    assert "family@example.com" not in log_line
    assert payload["duration_ms"] == 123
    assert metrics_snapshot() == {
        "events.guide_job_finished": 1,
        "outcomes.succeeded": 1,
    }
