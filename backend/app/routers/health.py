"""Health check endpoints for monitoring and orchestration."""

from datetime import datetime, timezone

from fastapi import APIRouter
from sqlalchemy import text

from app.config import settings
from app.db.session import async_session_factory
from app.logging import get_logger

router = APIRouter(tags=["health"])

logger = get_logger(__name__)

# Recorded at module load time
_start_time = datetime.now(timezone.utc)


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Simple health check — returns 200 if the service is running."""
    return {"status": "ok"}


@router.get("/health/detailed")
async def health_detailed() -> dict:
    """Detailed health check — verifies DB, Redis, and API Câmara connectivity.

    Returns an overall status:
    - healthy: all checks pass
    - degraded: at least one non-critical check failed (e.g., external API)
    - unhealthy: a critical dependency failed (DB or Redis)
    """
    checks: dict[str, dict[str, str]] = {}
    critical_ok = True

    # Database check
    try:
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
        checks["database"] = {"status": "ok"}
    except Exception as exc:
        checks["database"] = {"status": "error", "detail": str(exc)}
        critical_ok = False

    # Redis check
    try:
        import redis.asyncio as aioredis

        r = aioredis.from_url(settings.redis_url)
        await r.ping()
        await r.aclose()
        checks["redis"] = {"status": "ok"}
    except Exception as exc:
        checks["redis"] = {"status": "error", "detail": str(exc)}
        critical_ok = False

    # API Câmara check (non-critical)
    api_ok = True
    try:
        import httpx

        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                f"{settings.camara_api_base_url}/referencias/proposicoes/codTema"
            )
            resp.raise_for_status()
        checks["camara_api"] = {"status": "ok"}
    except Exception as exc:
        checks["camara_api"] = {"status": "error", "detail": str(exc)}
        api_ok = False

    # Compute overall status
    if not critical_ok:
        overall = "unhealthy"
    elif not api_ok:
        overall = "degraded"
    else:
        overall = "healthy"

    uptime_seconds = (datetime.now(timezone.utc) - _start_time).total_seconds()

    return {
        "status": overall,
        "version": "0.1.0",
        "environment": settings.app_env,
        "uptime_seconds": round(uptime_seconds, 1),
        "checks": checks,
    }
