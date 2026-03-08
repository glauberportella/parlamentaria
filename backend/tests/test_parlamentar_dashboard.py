"""Tests for the parliamentarian dashboard: auth service, routers, and JWT flows."""

import secrets
from datetime import datetime, timezone
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


class TestDashboardRouter:
    """Test /parlamentar/dashboard endpoints."""

    async def test_resumo_authenticated(
        self,
        client: AsyncClient,
        parlamentar_user: ParlamentarUser,
    ) -> None:
        """GET /parlamentar/dashboard/resumo returns dashboard data."""
        access = ParlamentarAuthService.create_access_token(parlamentar_user)

        response = await client.get(
            "/parlamentar/dashboard/resumo",
            headers={"Authorization": f"Bearer {access}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "kpis" in data
        assert "temas_ativos" in data
        assert "proposicoes_ranking" in data
        assert "alertas" in data

        # KPIs should have expected keys
        kpis = data["kpis"]
        assert "total_proposicoes" in kpis
        assert "total_eleitores" in kpis
        assert "total_votos" in kpis
        assert "alinhamento_medio" in kpis

    async def test_resumo_unauthenticated(self, client: AsyncClient) -> None:
        """GET /parlamentar/dashboard/resumo without auth returns 422."""
        response = await client.get("/parlamentar/dashboard/resumo")
        assert response.status_code == 422
