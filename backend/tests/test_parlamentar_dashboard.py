"""Tests for the parliamentarian dashboard: auth service, routers, and JWT flows."""

import secrets
from datetime import date, datetime, timezone
from unittest.mock import patch, MagicMock

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.domain.parlamentar_user import ParlamentarUser, TipoParlamentarUser
from app.services.parlamentar_auth_service import ParlamentarAuthService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_parlamentar_user_data(sample_deputado_data: dict) -> dict:
    """Return a dict of valid ParlamentarUser fields."""
    return {
        "email": "parlamentar@camara.leg.br",
        "nome": "João Deputado",
        "cargo": "Deputado Federal",
        "tipo": TipoParlamentarUser.DEPUTADO,
        "ativo": True,
        "convite_usado": True,
    }


@pytest.fixture
async def parlamentar_user(
    db_session: AsyncSession,
    sample_parlamentar_user_data: dict,
) -> ParlamentarUser:
    """Create and persist a ParlamentarUser for testing."""
    user = ParlamentarUser(**sample_parlamentar_user_data)
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.fixture
async def parlamentar_user_with_convite(
    db_session: AsyncSession,
) -> ParlamentarUser:
    """Create a ParlamentarUser with unused invitation code."""
    user = ParlamentarUser(
        email="novo@camara.leg.br",
        nome="Assessor Novo",
        cargo="Assessor Parlamentar",
        tipo=TipoParlamentarUser.ASSESSOR,
        ativo=True,
        convite_usado=False,
        codigo_convite=secrets.token_urlsafe(32),
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.fixture
def auth_service(db_session: AsyncSession) -> ParlamentarAuthService:
    """Return a ParlamentarAuthService with test session."""
    return ParlamentarAuthService(db_session)


# ===========================================================================
# Unit Tests — ParlamentarAuthService
# ===========================================================================


class TestJWTTokens:
    """Test JWT token creation and decoding."""

    async def test_create_access_token(
        self, parlamentar_user: ParlamentarUser
    ) -> None:
        """Access token contains correct claims."""
        token = ParlamentarAuthService.create_access_token(parlamentar_user)
        payload = ParlamentarAuthService.decode_token(token)

        assert payload["sub"] == str(parlamentar_user.id)
        assert payload["email"] == parlamentar_user.email
        assert payload["tipo"] == "DEPUTADO"
        assert payload["type"] == "access"

    async def test_create_refresh_token(
        self, parlamentar_user: ParlamentarUser
    ) -> None:
        """Refresh token contains correct claims."""
        token = ParlamentarAuthService.create_refresh_token(parlamentar_user)
        payload = ParlamentarAuthService.decode_token(token)

        assert payload["sub"] == str(parlamentar_user.id)
        assert payload["type"] == "refresh"
        assert "email" not in payload  # refresh token doesn't carry email

    async def test_create_magic_link_token(
        self, parlamentar_user: ParlamentarUser
    ) -> None:
        """Magic link token contains correct claims."""
        token = ParlamentarAuthService.create_magic_link_token(parlamentar_user)
        payload = ParlamentarAuthService.decode_token(token)

        assert payload["sub"] == str(parlamentar_user.id)
        assert payload["email"] == parlamentar_user.email
        assert payload["type"] == "magic_link"

    async def test_decode_invalid_token(self) -> None:
        """Decoding an invalid token raises UnauthorizedException."""
        from app.exceptions import UnauthorizedException

        with pytest.raises(UnauthorizedException, match="Token inválido"):
            ParlamentarAuthService.decode_token("invalid.token.here")

    async def test_decode_expired_token(
        self, parlamentar_user: ParlamentarUser
    ) -> None:
        """Decoding an expired token raises UnauthorizedException."""
        import jwt as pyjwt
        from datetime import timedelta
        from app.exceptions import UnauthorizedException

        expired_token = pyjwt.encode(
            {
                "sub": parlamentar_user.id,
                "type": "access",
                "exp": datetime.now(timezone.utc) - timedelta(hours=1),
                "iat": datetime.now(timezone.utc) - timedelta(hours=2),
            },
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
        )

        with pytest.raises(UnauthorizedException, match="Token expirado"):
            ParlamentarAuthService.decode_token(expired_token)


class TestUserQueries:
    """Test user lookup methods."""

    async def test_get_user_by_email(
        self,
        auth_service: ParlamentarAuthService,
        parlamentar_user: ParlamentarUser,
    ) -> None:
        """Find user by email returns correct user."""
        user = await auth_service.get_user_by_email("parlamentar@camara.leg.br")
        assert user is not None
        assert str(user.id) == str(parlamentar_user.id)

    async def test_get_user_by_email_not_found(
        self, auth_service: ParlamentarAuthService
    ) -> None:
        """Find user by non-existent email returns None."""
        user = await auth_service.get_user_by_email("naoexiste@example.com")
        assert user is None

    async def test_get_user_by_id(
        self,
        auth_service: ParlamentarAuthService,
        parlamentar_user: ParlamentarUser,
    ) -> None:
        """Find user by ID returns correct user."""
        user = await auth_service.get_user_by_id(str(parlamentar_user.id))
        assert user is not None
        assert user.email == parlamentar_user.email

    async def test_get_user_by_convite(
        self,
        auth_service: ParlamentarAuthService,
        parlamentar_user_with_convite: ParlamentarUser,
    ) -> None:
        """Find user by unused invitation code."""
        user = await auth_service.get_user_by_convite(
            parlamentar_user_with_convite.codigo_convite
        )
        assert user is not None
        assert str(user.id) == str(parlamentar_user_with_convite.id)


class TestMagicLinkFlow:
    """Test magic link login flow."""

    @patch.object(ParlamentarAuthService, "_send_magic_link_email", return_value=None)
    async def test_request_magic_link_existing_user(
        self,
        mock_email: MagicMock,
        auth_service: ParlamentarAuthService,
        parlamentar_user: ParlamentarUser,
    ) -> None:
        """Request magic link for existing user sends email."""
        result = await auth_service.request_magic_link("parlamentar@camara.leg.br")
        assert result is True
        mock_email.assert_called_once()

    async def test_request_magic_link_unknown_email(
        self, auth_service: ParlamentarAuthService
    ) -> None:
        """Request magic link for unknown email still returns True (no enumeration)."""
        result = await auth_service.request_magic_link("unknown@example.com")
        assert result is True

    @patch.object(ParlamentarAuthService, "_send_magic_link_email", return_value=None)
    async def test_verify_magic_link(
        self,
        mock_email: MagicMock,
        auth_service: ParlamentarAuthService,
        parlamentar_user: ParlamentarUser,
    ) -> None:
        """Verify magic link returns user and tokens."""
        token = ParlamentarAuthService.create_magic_link_token(parlamentar_user)
        user, access, refresh = await auth_service.verify_magic_link(token)

        assert str(user.id) == str(parlamentar_user.id)
        assert access is not None
        assert refresh is not None
        assert user.refresh_token_hash is not None

    async def test_verify_magic_link_invalid_type(
        self,
        auth_service: ParlamentarAuthService,
        parlamentar_user: ParlamentarUser,
    ) -> None:
        """Verify with a non-magic-link token type fails."""
        from app.exceptions import UnauthorizedException

        access_token = ParlamentarAuthService.create_access_token(parlamentar_user)
        with pytest.raises(UnauthorizedException, match="Token inválido"):
            await auth_service.verify_magic_link(access_token)


class TestTokenRefresh:
    """Test token refresh flow."""

    @patch.object(ParlamentarAuthService, "_send_magic_link_email", return_value=None)
    async def test_refresh_access_token(
        self,
        mock_email: MagicMock,
        auth_service: ParlamentarAuthService,
        parlamentar_user: ParlamentarUser,
    ) -> None:
        """Refresh token returns new token pair (rotation)."""
        # First, login to get a valid refresh token
        magic_token = ParlamentarAuthService.create_magic_link_token(parlamentar_user)
        _, _, refresh_token = await auth_service.verify_magic_link(magic_token)

        # Now refresh
        user, new_access, new_refresh = await auth_service.refresh_access_token(
            refresh_token
        )

        assert str(user.id) == str(parlamentar_user.id)
        assert new_access != refresh_token
        assert new_refresh != refresh_token  # Token rotation

    async def test_refresh_with_access_token_fails(
        self,
        auth_service: ParlamentarAuthService,
        parlamentar_user: ParlamentarUser,
    ) -> None:
        """Using access token for refresh fails."""
        from app.exceptions import UnauthorizedException

        access = ParlamentarAuthService.create_access_token(parlamentar_user)
        with pytest.raises(UnauthorizedException, match="Token inválido"):
            await auth_service.refresh_access_token(access)


class TestInvitations:
    """Test invitation code management."""

    async def test_create_invitation(
        self, auth_service: ParlamentarAuthService
    ) -> None:
        """Create invitation generates user with code."""
        user = await auth_service.create_invitation(
            email="assessor@camara.leg.br",
            nome="Assessor Test",
            tipo="ASSESSOR",
            cargo="Assessor Parlamentar",
        )

        assert user.codigo_convite is not None
        assert len(user.codigo_convite) > 20
        assert user.convite_usado is False
        assert user.tipo == TipoParlamentarUser.ASSESSOR

    async def test_create_invitation_duplicate_email(
        self,
        auth_service: ParlamentarAuthService,
        parlamentar_user: ParlamentarUser,
    ) -> None:
        """Creating invitation with existing email raises validation error."""
        from app.exceptions import ValidationException

        with pytest.raises(ValidationException, match="Email já cadastrado"):
            await auth_service.create_invitation(
                email="parlamentar@camara.leg.br",
                nome="Duplicate",
            )

    async def test_create_invitation_invalid_tipo(
        self, auth_service: ParlamentarAuthService
    ) -> None:
        """Creating invitation with invalid tipo raises validation error."""
        from app.exceptions import ValidationException

        with pytest.raises(ValidationException, match="Tipo inválido"):
            await auth_service.create_invitation(
                email="test@example.com",
                nome="Invalid",
                tipo="INVALIDO",
            )


# ===========================================================================
# Integration Tests — Routers
# ===========================================================================


class TestAuthRouter:
    """Test /parlamentar/auth endpoints."""

    async def test_login_endpoint(
        self,
        client: AsyncClient,
        parlamentar_user: ParlamentarUser,
    ) -> None:
        """POST /parlamentar/auth/login returns success message."""
        with patch.object(
            ParlamentarAuthService, "_send_magic_link_email", return_value=None
        ):
            response = await client.post(
                "/parlamentar/auth/login",
                json={"email": "parlamentar@camara.leg.br"},
            )

        assert response.status_code == 200
        data = response.json()
        assert "message" in data

    async def test_login_unknown_email(self, client: AsyncClient) -> None:
        """POST /parlamentar/auth/login with unknown email still returns 200."""
        response = await client.post(
            "/parlamentar/auth/login",
            json={"email": "unknown@example.com"},
        )
        assert response.status_code == 200

    async def test_verify_endpoint(
        self,
        client: AsyncClient,
        parlamentar_user: ParlamentarUser,
    ) -> None:
        """POST /parlamentar/auth/verify exchanges token for JWT."""
        token = ParlamentarAuthService.create_magic_link_token(parlamentar_user)

        response = await client.post(
            "/parlamentar/auth/verify",
            json={"token": token},
        )

        assert response.status_code == 200
        data = response.json()
        assert "tokens" in data
        assert "user" in data
        assert data["tokens"]["access_token"] is not None
        assert data["tokens"]["refresh_token"] is not None
        assert data["user"]["email"] == "parlamentar@camara.leg.br"

    async def test_verify_invalid_token(self, client: AsyncClient) -> None:
        """POST /parlamentar/auth/verify with invalid token returns 401."""
        response = await client.post(
            "/parlamentar/auth/verify",
            json={"token": "invalid.token.here"},
        )
        assert response.status_code == 401

    async def test_refresh_endpoint(
        self,
        client: AsyncClient,
        parlamentar_user: ParlamentarUser,
    ) -> None:
        """POST /parlamentar/auth/refresh rotates tokens."""
        # First: verify to get a refresh token
        magic_token = ParlamentarAuthService.create_magic_link_token(parlamentar_user)
        verify_resp = await client.post(
            "/parlamentar/auth/verify",
            json={"token": magic_token},
        )
        refresh_token = verify_resp.json()["tokens"]["refresh_token"]

        # Now: refresh
        response = await client.post(
            "/parlamentar/auth/refresh",
            json={"refresh_token": refresh_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["tokens"]["access_token"] is not None
        assert data["tokens"]["refresh_token"] != refresh_token  # rotation

    async def test_me_endpoint(
        self,
        client: AsyncClient,
        parlamentar_user: ParlamentarUser,
    ) -> None:
        """GET /parlamentar/auth/me returns current user."""
        access = ParlamentarAuthService.create_access_token(parlamentar_user)

        response = await client.get(
            "/parlamentar/auth/me",
            headers={"Authorization": f"Bearer {access}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "parlamentar@camara.leg.br"
        assert data["nome"] == "João Deputado"

    async def test_me_no_auth(self, client: AsyncClient) -> None:
        """GET /parlamentar/auth/me without token returns 422 (missing header)."""
        response = await client.get("/parlamentar/auth/me")
        assert response.status_code == 422

    async def test_me_invalid_token(self, client: AsyncClient) -> None:
        """GET /parlamentar/auth/me with invalid token returns 401."""
        response = await client.get(
            "/parlamentar/auth/me",
            headers={"Authorization": "Bearer invalid.token"},
        )
        assert response.status_code == 401

    async def test_convite_endpoint(
        self, client: AsyncClient
    ) -> None:
        """POST /parlamentar/auth/convite creates invitation with admin key."""
        response = await client.post(
            "/parlamentar/auth/convite",
            json={
                "email": "new_assessor@camara.leg.br",
                "nome": "Novo Assessor",
                "tipo": "ASSESSOR",
            },
            headers={"X-API-Key": settings.admin_api_key},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "new_assessor@camara.leg.br"
        assert "codigo_convite" in data
        assert len(data["codigo_convite"]) > 20

    async def test_convite_endpoint_wrong_api_key(
        self, client: AsyncClient
    ) -> None:
        """POST /parlamentar/auth/convite with wrong API key returns 401."""
        response = await client.post(
            "/parlamentar/auth/convite",
            json={
                "email": "test@example.com",
                "nome": "Test",
            },
            headers={"X-API-Key": "wrong-key"},
        )
        assert response.status_code == 401

    async def test_demo_status_disabled_by_default(
        self, client: AsyncClient
    ) -> None:
        """GET /parlamentar/auth/demo-status returns enabled=False by default."""
        response = await client.get("/parlamentar/auth/demo-status")
        assert response.status_code == 200
        assert response.json()["enabled"] is False

    async def test_demo_status_enabled(self, client: AsyncClient) -> None:
        """GET /parlamentar/auth/demo-status returns enabled=True when demo_mode=True."""
        with patch.object(settings, "demo_mode", True), \
             patch.object(settings, "app_env", "development"):
            response = await client.get("/parlamentar/auth/demo-status")
        assert response.status_code == 200
        assert response.json()["enabled"] is True

    async def test_demo_login_disabled(self, client: AsyncClient) -> None:
        """POST /parlamentar/auth/demo-login returns 422 when demo mode is off."""
        response = await client.post("/parlamentar/auth/demo-login")
        assert response.status_code == 422

    async def test_demo_login_enabled(self, client: AsyncClient) -> None:
        """POST /parlamentar/auth/demo-login creates demo user and returns tokens."""
        with patch.object(settings, "demo_mode", True), \
             patch.object(settings, "app_env", "development"):
            response = await client.post("/parlamentar/auth/demo-login")

        assert response.status_code == 200
        data = response.json()
        assert "tokens" in data
        assert "user" in data
        assert data["tokens"]["access_token"] is not None
        assert data["user"]["email"] == settings.demo_user_email
        assert data["user"]["nome"] == settings.demo_user_nome

    async def test_demo_login_idempotent(self, client: AsyncClient) -> None:
        """POST /parlamentar/auth/demo-login is idempotent — same user on 2nd call."""
        with patch.object(settings, "demo_mode", True), \
             patch.object(settings, "app_env", "development"):
            resp1 = await client.post("/parlamentar/auth/demo-login")
            resp2 = await client.post("/parlamentar/auth/demo-login")

        assert resp1.status_code == 200
        assert resp2.status_code == 200
        assert resp1.json()["user"]["id"] == resp2.json()["user"]["id"]

    async def test_demo_login_blocked_in_production(
        self, client: AsyncClient
    ) -> None:
        """POST /parlamentar/auth/demo-login returns 422 in production."""
        with patch.object(settings, "demo_mode", True), \
             patch.object(settings, "app_env", "production"):
            response = await client.post("/parlamentar/auth/demo-login")
        assert response.status_code == 422


class TestDashboardRouter:
    """Test /parlamentar/dashboard endpoints."""

    async def test_resumo_authenticated(
        self,
        client: AsyncClient,
        parlamentar_user: ParlamentarUser,
    ) -> None:
        """GET /parlamentar/dashboard/resumo returns dashboard data with new schema."""
        access = ParlamentarAuthService.create_access_token(parlamentar_user)

        response = await client.get(
            "/parlamentar/dashboard/resumo",
            headers={"Authorization": f"Bearer {access}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "kpis" in data
        assert "tendencias" in data
        assert "alertas" in data

        # KPIs should have expected keys aligned with frontend types
        kpis = data["kpis"]
        assert "total_proposicoes_ativas" in kpis
        assert "total_eleitores_cadastrados" in kpis
        assert "total_votos_populares" in kpis
        assert "total_comparativos" in kpis
        assert "alinhamento_medio" in kpis
        assert "taxa_participacao" in kpis

        # Tendencias structure
        tendencias = data["tendencias"]
        assert "votos_ultimos_7_dias" in tendencias
        assert "novos_eleitores_ultimos_7_dias" in tendencias
        assert "proposicoes_mais_votadas" in tendencias
        assert "temas_mais_ativos" in tendencias
        assert isinstance(tendencias["proposicoes_mais_votadas"], list)
        assert isinstance(tendencias["temas_mais_ativos"], list)

        # Alertas is a list
        assert isinstance(data["alertas"], list)

    async def test_resumo_empty_database(
        self,
        client: AsyncClient,
        parlamentar_user: ParlamentarUser,
    ) -> None:
        """GET /parlamentar/dashboard/resumo with empty DB returns zeroed KPIs."""
        access = ParlamentarAuthService.create_access_token(parlamentar_user)

        response = await client.get(
            "/parlamentar/dashboard/resumo",
            headers={"Authorization": f"Bearer {access}"},
        )

        assert response.status_code == 200
        kpis = response.json()["kpis"]
        assert kpis["total_proposicoes_ativas"] == 0
        assert kpis["total_eleitores_cadastrados"] == 0
        assert kpis["total_votos_populares"] == 0
        assert kpis["total_comparativos"] == 0
        assert kpis["alinhamento_medio"] == 0.0
        assert kpis["taxa_participacao"] == 0.0

    async def test_resumo_with_data(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        parlamentar_user: ParlamentarUser,
        sample_proposicao_data: dict,
        sample_eleitor_data: dict,
    ) -> None:
        """GET /parlamentar/dashboard/resumo reflects actual data in DB."""
        from app.domain.proposicao import Proposicao
        from app.domain.eleitor import Eleitor
        from app.domain.voto_popular import VotoPopular, VotoEnum

        # Create proposição + eleitor + voto
        prop = Proposicao(**sample_proposicao_data)
        db_session.add(prop)
        eleitor = Eleitor(**sample_eleitor_data)
        db_session.add(eleitor)
        await db_session.flush()

        voto = VotoPopular(
            eleitor_id=eleitor.id,
            proposicao_id=prop.id,
            voto=VotoEnum.SIM,
        )
        db_session.add(voto)
        await db_session.flush()

        access = ParlamentarAuthService.create_access_token(parlamentar_user)
        response = await client.get(
            "/parlamentar/dashboard/resumo",
            headers={"Authorization": f"Bearer {access}"},
        )

        assert response.status_code == 200
        kpis = response.json()["kpis"]
        assert kpis["total_proposicoes_ativas"] == 1
        assert kpis["total_eleitores_cadastrados"] == 1
        assert kpis["total_votos_populares"] == 1
        assert kpis["taxa_participacao"] == 1.0

    async def test_resumo_unauthenticated(self, client: AsyncClient) -> None:
        """GET /parlamentar/dashboard/resumo without auth returns 422."""
        response = await client.get("/parlamentar/dashboard/resumo")
        assert response.status_code == 422


# ===========================================================================
# Integration Tests — Proposições Router
# ===========================================================================


class TestProposicoesListRouter:
    """Test GET /parlamentar/proposicoes listing endpoint."""

    async def test_list_empty(
        self,
        client: AsyncClient,
        parlamentar_user: ParlamentarUser,
    ) -> None:
        """Empty DB returns paginated response with zero items."""
        access = ParlamentarAuthService.create_access_token(parlamentar_user)

        response = await client.get(
            "/parlamentar/proposicoes",
            headers={"Authorization": f"Bearer {access}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []
        assert data["pagina"] == 1
        assert data["itens_por_pagina"] == 20

    async def test_list_with_proposicao(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        parlamentar_user: ParlamentarUser,
        sample_proposicao_data: dict,
    ) -> None:
        """Lists proposição with enriched vote data."""
        from app.domain.proposicao import Proposicao

        prop = Proposicao(**sample_proposicao_data)
        db_session.add(prop)
        await db_session.flush()

        access = ParlamentarAuthService.create_access_token(parlamentar_user)
        response = await client.get(
            "/parlamentar/proposicoes",
            headers={"Authorization": f"Bearer {access}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1

        item = data["items"][0]
        assert item["id"] == sample_proposicao_data["id"]
        assert item["tipo"] == "PL"
        assert item["numero"] == 100
        assert item["ano"] == 2024
        assert "votos" in item
        assert item["votos"]["total"] == 0
        assert item["tem_analise"] is False
        assert item["tem_comparativo"] is False

    async def test_list_with_votes(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        parlamentar_user: ParlamentarUser,
        sample_proposicao_data: dict,
        sample_eleitor_data: dict,
    ) -> None:
        """Lists proposição with aggregated vote data."""
        from app.domain.proposicao import Proposicao
        from app.domain.eleitor import Eleitor
        from app.domain.voto_popular import VotoPopular, VotoEnum

        prop = Proposicao(**sample_proposicao_data)
        db_session.add(prop)
        eleitor = Eleitor(**sample_eleitor_data)
        db_session.add(eleitor)
        await db_session.flush()

        voto = VotoPopular(
            eleitor_id=eleitor.id,
            proposicao_id=prop.id,
            voto=VotoEnum.SIM,
        )
        db_session.add(voto)
        await db_session.flush()

        access = ParlamentarAuthService.create_access_token(parlamentar_user)
        response = await client.get(
            "/parlamentar/proposicoes",
            headers={"Authorization": f"Bearer {access}"},
        )

        data = response.json()
        votos = data["items"][0]["votos"]
        assert votos["total"] == 1
        assert votos["sim"] == 1
        assert votos["nao"] == 0
        assert votos["percentual_sim"] == 100.0

    async def test_list_filter_by_tipo(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        parlamentar_user: ParlamentarUser,
    ) -> None:
        """Filter by tipo returns only matching proposições."""
        from app.domain.proposicao import Proposicao

        pl = Proposicao(id=1, tipo="PL", numero=1, ano=2024, ementa="PL test", data_apresentacao=date(2024, 1, 1), situacao="Em tramitação")
        pec = Proposicao(id=2, tipo="PEC", numero=2, ano=2024, ementa="PEC test", data_apresentacao=date(2024, 1, 1), situacao="Em tramitação")
        db_session.add_all([pl, pec])
        await db_session.flush()

        access = ParlamentarAuthService.create_access_token(parlamentar_user)
        response = await client.get(
            "/parlamentar/proposicoes?tipo=PL",
            headers={"Authorization": f"Bearer {access}"},
        )

        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["tipo"] == "PL"

    async def test_list_filter_by_ano(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        parlamentar_user: ParlamentarUser,
    ) -> None:
        """Filter by ano returns only matching proposições."""
        from app.domain.proposicao import Proposicao

        p1 = Proposicao(id=1, tipo="PL", numero=1, ano=2023, ementa="old", data_apresentacao=date(2023, 1, 1), situacao="Arquivada")
        p2 = Proposicao(id=2, tipo="PL", numero=2, ano=2024, ementa="new", data_apresentacao=date(2024, 1, 1), situacao="Em tramitação")
        db_session.add_all([p1, p2])
        await db_session.flush()

        access = ParlamentarAuthService.create_access_token(parlamentar_user)
        response = await client.get(
            "/parlamentar/proposicoes?ano=2024",
            headers={"Authorization": f"Bearer {access}"},
        )

        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["ano"] == 2024

    async def test_list_filter_by_busca(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        parlamentar_user: ParlamentarUser,
    ) -> None:
        """Busca filter searches in ementa."""
        from app.domain.proposicao import Proposicao

        p1 = Proposicao(id=1, tipo="PL", numero=1, ano=2024, ementa="Reforma tributária", data_apresentacao=date(2024, 1, 1), situacao="Em tramitação")
        p2 = Proposicao(id=2, tipo="PL", numero=2, ano=2024, ementa="Educação pública", data_apresentacao=date(2024, 1, 1), situacao="Em tramitação")
        db_session.add_all([p1, p2])
        await db_session.flush()

        access = ParlamentarAuthService.create_access_token(parlamentar_user)
        response = await client.get(
            "/parlamentar/proposicoes?busca=tributária",
            headers={"Authorization": f"Bearer {access}"},
        )

        data = response.json()
        assert data["total"] == 1
        assert "tributária" in data["items"][0]["ementa"].lower()

    async def test_list_pagination(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        parlamentar_user: ParlamentarUser,
    ) -> None:
        """Pagination returns correct subset."""
        from app.domain.proposicao import Proposicao

        for i in range(5):
            db_session.add(Proposicao(
                id=i + 1, tipo="PL", numero=i + 1, ano=2024,
                ementa=f"Proposição {i+1}", data_apresentacao=date(2024, 1, 1),
                situacao="Em tramitação",
            ))
        await db_session.flush()

        access = ParlamentarAuthService.create_access_token(parlamentar_user)
        response = await client.get(
            "/parlamentar/proposicoes?pagina=2&itens=2",
            headers={"Authorization": f"Bearer {access}"},
        )

        data = response.json()
        assert data["total"] == 5
        assert len(data["items"]) == 2
        assert data["pagina"] == 2
        assert data["itens_por_pagina"] == 2

    async def test_list_unauthenticated(self, client: AsyncClient) -> None:
        """GET /parlamentar/proposicoes without auth returns 422."""
        response = await client.get("/parlamentar/proposicoes")
        assert response.status_code == 422


class TestProposicaoDetalheRouter:
    """Test GET /parlamentar/proposicoes/{id} detail endpoint."""

    async def test_detail_found(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        parlamentar_user: ParlamentarUser,
        sample_proposicao_data: dict,
    ) -> None:
        """Returns full proposição detail."""
        from app.domain.proposicao import Proposicao

        prop = Proposicao(**sample_proposicao_data)
        db_session.add(prop)
        await db_session.flush()

        access = ParlamentarAuthService.create_access_token(parlamentar_user)
        response = await client.get(
            f"/parlamentar/proposicoes/{sample_proposicao_data['id']}",
            headers={"Authorization": f"Bearer {access}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_proposicao_data["id"]
        assert data["tipo"] == "PL"
        assert data["ementa"] == sample_proposicao_data["ementa"]
        assert "votos" in data
        assert data["analise"] is None
        assert data["comparativo"] is None

    async def test_detail_not_found(
        self,
        client: AsyncClient,
        parlamentar_user: ParlamentarUser,
    ) -> None:
        """Non-existent proposição returns 404."""
        access = ParlamentarAuthService.create_access_token(parlamentar_user)

        response = await client.get(
            "/parlamentar/proposicoes/99999",
            headers={"Authorization": f"Bearer {access}"},
        )

        assert response.status_code == 404

    async def test_detail_with_votes(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        parlamentar_user: ParlamentarUser,
        sample_proposicao_data: dict,
        sample_eleitor_data: dict,
    ) -> None:
        """Detail includes aggregated vote data."""
        from app.domain.proposicao import Proposicao
        from app.domain.eleitor import Eleitor
        from app.domain.voto_popular import VotoPopular, VotoEnum

        prop = Proposicao(**sample_proposicao_data)
        db_session.add(prop)
        eleitor = Eleitor(**sample_eleitor_data)
        db_session.add(eleitor)
        await db_session.flush()

        # Add 2 SIM + 1 NAO
        e2_data = {**sample_eleitor_data, "email": "e2@test.com", "chat_id": "22222", "cpf_hash": "b" * 64}
        e2 = Eleitor(**e2_data)
        e3_data = {**sample_eleitor_data, "email": "e3@test.com", "chat_id": "33333", "cpf_hash": "c" * 64}
        e3 = Eleitor(**e3_data)
        db_session.add_all([e2, e3])
        await db_session.flush()

        db_session.add_all([
            VotoPopular(eleitor_id=eleitor.id, proposicao_id=prop.id, voto=VotoEnum.SIM),
            VotoPopular(eleitor_id=e2.id, proposicao_id=prop.id, voto=VotoEnum.SIM),
            VotoPopular(eleitor_id=e3.id, proposicao_id=prop.id, voto=VotoEnum.NAO),
        ])
        await db_session.flush()

        access = ParlamentarAuthService.create_access_token(parlamentar_user)
        response = await client.get(
            f"/parlamentar/proposicoes/{prop.id}",
            headers={"Authorization": f"Bearer {access}"},
        )

        data = response.json()
        votos = data["votos"]
        assert votos["total"] == 3
        assert votos["sim"] == 2
        assert votos["nao"] == 1
        assert votos["abstencao"] == 0
        assert votos["percentual_sim"] == pytest.approx(66.7, abs=0.1)
        assert votos["percentual_nao"] == pytest.approx(33.3, abs=0.1)

    async def test_detail_with_analise(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        parlamentar_user: ParlamentarUser,
        sample_proposicao_data: dict,
    ) -> None:
        """Detail includes latest AI analysis."""
        from app.domain.proposicao import Proposicao
        from app.domain.analise_ia import AnaliseIA

        prop = Proposicao(**sample_proposicao_data)
        db_session.add(prop)
        await db_session.flush()

        analise = AnaliseIA(
            proposicao_id=prop.id,
            resumo_leigo="Resumo acessível do PL",
            impacto_esperado="Impacto no sistema tributário",
            areas_afetadas=["economia", "tributos"],
            argumentos_favor=["Simplificação"],
            argumentos_contra=["Aumento de carga"],
            provedor_llm="gemini",
            modelo="gemini-2.0-flash",
            versao=1,
        )
        db_session.add(analise)
        await db_session.flush()

        access = ParlamentarAuthService.create_access_token(parlamentar_user)
        response = await client.get(
            f"/parlamentar/proposicoes/{prop.id}",
            headers={"Authorization": f"Bearer {access}"},
        )

        data = response.json()
        assert data["analise"] is not None
        assert data["analise"]["resumo_leigo"] == "Resumo acessível do PL"
        assert data["analise"]["versao"] == 1
        assert "economia" in data["analise"]["areas_afetadas"]

    async def test_detail_with_comparativo(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        parlamentar_user: ParlamentarUser,
        sample_proposicao_data: dict,
        sample_votacao_data: dict,
    ) -> None:
        """Detail includes latest comparativo data."""
        from app.domain.proposicao import Proposicao
        from app.domain.votacao import Votacao
        from app.domain.comparativo import ComparativoVotacao

        prop = Proposicao(**sample_proposicao_data)
        db_session.add(prop)
        votacao = Votacao(**sample_votacao_data)
        db_session.add(votacao)
        await db_session.flush()

        comp = ComparativoVotacao(
            proposicao_id=prop.id,
            votacao_camara_id=votacao.id,
            voto_popular_sim=100,
            voto_popular_nao=50,
            voto_popular_abstencao=10,
            resultado_camara="APROVADO",
            votos_camara_sim=300,
            votos_camara_nao=150,
            alinhamento=0.85,
        )
        db_session.add(comp)
        await db_session.flush()

        access = ParlamentarAuthService.create_access_token(parlamentar_user)
        response = await client.get(
            f"/parlamentar/proposicoes/{prop.id}",
            headers={"Authorization": f"Bearer {access}"},
        )

        data = response.json()
        assert data["comparativo"] is not None
        assert data["comparativo"]["resultado_camara"] == "APROVADO"
        assert data["comparativo"]["alinhamento"] == 0.85
        assert data["comparativo"]["votos_camara_sim"] == 300

    async def test_detail_unauthenticated(self, client: AsyncClient) -> None:
        """GET /parlamentar/proposicoes/{id} without auth returns 422."""
        response = await client.get("/parlamentar/proposicoes/1")
        assert response.status_code == 422
