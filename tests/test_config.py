import pytest
from pydantic import ValidationError

from weather_dashboard.config import Settings


def test_reads_values_from_environment(monkeypatch):
    monkeypatch.setenv("OPENWEATHER_API_KEY", "env-key")
    monkeypatch.setenv("OPENWEATHER_UNITS", "imperial")

    settings = Settings(_env_file=None)

    assert settings.api_key.get_secret_value() == "env-key"
    assert settings.units == "imperial"


def test_fails_fast_when_api_key_is_missing(monkeypatch):
    monkeypatch.delenv("OPENWEATHER_API_KEY", raising=False)

    with pytest.raises(ValidationError, match="api_key"):
        Settings(_env_file=None)


def test_api_key_is_masked_in_repr(monkeypatch):
    monkeypatch.setenv("OPENWEATHER_API_KEY", "super-secret")

    settings = Settings(_env_file=None)

    assert "super-secret" not in repr(settings)


def test_rejects_invalid_units(monkeypatch):
    monkeypatch.setenv("OPENWEATHER_API_KEY", "k")
    monkeypatch.setenv("OPENWEATHER_UNITS", "kelvin")

    with pytest.raises(ValidationError):
        Settings(_env_file=None)
