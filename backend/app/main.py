"""FastAPI application entrypoint with lifespan management."""

from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.exceptions import AppException
from app.logging import setup_logging, get_logger
from app.middleware import RequestIdMiddleware, SecurityHeadersMiddleware, limiter
from app.routers import health, webhooks, admin, rss, assinaturas, cidadao
from app.routers.parlamentar import router as parlamentar_router

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application startup and shutdown lifecycle."""
    setup_logging()
    logger.info("parlamentaria.startup", env=settings.app_env)

    # Setup Telegram webhook if token is configured
    if settings.telegram_bot_token and settings.telegram_webhook_url:
        try:
            from channels.telegram.bot import TelegramAdapter

            adapter = TelegramAdapter()
            success = await adapter.setup_webhook(settings.telegram_webhook_url)
            if success:
                logger.info(
                    "telegram.webhook.configured",
                    url=settings.telegram_webhook_url,
                )
            else:
                logger.warning("telegram.webhook.setup_failed")
        except Exception as e:
            logger.error("telegram.webhook.setup_error", error=str(e))

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

# Rate limiter state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS — always include dashboard_url; permissive in dev
_cors_origins: list[str] = [settings.dashboard_url, settings.cidadao_site_url]
if settings.cors_extra_origins:
    _cors_origins.extend(
        o.strip() for o in settings.cors_extra_origins.split(",") if o.strip()
    )
if settings.app_debug:
    _cors_origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Trusted hosts (production)
if settings.is_production:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["parlamentaria.app", "*.parlamentaria.app"])

# Custom middlewares (order matters: outermost first)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestIdMiddleware)


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
app.include_router(rss.router)
app.include_router(assinaturas.router)
app.include_router(cidadao.router)
app.include_router(parlamentar_router)
