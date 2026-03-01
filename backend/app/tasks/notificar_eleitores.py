"""Celery task: notify voters about relevant new propositions."""

import asyncio

from app.tasks.celery_app import celery_app
from app.tasks.helpers import get_async_session
from app.logging import get_logger

logger = get_logger(__name__)


@celery_app.task(name="app.tasks.notificar_eleitores.notificar_eleitores_task")
def notificar_eleitores_task(proposicao_id: int, temas: list[str] | None = None) -> dict:
    """Notify voters interested in the given themes about a new proposition.

    Args:
        proposicao_id: ID of the proposition to notify about.
        temas: Themes of the proposition for matching voter interests.

    Returns:
        Dict with notification stats.
    """
    logger.info("task.notificar_eleitores.start", proposicao_id=proposicao_id)

    async def _run() -> dict:
        async with get_async_session() as session:
            from app.services.eleitor_service import EleitorService
            service = EleitorService(session)

            notified = 0
            if temas:
                for tema in temas:
                    eleitores = await service.find_by_tema(tema)
                    notified += len(eleitores)
                    # TODO: actually send notifications via channel adapter
                    for eleitor in eleitores:
                        logger.info(
                            "task.notificar.would_send",
                            eleitor_id=str(eleitor.id),
                            chat_id=eleitor.chat_id,
                            proposicao_id=proposicao_id,
                            tema=tema,
                        )

            return {"proposicao_id": proposicao_id, "notified": notified}

    try:
        result = asyncio.get_event_loop().run_until_complete(_run())
    except RuntimeError:
        result = asyncio.run(_run())

    logger.info("task.notificar_eleitores.complete", **result)
    return result
