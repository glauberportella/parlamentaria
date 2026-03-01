"""Celery task: dispatch outbound webhooks for events."""

import asyncio

from app.tasks.celery_app import celery_app
from app.tasks.helpers import get_async_session
from app.logging import get_logger

logger = get_logger(__name__)


@celery_app.task(name="app.tasks.dispatch_webhooks.dispatch_webhooks_task")
def dispatch_webhooks_task(evento: str, payload: dict) -> dict:
    """Dispatch a webhook event to all subscribed endpoints.

    Args:
        evento: Event type (e.g., "voto_consolidado", "comparativo_gerado").
        payload: Event payload data.

    Returns:
        Dict with dispatch stats.
    """
    logger.info("task.dispatch_webhooks.start", evento=evento)

    async def _run() -> dict:
        async with get_async_session() as session:
            from app.services.publicacao_service import PublicacaoService
            service = PublicacaoService(session)
            stats = await service.dispatch_event(evento, payload)
            await session.commit()
            return stats

    try:
        result = asyncio.get_event_loop().run_until_complete(_run())
    except RuntimeError:
        result = asyncio.run(_run())

    logger.info("task.dispatch_webhooks.complete", **result)
    return result
