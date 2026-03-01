"""FastAPI application entrypoint with lifespan management."""

from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.config import settings
from app.exceptions import AppException
from app.logging import setup_logging, get_logger
from app.routers import health, webhooks, admin

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application startup and shutdown lifecycle."""
    setup_logging()
    logger.info("parlamentaria.startup", env=settings.app_env)
    yield
    logger.info("parlamentaria.shutdown")


app = FastAPI(
    title="Parlamentaria API",
    description="Backend API para a plataforma agêntica Parlamentaria",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.app_debug else None,
    redoc_url=None,
)


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Handle application-level exceptions with structured responses."""
    logger.warning(
        "app.exception",
        status_code=exc.status_code,
        detail=exc.detail,
        path=str(request.url),
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all for unhandled exceptions — never leak stack traces in production."""
    logger.error(
        "app.unhandled_exception",
        exc_type=type(exc).__name__,
        detail=str(exc),
        path=str(request.url),
    )
    detail = str(exc) if settings.app_debug else "Erro interno do servidor"
    return JSONResponse(status_code=500, content={"detail": detail})


# Register routers
app.include_router(health.router)
app.include_router(webhooks.router)
app.include_router(admin.router)
