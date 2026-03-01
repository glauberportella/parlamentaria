"""Health check endpoints."""

from fastapi import APIRouter
from sqlalchemy import text

from app.db.session import async_session_factory

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Simple health check — returns 200 if the service is running."""
    return {"status": "ok"}


@router.get("/health/detailed")
async def health_detailed() -> dict[str, dict[str, str]]:
    """Detailed health check — verifies DB and Redis connectivity."""
    checks: dict[str, dict[str, str]] = {}

    # Database check
    try:
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
        checks["database"] = {"status": "ok"}
    except Exception as exc:
        checks["database"] = {"status": "error", "detail": str(exc)}

    # Redis check
    try:
        import redis.asyncio as aioredis

        from app.config import settings

        r = aioredis.from_url(settings.redis_url)
        await r.ping()
        await r.aclose()
        checks["redis"] = {"status": "ok"}
    except Exception as exc:
        checks["redis"] = {"status": "error", "detail": str(exc)}

    return checks
