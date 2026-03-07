"""Celery task: sync political parties from the Câmara API."""

import asyncio

from app.tasks.celery_app import celery_app
from app.tasks.helpers import get_async_session
from app.logging import get_logger

logger = get_logger(__name__)


@celery_app.task(name="app.tasks.sync_partidos.sync_partidos_task", bind=True, max_retries=3)
def sync_partidos_task(self) -> dict:
    """Celery task to sync political parties from the Câmara API.

    Returns:
        Sync statistics dict.
    """
    logger.info("task.sync_partidos.start")

    async def _run() -> dict:
        async with get_async_session() as session:
            from app.services.sync_service import SyncService
            service = SyncService(session)
            stats = await service.sync_partidos()
            try:
                await session.commit()
            except Exception:
                await session.rollback()
                logger.warning("task.sync_partidos.commit_failed_rollback")
            return stats

    try:
        result = asyncio.get_event_loop().run_until_complete(_run())
    except RuntimeError:
        result = asyncio.run(_run())

    logger.info("task.sync_partidos.complete", **result)
    return result
