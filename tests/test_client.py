import logging
from datetime import timedelta

import httpx
import pytest
import respx

from tests.conftest import BASE_URL
from weather_dashboard.client import CityNotFoundError, OpenWeatherClient, UpstreamError

pytestmark = pytest.mark.anyio


@pytest.fixture
async def client(settings):
    async with httpx.AsyncClient() as http:
        yield OpenWeatherClient(http, settings)


class TestGetCurrent:
    @respx.mock
    async def test_parses_current_weather(self, client, current_payload):
        respx.get(f"{BASE_URL}/weather").mock(
            return_value=httpx.Response(200, json=current_payload)
        )

        weather = await client.get_current("São Paulo")

        assert weather.city == "São Paulo"
        assert weather.country == "BR"
        assert weather.temperature == 24.5
        assert weather.humidity == 65
        assert weather.icon == "03d"

    @respx.mock
    async def test_converts_observation_time_to_city_timezone(self, client, current_payload):
        respx.get(f"{BASE_URL}/weather").mock(
            return_value=httpx.Response(200, json=current_payload)
        )

        weather = await client.get_current("São Paulo")

        assert weather.observed_at.utcoffset() == timedelta(hours=-3)
        assert weather.observed_at.hour == 9  # 12:00 UTC -> 09:00 em São Paulo

    @respx.mock
    async def test_sends_city_key_units_and_language(self, client, current_payload):
        route = respx.get(f"{BASE_URL}/weather").mock(
            return_value=httpx.Response(200, json=current_payload)
        )

        await client.get_current("Curitiba")

        params = route.calls.last.request.url.params
        assert params["q"] == "Curitiba"
        assert params["appid"] == "test-key"
        assert params["units"] == "metric"
        assert params["lang"] == "pt_br"


class TestGetForecast:
    @respx.mock
    async def test_parses_forecast_entries(self, client, forecast_payload):
        respx.get(f"{BASE_URL}/forecast").mock(
            return_value=httpx.Response(200, json=forecast_payload)
        )

        city, country, entries = await client.get_forecast("São Paulo")

        assert (city, country) == ("São Paulo", "BR")
        assert len(entries) == 8
        assert entries[0].temperature == 20
        assert entries[0].timestamp.utcoffset() == timedelta(hours=-3)


class TestErrorHandling:
    @respx.mock
    async def test_raises_city_not_found_on_404(self, client):
        respx.get(f"{BASE_URL}/weather").mock(return_value=httpx.Response(404, json={}))

        with pytest.raises(CityNotFoundError):
            await client.get_current("Cidade Inexistente")

    @pytest.mark.parametrize("status", [401, 429, 500, 503])
    @respx.mock
    async def test_raises_upstream_error_on_other_http_errors(self, client, status):
        respx.get(f"{BASE_URL}/weather").mock(return_value=httpx.Response(status, json={}))

        with pytest.raises(UpstreamError):
            await client.get_current("Curitiba")

    @respx.mock
    async def test_raises_upstream_error_on_network_failure(self, client):
        respx.get(f"{BASE_URL}/weather").mock(side_effect=httpx.ConnectTimeout("timeout"))

        with pytest.raises(UpstreamError, match="indisponível"):
            await client.get_current("Curitiba")

    @respx.mock
    async def test_raises_upstream_error_on_invalid_json(self, client):
        respx.get(f"{BASE_URL}/weather").mock(return_value=httpx.Response(200, text="<html>"))

        with pytest.raises(UpstreamError, match="JSON"):
            await client.get_current("Curitiba")

    @respx.mock
    async def test_raises_upstream_error_on_unexpected_payload(self, client):
        respx.get(f"{BASE_URL}/weather").mock(return_value=httpx.Response(200, json={"foo": 1}))

        with pytest.raises(UpstreamError, match="formato inesperado"):
            await client.get_current("Curitiba")

    @respx.mock
    async def test_rejects_malicious_icon_code(self, client, current_payload):
        current_payload["weather"][0]["icon"] = '"><script>alert(1)</script>'
        respx.get(f"{BASE_URL}/weather").mock(
            return_value=httpx.Response(200, json=current_payload)
        )

        with pytest.raises(UpstreamError):
            await client.get_current("Curitiba")

    @respx.mock
    async def test_logs_do_not_leak_api_key(self, client, current_payload, caplog):
        import weather_dashboard.main  # noqa: F401 — aplica a configuração de logging do app

        caplog.set_level(logging.DEBUG)
        respx.get(f"{BASE_URL}/weather").mock(return_value=httpx.Response(401, json={}))

        with pytest.raises(UpstreamError):
            await client.get_current("Curitiba")

        assert caplog.records, "esperava ao menos o log de erro de autenticação"
        assert "test-key" not in caplog.text

    @respx.mock
    async def test_error_messages_do_not_leak_api_key(self, client):
        respx.get(f"{BASE_URL}/weather").mock(side_effect=httpx.ConnectError("boom"))

        with pytest.raises(UpstreamError) as exc_info:
            await client.get_current("Curitiba")

        assert "test-key" not in str(exc_info.value)
