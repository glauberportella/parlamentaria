"""Celery task: notify voters about relevant new propositions.

When a new proposition is synced from the Câmara API, this task finds
voters whose interest themes match the proposition's themes and sends
them a proactive notification via their messaging channel.
"""

import asyncio

from app.tasks.celery_app import celery_app
from app.tasks.helpers import get_async_session
from app.logging import get_logger

logger = get_logger(__name__)


@celery_app.task(name="app.tasks.notificar_eleitores.notificar_eleitores_task")
def notificar_eleitores_task(
    proposicao_id: int,
    temas: list[str] | None = None,
    tipo: str = "PL",
    numero: int = 0,
    ano: int = 0,
    ementa: str = "",
) -> dict:
    """Notify voters interested in the given themes about a new proposition.

    Args:
        proposicao_id: ID of the proposition to notify about.
        temas: Themes of the proposition for matching voter interests.
        tipo: Type of the proposition (PL, PEC, etc.).
        numero: Proposition number.
        ano: Proposition year.
        ementa: Summary of the proposition.

    Returns:
        Dict with notification stats.
    """
    logger.info("task.notificar_eleitores.start", proposicao_id=proposicao_id)

    async def _run() -> dict:
        async with get_async_session() as session:
            from app.services.notification_service import NotificationService

            service = NotificationService(session)
            stats = await service.notify_voters_about_proposicao(
                proposicao_id=proposicao_id,
                tipo=tipo,
                numero=numero,
                ano=ano,
                ementa=ementa,
                temas=temas or [],
                send_fn=None,  # Default: dry run (log only, no channel adapter in Celery context)
            )
            return stats

    try:
        result = asyncio.get_event_loop().run_until_complete(_run())
    except RuntimeError:
        result = asyncio.run(_run())

    logger.info("task.notificar_eleitores.complete", **result)
    return result


@celery_app.task(name="app.tasks.notificar_eleitores.notificar_comparativo_task")
def notificar_comparativo_task(
    proposicao_id: int,
    tipo: str = "PL",
    numero: int = 0,
    ano: int = 0,
    resultado_camara: str = "APROVADO",
    percentual_sim_popular: float = 0.0,
    alinhamento: float = 0.5,
) -> dict:
    """Notify voters who voted on a proposition about the comparison result.

    Args:
        proposicao_id: ID of the proposition.
        tipo: Type of the proposition (PL, PEC, etc.).
        numero: Proposition number.
        ano: Proposition year.
        resultado_camara: "APROVADO" or "REJEITADO".
        percentual_sim_popular: Popular SIM percentage.
        alinhamento: Alignment score (0.0 to 1.0).

    Returns:
        Dict with notification stats.
    """
    logger.info(
        "task.notificar_comparativo.start",
        proposicao_id=proposicao_id,
        resultado_camara=resultado_camara,
    )

    async def _run() -> dict:
        async with get_async_session() as session:
            from app.services.notification_service import NotificationService

            service = NotificationService(session)
            stats = await service.notify_voters_comparativo(
                proposicao_id=proposicao_id,
                tipo=tipo,
                numero=numero,
                ano=ano,
                resultado_camara=resultado_camara,
                percentual_sim_popular=percentual_sim_popular,
                alinhamento=alinhamento,
                send_fn=None,  # Dry run in Celery context
            )
            return stats

    try:
        result = asyncio.get_event_loop().run_until_complete(_run())
    except RuntimeError:
        result = asyncio.run(_run())

    logger.info("task.notificar_comparativo.complete", **result)
    return result
