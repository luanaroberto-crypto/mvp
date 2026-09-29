"""Ponto de entrada da aplicação FastAPI.

Executar localmente:
    uvicorn weather_dashboard.main:app --app-dir src --reload
"""

import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI, Request, Response, status
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from weather_dashboard import __version__
from weather_dashboard.api import router
from weather_dashboard.client import CityNotFoundError, OpenWeatherClient, UpstreamError
from weather_dashboard.config import Settings, get_settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
# O httpx registra a URL completa de cada requisição em INFO — e a URL do OpenWeatherMap
# carrega a chave de API na query string (appid). Silenciar evita vazar o segredo nos logs.
logging.getLogger("httpx").setLevel(logging.WARNING)

STATIC_DIR = Path(__file__).parent / "static"

# A documentação interativa (/docs) carrega JS/CSS de CDN, então fica fora da CSP restrita.
DOCS_PATHS = ("/docs", "/redoc", "/openapi.json")

CONTENT_SECURITY_POLICY = "; ".join(
    [
        "default-src 'self'",
        "img-src 'self' https://openweathermap.org",
        "script-src 'self'",
        "style-src 'self'",
        "connect-src 'self'",
        "frame-ancestors 'none'",
        "base-uri 'self'",
        "form-action 'self'",
    ]
)


def create_app(settings: Settings | None = None) -> FastAPI:
    """Cria a aplicação. `settings` explícito permite testes sem variáveis de ambiente."""

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        resolved = settings or get_settings()
        async with httpx.AsyncClient(timeout=resolved.timeout_seconds) as http_client:
            app.state.weather_client = OpenWeatherClient(http_client, resolved)
            yield

    app = FastAPI(title="Weather Dashboard", version=__version__, lifespan=lifespan)
    app.include_router(router)

    @app.get("/health", tags=["infra"])
    async def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    @app.exception_handler(CityNotFoundError)
    async def city_not_found(_: Request, __: CityNotFoundError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": "Cidade não encontrada."},
        )

    @app.exception_handler(UpstreamError)
    async def upstream_error(_: Request, __: UpstreamError) -> JSONResponse:
        # Mensagem genérica: detalhes do provedor ficam apenas no log do servidor.
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={"detail": "Serviço de clima indisponível no momento. Tente novamente."},
        )

    @app.middleware("http")
    async def security_headers(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        if not request.url.path.startswith(DOCS_PATHS):
            response.headers["Content-Security-Policy"] = CONTENT_SECURITY_POLICY
        return response

    # Montado por último: as rotas da API e /health têm precedência sobre os arquivos estáticos.
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")

    return app


app = create_app()
