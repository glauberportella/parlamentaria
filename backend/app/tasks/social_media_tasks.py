"""Celery tasks for social media post generation and publishing.

Tasks are triggered by:
- Celery Beat schedule (weekly summary, metrics update)
- Other tasks (gerar_comparativos → post_comparativo)
- Admin actions (approve post → publish)
"""

import asyncio

from app.tasks.celery_app import celery_app
from app.tasks.helpers import get_async_session
from app.logging import get_logger

logger = get_logger(__name__)


@celery_app.task(
    name="app.tasks.social_media_tasks.post_resumo_semanal_task",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    max_retries=2,
)
def post_resumo_semanal_task() -> dict:
    """Generate and publish weekly summary across all active networks.

    Scheduled via Celery Beat (default: Mondays at SOCIAL_WEEKLY_HOUR).

    Returns:
        Dict with creation stats.
    """
    from app.config import settings

    if not settings.social_enabled:
        return {"status": "disabled"}

    logger.info("task.social.resumo_semanal.start")

    async def _run() -> dict:
        async with get_async_session() as session:
            from datetime import datetime, timedelta, timezone
            from sqlalchemy import func, select
            from app.domain.proposicao import Proposicao
            from app.domain.voto_popular import VotoPopular
            from app.domain.eleitor import Eleitor
            from app.domain.social_post import RedeSocial, TipoPostSocial
            from app.services.social_media_service import SocialMediaService

            service = SocialMediaService(session)
            now = datetime.now(timezone.utc)
            week_ago = now - timedelta(days=7)

            # Gather KPIs
            prop_count = (await session.execute(
                select(func.count()).select_from(Proposicao)
            )).scalar_one()

            vote_count = (await session.execute(
                select(func.count()).select_from(VotoPopular)
                .where(VotoPopular.data_voto >= week_ago)
            )).scalar_one()

            voter_count = (await session.execute(
                select(func.count()).select_from(Eleitor)
            )).scalar_one()

            # Top voted propositions this week
            top_stmt = (
                select(
                    VotoPopular.proposicao_id,
                    func.count().label("total"),
                )
                .where(VotoPopular.data_voto >= week_ago)
                .group_by(VotoPopular.proposicao_id)
                .order_by(func.count().desc())
                .limit(5)
            )
            top_result = await session.execute(top_stmt)
            top_rows = top_result.all()

            top_proposicoes = []
            for row in top_rows:
                prop = await session.get(Proposicao, row.proposicao_id)
                if prop:
                    top_proposicoes.append({
                        "nome": f"{prop.tipo} {prop.numero}/{prop.ano}",
                        "votos": row.total,
                    })

            periodo = f"{week_ago.strftime('%d/%m')} a {now.strftime('%d/%m/%Y')}"

            # Generate images
            images = await service.generate_resumo_semanal_images(
                total_proposicoes=prop_count,
                total_votos=vote_count,
                total_eleitores=voter_count,
                top_proposicoes=top_proposicoes,
                periodo=periodo,
            )

            # Build text data for each network (simplified — in production,
            # the SocialMediaAgent LLM would generate optimized text)
            texto_base = (
                f"📊 Resumo Semanal Parlamentaria ({periodo})\n\n"
                f"📋 {prop_count} proposições ativas\n"
                f"🗳️ {vote_count} votos populares esta semana\n"
                f"👥 {voter_count} eleitores cadastrados\n"
            )
            if top_proposicoes:
                texto_base += "\n🔥 Mais votadas:\n"
                for i, tp in enumerate(top_proposicoes, 1):
                    texto_base += f"  {i}. {tp['nome']} — {tp['votos']} votos\n"

            texto_base += "\n#Parlamentaria #DemocraciaParticipativa"

            from app.integrations.social_publisher import get_active_networks
            texts = {rede: texto_base for rede in get_active_networks()}

            posts = await service.create_and_publish_for_all_networks(
                tipo=TipoPostSocial.RESUMO_SEMANAL,
                texts_by_rede=texts,
                images_by_rede=images,
            )

            try:
                await session.commit()
            except Exception:
                await session.rollback()
                logger.warning("task.social.resumo_semanal.commit_failed")

            await service.close()
            return {"posts_created": len(posts)}

    try:
        result = asyncio.get_event_loop().run_until_complete(_run())
    except RuntimeError:
        result = asyncio.run(_run())

    logger.info("task.social.resumo_semanal.complete", **result)
    return result


@celery_app.task(
    name="app.tasks.social_media_tasks.post_comparativo_task",
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=2,
)
def post_comparativo_task(comparativo_id: str) -> dict:
    """Generate and publish a comparative post (popular vs parliamentary).

    Triggered by gerar_comparativos_task when a new comparative is created.

    Args:
        comparativo_id: UUID string of the ComparativoVotacao.

    Returns:
        Dict with publication stats.
    """
    from app.config import settings

    if not settings.social_enabled:
        return {"status": "disabled"}

    logger.info("task.social.comparativo.start", comparativo_id=comparativo_id)

    async def _run() -> dict:
        import uuid
        async with get_async_session() as session:
            from app.domain.comparativo import ComparativoVotacao
            from app.domain.proposicao import Proposicao
            from app.domain.social_post import TipoPostSocial
            from app.services.social_media_service import SocialMediaService
            from app.integrations.social_publisher import get_active_networks

            comp_uuid = uuid.UUID(comparativo_id)
            comp = await session.get(ComparativoVotacao, comp_uuid)
            if not comp:
                return {"error": "comparativo not found"}

            prop = await session.get(Proposicao, comp.proposicao_id)
            if not prop:
                return {"error": "proposicao not found"}

            service = SocialMediaService(session)
            label = f"{prop.tipo} {prop.numero}/{prop.ano}"

            total_pop = comp.voto_popular_sim + comp.voto_popular_nao + comp.voto_popular_abstencao
            sim_pct = round(comp.voto_popular_sim / total_pop * 100, 1) if total_pop > 0 else 0
            nao_pct = round(comp.voto_popular_nao / total_pop * 100, 1) if total_pop > 0 else 0

            resultado = comp.resultado_camara or "APROVADO"
            alinhamento_pct = round((comp.alinhamento or 0) * 100, 1)

            images = await service.generate_comparativo_images(
                proposicao_label=label,
                sim_pct=sim_pct,
                nao_pct=nao_pct,
                resultado_camara=resultado,
                alinhamento_pct=alinhamento_pct,
            )

            texto_base = (
                f"🏛️ Comparativo: {label}\n\n"
                f"🗳️ Voto Popular: {sim_pct}% SIM / {nao_pct}% NÃO\n"
                f"🏛️ Câmara: {resultado}\n"
                f"📏 Alinhamento: {alinhamento_pct}%\n\n"
                f"#Parlamentaria #DemocraciaParticipativa"
            )

            texts = {rede: texto_base for rede in get_active_networks()}

            posts = await service.create_and_publish_for_all_networks(
                tipo=TipoPostSocial.COMPARATIVO,
                texts_by_rede=texts,
                comparativo_id=comp_uuid,
                proposicao_id=comp.proposicao_id,
                images_by_rede=images,
            )

            try:
                await session.commit()
            except Exception:
                await session.rollback()

            await service.close()
            return {"posts_created": len(posts)}

    try:
        result = asyncio.get_event_loop().run_until_complete(_run())
    except RuntimeError:
        result = asyncio.run(_run())

    logger.info("task.social.comparativo.complete", **result)
    return result


@celery_app.task(
    name="app.tasks.social_media_tasks.post_votacao_relevante_task",
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=2,
)
def post_votacao_relevante_task(proposicao_id: int) -> dict:
    """Publish when a proposition reaches the vote threshold.

    Args:
        proposicao_id: Proposition ID that reached the threshold.

    Returns:
        Dict with publication stats.
    """
    from app.config import settings

    if not settings.social_enabled:
        return {"status": "disabled"}

    logger.info("task.social.votacao_relevante.start", proposicao_id=proposicao_id)

    async def _run() -> dict:
        async with get_async_session() as session:
            from sqlalchemy import select, func
            from app.domain.proposicao import Proposicao
            from app.domain.voto_popular import VotoPopular, VotoEnum
            from app.domain.social_post import TipoPostSocial
            from app.services.social_media_service import SocialMediaService
            from app.integrations.social_publisher import get_active_networks

            prop = await session.get(Proposicao, proposicao_id)
            if not prop:
                return {"error": "proposicao not found"}

            # Get vote counts
            counts_stmt = (
                select(VotoPopular.voto, func.count())
                .where(VotoPopular.proposicao_id == proposicao_id)
                .group_by(VotoPopular.voto)
            )
            counts_result = await session.execute(counts_stmt)
            counts = {row[0]: row[1] for row in counts_result.all()}

            sim = counts.get(VotoEnum.SIM, 0)
            nao = counts.get(VotoEnum.NAO, 0)
            abst = counts.get(VotoEnum.ABSTENCAO, 0)
            total = sim + nao + abst
            if total == 0:
                return {"error": "no votes"}

            sim_pct = round(sim / total * 100, 1)
            nao_pct = round(nao / total * 100, 1)
            abst_pct = round(abst / total * 100, 1)

            service = SocialMediaService(session)
            label = f"{prop.tipo} {prop.numero}/{prop.ano}"
            temas = prop.temas or []

            images = await service.generate_votacao_images(
                proposicao_label=label,
                sim_pct=sim_pct,
                nao_pct=nao_pct,
                abstencao_pct=abst_pct,
                total_votos=total,
                temas=temas,
            )

            texto_base = (
                f"🗳️ {label} atingiu {total} votos populares!\n\n"
                f"👍 SIM: {sim_pct}%\n"
                f"👎 NÃO: {nao_pct}%\n"
                f"⚖️ ABSTENÇÃO: {abst_pct}%\n\n"
                f"#Parlamentaria #DemocraciaParticipativa"
            )

            texts = {rede: texto_base for rede in get_active_networks()}

            posts = await service.create_and_publish_for_all_networks(
                tipo=TipoPostSocial.VOTACAO_RELEVANTE,
                texts_by_rede=texts,
                proposicao_id=proposicao_id,
                images_by_rede=images,
            )

            try:
                await session.commit()
            except Exception:
                await session.rollback()

            await service.close()
            return {"posts_created": len(posts)}

    try:
        result = asyncio.get_event_loop().run_until_complete(_run())
    except RuntimeError:
        result = asyncio.run(_run())

    logger.info("task.social.votacao_relevante.complete", **result)
    return result


@celery_app.task(
    name="app.tasks.social_media_tasks.post_explicativo_educativo_task",
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=2,
)
def post_explicativo_educativo_task(proposicao_id: int) -> dict:
    """Generate and publish an educational explainer post for a proposition.

    Triggered when AnaliseIA is generated for a relevant proposition type.

    Args:
        proposicao_id: Proposition ID that was analyzed.

    Returns:
        Dict with publication stats.
    """
    from app.config import settings

    if not settings.social_enabled or not settings.social_educational_enabled:
        return {"status": "disabled"}

    logger.info("task.social.explicativo.start", proposicao_id=proposicao_id)

    async def _run() -> dict:
        async with get_async_session() as session:
            from app.domain.proposicao import Proposicao
            from app.domain.analise_ia import AnaliseIA
            from app.domain.social_post import TipoPostSocial
            from app.services.social_media_service import SocialMediaService, is_proposicao_relevante
            from app.services.analise_service import AnaliseIAService
            from app.integrations.social_publisher import get_active_networks

            prop = await session.get(Proposicao, proposicao_id)
            if not prop:
                return {"error": "proposicao not found"}

            if not is_proposicao_relevante(prop.tipo):
                return {"status": "skipped", "reason": f"tipo {prop.tipo} not relevant"}

            analise_service = AnaliseIAService(session)
            analise = await analise_service.get_latest(proposicao_id)
            if not analise:
                return {"error": "no analysis found"}

            service = SocialMediaService(session)
            label = f"{prop.tipo} {prop.numero}/{prop.ano}"

            images = await service.generate_explicativo_images(
                proposicao_label=label,
                o_que_muda=analise.resumo_leigo or prop.ementa or "",
                areas=analise.areas_afetadas or [],
                argumentos_favor=analise.argumentos_favor or [],
                argumentos_contra=analise.argumentos_contra or [],
            )

            texto_base = (
                f"📖 Entenda: {label}\n\n"
                f"{analise.resumo_leigo or prop.ementa or ''}\n\n"
            )
            if analise.areas_afetadas:
                texto_base += f"📌 Áreas: {', '.join(analise.areas_afetadas[:3])}\n"
            texto_base += "\n#Parlamentaria #DemocraciaParticipativa"

            texts = {rede: texto_base for rede in get_active_networks()}

            posts = await service.create_and_publish_for_all_networks(
                tipo=TipoPostSocial.EXPLICATIVO_EDUCATIVO,
                texts_by_rede=texts,
                proposicao_id=proposicao_id,
                images_by_rede=images,
            )

            try:
                await session.commit()
            except Exception:
                await session.rollback()

            await service.close()
            return {"posts_created": len(posts)}

    try:
        result = asyncio.get_event_loop().run_until_complete(_run())
    except RuntimeError:
        result = asyncio.run(_run())

    logger.info("task.social.explicativo.complete", **result)
    return result


@celery_app.task(
    name="app.tasks.social_media_tasks.post_destaque_proposicao_task",
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=2,
)
def post_destaque_proposicao_task(proposicao_id: int) -> dict:
    """Publish a featured proposition highlight post.

    Args:
        proposicao_id: Proposition ID to feature.

    Returns:
        Dict with publication stats.
    """
    from app.config import settings

    if not settings.social_enabled:
        return {"status": "disabled"}

    logger.info("task.social.destaque.start", proposicao_id=proposicao_id)

    async def _run() -> dict:
        async with get_async_session() as session:
            from sqlalchemy import select, func
            from app.domain.proposicao import Proposicao
            from app.domain.voto_popular import VotoPopular, VotoEnum
            from app.domain.social_post import TipoPostSocial
            from app.services.social_media_service import SocialMediaService
            from app.services.analise_service import AnaliseIAService
            from app.integrations.social_publisher import get_active_networks

            prop = await session.get(Proposicao, proposicao_id)
            if not prop:
                return {"error": "proposicao not found"}

            analise_service = AnaliseIAService(session)
            analise = await analise_service.get_latest(proposicao_id)

            # Get vote counts
            counts_stmt = (
                select(VotoPopular.voto, func.count())
                .where(VotoPopular.proposicao_id == proposicao_id)
                .group_by(VotoPopular.voto)
            )
            counts_result = await session.execute(counts_stmt)
            counts = {row[0]: row[1] for row in counts_result.all()}

            sim = counts.get(VotoEnum.SIM, 0)
            nao = counts.get(VotoEnum.NAO, 0)
            total = sim + nao
            sim_pct = round(sim / total * 100, 1) if total > 0 else 0
            nao_pct = round(nao / total * 100, 1) if total > 0 else 0

            service = SocialMediaService(session)
            label = f"{prop.tipo} {prop.numero}/{prop.ano}"
            ementa = (
                analise.resumo_leigo if analise and analise.resumo_leigo
                else prop.ementa or ""
            )

            images = await service.generate_destaque_images(
                proposicao_label=label,
                ementa_resumida=ementa[:200],
                areas=getattr(analise, "areas_afetadas", None) or prop.temas or [],
                sim_pct=sim_pct,
                nao_pct=nao_pct,
            )

            texto_base = (
                f"⭐ Destaque: {label}\n\n"
                f"{ementa[:200]}\n\n"
                f"👍 {sim_pct}% SIM / 👎 {nao_pct}% NÃO\n\n"
                f"#Parlamentaria #DemocraciaParticipativa"
            )

            texts = {rede: texto_base for rede in get_active_networks()}

            posts = await service.create_and_publish_for_all_networks(
                tipo=TipoPostSocial.DESTAQUE_PROPOSICAO,
                texts_by_rede=texts,
                proposicao_id=proposicao_id,
                images_by_rede=images,
            )

            try:
                await session.commit()
            except Exception:
                await session.rollback()

            await service.close()
            return {"posts_created": len(posts)}

    try:
        result = asyncio.get_event_loop().run_until_complete(_run())
    except RuntimeError:
        result = asyncio.run(_run())

    logger.info("task.social.destaque.complete", **result)
    return result


@celery_app.task(
    name="app.tasks.social_media_tasks.atualizar_metricas_task",
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=2,
)
def atualizar_metricas_task() -> dict:
    """Update engagement metrics for recently published posts.

    Fetches likes/shares/comments from each network's API for posts
    published in the last 48 hours. Scheduled 4x/day via Celery Beat.

    Returns:
        Dict with update stats.
    """
    from app.config import settings

    if not settings.social_enabled:
        return {"status": "disabled"}

    logger.info("task.social.metricas.start")

    async def _run() -> dict:
        async with get_async_session() as session:
            from app.services.social_media_service import SocialMediaService

            service = SocialMediaService(session)
            updated = await service.update_metrics_for_recent_posts(hours=48)

            try:
                await session.commit()
            except Exception:
                await session.rollback()

            await service.close()
            return {"posts_updated": updated}

    try:
        result = asyncio.get_event_loop().run_until_complete(_run())
    except RuntimeError:
        result = asyncio.run(_run())

    logger.info("task.social.metricas.complete", **result)
    return result


@celery_app.task(
    name="app.tasks.social_media_tasks.publicar_post_aprovado_task",
)
def publicar_post_aprovado_task(post_id: str) -> dict:
    """Publish a post that was approved through moderation.

    Args:
        post_id: UUID string of the SocialPost.

    Returns:
        Dict with publication result.
    """
    from app.config import settings

    if not settings.social_enabled:
        return {"status": "disabled"}

    logger.info("task.social.publicar_aprovado.start", post_id=post_id)

    async def _run() -> dict:
        import uuid
        async with get_async_session() as session:
            from app.domain.social_post import SocialPost, StatusPost
            from app.services.social_media_service import SocialMediaService

            post = await session.get(SocialPost, uuid.UUID(post_id))
            if not post:
                return {"error": "post not found"}
            if post.status != StatusPost.APROVADO:
                return {"error": f"post status is {post.status.value}, expected APROVADO"}

            service = SocialMediaService(session)
            await service.publish_post(post)

            try:
                await session.commit()
            except Exception:
                await session.rollback()

            await service.close()
            return {"published": post.status.value == "publicado"}

    try:
        result = asyncio.get_event_loop().run_until_complete(_run())
    except RuntimeError:
        result = asyncio.run(_run())

    logger.info("task.social.publicar_aprovado.complete", **result)
    return result
