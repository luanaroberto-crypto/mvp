"""Configuração da aplicação carregada de variáveis de ambiente (ou de um arquivo .env)."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configurações validadas na inicialização — falha cedo se algo obrigatório faltar."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="OPENWEATHER_",
        extra="ignore",
    )

    # SecretStr evita que a chave apareça em logs, reprs ou mensagens de erro.
    api_key: SecretStr
    base_url: str = "https://api.openweathermap.org/data/2.5"
    timeout_seconds: float = Field(default=5.0, gt=0, le=30)
    units: Literal["metric", "imperial"] = "metric"
    lang: str = Field(default="pt_br", pattern=r"^[a-z]{2}(_[a-z]{2})?$")


@lru_cache
def get_settings() -> Settings:
    """Retorna a instância única de configurações (lida uma vez por processo)."""
    return Settings()
