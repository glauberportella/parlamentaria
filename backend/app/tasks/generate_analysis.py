"""Celery task: generate AI analysis for propositions.

Analyses newly synced or updated propositions by calling the LLM
(Gemini) via LLMAnalysisService and persisting the structured analysis
via AnaliseIAService.
"""

import asyncio

from app.tasks.celery_app import celery_app
from app.tasks.helpers import get_async_session
from app.logging import get_logger

logger = get_logger(__name__)


@celery_app.task(
    name="app.tasks.generate_analysis.generate_analysis_task",
    bind=True,
    max_retries=2,
    default_retry_delay=30,
)
def generate_analysis_task(self, proposicao_id: int | None = None) -> dict:
    """Generate AI analysis for propositions.

    If proposicao_id is given, analyses that single proposition.
    Otherwise, analyses all propositions that have no AI analysis yet.

    Args:
        proposicao_id: Optional specific proposition ID.

    Returns:
        Dict with statistics: analysed, skipped, errors.
    """
    logger.info(
        "task.generate_analysis.start",
        proposicao_id=proposicao_id,
    )

    async def _run() -> dict:
        from app.services.proposicao_service import ProposicaoService
        from app.services.analise_service import AnaliseIAService
        from app.services.llm_analysis_service import LLMAnalysisService, LLMAnalysisError
        from app.schemas.analise_ia import AnaliseIACreate
        from app.config import settings

        stats = {"analysed": 0, "skipped": 0, "errors": 0}

        async with get_async_session() as session:
            prop_service = ProposicaoService(session)
            analise_service = AnaliseIAService(session)
            llm_service = LLMAnalysisService()

            if proposicao_id:
                # Single proposition
                proposicoes = [await prop_service.get_by_id(proposicao_id)]
            else:
                # All propositions without analysis  
                all_props = await prop_service.list_proposicoes(limit=500)
                proposicoes = []
                for p in all_props:
                    existing = await analise_service.get_latest(p.id)
                    if existing is None:
                        proposicoes.append(p)

                logger.info(
                    "task.generate_analysis.found_pending",
                    total=len(proposicoes),
                )

            for prop in proposicoes:
                try:
                    # Check if already analysed (for single mode, skip if has analysis)
                    if proposicao_id is None:
                        existing = await analise_service.get_latest(prop.id)
                        if existing is not None:
                            stats["skipped"] += 1
                            continue

                    # Build proposition data dict for the LLM
                    prop_data = {
                        "id": prop.id,
                        "tipo": prop.tipo,
                        "numero": prop.numero,
                        "ano": prop.ano,
                        "ementa": prop.ementa,
                        "situacao": prop.situacao,
                        "temas": prop.temas,
                        "autores": prop.autores,
                    }

                    # Call LLM
                    analysis_result = await llm_service.analyze_proposition(prop_data)

                    # Persist via AnaliseIAService
                    create_data = AnaliseIACreate(
                        proposicao_id=prop.id,
                        resumo_leigo=analysis_result["resumo_leigo"],
                        impacto_esperado=analysis_result["impacto_esperado"],
                        areas_afetadas=analysis_result["areas_afetadas"],
                        argumentos_favor=analysis_result["argumentos_favor"],
                        argumentos_contra=analysis_result["argumentos_contra"],
                        provedor_llm="google",
                        modelo=settings.agent_model,
                    )

                    async with session.begin_nested():
                        await analise_service.create_analysis(create_data)

                    stats["analysed"] += 1
                    logger.info(
                        "task.generate_analysis.proposition_done",
                        proposicao_id=prop.id,
                    )

                except LLMAnalysisError as e:
                    stats["errors"] += 1
                    logger.error(
                        "task.generate_analysis.llm_error",
                        proposicao_id=prop.id,
                        error=str(e),
                    )
                except Exception as e:
                    stats["errors"] += 1
                    logger.error(
                        "task.generate_analysis.error",
                        proposicao_id=prop.id,
                        error=str(e),
                    )

            try:
                await session.commit()
            except Exception:
                await session.rollback()
                logger.warning("task.generate_analysis.commit_failed_rollback")

        return stats

    try:
        result = asyncio.get_event_loop().run_until_complete(_run())
    except RuntimeError:
        result = asyncio.run(_run())

    logger.info("task.generate_analysis.complete", **result)
    return result


@celery_app.task(
    name="app.tasks.generate_analysis.reanalyze_all_task",
    bind=True,
    max_retries=1,
)
def reanalyze_all_task(self) -> dict:
    """Re-analyze all propositions (creates new version for each).

    Useful for regenerating analyses when the model or prompt changes.
    
    Returns:
        Dict with statistics.
    """
    logger.info("task.reanalyze_all.start")

    async def _run() -> dict:
        from app.services.proposicao_service import ProposicaoService
        from app.services.analise_service import AnaliseIAService
        from app.services.llm_analysis_service import LLMAnalysisService, LLMAnalysisError
        from app.schemas.analise_ia import AnaliseIACreate
        from app.config import settings

        stats = {"analysed": 0, "errors": 0}

        async with get_async_session() as session:
            prop_service = ProposicaoService(session)
            analise_service = AnaliseIAService(session)
            llm_service = LLMAnalysisService()

            all_props = await prop_service.list_proposicoes(limit=500)

            logger.info("task.reanalyze_all.total", total=len(all_props))

            for prop in all_props:
                try:
                    prop_data = {
                        "id": prop.id,
                        "tipo": prop.tipo,
                        "numero": prop.numero,
                        "ano": prop.ano,
                        "ementa": prop.ementa,
                        "situacao": prop.situacao,
                        "temas": prop.temas,
                        "autores": prop.autores,
                    }

                    analysis_result = await llm_service.analyze_proposition(prop_data)

                    create_data = AnaliseIACreate(
                        proposicao_id=prop.id,
                        resumo_leigo=analysis_result["resumo_leigo"],
                        impacto_esperado=analysis_result["impacto_esperado"],
                        areas_afetadas=analysis_result["areas_afetadas"],
                        argumentos_favor=analysis_result["argumentos_favor"],
                        argumentos_contra=analysis_result["argumentos_contra"],
                        provedor_llm="google",
                        modelo=settings.agent_model,
                    )

                    async with session.begin_nested():
                        await analise_service.create_analysis(create_data)

                    stats["analysed"] += 1

                except LLMAnalysisError as e:
                    stats["errors"] += 1
                    logger.error(
                        "task.reanalyze_all.llm_error",
                        proposicao_id=prop.id,
                        error=str(e),
                    )
                except Exception as e:
                    stats["errors"] += 1
                    logger.error(
                        "task.reanalyze_all.error",
                        proposicao_id=prop.id,
                        error=str(e),
                    )

            try:
                await session.commit()
            except Exception:
                await session.rollback()
                logger.warning("task.reanalyze_all.commit_failed_rollback")

        return stats

    try:
        result = asyncio.get_event_loop().run_until_complete(_run())
    except RuntimeError:
        result = asyncio.run(_run())

    logger.info("task.reanalyze_all.complete", **result)
    return result
