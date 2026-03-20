"""SocialMediaService — orchestrates social media post generation and publishing."""

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.domain.social_post import (
    RedeSocial,
    SocialPost,
    StatusPost,
    TipoPostSocial,
)
from app.integrations.social_publisher import (
    get_active_networks,
    get_publisher,
)
from app.logging import get_logger
from app.repositories.social_post_repo import SocialPostRepository
from app.services.image_generation_service import ImageGenerationService

logger = get_logger(__name__)

# Types of propositions worth posting about
TIPOS_RELEVANTES: set[str] = set()


def _load_relevant_types() -> set[str]:
    global TIPOS_RELEVANTES
    if not TIPOS_RELEVANTES:
        TIPOS_RELEVANTES = {
            t.strip().upper() for t in settings.social_relevant_types.split(",") if t.strip()
        }
    return TIPOS_RELEVANTES


def is_proposicao_relevante(tipo: str | None) -> bool:
    """Check if a proposition type is relevant for social posts."""
    if not tipo:
        return False
    return tipo.strip().upper() in _load_relevant_types()


class SocialMediaService:
    """Orchestrates social media post generation, image creation and publishing.

    Coordinates between:
    - Repositories (data access)
    - ImageGenerationService (HTML→PNG)
    - SocialPublisher adapters (per-network publishing)
    - SocialMediaAgent (LLM text generation — called externally)
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = SocialPostRepository(session)
        self.image_service = ImageGenerationService()

    async def create_post(
        self,
        tipo: TipoPostSocial,
        rede: RedeSocial,
        texto: str,
        proposicao_id: int | None = None,
        comparativo_id: uuid.UUID | None = None,
        imagem_path: str | None = None,
        imagem_url: str | None = None,
    ) -> SocialPost:
        """Create a social post record.

        If moderation is enabled, post starts as RASCUNHO (draft).
        Otherwise, it starts as APROVADO (ready to publish).
        """
        initial_status = (
            StatusPost.RASCUNHO
            if settings.social_moderation_enabled
            else StatusPost.APROVADO
        )

        post = SocialPost(
            id=uuid.uuid4(),
            tipo=tipo,
            rede=rede,
            texto=texto,
            proposicao_id=proposicao_id,
            comparativo_id=comparativo_id,
            imagem_path=imagem_path,
            imagem_url=imagem_url,
            status=initial_status,
        )
        self.session.add(post)
        await self.session.flush()
        logger.info(
            "social.post_created",
            post_id=str(post.id),
            tipo=tipo.value,
            rede=rede.value,
            status=initial_status.value,
        )
        return post

    async def publish_post(self, post: SocialPost) -> SocialPost:
        """Publish a single post to its target social network.

        Args:
            post: SocialPost with status APROVADO.

        Returns:
            Updated SocialPost with publication result.
        """
        if post.status not in (StatusPost.APROVADO, StatusPost.FALHOU):
            logger.warning(
                "social.publish_skipped",
                post_id=str(post.id),
                status=post.status.value,
            )
            return post

        publisher = get_publisher(post.rede)

        if post.imagem_path:
            result = await publisher.publish_with_image(post.texto, post.imagem_path)
        else:
            result = await publisher.publish_text(post.texto)

        if result.success:
            post.status = StatusPost.PUBLICADO
            post.rede_post_id = result.post_id
            post.publicado_em = datetime.now(timezone.utc)
            post.erro = None
            logger.info(
                "social.post_published",
                post_id=str(post.id),
                rede=post.rede.value,
                rede_post_id=result.post_id,
            )
        else:
            post.status = StatusPost.FALHOU
            post.erro = result.error
            logger.error(
                "social.post_failed",
                post_id=str(post.id),
                rede=post.rede.value,
                error=result.error,
            )

        await self.session.flush()
        return post

    async def create_and_publish_for_all_networks(
        self,
        tipo: TipoPostSocial,
        texts_by_rede: dict[RedeSocial, str],
        proposicao_id: int | None = None,
        comparativo_id: uuid.UUID | None = None,
        images_by_rede: dict[RedeSocial, str] | None = None,
    ) -> list[SocialPost]:
        """Create and publish posts across all active networks.

        Args:
            tipo: Type of social post.
            texts_by_rede: Dict mapping each network to its adapted text.
            proposicao_id: Optional proposition FK.
            comparativo_id: Optional comparative FK.
            images_by_rede: Optional dict mapping network to image file path.

        Returns:
            List of created SocialPost records.
        """
        posts: list[SocialPost] = []
        active_networks = get_active_networks()
        images = images_by_rede or {}

        for rede in active_networks:
            texto = texts_by_rede.get(rede)
            if not texto:
                continue

            # Skip duplicates
            if proposicao_id and await self.repo.exists_for_proposicao_rede_tipo(
                proposicao_id, rede, tipo
            ):
                logger.info(
                    "social.duplicate_skipped",
                    proposicao_id=proposicao_id,
                    rede=rede.value,
                    tipo=tipo.value,
                )
                continue

            if comparativo_id and await self.repo.exists_for_comparativo_rede(
                comparativo_id, rede
            ):
                logger.info(
                    "social.duplicate_skipped",
                    comparativo_id=str(comparativo_id),
                    rede=rede.value,
                )
                continue

            image_path = images.get(rede)
            post = await self.create_post(
                tipo=tipo,
                rede=rede,
                texto=texto,
                proposicao_id=proposicao_id,
                comparativo_id=comparativo_id,
                imagem_path=image_path,
            )
            posts.append(post)

            # Auto-publish if moderation is disabled
            if post.status == StatusPost.APROVADO:
                await self.publish_post(post)

        return posts

    async def generate_comparativo_images(
        self,
        proposicao_label: str,
        sim_pct: float,
        nao_pct: float,
        resultado_camara: str,
        alinhamento_pct: float,
    ) -> dict[RedeSocial, str]:
        """Generate comparative images for all active networks.

        Returns:
            Dict mapping RedeSocial to image file path.
        """
        images: dict[RedeSocial, str] = {}
        for rede in get_active_networks():
            path = await self.image_service.generate_comparativo_image(
                proposicao=proposicao_label,
                voto_popular_sim=sim_pct,
                voto_popular_nao=nao_pct,
                resultado_camara=resultado_camara,
                alinhamento=alinhamento_pct,
                rede=rede.value,
            )
            images[rede] = path
        return images

    async def generate_votacao_images(
        self,
        proposicao_label: str,
        sim_pct: float,
        nao_pct: float,
        abstencao_pct: float,
        total_votos: int,
        temas: list[str],
    ) -> dict[RedeSocial, str]:
        """Generate voting results images for all active networks."""
        images: dict[RedeSocial, str] = {}
        for rede in get_active_networks():
            path = await self.image_service.generate_votacao_image(
                proposicao=proposicao_label,
                sim_pct=sim_pct,
                nao_pct=nao_pct,
                abstencao_pct=abstencao_pct,
                total_votos=total_votos,
                temas=temas,
                rede=rede.value,
            )
            images[rede] = path
        return images

    async def generate_resumo_semanal_images(
        self,
        total_proposicoes: int,
        total_votos: int,
        total_eleitores: int,
        top_proposicoes: list[dict],
        periodo: str,
    ) -> dict[RedeSocial, str]:
        """Generate weekly summary images for all active networks."""
        images: dict[RedeSocial, str] = {}
        for rede in get_active_networks():
            path = await self.image_service.generate_resumo_semanal_image(
                total_proposicoes=total_proposicoes,
                total_votos=total_votos,
                total_eleitores=total_eleitores,
                top_proposicoes=top_proposicoes,
                periodo=periodo,
                rede=rede.value,
            )
            images[rede] = path
        return images

    async def generate_explicativo_images(
        self,
        proposicao_label: str,
        o_que_muda: str,
        areas: list[str],
        argumentos_favor: list[str],
        argumentos_contra: list[str],
    ) -> dict[RedeSocial, str]:
        """Generate educational explainer images for all active networks."""
        images: dict[RedeSocial, str] = {}
        for rede in get_active_networks():
            path = await self.image_service.generate_explicativo_image(
                proposicao=proposicao_label,
                o_que_muda=o_que_muda,
                areas=areas,
                argumentos_favor=argumentos_favor,
                argumentos_contra=argumentos_contra,
                rede=rede.value,
            )
            images[rede] = path
        return images

    async def generate_destaque_images(
        self,
        proposicao_label: str,
        ementa_resumida: str,
        areas: list[str],
        sim_pct: float,
        nao_pct: float,
    ) -> dict[RedeSocial, str]:
        """Generate featured proposition images for all active networks."""
        images: dict[RedeSocial, str] = {}
        for rede in get_active_networks():
            path = await self.image_service.generate_destaque_proposicao_image(
                proposicao=proposicao_label,
                ementa_resumida=ementa_resumida,
                areas=areas,
                sim_pct=sim_pct,
                nao_pct=nao_pct,
                rede=rede.value,
            )
            images[rede] = path
        return images

    async def approve_post(self, post_id: uuid.UUID) -> SocialPost:
        """Approve a draft post for publishing."""
        post = await self.repo.get_by_id(post_id)
        if post is None:
            raise ValueError(f"Post {post_id} não encontrado.")
        if post.status != StatusPost.RASCUNHO:
            raise ValueError(f"Post {post_id} não está em rascunho.")

        post.status = StatusPost.APROVADO
        await self.session.flush()
        logger.info("social.post_approved", post_id=str(post_id))
        return post

    async def cancel_post(self, post_id: uuid.UUID) -> SocialPost:
        """Cancel a draft or approved post."""
        post = await self.repo.get_by_id(post_id)
        if post is None:
            raise ValueError(f"Post {post_id} não encontrado.")
        if post.status in (StatusPost.PUBLICADO,):
            raise ValueError(f"Post {post_id} já foi publicado.")

        post.status = StatusPost.CANCELADO
        await self.session.flush()
        logger.info("social.post_cancelled", post_id=str(post_id))
        return post

    async def update_metrics_for_recent_posts(self, hours: int = 48) -> int:
        """Fetch and update engagement metrics for recently published posts.

        Returns:
            Number of posts updated.
        """
        posts = await self.repo.find_recent_published(hours=hours)
        updated = 0

        for post in posts:
            if not post.rede_post_id:
                continue
            try:
                publisher = get_publisher(post.rede)
                metrics = await publisher.get_metrics(post.rede_post_id)
                post.likes = metrics.likes or 0
                post.shares = metrics.shares or 0
                post.comments = metrics.comments or 0
                post.impressions = metrics.impressions or 0
                updated += 1
            except Exception:
                logger.warning(
                    "social.metrics_update_failed",
                    post_id=str(post.id),
                    rede=post.rede.value,
                )

        if updated > 0:
            await self.session.flush()
            logger.info("social.metrics_updated", count=updated)

        return updated

    async def close(self) -> None:
        """Cleanup resources (browser instance)."""
        await self.image_service.close()
