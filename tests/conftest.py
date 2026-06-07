import pytest


@pytest.fixture(autouse=True)
def disable_external_supabase_storage(monkeypatch):
    monkeypatch.setenv("SUPABASE_STORAGE_ENABLED", "false")
