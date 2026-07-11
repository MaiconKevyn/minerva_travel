import pytest


@pytest.fixture(autouse=True)
def disable_external_supabase_storage(monkeypatch):
    monkeypatch.setenv("SUPABASE_STORAGE_ENABLED", "false")
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("AUTH_REQUIRED", "false")
    monkeypatch.setenv("PHOTO_PROCESSING_CONSENT_REQUIRED", "false")
