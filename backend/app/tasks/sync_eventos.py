"""Celery task: sync plenary events from the Câmara API."""

import asyncio

from app.tasks.celery_app import celery_app
from app.tasks.helpers import get_async_session
from app.logging import get_logger

logger = get_logger(__name__)


@celery_app.task(name="app.tasks.sync_eventos.sync_eventos_task", bind=True, max_retries=3)
def sync_eventos_task(self, dias_atras: int = 7) -> dict:
    """Celery task to sync recent plenary events from the Câmara API.

    Args:
        dias_atras: How many days back to sync.

    Returns:
        Sync statistics dict.
    """
    logger.info("task.sync_eventos.start", dias_atras=dias_atras)

    async def _run() -> dict:
        async with get_async_session() as session:
            from app.services.sync_service import SyncService
            service = SyncService(session)
            stats = await service.sync_eventos(dias_atras=dias_atras)
            try:
                await session.commit()
            except Exception:
                await session.rollback()
                logger.warning("task.sync_eventos.commit_failed_rollback")
            return stats

    try:
        result = asyncio.get_event_loop().run_until_complete(_run())
    except RuntimeError:
        result = asyncio.run(_run())

    logger.info("task.sync_eventos.complete", **result)
    return result
