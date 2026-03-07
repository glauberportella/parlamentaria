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
            try:
                await session.commit()
            except Exception:
                await session.rollback()
                logger.warning("task.sync_proposicoes.commit_failed_rollback")
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

        # Chain: trigger AI analysis for newly synced propositions
        from app.tasks.generate_analysis import generate_analysis_task
        generate_analysis_task.delay()
        logger.info("task.sync_proposicoes.triggered_analysis")

    # Chain: notify voters about newly synced propositions
    if result.get("created", 0) > 0:
        _trigger_notifications_for_new_proposicoes()

    return result


def _trigger_notifications_for_new_proposicoes() -> None:
    """Trigger voter notifications for recently synced propositions.

    Queries propositions synced in the last hour and dispatches a
    notification task for each one that has themes defined.
    """
    from datetime import datetime, timedelta, timezone

    async def _query_and_dispatch() -> None:
        async with get_async_session() as session:
            from sqlalchemy import select
            from app.domain.proposicao import Proposicao
            from app.tasks.notificar_eleitores import notificar_eleitores_task

            cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
            stmt = select(Proposicao).where(
                Proposicao.ultima_sincronizacao >= cutoff
            )
            result = await session.execute(stmt)
            proposicoes = result.scalars().all()

            for prop in proposicoes:
                temas = prop.temas if prop.temas else []
                if temas:
                    notificar_eleitores_task.delay(
                        proposicao_id=prop.id,
                        temas=temas,
                        tipo=prop.tipo or "PL",
                        numero=prop.numero or 0,
                        ano=prop.ano or 0,
                        ementa=prop.ementa or "",
                    )
                    logger.info(
                        "task.sync_proposicoes.triggered_notification",
                        proposicao_id=prop.id,
                    )

    import asyncio
    try:
        asyncio.get_event_loop().run_until_complete(_query_and_dispatch())
    except RuntimeError:
        asyncio.run(_query_and_dispatch())
