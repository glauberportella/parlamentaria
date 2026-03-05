"""Celery task: sync parliamentary votes from the Câmara API."""

import asyncio

from app.tasks.celery_app import celery_app
from app.tasks.helpers import get_async_session
from app.logging import get_logger

logger = get_logger(__name__)


@celery_app.task(name="app.tasks.sync_votacoes.sync_votacoes_task", bind=True, max_retries=3)
def sync_votacoes_task(self) -> dict:
    """Celery task to sync recent parliamentary votes.

    Returns:
        Sync statistics dict.
    """
    logger.info("task.sync_votacoes.start")

    async def _run() -> dict:
        async with get_async_session() as session:
            from app.services.sync_service import SyncService
            service = SyncService(session)
            stats = await service.sync_votacoes()
            try:
                await session.commit()
            except Exception:
                await session.rollback()
                logger.warning("task.sync_votacoes.commit_failed_rollback")
            return stats

    try:
        result = asyncio.get_event_loop().run_until_complete(_run())
    except RuntimeError:
        result = asyncio.run(_run())

    logger.info("task.sync_votacoes.complete", **result)
    return result
