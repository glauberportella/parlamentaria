"""Tests for social media admin endpoints in /parlamentar/admin/social/."""

import uuid
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.parlamentar_user import ParlamentarUser, TipoParlamentarUser
from app.domain.social_post import RedeSocial, SocialPost, StatusPost, TipoPostSocial
from app.services.parlamentar_auth_service import ParlamentarAuthService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def admin_user(db_session: AsyncSession) -> ParlamentarUser:
    """Create an admin parlamentar user."""
    user = ParlamentarUser(
        email="admin@camara.leg.br",
        nome="Admin User",
        cargo="Deputado Federal",
        tipo=TipoParlamentarUser.DEPUTADO,
        ativo=True,
        convite_usado=True,
        is_admin=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.fixture
async def non_admin_user(db_session: AsyncSession) -> ParlamentarUser:
    """Create a non-admin parlamentar user."""
    user = ParlamentarUser(
        email="assessor@camara.leg.br",
        nome="Assessor Normal",
        cargo="Assessor",
        tipo=TipoParlamentarUser.ASSESSOR,
        ativo=True,
        convite_usado=True,
        is_admin=False,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.fixture
def admin_headers(admin_user: ParlamentarUser) -> dict:
    """Return auth headers for admin user."""
    token = ParlamentarAuthService.create_access_token(admin_user)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def non_admin_headers(non_admin_user: ParlamentarUser) -> dict:
    """Return auth headers for non-admin user."""
    token = ParlamentarAuthService.create_access_token(non_admin_user)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def draft_post(db_session: AsyncSession) -> SocialPost:
    """Create a draft social post."""
    post = SocialPost(
        tipo=TipoPostSocial.VOTACAO_RELEVANTE,
        rede=RedeSocial.TWITTER,
        texto="73% dos eleitores votaram SIM na PL 1234/2026.",
        status=StatusPost.RASCUNHO,
    )
    db_session.add(post)
    await db_session.flush()
    return post


@pytest.fixture
async def published_post(db_session: AsyncSession) -> SocialPost:
    """Create a published social post."""
    post = SocialPost(
        tipo=TipoPostSocial.RESUMO_SEMANAL,
        rede=RedeSocial.FACEBOOK,
        texto="Resumo da semana legislativa.",
        status=StatusPost.PUBLICADO,
        rede_post_id="fb_12345",
        publicado_em=datetime.now(timezone.utc),
        likes=12,
        shares=4,
        comments=2,
        impressions=890,
    )
    db_session.add(post)
    await db_session.flush()
    return post


@pytest.fixture
async def failed_post(db_session: AsyncSession) -> SocialPost:
    """Create a failed social post."""
    post = SocialPost(
        tipo=TipoPostSocial.COMPARATIVO,
        rede=RedeSocial.TWITTER,
        texto="Alinhamento popular vs Câmara: 95%.",
        status=StatusPost.FALHOU,
        erro="Rate limit exceeded",
    )
    db_session.add(post)
    await db_session.flush()
    return post


# ===========================================================================
# Tests
# ===========================================================================


class TestSocialAdminAuth:
    """Test authentication/authorization for social admin endpoints."""

    async def test_unauthenticated_returns_422(self, client: AsyncClient) -> None:
        resp = await client.get("/parlamentar/admin/social/posts")
        assert resp.status_code == 422

    async def test_non_admin_returns_401(
        self, client: AsyncClient, non_admin_headers: dict
    ) -> None:
        resp = await client.get(
            "/parlamentar/admin/social/posts",
            headers=non_admin_headers,
        )
        assert resp.status_code == 401


class TestListPosts:
    """Test GET /parlamentar/admin/social/posts."""

    async def test_list_empty(
        self, client: AsyncClient, admin_headers: dict
    ) -> None:
        resp = await client.get(
            "/parlamentar/admin/social/posts", headers=admin_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["items"] == []

    async def test_list_with_posts(
        self,
        client: AsyncClient,
        admin_headers: dict,
        draft_post: SocialPost,
        published_post: SocialPost,
    ) -> None:
        resp = await client.get(
            "/parlamentar/admin/social/posts", headers=admin_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2

    async def test_list_filter_by_status(
        self,
        client: AsyncClient,
        admin_headers: dict,
        draft_post: SocialPost,
        published_post: SocialPost,
    ) -> None:
        resp = await client.get(
            "/parlamentar/admin/social/posts?status=rascunho",
            headers=admin_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["status"] == "rascunho"

    async def test_list_filter_by_rede(
        self,
        client: AsyncClient,
        admin_headers: dict,
        draft_post: SocialPost,
        published_post: SocialPost,
    ) -> None:
        resp = await client.get(
            "/parlamentar/admin/social/posts?rede=twitter",
            headers=admin_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["rede"] == "twitter"


class TestGetPost:
    """Test GET /parlamentar/admin/social/posts/{post_id}."""

    async def test_get_existing(
        self, client: AsyncClient, admin_headers: dict, draft_post: SocialPost
    ) -> None:
        resp = await client.get(
            f"/parlamentar/admin/social/posts/{draft_post.id}",
            headers=admin_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["texto"] == draft_post.texto

    async def test_get_not_found(
        self, client: AsyncClient, admin_headers: dict
    ) -> None:
        fake_id = str(uuid.uuid4())
        resp = await client.get(
            f"/parlamentar/admin/social/posts/{fake_id}",
            headers=admin_headers,
        )
        assert resp.status_code == 404


class TestApprovePost:
    """Test POST /parlamentar/admin/social/posts/{id}/approve."""

    async def test_approve_draft(
        self, client: AsyncClient, admin_headers: dict, draft_post: SocialPost
    ) -> None:
        from unittest.mock import patch, MagicMock

        with patch(
            "app.tasks.social_media_tasks.publicar_post_aprovado_task"
        ) as mock_task:
            mock_task.delay = MagicMock()
            resp = await client.post(
                f"/parlamentar/admin/social/posts/{draft_post.id}/approve",
                headers=admin_headers,
            )
        assert resp.status_code == 200
        assert resp.json()["status"] == "approved"

    async def test_approve_published_fails(
        self, client: AsyncClient, admin_headers: dict, published_post: SocialPost
    ) -> None:
        resp = await client.post(
            f"/parlamentar/admin/social/posts/{published_post.id}/approve",
            headers=admin_headers,
        )
        assert resp.status_code == 422


class TestRejectPost:
    """Test POST /parlamentar/admin/social/posts/{id}/reject."""

    async def test_reject_draft(
        self, client: AsyncClient, admin_headers: dict, draft_post: SocialPost
    ) -> None:
        resp = await client.post(
            f"/parlamentar/admin/social/posts/{draft_post.id}/reject",
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "rejected"

    async def test_reject_published_fails(
        self, client: AsyncClient, admin_headers: dict, published_post: SocialPost
    ) -> None:
        resp = await client.post(
            f"/parlamentar/admin/social/posts/{published_post.id}/reject",
            headers=admin_headers,
        )
        assert resp.status_code == 422


class TestRepublishPost:
    """Test POST /parlamentar/admin/social/posts/{id}/republish."""

    async def test_republish_failed(
        self, client: AsyncClient, admin_headers: dict, failed_post: SocialPost
    ) -> None:
        from unittest.mock import patch, MagicMock

        with patch(
            "app.tasks.social_media_tasks.publicar_post_aprovado_task"
        ) as mock_task:
            mock_task.delay = MagicMock()
            resp = await client.post(
                f"/parlamentar/admin/social/posts/{failed_post.id}/republish",
                headers=admin_headers,
            )
        assert resp.status_code == 200
        assert resp.json()["status"] == "queued_for_republish"

    async def test_republish_draft_fails(
        self, client: AsyncClient, admin_headers: dict, draft_post: SocialPost
    ) -> None:
        resp = await client.post(
            f"/parlamentar/admin/social/posts/{draft_post.id}/republish",
            headers=admin_headers,
        )
        assert resp.status_code == 422


class TestMetricsAndCounts:
    """Test GET /parlamentar/admin/social/metrics and /counts."""

    async def test_metrics_empty(
        self, client: AsyncClient, admin_headers: dict
    ) -> None:
        resp = await client.get(
            "/parlamentar/admin/social/metrics", headers=admin_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_posts"] == 0

    async def test_counts_with_data(
        self,
        client: AsyncClient,
        admin_headers: dict,
        draft_post: SocialPost,
        published_post: SocialPost,
        failed_post: SocialPost,
    ) -> None:
        resp = await client.get(
            "/parlamentar/admin/social/counts", headers=admin_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "by_rede" in data
        assert "by_tipo" in data
        assert "by_status" in data
        assert data["by_status"]["rascunho"] == 1
        assert data["by_status"]["publicado"] == 1
        assert data["by_status"]["falhou"] == 1
