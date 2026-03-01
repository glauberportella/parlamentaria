"""Celery task: generate comparative analyses (popular vs parliamentary votes)."""

import asyncio

from app.tasks.celery_app import celery_app
from app.tasks.helpers import get_async_session
from app.logging import get_logger

logger = get_logger(__name__)


@celery_app.task(name="app.tasks.gerar_comparativos.gerar_comparativos_task")
def gerar_comparativos_task() -> dict:
    """Check for parliamentary votes with matching popular votes and generate comparatives.

    Scans for votações that have both a parliamentary result and popular votes
    but no comparative yet, then generates one.

    Returns:
        Dict with generation stats.
    """
    logger.info("task.gerar_comparativos.start")

    async def _run() -> dict:
        async with get_async_session() as session:
            from sqlalchemy import select
            from app.domain.votacao import Votacao
            from app.domain.comparativo import ComparativoVotacao
            from app.services.comparativo_service import ComparativoService

            service = ComparativoService(session)
            stats = {"generated": 0, "skipped": 0, "errors": 0}

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
                existing = await service.get_by_proposicao(votacao.proposicao_id)
                if existing:
                    stats["skipped"] += 1
                    continue

                try:
                    resultado = "APROVADO" if votacao.aprovacao else "REJEITADO"
                    await service.gerar_comparativo(
                        proposicao_id=votacao.proposicao_id,
                        votacao_camara_id=votacao.id,
                        resultado_camara=resultado,
                        votos_camara_sim=votacao.votos_sim or 0,
                        votos_camara_nao=votacao.votos_nao or 0,
                    )
                    stats["generated"] += 1
                except Exception as e:
                    logger.error(
                        "task.gerar_comparativo.error",
                        votacao_id=votacao.id,
                        error=str(e),
                    )
                    stats["errors"] += 1

            await session.commit()
            return stats

    try:
        result = asyncio.get_event_loop().run_until_complete(_run())
    except RuntimeError:
        result = asyncio.run(_run())

    logger.info("task.gerar_comparativos.complete", **result)
    return result
