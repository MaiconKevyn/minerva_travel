from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from minerva_travel.app import app
from minerva_travel.privacy import (
    CURRENT_PRIVACY_CONSENT_VERSION,
    PrivacyConsentError,
    validate_photo_processing_consent,
)

NOW = datetime(2026, 7, 9, 18, 30, tzinfo=UTC)


def test_consent_is_required_before_processing_photo():
    with pytest.raises(PrivacyConsentError) as raised:
        validate_photo_processing_consent(
            granted=False,
            version=None,
            granted_at=None,
            required=True,
            now=NOW,
        )

    assert raised.value.code == "photo_processing_consent_required"


def test_valid_versioned_consent_is_normalized_to_utc():
    consent = validate_photo_processing_consent(
        granted=True,
        version=CURRENT_PRIVACY_CONSENT_VERSION,
        granted_at="2026-07-09T15:30:00-03:00",
        required=True,
        now=NOW,
    )

    assert consent is not None
    assert consent.metadata() == {
        "version": CURRENT_PRIVACY_CONSENT_VERSION,
        "granted_at": "2026-07-09T18:30:00+00:00",
    }


@pytest.mark.parametrize(
    ("version", "granted_at", "expected_code"),
    [
        ("old-version", NOW.isoformat(), "privacy_consent_version_invalid"),
        (
            CURRENT_PRIVACY_CONSENT_VERSION,
            "not-a-date",
            "privacy_consent_timestamp_invalid",
        ),
        (
            CURRENT_PRIVACY_CONSENT_VERSION,
            "2026-07-09T18:30:00",
            "privacy_consent_timestamp_invalid",
        ),
        (
            CURRENT_PRIVACY_CONSENT_VERSION,
            (NOW + timedelta(hours=1)).isoformat(),
            "privacy_consent_timestamp_future",
        ),
        (
            CURRENT_PRIVACY_CONSENT_VERSION,
            (NOW - timedelta(days=366)).isoformat(),
            "privacy_consent_timestamp_expired",
        ),
    ],
)
def test_invalid_or_stale_consent_is_rejected(version, granted_at, expected_code):
    with pytest.raises(PrivacyConsentError) as raised:
        validate_photo_processing_consent(
            granted=True,
            version=version,
            granted_at=granted_at,
            required=True,
            now=NOW,
        )

    assert raised.value.code == expected_code


def test_optional_test_environment_can_skip_consent():
    assert (
        validate_photo_processing_consent(
            granted=False,
            version=None,
            granted_at=None,
            required=False,
            now=NOW,
        )
        is None
    )


def test_generation_rejects_missing_consent_before_persisting_upload(monkeypatch):
    upload_started = False

    async def fail_if_upload_starts(*_args, **_kwargs):
        nonlocal upload_started
        upload_started = True
        raise AssertionError("Upload persistence must happen after consent validation.")

    monkeypatch.setenv("PHOTO_PROCESSING_CONSENT_REQUIRED", "true")
    monkeypatch.setattr("minerva_travel.storage.save_upload", fail_if_upload_starts)
    client = TestClient(app)

    response = client.post(
        "/api/generate",
        data={
            "title": "Guia de teste",
            "children_names": "Lia",
            "parents_names": "Alex",
            "year": "2026",
            "selected_landmarks": "paris:eiffel-tower",
        },
        files={
            "family_photo": (
                "family.png",
                b"not-read-before-consent",
                "image/png",
            )
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "photo_processing_consent_required"
    assert upload_started is False
