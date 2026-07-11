from minerva_travel.config import pilot_restaurant_recommendations_enabled


def test_restaurant_pilot_feature_requires_explicit_production_enablement(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("PILOT_RESTAURANT_RECOMMENDATIONS_ENABLED", raising=False)

    assert pilot_restaurant_recommendations_enabled() is False

    monkeypatch.setenv("PILOT_RESTAURANT_RECOMMENDATIONS_ENABLED", "true")
    assert pilot_restaurant_recommendations_enabled() is True


def test_restaurant_pilot_feature_is_available_for_local_validation(monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.delenv("PILOT_RESTAURANT_RECOMMENDATIONS_ENABLED", raising=False)

    assert pilot_restaurant_recommendations_enabled() is True
