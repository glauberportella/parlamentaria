"""Celery task: sync deputies from the Câmara API."""

import asyncio

from app.tasks.celery_app import celery_app
from app.tasks.helpers import get_async_session
from app.logging import get_logger

logger = get_logger(__name__)


@celery_app.task(name="app.tasks.sync_deputados.sync_deputados_task", bind=True, max_retries=3)
def sync_deputados_task(
    self,
    sigla_uf: str | None = None,
    sigla_partido: str | None = None,
) -> dict:
    """Celery task to sync active deputies from the Câmara API.

    Args:
        sigla_uf: Optional state filter.
        sigla_partido: Optional party filter.

    Returns:
        Sync statistics dict.
    """
    logger.info("task.sync_deputados.start", sigla_uf=sigla_uf, sigla_partido=sigla_partido)

    async def _run() -> dict:
        async with get_async_session() as session:
            from app.services.sync_service import SyncService
            service = SyncService(session)
            stats = await service.sync_deputados(
                sigla_uf=sigla_uf,
                sigla_partido=sigla_partido,
            )
            try:
                await session.commit()
            except Exception:
                await session.rollback()
                logger.warning("task.sync_deputados.commit_failed_rollback")
            return stats

    try:
        result = asyncio.get_event_loop().run_until_complete(_run())
    except RuntimeError:
        result = asyncio.run(_run())

    logger.info("task.sync_deputados.complete", **result)
    return result
