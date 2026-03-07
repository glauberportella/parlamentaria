"""Tests for RSS and Assinaturas routers."""

import pytest
import uuid
from datetime import date

from httpx import AsyncClient

from app.config import settings
from app.domain.proposicao import Proposicao
from app.domain.eleitor import Eleitor
from app.domain.voto_popular import VotoPopular, VotoEnum, TipoVoto
from app.domain.assinatura import AssinaturaRSS


class TestRSSRouter:
    """Tests for /rss/* endpoints."""

    async def test_rss_votos_invalid_token(self, client: AsyncClient):
        """GET /rss/votos with bad token should return 403."""
        resp = await client.get("/rss/votos", params={"token": "bad_token"})
        assert resp.status_code == 403

    async def test_rss_votos_valid_token(self, client: AsyncClient, db_session):
        """GET /rss/votos with valid token should return RSS XML."""
        # Create an RSS subscription
        assinatura = AssinaturaRSS(nome="Test", token="valid_test_token_12345")
        db_session.add(assinatura)
        await db_session.flush()

        resp = await client.get("/rss/votos", params={"token": "valid_test_token_12345"})
        assert resp.status_code == 200
        assert "application/rss+xml" in resp.headers["content-type"]
        assert "<rss" in resp.text
        assert "Parlamentaria" in resp.text

    async def test_rss_votos_with_data(self, client: AsyncClient, db_session):
        """RSS feed should include items for propositions with popular votes."""
        assinatura = AssinaturaRSS(nome="Test", token="feed_token_123")
        db_session.add(assinatura)

        prop = Proposicao(
            id=12345, tipo="PL", numero=100, ano=2024,
            ementa="Transparência legislativa",
            data_apresentacao=date(2024, 3, 15),
            situacao="Em tramitação",
        )
        db_session.add(prop)

        eleitor = Eleitor(
            nome="Maria", email="maria@test.com", uf="SP",
            chat_id="t123", channel="telegram",
            cidadao_brasileiro=True,
            data_nascimento=date(1990, 1, 1),
            verificado=True,
        )
        db_session.add(eleitor)
        await db_session.flush()
        await db_session.refresh(eleitor)

        voto = VotoPopular(
            eleitor_id=eleitor.id, proposicao_id=12345, voto=VotoEnum.SIM,
            tipo_voto=TipoVoto.OFICIAL,
        )
        db_session.add(voto)
        await db_session.flush()

        resp = await client.get("/rss/votos", params={"token": "feed_token_123"})
        assert resp.status_code == 200
        assert "PL 100/2024" in resp.text
        assert "100%" in resp.text or "SIM" in resp.text

    async def test_rss_comparativos_invalid_token(self, client: AsyncClient):
        """GET /rss/comparativos with bad token should return 403."""
        resp = await client.get("/rss/comparativos", params={"token": "bad"})
        assert resp.status_code == 403

    async def test_rss_comparativos_valid_token(self, client: AsyncClient, db_session):
        """GET /rss/comparativos with valid token should return RSS XML."""
        assinatura = AssinaturaRSS(nome="Test", token="comp_token_abc")
        db_session.add(assinatura)
        await db_session.flush()

        resp = await client.get("/rss/comparativos", params={"token": "comp_token_abc"})
        assert resp.status_code == 200
        assert "<rss" in resp.text


class TestAssinaturasRouter:
    """Tests for /assinaturas/* endpoints."""

    # --- RSS ---

    async def test_create_rss_subscription(self, client: AsyncClient):
        resp = await client.post(
            "/assinaturas/rss",
            json={"nome": "Dep. Teste", "email": "dep@test.com"},
            headers={"X-API-Key": settings.admin_api_key},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["nome"] == "Dep. Teste"
        assert "token" in data

    async def test_create_rss_subscription_no_auth(self, client: AsyncClient):
        resp = await client.post(
            "/assinaturas/rss",
            json={"nome": "Test"},
        )
        assert resp.status_code == 422  # Missing header

    async def test_get_rss_subscription(self, client: AsyncClient):
        # Create first
        create_resp = await client.post(
            "/assinaturas/rss",
            json={"nome": "Fetch Me"},
            headers={"X-API-Key": settings.admin_api_key},
        )
        sub_id = create_resp.json()["id"]

        resp = await client.get(
            f"/assinaturas/rss/{sub_id}",
            headers={"X-API-Key": settings.admin_api_key},
        )
        assert resp.status_code == 200
        assert resp.json()["nome"] == "Fetch Me"

    async def test_get_rss_subscription_not_found(self, client: AsyncClient):
        fake_id = str(uuid.uuid4())
        resp = await client.get(
            f"/assinaturas/rss/{fake_id}",
            headers={"X-API-Key": settings.admin_api_key},
        )
        assert resp.status_code == 404

    async def test_delete_rss_subscription(self, client: AsyncClient):
        create_resp = await client.post(
            "/assinaturas/rss",
            json={"nome": "Delete Me"},
            headers={"X-API-Key": settings.admin_api_key},
        )
        sub_id = create_resp.json()["id"]

        resp = await client.delete(
            f"/assinaturas/rss/{sub_id}",
            headers={"X-API-Key": settings.admin_api_key},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "deleted"

    # --- Webhooks ---

    async def test_create_webhook_subscription(self, client: AsyncClient):
        resp = await client.post(
            "/assinaturas/webhooks",
            json={
                "nome": "External System",
                "url": "https://example.com/hook",
                "eventos": ["voto_consolidado"],
            },
            headers={"X-API-Key": settings.admin_api_key},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["nome"] == "External System"
        assert data["ativo"] is True

    async def test_get_webhook_subscription(self, client: AsyncClient):
        create_resp = await client.post(
            "/assinaturas/webhooks",
            json={
                "nome": "Get Me",
                "url": "https://example.com/hook2",
                "eventos": ["test"],
            },
            headers={"X-API-Key": settings.admin_api_key},
        )
        wh_id = create_resp.json()["id"]

        resp = await client.get(
            f"/assinaturas/webhooks/{wh_id}",
            headers={"X-API-Key": settings.admin_api_key},
        )
        assert resp.status_code == 200
        assert resp.json()["nome"] == "Get Me"

    async def test_delete_webhook_subscription(self, client: AsyncClient):
        create_resp = await client.post(
            "/assinaturas/webhooks",
            json={
                "nome": "Delete WH",
                "url": "https://example.com/del",
                "eventos": ["test"],
            },
            headers={"X-API-Key": settings.admin_api_key},
        )
        wh_id = create_resp.json()["id"]

        resp = await client.delete(
            f"/assinaturas/webhooks/{wh_id}",
            headers={"X-API-Key": settings.admin_api_key},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "deleted"

    async def test_test_webhook_not_found(self, client: AsyncClient):
        fake_id = str(uuid.uuid4())
        resp = await client.post(
            f"/assinaturas/webhooks/{fake_id}/test",
            headers={"X-API-Key": settings.admin_api_key},
        )
        assert resp.status_code == 404


class TestAdminRouterUpdated:
    """Tests for updated admin endpoints with service layer."""

    async def test_admin_proposicoes_returns_items(self, client: AsyncClient, db_session):
        prop = Proposicao(
            id=55555, tipo="PEC", numero=10, ano=2025,
            ementa="Test prop", data_apresentacao=date(2025, 1, 1),
            situacao="Em tramitação",
        )
        db_session.add(prop)
        await db_session.flush()

        resp = await client.get(
            "/admin/proposicoes",
            headers={"X-API-Key": settings.admin_api_key},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["id"] == 55555

    async def test_admin_eleitores_returns_items(self, client: AsyncClient, db_session):
        eleitor = Eleitor(
            nome="Admin Test", email="admin@test.com", uf="RJ",
            chat_id="admin_chat", channel="telegram",
        )
        db_session.add(eleitor)
        await db_session.flush()

        resp = await client.get(
            "/admin/eleitores",
            headers={"X-API-Key": settings.admin_api_key},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["nome"] == "Admin Test"

    async def test_admin_resultado_votacao(self, client: AsyncClient, db_session):
        prop = Proposicao(
            id=66666, tipo="PL", numero=666, ano=2024,
            ementa="Test", data_apresentacao=date(2024, 1, 1),
            situacao="Em tramitação",
        )
        db_session.add(prop)
        await db_session.flush()

        resp = await client.get(
            "/admin/votacoes/resultado/66666",
            headers={"X-API-Key": settings.admin_api_key},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["proposicao_id"] == 66666
        assert "oficial" in data
        assert "consultivo" in data
        assert data["oficial"]["total"] == 0

    async def test_admin_trigger_analise(self, client: AsyncClient):
        """Trigger analysis returns 404 when proposition does not exist."""
        resp = await client.post(
            "/admin/proposicoes/12345/analisar",
            headers={"X-API-Key": settings.admin_api_key},
        )
        # Endpoint now validates that the proposition exists before enqueuing
        assert resp.status_code == 404

    async def test_admin_comparativos(self, client: AsyncClient):
        resp = await client.get(
            "/admin/comparativos",
            headers={"X-API-Key": settings.admin_api_key},
        )
        assert resp.status_code == 200
        assert resp.json()["total"] == 0
