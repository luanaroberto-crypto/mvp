"""Rotas REST consumidas pelo frontend. A chave do OpenWeatherMap nunca sai do servidor."""

import re
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from weather_dashboard.client import OpenWeatherClient
from weather_dashboard.forecast import summarize_daily
from weather_dashboard.models import CurrentWeather, Forecast

MAX_CITY_LENGTH = 100
MAX_FORECAST_DAYS = 5

# Letras (inclusive acentuadas), espaços, hífen, apóstrofo, ponto e vírgula ("Paris,FR").
CITY_PATTERN = re.compile(r"[^\W_][\w\s.,'\-]*")

router = APIRouter(prefix="/api", tags=["weather"])


def validated_city(
    city: Annotated[
        str,
        Query(
            min_length=1,
            max_length=MAX_CITY_LENGTH,
            description="Nome da cidade, opcionalmente com o código do país (ex.: 'Curitiba,BR').",
        ),
    ],
) -> str:
    """Normaliza espaços e rejeita entradas que não parecem nomes de cidade."""
    normalized = " ".join(city.split())
    if not CITY_PATTERN.fullmatch(normalized) or not any(ch.isalpha() for ch in normalized):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Nome de cidade inválido.",
        )
    return normalized


def get_weather_client(request: Request) -> OpenWeatherClient:
    """Fornece o cliente criado no lifespan da aplicação (substituível nos testes)."""
    client: OpenWeatherClient = request.app.state.weather_client
    return client


City = Annotated[str, Depends(validated_city)]
WeatherClient = Annotated[OpenWeatherClient, Depends(get_weather_client)]


@router.get("/weather/current", response_model=CurrentWeather)
async def current_weather(city: City, client: WeatherClient) -> CurrentWeather:
    """Condições atuais da cidade informada."""
    return await client.get_current(city)


@router.get("/weather/forecast", response_model=Forecast)
async def forecast(
    city: City,
    client: WeatherClient,
    days: Annotated[int, Query(ge=1, le=MAX_FORECAST_DAYS)] = MAX_FORECAST_DAYS,
) -> Forecast:
    """Previsão resumida por dia para os próximos `days` dias."""
    city_name, country, entries = await client.get_forecast(city)
    return Forecast(city=city_name, country=country, days=summarize_daily(entries, days))
