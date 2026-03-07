"""Tests for RSS and Assinaturas routers."""

import pytest
import uuid
from datetime import date, datetime, timezone
from unittest.mock import patch, MagicMock

from httpx import AsyncClient

from app.config import settings
from app.domain.proposicao import Proposicao
from app.domain.eleitor import Eleitor
from app.domain.deputado import Deputado
from app.domain.partido import Partido
from app.domain.evento import Evento
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


# ------------------------------------------------------------------
# Admin: Deputados
# ------------------------------------------------------------------


@pytest.mark.asyncio
class TestAdminDeputadosRouter:
    """Tests for admin deputy endpoints."""

    async def test_list_deputados(self, client: AsyncClient, db_session):
        dep = Deputado(
            id=999, nome="Dep Teste", sigla_partido="PT", sigla_uf="SP",
        )
        db_session.add(dep)
        await db_session.flush()

        resp = await client.get(
            "/admin/deputados",
            headers={"X-API-Key": settings.admin_api_key},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["nome"] == "Dep Teste"
        assert data["items"][0]["sigla_partido"] == "PT"

    async def test_list_deputados_filter_uf(self, client: AsyncClient, db_session):
        dep1 = Deputado(id=1001, nome="Dep SP", sigla_partido="PT", sigla_uf="SP")
        dep2 = Deputado(id=1002, nome="Dep RJ", sigla_partido="PL", sigla_uf="RJ")
        db_session.add_all([dep1, dep2])
        await db_session.flush()

        resp = await client.get(
            "/admin/deputados?sigla_uf=SP",
            headers={"X-API-Key": settings.admin_api_key},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["sigla_uf"] == "SP"

    async def test_list_deputados_unauthorized(self, client: AsyncClient):
        resp = await client.get("/admin/deputados")
        assert resp.status_code == 422  # Missing header

    @patch("app.tasks.sync_deputados.sync_deputados_task")
    async def test_sync_deputados(self, mock_task, client: AsyncClient):
        mock_task.delay = MagicMock()
        resp = await client.post(
            "/admin/sync/deputados",
            headers={"X-API-Key": settings.admin_api_key},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "queued"
        mock_task.delay.assert_called_once()

    @patch("app.tasks.sync_deputados.sync_deputados_task")
    async def test_sync_deputados_with_filters(self, mock_task, client: AsyncClient):
        mock_task.delay = MagicMock()
        resp = await client.post(
            "/admin/sync/deputados?sigla_uf=MG&sigla_partido=PT",
            headers={"X-API-Key": settings.admin_api_key},
        )
        assert resp.status_code == 200
        mock_task.delay.assert_called_once_with(sigla_uf="MG", sigla_partido="PT")


# ------------------------------------------------------------------
# Admin: Partidos
# ------------------------------------------------------------------


@pytest.mark.asyncio
class TestAdminPartidosRouter:
    """Tests for admin party endpoints."""

    async def test_list_partidos(self, client: AsyncClient, db_session):
        partido = Partido(id=100, sigla="PT", nome="Partido dos Trabalhadores")
        db_session.add(partido)
        await db_session.flush()

        resp = await client.get(
            "/admin/partidos",
            headers={"X-API-Key": settings.admin_api_key},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["sigla"] == "PT"

    async def test_list_partidos_empty(self, client: AsyncClient):
        resp = await client.get(
            "/admin/partidos",
            headers={"X-API-Key": settings.admin_api_key},
        )
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    @patch("app.tasks.sync_partidos.sync_partidos_task")
    async def test_sync_partidos(self, mock_task, client: AsyncClient):
        mock_task.delay = MagicMock()
        resp = await client.post(
            "/admin/sync/partidos",
            headers={"X-API-Key": settings.admin_api_key},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "queued"
        mock_task.delay.assert_called_once()


# ------------------------------------------------------------------
# Admin: Eventos
# ------------------------------------------------------------------


@pytest.mark.asyncio
class TestAdminEventosRouter:
    """Tests for admin event endpoints."""

    async def test_list_eventos(self, client: AsyncClient, db_session):
        evento = Evento(
            id=500,
            descricao="Sessão Plenária Ordinária",
            tipo_evento="Sessão Deliberativa",
            data_inicio=datetime(2026, 3, 1, 14, 0, tzinfo=timezone.utc),
            situacao="Encerrada",
        )
        db_session.add(evento)
        await db_session.flush()

        resp = await client.get(
            "/admin/eventos",
            headers={"X-API-Key": settings.admin_api_key},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["descricao"] == "Sessão Plenária Ordinária"

    async def test_list_eventos_empty(self, client: AsyncClient):
        resp = await client.get(
            "/admin/eventos",
            headers={"X-API-Key": settings.admin_api_key},
        )
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    @patch("app.tasks.sync_eventos.sync_eventos_task")
    async def test_sync_eventos(self, mock_task, client: AsyncClient):
        mock_task.delay = MagicMock()
        resp = await client.post(
            "/admin/sync/eventos",
            headers={"X-API-Key": settings.admin_api_key},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "queued"
        mock_task.delay.assert_called_once()

    @patch("app.tasks.sync_eventos.sync_eventos_task")
    async def test_sync_eventos_with_dias_atras(self, mock_task, client: AsyncClient):
        mock_task.delay = MagicMock()
        resp = await client.post(
            "/admin/sync/eventos?dias_atras=30",
            headers={"X-API-Key": settings.admin_api_key},
        )
        assert resp.status_code == 200
        mock_task.delay.assert_called_once_with(dias_atras=30)


# ------------------------------------------------------------------
# Admin: Sync Proposições / Votações / All
# ------------------------------------------------------------------


@pytest.mark.asyncio
class TestAdminSyncGeneralRouter:
    """Tests for general sync admin endpoints."""

    @patch("app.tasks.sync_proposicoes.sync_proposicoes_task")
    async def test_sync_proposicoes(self, mock_task, client: AsyncClient):
        mock_task.delay = MagicMock()
        resp = await client.post(
            "/admin/sync/proposicoes?ano=2026&sigla_tipo=PL",
            headers={"X-API-Key": settings.admin_api_key},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "queued"
        mock_task.delay.assert_called_once_with(ano=2026, sigla_tipo="PL")

    @patch("app.tasks.sync_votacoes.sync_votacoes_task")
    async def test_sync_votacoes(self, mock_task, client: AsyncClient):
        mock_task.delay = MagicMock()
        resp = await client.post(
            "/admin/sync/votacoes",
            headers={"X-API-Key": settings.admin_api_key},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "queued"
        mock_task.delay.assert_called_once()

    async def test_sync_all(self, client: AsyncClient):
        with patch("app.tasks.sync_proposicoes.sync_proposicoes_task") as m1, \
             patch("app.tasks.sync_votacoes.sync_votacoes_task") as m2, \
             patch("app.tasks.sync_deputados.sync_deputados_task") as m3, \
             patch("app.tasks.sync_partidos.sync_partidos_task") as m4, \
             patch("app.tasks.sync_eventos.sync_eventos_task") as m5:
            m1.delay = MagicMock()
            m2.delay = MagicMock()
            m3.delay = MagicMock()
            m4.delay = MagicMock()
            m5.delay = MagicMock()

            resp = await client.post(
                "/admin/sync/all",
                headers={"X-API-Key": settings.admin_api_key},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "queued"
            m1.delay.assert_called_once()
            m2.delay.assert_called_once()
            m3.delay.assert_called_once()
            m4.delay.assert_called_once()
            m5.delay.assert_called_once()

    async def test_sync_all_unauthorized(self, client: AsyncClient):
        resp = await client.post("/admin/sync/all")
        assert resp.status_code == 422  # Missing header
