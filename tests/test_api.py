"""Testes de integração da API: rotas + validação + tratamento de erros, com cliente falso."""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from weather_dashboard.api import get_weather_client
from weather_dashboard.client import CityNotFoundError, UpstreamError
from weather_dashboard.main import create_app
from weather_dashboard.models import CurrentWeather, ForecastEntry

TZ = timezone(timedelta(hours=-3))


class FakeWeatherClient:
    """Dublê do OpenWeatherClient: registra chamadas e pode simular falhas."""

    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.requested_cities: list[str] = []

    async def get_current(self, city: str) -> CurrentWeather:
        self.requested_cities.append(city)
        if self.error:
            raise self.error
        return CurrentWeather(
            city=city,
            country="BR",
            temperature=22.0,
            feels_like=21.5,
            temp_min=18.0,
            temp_max=25.0,
            humidity=70,
            pressure=1012,
            wind_speed=2.5,
            description="céu limpo",
            icon="01d",
            observed_at=datetime(2026, 9, 29, 12, tzinfo=TZ),
        )

    async def get_forecast(self, city: str) -> tuple[str, str, list[ForecastEntry]]:
        self.requested_cities.append(city)
        if self.error:
            raise self.error
        entries = [
            ForecastEntry(
                timestamp=datetime(2026, 9, 29, hour, tzinfo=TZ) + timedelta(days=day),
                temperature=15 + day + hour / 3,
                humidity=60,
                description="chuva leve",
                icon="10d",
            )
            for day in range(6)
            for hour in (0, 12)
        ]
        return city, "BR", entries


@pytest.fixture
def fake_client() -> FakeWeatherClient:
    return FakeWeatherClient()


@pytest.fixture
def make_api(settings):
    def _make(fake: FakeWeatherClient) -> TestClient:
        app = create_app(settings)
        app.dependency_overrides[get_weather_client] = lambda: fake
        return TestClient(app)

    return _make


@pytest.fixture
def api(make_api, fake_client):
    with make_api(fake_client) as test_client:
        yield test_client


class TestHealth:
    def test_returns_ok_with_version(self, api):
        response = api.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "ok", "version": "1.0.0"}


class TestCurrentWeather:
    def test_returns_current_weather(self, api):
        response = api.get("/api/weather/current", params={"city": "Curitiba"})

        assert response.status_code == 200
        body = response.json()
        assert body["city"] == "Curitiba"
        assert body["temperature"] == 22.0
        assert body["icon"] == "01d"

    def test_normalizes_whitespace_in_city(self, api, fake_client):
        api.get("/api/weather/current", params={"city": "  São   Paulo "})

        assert fake_client.requested_cities == ["São Paulo"]

    @pytest.mark.parametrize("city", ["São Paulo", "Paris,FR", "Porto-Alegre", "N'Djamena"])
    def test_accepts_valid_city_names(self, api, city):
        assert api.get("/api/weather/current", params={"city": city}).status_code == 200

    @pytest.mark.parametrize(
        "city",
        ["", "   ", "12345", "<script>", "Curitiba; DROP TABLE", "a" * 101, "../etc/passwd"],
    )
    def test_rejects_invalid_city_names(self, api, fake_client, city):
        response = api.get("/api/weather/current", params={"city": city})

        assert response.status_code == 422
        assert fake_client.requested_cities == []

    def test_requires_city_parameter(self, api):
        assert api.get("/api/weather/current").status_code == 422


class TestForecast:
    def test_returns_five_days_by_default(self, api):
        response = api.get("/api/weather/forecast", params={"city": "Curitiba"})

        assert response.status_code == 200
        body = response.json()
        assert body["city"] == "Curitiba"
        assert len(body["days"]) == 5
        assert body["days"][0]["day"] == "2026-09-29"

    def test_respects_days_parameter(self, api):
        response = api.get("/api/weather/forecast", params={"city": "Curitiba", "days": 2})

        assert len(response.json()["days"]) == 2

    @pytest.mark.parametrize("days", [0, 6, -1])
    def test_rejects_days_out_of_range(self, api, days):
        response = api.get("/api/weather/forecast", params={"city": "Curitiba", "days": days})

        assert response.status_code == 422


class TestErrorMapping:
    @pytest.mark.parametrize("path", ["/api/weather/current", "/api/weather/forecast"])
    def test_city_not_found_returns_404(self, make_api, path):
        with make_api(FakeWeatherClient(error=CityNotFoundError("x"))) as api:
            response = api.get(path, params={"city": "Atlantis"})

        assert response.status_code == 404
        assert response.json() == {"detail": "Cidade não encontrada."}

    def test_upstream_error_returns_502_with_generic_message(self, make_api):
        fake = FakeWeatherClient(error=UpstreamError("detalhe interno do provedor"))
        with make_api(fake) as api:
            response = api.get("/api/weather/current", params={"city": "Curitiba"})

        assert response.status_code == 502
        assert "detalhe interno" not in response.text


class TestSecurityHeaders:
    def test_api_responses_include_security_headers(self, api):
        response = api.get("/health")

        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] == "DENY"
        assert "default-src 'self'" in response.headers["Content-Security-Policy"]

    def test_docs_are_exempt_from_strict_csp(self, api):
        response = api.get("/docs")

        assert response.status_code == 200
        assert "Content-Security-Policy" not in response.headers
