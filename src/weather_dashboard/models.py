"""Modelos de domínio expostos pela API — independentes do formato bruto do OpenWeatherMap."""

from datetime import date, datetime

from pydantic import BaseModel, Field

# Códigos de ícone do OpenWeatherMap têm o formato "01d", "10n" etc. Validar o formato
# impede que um valor inesperado vire parte de uma URL de imagem no frontend.
ICON_PATTERN = r"^\d{2}[dn]$"


class CurrentWeather(BaseModel):
    """Condições atuais de uma cidade."""

    city: str
    country: str
    temperature: float
    feels_like: float
    temp_min: float
    temp_max: float
    humidity: int = Field(ge=0, le=100)
    pressure: int
    wind_speed: float = Field(ge=0)
    description: str
    icon: str = Field(pattern=ICON_PATTERN)
    observed_at: datetime


class ForecastEntry(BaseModel):
    """Um ponto da previsão de 3 em 3 horas retornada pelo OpenWeatherMap."""

    timestamp: datetime
    temperature: float
    humidity: int = Field(ge=0, le=100)
    description: str
    icon: str = Field(pattern=ICON_PATTERN)


class DailyForecast(BaseModel):
    """Resumo diário agregado a partir dos pontos de 3 em 3 horas."""

    day: date
    temp_min: float
    temp_max: float
    humidity: int = Field(ge=0, le=100)
    description: str
    icon: str = Field(pattern=ICON_PATTERN)


class Forecast(BaseModel):
    """Previsão de vários dias para uma cidade."""

    city: str
    country: str
    days: list[DailyForecast]
