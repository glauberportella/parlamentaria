"""Tests for social media module — repository, service, tasks, router."""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.domain.social_post import (
    RedeSocial,
    SocialPost,
    StatusPost,
    TipoPostSocial,
)
from app.repositories.social_post_repo import SocialPostRepository
from app.schemas.social_post import SocialPostCreate, SocialPostResponse

# Pre-import modules that trigger db.session loading so that task imports
# don't fail when running this file in isolation.
import app.tasks.social_media_tasks as _social_tasks_mod  # noqa: F401


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_social_post_data() -> dict:
    """Return valid SocialPost field values."""
    return {
        "id": uuid.uuid4(),
        "tipo": TipoPostSocial.VOTACAO_RELEVANTE,
        "rede": RedeSocial.TWITTER,
        "texto": "🗳️ PL 100/2024 atingiu 100 votos!",
        "status": StatusPost.RASCUNHO,
    }


@pytest.fixture
async def social_post(
    db_session: AsyncSession, sample_social_post_data: dict
) -> SocialPost:
    """Create and return a persisted SocialPost."""
    post = SocialPost(**sample_social_post_data)
    db_session.add(post)
    await db_session.commit()
    await db_session.refresh(post)
    return post


# ---------------------------------------------------------------------------
# Repository Tests
# ---------------------------------------------------------------------------


class TestSocialPostRepository:
    async def test_create_and_retrieve(
        self, db_session: AsyncSession, sample_social_post_data: dict
    ):
        repo = SocialPostRepository(db_session)
        post = SocialPost(**sample_social_post_data)
        created = await repo.create(post)
        assert created.id == sample_social_post_data["id"]
        assert created.rede == RedeSocial.TWITTER

    async def test_find_by_status(
        self, db_session: AsyncSession, social_post: SocialPost
    ):
        repo = SocialPostRepository(db_session)
        results = await repo.find_by_status(StatusPost.RASCUNHO)
        assert len(results) == 1
        assert results[0].id == social_post.id

    async def test_find_by_rede(
        self, db_session: AsyncSession, social_post: SocialPost
    ):
        repo = SocialPostRepository(db_session)
        results = await repo.find_by_rede(RedeSocial.TWITTER)
        assert len(results) == 1

    async def test_find_by_tipo(
        self, db_session: AsyncSession, social_post: SocialPost
    ):
        repo = SocialPostRepository(db_session)
        results = await repo.find_by_tipo(TipoPostSocial.VOTACAO_RELEVANTE)
        assert len(results) == 1

    async def test_list_filtered_with_no_filters(
        self, db_session: AsyncSession, social_post: SocialPost
    ):
        repo = SocialPostRepository(db_session)
        items, total = await repo.list_filtered()
        assert total == 1
        assert len(items) == 1

    async def test_list_filtered_by_rede(
        self, db_session: AsyncSession, social_post: SocialPost
    ):
        repo = SocialPostRepository(db_session)
        items, total = await repo.list_filtered(rede=RedeSocial.FACEBOOK)
        assert total == 0

    async def test_exists_for_proposicao_rede_tipo_false(
        self, db_session: AsyncSession
    ):
        repo = SocialPostRepository(db_session)
        exists = await repo.exists_for_proposicao_rede_tipo(
            999, RedeSocial.TWITTER, TipoPostSocial.COMPARATIVO
        )
        assert exists is False

    async def test_exists_for_proposicao_rede_tipo_true(
        self, db_session: AsyncSession
    ):
        repo = SocialPostRepository(db_session)
        post = SocialPost(
            id=uuid.uuid4(),
            tipo=TipoPostSocial.COMPARATIVO,
            rede=RedeSocial.TWITTER,
            texto="Test",
            status=StatusPost.PUBLICADO,
            proposicao_id=999,
        )
        await repo.create(post)
        assert await repo.exists_for_proposicao_rede_tipo(
            999, RedeSocial.TWITTER, TipoPostSocial.COMPARATIVO
        ) is True

    async def test_count_by_rede(
        self, db_session: AsyncSession, social_post: SocialPost
    ):
        repo = SocialPostRepository(db_session)
        counts = await repo.count_by_rede()
        assert "twitter" in counts
        assert counts["twitter"] == 1

    async def test_count_by_tipo(
        self, db_session: AsyncSession, social_post: SocialPost
    ):
        repo = SocialPostRepository(db_session)
        counts = await repo.count_by_tipo()
        assert "votacao_relevante" in counts

    async def test_get_aggregated_metrics(
        self, db_session: AsyncSession, social_post: SocialPost
    ):
        repo = SocialPostRepository(db_session)
        metrics = await repo.get_aggregated_metrics()
        assert "total_posts" in metrics
        assert metrics["total_posts"] == 1


# ---------------------------------------------------------------------------
# Schema Tests
# ---------------------------------------------------------------------------


class TestSocialPostSchemas:
    def test_create_schema(self):
        schema = SocialPostCreate(
            tipo=TipoPostSocial.RESUMO_SEMANAL,
            rede=RedeSocial.FACEBOOK,
            texto="Resumo da semana!",
        )
        assert schema.tipo == TipoPostSocial.RESUMO_SEMANAL

    def test_response_from_attributes(self, social_post: SocialPost):
        resp = SocialPostResponse.model_validate(social_post)
        assert resp.rede == RedeSocial.TWITTER
        assert resp.status == StatusPost.RASCUNHO


# ---------------------------------------------------------------------------
# Publisher Tests (mock-based)
# ---------------------------------------------------------------------------


class TestPublisherFactory:
    def test_get_publisher_twitter(self):
        with patch("app.integrations.social_publisher.settings") as ms:
            ms.social_networks = "twitter,facebook,discord,reddit"
            ms.twitter_enabled = True
            from app.integrations.social_publisher import get_publisher
            from app.integrations.twitter_publisher import TwitterPublisher

            publisher = get_publisher(RedeSocial.TWITTER)
            assert isinstance(publisher, TwitterPublisher)

    def test_get_publisher_facebook(self):
        with patch("app.integrations.social_publisher.settings") as ms:
            ms.social_networks = "twitter,facebook,discord,reddit"
            ms.facebook_enabled = True
            from app.integrations.social_publisher import get_publisher
            from app.integrations.facebook_publisher import FacebookPublisher

            publisher = get_publisher(RedeSocial.FACEBOOK)
            assert isinstance(publisher, FacebookPublisher)

    def test_get_publisher_discord(self):
        with patch("app.integrations.social_publisher.settings") as ms:
            ms.social_networks = "twitter,facebook,discord,reddit"
            ms.discord_enabled = True
            from app.integrations.social_publisher import get_publisher
            from app.integrations.discord_publisher import DiscordPublisher

            publisher = get_publisher(RedeSocial.DISCORD)
            assert isinstance(publisher, DiscordPublisher)

    def test_get_publisher_reddit(self):
        with patch("app.integrations.social_publisher.settings") as ms:
            ms.social_networks = "twitter,facebook,discord,reddit"
            ms.reddit_enabled = True
            from app.integrations.social_publisher import get_publisher
            from app.integrations.reddit_publisher import RedditPublisher

            publisher = get_publisher(RedeSocial.REDDIT)
            assert isinstance(publisher, RedditPublisher)

    def test_get_active_networks(self):
        with patch("app.integrations.social_publisher.settings") as ms:
            ms.social_networks = "twitter,facebook"
            ms.twitter_enabled = True
            ms.facebook_enabled = True
            ms.instagram_enabled = False
            ms.linkedin_enabled = False
            ms.discord_enabled = False
            ms.reddit_enabled = False
            from app.integrations.social_publisher import get_active_networks

            networks = get_active_networks()
            assert RedeSocial.TWITTER in networks
            assert RedeSocial.FACEBOOK in networks

    def test_get_active_networks_empty(self):
        with patch("app.integrations.social_publisher.settings") as ms:
            ms.social_networks = ""
            ms.twitter_enabled = False
            ms.facebook_enabled = False
            ms.instagram_enabled = False
            ms.linkedin_enabled = False
            ms.discord_enabled = False
            ms.reddit_enabled = False
            from app.integrations.social_publisher import get_active_networks

            networks = get_active_networks()
            assert networks == []


# ---------------------------------------------------------------------------
# Service Tests (with mock publisher)
# ---------------------------------------------------------------------------


class TestSocialMediaService:
    async def test_create_post_with_moderation(self, db_session: AsyncSession):
        from app.services.social_media_service import SocialMediaService

        with patch("app.services.social_media_service.settings") as ms:
            ms.social_moderation_enabled = True
            service = SocialMediaService(db_session)
            post = await service.create_post(
                tipo=TipoPostSocial.VOTACAO_RELEVANTE,
                rede=RedeSocial.TWITTER,
                texto="Test post",
            )
            assert post.status == StatusPost.RASCUNHO

    async def test_create_post_without_moderation(self, db_session: AsyncSession):
        from app.services.social_media_service import SocialMediaService

        with patch("app.services.social_media_service.settings") as ms:
            ms.social_moderation_enabled = False
            service = SocialMediaService(db_session)
            post = await service.create_post(
                tipo=TipoPostSocial.VOTACAO_RELEVANTE,
                rede=RedeSocial.TWITTER,
                texto="Test post",
            )
            assert post.status == StatusPost.APROVADO

    async def test_approve_post(
        self, db_session: AsyncSession, social_post: SocialPost
    ):
        from app.services.social_media_service import SocialMediaService

        service = SocialMediaService(db_session)
        result = await service.approve_post(social_post.id)
        assert result.status == StatusPost.APROVADO

    async def test_cancel_post(
        self, db_session: AsyncSession, social_post: SocialPost
    ):
        from app.services.social_media_service import SocialMediaService

        service = SocialMediaService(db_session)
        result = await service.cancel_post(social_post.id)
        assert result.status == StatusPost.CANCELADO

    async def test_publish_post_success(
        self, db_session: AsyncSession, social_post: SocialPost
    ):
        social_post.status = StatusPost.APROVADO
        await db_session.commit()

        mock_publisher = MagicMock()
        mock_publisher.publish_text = AsyncMock(
            return_value=MagicMock(success=True, post_id="123", url="https://x.com/123", error=None)
        )

        with patch(
            "app.services.social_media_service.get_publisher",
            return_value=mock_publisher,
        ):
            from app.services.social_media_service import SocialMediaService

            service = SocialMediaService(db_session)
            await service.publish_post(social_post)
            assert social_post.status == StatusPost.PUBLICADO
            assert social_post.rede_post_id == "123"

    async def test_publish_post_failure(
        self, db_session: AsyncSession, social_post: SocialPost
    ):
        social_post.status = StatusPost.APROVADO
        await db_session.commit()

        mock_publisher = MagicMock()
        mock_publisher.publish_text = AsyncMock(
            return_value=MagicMock(success=False, post_id=None, url=None, error="rate limited")
        )

        with patch(
            "app.services.social_media_service.get_publisher",
            return_value=mock_publisher,
        ):
            from app.services.social_media_service import SocialMediaService

            service = SocialMediaService(db_session)
            await service.publish_post(social_post)
            assert social_post.status == StatusPost.FALHOU
            assert "rate limited" in social_post.erro


class TestIsProposicaoRelevante:
    def test_pl_is_relevant(self):
        import app.services.social_media_service as sms

        # Reset cached set so settings mock takes effect
        sms.TIPOS_RELEVANTES = set()
        with patch.object(sms, "settings") as ms:
            ms.social_relevant_types = "PEC,MPV,PL,PLP,PDL"
            assert sms.is_proposicao_relevante("PL") is True
        sms.TIPOS_RELEVANTES = set()  # cleanup

    def test_req_is_not_relevant(self):
        import app.services.social_media_service as sms

        sms.TIPOS_RELEVANTES = set()
        with patch.object(sms, "settings") as ms:
            ms.social_relevant_types = "PEC,MPV,PL,PLP,PDL"
            assert sms.is_proposicao_relevante("REQ") is False
        sms.TIPOS_RELEVANTES = set()


# ---------------------------------------------------------------------------
# Task Tests (mock-based — no real DB or API)
# ---------------------------------------------------------------------------


class TestSocialMediaTasks:
    def test_resumo_semanal_disabled(self):
        with patch("app.config.settings") as ms:
            ms.social_enabled = False
            result = _social_tasks_mod.post_resumo_semanal_task()
            assert result["status"] == "disabled"

    def test_comparativo_disabled(self):
        with patch("app.config.settings") as ms:
            ms.social_enabled = False
            result = _social_tasks_mod.post_comparativo_task(str(uuid.uuid4()))
            assert result["status"] == "disabled"

    def test_votacao_relevante_disabled(self):
        with patch("app.config.settings") as ms:
            ms.social_enabled = False
            result = _social_tasks_mod.post_votacao_relevante_task(123)
            assert result["status"] == "disabled"

    def test_explicativo_disabled_social(self):
        with patch("app.config.settings") as ms:
            ms.social_enabled = False
            result = _social_tasks_mod.post_explicativo_educativo_task(123)
            assert result["status"] == "disabled"

    def test_explicativo_disabled_educational(self):
        with patch("app.config.settings") as ms:
            ms.social_enabled = True
            ms.social_educational_enabled = False
            result = _social_tasks_mod.post_explicativo_educativo_task(123)
            assert result["status"] == "disabled"

    def test_metricas_disabled(self):
        with patch("app.config.settings") as ms:
            ms.social_enabled = False
            result = _social_tasks_mod.atualizar_metricas_task()
            assert result["status"] == "disabled"

    def test_publicar_aprovado_disabled(self):
        with patch("app.config.settings") as ms:
            ms.social_enabled = False
            result = _social_tasks_mod.publicar_post_aprovado_task(str(uuid.uuid4()))
            assert result["status"] == "disabled"

    def test_metricas_enabled_runs(self):
        with (
            patch("app.config.settings") as ms,
            patch.object(_social_tasks_mod, "get_async_session") as mock_session_ctx,
            patch("app.services.social_media_service.SocialMediaService") as MockService,
        ):
            ms.social_enabled = True

            mock_session = AsyncMock()
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
            mock_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_session_ctx.return_value = mock_ctx

            mock_service = AsyncMock()
            mock_service.update_metrics_for_recent_posts = AsyncMock(return_value=5)
            mock_service.close = AsyncMock()
            MockService.return_value = mock_service

            result = _social_tasks_mod.atualizar_metricas_task()
            assert result["posts_updated"] == 5


# ---------------------------------------------------------------------------
# Router Tests
# ---------------------------------------------------------------------------


class TestSocialAdminRouter:
    async def test_list_posts_unauthenticated(self, client):
        resp = await client.get("/admin/social/posts")
        assert resp.status_code == 422  # Missing X-API-Key header

    async def test_list_posts_bad_api_key(self, client):
        resp = await client.get(
            "/admin/social/posts",
            headers={"X-API-Key": "wrong-key"},
        )
        assert resp.status_code == 401

    async def test_list_posts_with_key(self, client):
        resp = await client.get(
            "/admin/social/posts",
            headers={"X-API-Key": settings.admin_api_key},
        )
        assert resp.status_code == 200

    async def test_get_nonexistent_post(self, client):
        resp = await client.get(
            f"/admin/social/posts/{uuid.uuid4()}",
            headers={"X-API-Key": settings.admin_api_key},
        )
        assert resp.status_code == 404

    async def test_metrics_endpoint(self, client):
        resp = await client.get(
            "/admin/social/metrics",
            headers={"X-API-Key": settings.admin_api_key},
        )
        assert resp.status_code == 200

    async def test_counts_endpoint(self, client):
        resp = await client.get(
            "/admin/social/counts",
            headers={"X-API-Key": settings.admin_api_key},
        )
        assert resp.status_code == 200
