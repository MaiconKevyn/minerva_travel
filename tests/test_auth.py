import asyncio
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException
from fastapi.testclient import TestClient

from minerva_travel.app import app
from minerva_travel.auth import decode_verified_token, get_current_user
from minerva_travel.config import auth_required

ISSUER = "https://project.supabase.co/auth/v1"
AUDIENCE = "authenticated"


def _key_pair():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return private_key, private_key.public_key()


def _token(private_key, **overrides):
    now = datetime.now(UTC)
    payload = {
        "iss": ISSUER,
        "aud": AUDIENCE,
        "sub": "user-123",
        "role": "authenticated",
        "email": "family@example.com",
        "iat": now,
        "exp": now + timedelta(minutes=5),
        **overrides,
    }
    return jwt.encode(payload, private_key, algorithm="RS256", headers={"kid": "test-key"})


def test_decode_verified_token_validates_required_supabase_claims():
    private_key, public_key = _key_pair()

    claims = decode_verified_token(
        _token(private_key),
        public_key,
        algorithm="RS256",
        audience=AUDIENCE,
        issuer=ISSUER,
    )

    assert claims["sub"] == "user-123"
    assert claims["role"] == "authenticated"


@pytest.mark.parametrize(
    "overrides",
    [
        {"exp": datetime.now(UTC) - timedelta(seconds=1)},
        {"iss": "https://attacker.invalid/auth/v1"},
        {"aud": "another-project"},
    ],
)
def test_decode_verified_token_rejects_expired_or_wrong_project_tokens(overrides):
    private_key, public_key = _key_pair()

    with pytest.raises(HTTPException) as error:
        decode_verified_token(
            _token(private_key, **overrides),
            public_key,
            algorithm="RS256",
            audience=AUDIENCE,
            issuer=ISSUER,
        )

    assert error.value.status_code == 401


def test_decode_verified_token_rejects_algorithm_downgrade():
    with pytest.raises(HTTPException) as error:
        decode_verified_token(
            "malformed",
            b"shared-secret",
            algorithm="HS256",
            audience=AUDIENCE,
            issuer=ISSUER,
        )

    assert error.value.status_code == 401


def test_decode_verified_token_rejects_tampered_signature():
    private_key, _public_key = _key_pair()
    _other_private_key, other_public_key = _key_pair()

    with pytest.raises(HTTPException) as error:
        decode_verified_token(
            _token(private_key),
            other_public_key,
            algorithm="RS256",
            audience=AUDIENCE,
            issuer=ISSUER,
        )

    assert error.value.status_code == 401


def test_auth_dependency_has_explicit_test_only_bypass(monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("AUTH_REQUIRED", "false")

    user = asyncio.run(get_current_user(None))

    assert user.id == "development-user"
    assert user.role == "authenticated"


def test_auth_cannot_be_disabled_in_production(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("AUTH_REQUIRED", "false")

    with pytest.raises(RuntimeError):
        auth_required()


def test_expensive_endpoint_rejects_missing_token_before_provider(monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("AUTH_REQUIRED", "true")
    provider_called = False

    def forbidden_provider(*_args, **_kwargs):
        nonlocal provider_called
        provider_called = True
        raise AssertionError("Provider must not run before authentication.")

    monkeypatch.setattr("minerva_travel.app.discover_dynamic_itinerary", forbidden_provider)
    client = TestClient(app)

    response = client.post(
        "/api/itinerary/discover",
        json={"destination": "Paris", "days": 1},
    )

    assert response.status_code == 401
    assert response.json()["code"] == "unauthorized"
    assert response.headers["www-authenticate"] == "Bearer"
    assert provider_called is False
    assert client.get("/api/catalog").status_code == 200
    assert client.get("/health/live").status_code == 200
