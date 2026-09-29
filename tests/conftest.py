"""Fixtures compartilhadas: configurações de teste e payloads resumidos do OpenWeatherMap."""

from typing import Any

import pytest
from pydantic import SecretStr

from weather_dashboard.config import Settings

BASE_URL = "https://api.test/data/2.5"

# 2026-09-29 12:00:00 UTC
NOON_UTC = 1790683200
THREE_HOURS = 3 * 3600
SAO_PAULO_OFFSET = -3 * 3600


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def settings() -> Settings:
    # _env_file=None garante que um .env local não interfira nos testes.
    return Settings(api_key=SecretStr("test-key"), base_url=BASE_URL, _env_file=None)


@pytest.fixture
def current_payload() -> dict[str, Any]:
    return {
        "name": "São Paulo",
        "sys": {"country": "BR"},
        "timezone": SAO_PAULO_OFFSET,
        "dt": NOON_UTC,
        "main": {
            "temp": 24.5,
            "feels_like": 25.1,
            "temp_min": 21.0,
            "temp_max": 27.3,
            "humidity": 65,
            "pressure": 1015,
        },
        "wind": {"speed": 3.6},
        "weather": [{"description": "nuvens dispersas", "icon": "03d"}],
    }


def make_forecast_item(dt: int, temp: float, humidity: int, description: str, icon: str) -> dict:
    return {
        "dt": dt,
        "main": {"temp": temp, "humidity": humidity},
        "weather": [{"description": description, "icon": icon}],
    }


@pytest.fixture
def forecast_payload() -> dict[str, Any]:
    items = [
        make_forecast_item(NOON_UTC + i * THREE_HOURS, 20 + i, 60 + i, "céu limpo", "01d")
        for i in range(8)
    ]
    return {
        "city": {"name": "São Paulo", "country": "BR", "timezone": SAO_PAULO_OFFSET},
        "list": items,
    }
