"""Celery task: generate comparative analyses (popular vs parliamentary votes).

After generating each comparative, dispatches webhook events and notifies
voters who participated in the popular vote.
"""

import asyncio

from app.tasks.celery_app import celery_app
from app.tasks.helpers import get_async_session
from app.logging import get_logger

logger = get_logger(__name__)


@celery_app.task(
    name="app.tasks.gerar_comparativos.gerar_comparativos_task",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    max_retries=3,
    retry_jitter=True,
)
def gerar_comparativos_task() -> dict:
    """Check for parliamentary votes with matching popular votes and generate comparatives.

    Scans for votações that have both a parliamentary result and popular votes
    but no comparative yet, then generates one. After generation, dispatches
    webhook events and triggers voter notifications.

    Returns:
        Dict with generation stats.
    """
    logger.info("task.gerar_comparativos.start")

    async def _run() -> dict:
        async with get_async_session() as session:
            from sqlalchemy import select
            from app.domain.votacao import Votacao
            from app.domain.proposicao import Proposicao
            from app.services.comparativo_service import ComparativoService

            service = ComparativoService(session)
            stats = {"generated": 0, "skipped": 0, "errors": 0, "webhooks_dispatched": 0, "notifications_triggered": 0}

            # Find votações that have a result but no comparative
            stmt = (
                select(Votacao)
                .where(
                    Votacao.aprovacao.isnot(None),
                    Votacao.proposicao_id.isnot(None),
                )
                .limit(100)
            )
            result = await session.execute(stmt)
            votacoes = result.scalars().all()

            for votacao in votacoes:
                # Check if comparative already exists
                existing = await service.exists_for_votacao(votacao.id)
                if existing:
                    stats["skipped"] += 1
                    continue

                try:
                    async with session.begin_nested():
                        resultado = "APROVADO" if votacao.aprovacao else "REJEITADO"
                        comparativo = await service.gerar_comparativo(
                            proposicao_id=votacao.proposicao_id,
                            votacao_camara_id=votacao.id,
                            resultado_camara=resultado,
                            votos_camara_sim=votacao.votos_sim or 0,
                            votos_camara_nao=votacao.votos_nao or 0,
                        )
                    stats["generated"] += 1

                    # Fetch proposicao details for notifications
                    proposicao = await session.get(Proposicao, votacao.proposicao_id)

                    # Calculate popular SIM percentage
                    total_popular = (
                        comparativo.voto_popular_sim
                        + comparativo.voto_popular_nao
                        + comparativo.voto_popular_abstencao
                    )
                    pct_sim = (
                        round(comparativo.voto_popular_sim / total_popular * 100, 1)
                        if total_popular > 0
                        else 0.0
                    )

                    # Dispatch webhook event for comparativo_gerado
                    try:
                        from app.tasks.dispatch_webhooks import dispatch_webhooks_task

                        dispatch_webhooks_task.delay(
                            "comparativo_gerado",
                            {
                                "proposicao_id": votacao.proposicao_id,
                                "votacao_camara_id": votacao.id,
                                "resultado_camara": resultado,
                                "alinhamento": comparativo.alinhamento,
                                "voto_popular_sim": comparativo.voto_popular_sim,
                                "voto_popular_nao": comparativo.voto_popular_nao,
                                "votos_camara_sim": votacao.votos_sim or 0,
                                "votos_camara_nao": votacao.votos_nao or 0,
                            },
                        )
                        stats["webhooks_dispatched"] += 1
                    except Exception as e:
                        logger.warning(
                            "task.gerar_comparativo.webhook_dispatch_error",
                            votacao_id=votacao.id,
                            error=str(e),
                        )

                    # Notify voters who participated in the popular vote
                    try:
                        from app.tasks.notificar_eleitores import notificar_comparativo_task

                        notificar_comparativo_task.delay(
                            proposicao_id=votacao.proposicao_id,
                            tipo=proposicao.tipo if proposicao else "PL",
                            numero=proposicao.numero if proposicao else 0,
                            ano=proposicao.ano if proposicao else 0,
                            resultado_camara=resultado,
                            percentual_sim_popular=pct_sim,
                            alinhamento=comparativo.alinhamento,
                        )
                        stats["notifications_triggered"] += 1
                    except Exception as e:
                        logger.warning(
                            "task.gerar_comparativo.notification_error",
                            votacao_id=votacao.id,
                            error=str(e),
                        )

                except Exception as e:
                    logger.error(
                        "task.gerar_comparativo.error",
                        votacao_id=votacao.id,
                        error=str(e),
                    )
                    stats["errors"] += 1

            try:
                await session.commit()
            except Exception:
                await session.rollback()
                logger.warning("task.gerar_comparativos.commit_failed_rollback")
            return stats

    try:
        result = asyncio.get_event_loop().run_until_complete(_run())
    except RuntimeError:
        result = asyncio.run(_run())

    logger.info("task.gerar_comparativos.complete", **result)
    return result
