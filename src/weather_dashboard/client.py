"""Cliente HTTP do OpenWeatherMap — única camada que conhece o formato bruto da API externa."""

import logging
from collections.abc import Callable
from datetime import UTC, datetime, timedelta, timezone
from typing import Any

import httpx
from pydantic import ValidationError

from weather_dashboard.config import Settings
from weather_dashboard.models import CurrentWeather, ForecastEntry

logger = logging.getLogger(__name__)


class WeatherServiceError(Exception):
    """Erro base ao consultar o provedor de clima."""


class CityNotFoundError(WeatherServiceError):
    """A cidade pesquisada não existe no provedor."""


class UpstreamError(WeatherServiceError):
    """O provedor falhou, está indisponível ou respondeu algo inesperado."""


class OpenWeatherClient:
    """Consulta clima atual e previsão. Recebe o httpx.AsyncClient por injeção de dependência."""

    def __init__(self, http_client: httpx.AsyncClient, settings: Settings) -> None:
        self._http = http_client
        self._settings = settings

    async def get_current(self, city: str) -> CurrentWeather:
        payload = await self._get("weather", city)
        return _parse(parse_current, payload)

    async def get_forecast(self, city: str) -> tuple[str, str, list[ForecastEntry]]:
        """Retorna (cidade, país, pontos de previsão) — os pontos vêm no fuso local da cidade."""
        payload = await self._get("forecast", city)
        return _parse(parse_forecast, payload)

    async def _get(self, path: str, city: str) -> dict[str, Any]:
        url = f"{self._settings.base_url.rstrip('/')}/{path}"
        params = {
            "q": city,
            "appid": self._settings.api_key.get_secret_value(),
            "units": self._settings.units,
            "lang": self._settings.lang,
        }
        try:
            response = await self._http.get(url, params=params)
        except httpx.HTTPError as exc:
            # Não logar a URL completa: ela contém a chave da API na query string.
            logger.warning(
                "Falha de rede ao consultar OpenWeatherMap (%s): %s", path, type(exc).__name__
            )
            raise UpstreamError("Provedor de clima indisponível") from exc

        if response.status_code == httpx.codes.NOT_FOUND:
            raise CityNotFoundError(city)
        if response.status_code == httpx.codes.UNAUTHORIZED:
            logger.error(
                "OpenWeatherMap recusou a chave de API (401). Verifique OPENWEATHER_API_KEY."
            )
            raise UpstreamError("Provedor de clima recusou a autenticação")
        if response.is_error:
            logger.warning("OpenWeatherMap respondeu %s em %s", response.status_code, path)
            raise UpstreamError(f"Provedor de clima respondeu {response.status_code}")

        try:
            data: dict[str, Any] = response.json()
        except ValueError as exc:
            raise UpstreamError("Resposta do provedor não é JSON válido") from exc
        return data


def _parse[T](parser: Callable[[dict[str, Any]], T], payload: dict[str, Any]) -> T:
    """Converte falhas de formato da resposta externa em UpstreamError."""
    try:
        return parser(payload)
    except (KeyError, IndexError, TypeError, ValueError, ValidationError) as exc:
        logger.warning("Resposta inesperada do OpenWeatherMap: %s", type(exc).__name__)
        raise UpstreamError("Resposta do provedor em formato inesperado") from exc


def parse_current(payload: dict[str, Any]) -> CurrentWeather:
    """Traduz a resposta de /weather para o modelo de domínio."""
    tz = timezone(timedelta(seconds=payload.get("timezone", 0)))
    main = payload["main"]
    condition = payload["weather"][0]
    return CurrentWeather(
        city=payload["name"],
        country=payload["sys"]["country"],
        temperature=main["temp"],
        feels_like=main["feels_like"],
        temp_min=main["temp_min"],
        temp_max=main["temp_max"],
        humidity=main["humidity"],
        pressure=main["pressure"],
        wind_speed=payload["wind"]["speed"],
        description=condition["description"],
        icon=condition["icon"],
        observed_at=datetime.fromtimestamp(payload["dt"], tz=UTC).astimezone(tz),
    )


def parse_forecast(payload: dict[str, Any]) -> tuple[str, str, list[ForecastEntry]]:
    """Traduz a resposta de /forecast, convertendo horários para o fuso da cidade."""
    city = payload["city"]
    tz = timezone(timedelta(seconds=city.get("timezone", 0)))
    entries = [
        ForecastEntry(
            timestamp=datetime.fromtimestamp(item["dt"], tz=UTC).astimezone(tz),
            temperature=item["main"]["temp"],
            humidity=item["main"]["humidity"],
            description=item["weather"][0]["description"],
            icon=item["weather"][0]["icon"],
        )
        for item in payload["list"]
    ]
    return city["name"], city["country"], entries
