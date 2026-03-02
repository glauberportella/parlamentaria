"""Celery task: sync propositions from the Câmara API."""

import asyncio

from app.tasks.celery_app import celery_app
from app.tasks.helpers import get_async_session
from app.logging import get_logger

logger = get_logger(__name__)


@celery_app.task(name="app.tasks.sync_proposicoes.sync_proposicoes_task", bind=True, max_retries=3)
def sync_proposicoes_task(self, ano: int | None = None, sigla_tipo: str | None = None) -> dict:
    """Celery task to sync propositions from the Câmara API.

    Args:
        ano: Year filter.
        sigla_tipo: Type filter.

    Returns:
        Sync statistics dict.
    """
    logger.info("task.sync_proposicoes.start", ano=ano, sigla_tipo=sigla_tipo)

    async def _run() -> dict:
        async with get_async_session() as session:
            from app.services.sync_service import SyncService
            service = SyncService(session)
            stats = await service.sync_proposicoes(ano=ano, sigla_tipo=sigla_tipo)
            await session.commit()
            return stats

    try:
        result = asyncio.get_event_loop().run_until_complete(_run())
    except RuntimeError:
        # No event loop running — create one
        result = asyncio.run(_run())

    logger.info("task.sync_proposicoes.complete", **result)

    # Chain: trigger embedding generation for newly synced propositions
    if result.get("created", 0) > 0 or result.get("updated", 0) > 0:
        from app.tasks.generate_embeddings import generate_embeddings_task
        generate_embeddings_task.delay()
        logger.info("task.sync_proposicoes.triggered_embeddings")

    return result
