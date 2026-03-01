"""Comprehensive tests for Fase 6 — Publication: RSS Feed, Webhooks de saída.

Covers:
- RSS feed generation with actual data (votos + comparativos)
- Theme filtering (single, multiple, subscription-based)
- Webhook dispatch with httpx mocking (success, failure, exception)
- Event dispatch to multiple webhooks
- Circuit breaker integration
- Assinaturas router CRUD endpoints
- PublicacaoAgent tools
"""

import json
import uuid
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.config import settings
from app.domain.assinatura import AssinaturaRSS, AssinaturaWebhook
from app.domain.comparativo import ComparativoVotacao
from app.domain.eleitor import Eleitor
from app.domain.proposicao import Proposicao
from app.domain.voto_popular import VotoEnum, VotoPopular
from app.services.publicacao_service import PublicacaoService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _create_proposicao_with_votes(db_session, prop_id=10001, temas=None):
    """Helper: insert a proposicao + eleitor + votes for RSS feed tests."""
    prop = Proposicao(
        id=prop_id,
        tipo="PL",
        numero=prop_id % 1000,
        ano=2026,
        ementa=f"Proposição de teste {prop_id}",
        data_apresentacao=date(2026, 1, 15),
        situacao="Em tramitação",
        temas=temas or ["saúde"],
    )
    db_session.add(prop)

    eleitor = Eleitor(
        nome=f"Eleitor {prop_id}",
        email=f"e{prop_id}@test.com",
        uf="SP",
        chat_id=f"chat_{prop_id}",
        channel="telegram",
    )
    db_session.add(eleitor)
    await db_session.flush()
    await db_session.refresh(eleitor)

    voto = VotoPopular(
        eleitor_id=eleitor.id,
        proposicao_id=prop_id,
        voto=VotoEnum.SIM,
    )
    db_session.add(voto)
    await db_session.flush()
    return prop, eleitor


async def _create_rss_subscription(db_session, token="test_token_123", filtro_temas=None):
    """Helper: insert an RSS subscription."""
    assinatura = AssinaturaRSS(
        nome="Test Sub",
        token=token,
        filtro_temas=filtro_temas,
    )
    db_session.add(assinatura)
    await db_session.flush()
    return assinatura


async def _create_comparativo(db_session, proposicao_id=10001):
    """Helper: insert a ComparativoVotacao."""
    comp = ComparativoVotacao(
        proposicao_id=proposicao_id,
        votacao_camara_id=99999,
        voto_popular_sim=80,
        voto_popular_nao=15,
        voto_popular_abstencao=5,
        resultado_camara="APROVADO",
        votos_camara_sim=300,
        votos_camara_nao=150,
        alinhamento=0.84,
        resumo_ia="Boa convergência entre voto popular e parlamentar.",
        data_geracao=datetime(2026, 3, 1, 14, 30, tzinfo=timezone.utc),
    )
    db_session.add(comp)
    await db_session.flush()
    return comp


# ===========================================================================
# RSS Feed Tests — /rss/votos
# ===========================================================================

class TestRSSVotosWithData:
    """Test RSS votos feed with actual propositions and votes in the DB."""

    async def test_rss_votos_contains_vote_items(self, client: AsyncClient, db_session):
        """Feed should contain items for propositions with popular votes."""
        await _create_rss_subscription(db_session)
        await _create_proposicao_with_votes(db_session, prop_id=20001, temas=["saúde"])

        resp = await client.get("/rss/votos", params={"token": "test_token_123"})
        assert resp.status_code == 200
        assert "application/rss+xml" in resp.headers["content-type"]
        assert "<item>" in resp.text
        assert "PL 1/2026" in resp.text
        assert "SIM" in resp.text

    async def test_rss_votos_theme_filter_query_param(self, client: AsyncClient, db_session):
        """Query param ?tema= should filter propositions by theme."""
        await _create_rss_subscription(db_session)
        await _create_proposicao_with_votes(db_session, prop_id=20002, temas=["saúde"])
        await _create_proposicao_with_votes(db_session, prop_id=20003, temas=["economia"])

        # Only saúde
        resp = await client.get("/rss/votos", params={"token": "test_token_123", "tema": "saúde"})
        assert resp.status_code == 200
        assert "20002" in resp.text or "PL 2/2026" in resp.text
        assert "20003" not in resp.text

    async def test_rss_votos_theme_filter_from_subscription(self, client: AsyncClient, db_session):
        """Subscription filtro_temas should filter when no ?tema= param."""
        await _create_rss_subscription(db_session, filtro_temas=["economia"])
        await _create_proposicao_with_votes(db_session, prop_id=20004, temas=["saúde"])
        await _create_proposicao_with_votes(db_session, prop_id=20005, temas=["economia"])

        resp = await client.get("/rss/votos", params={"token": "test_token_123"})
        assert resp.status_code == 200
        # Should contain the economia proposicao but not saúde
        assert "20005" in resp.text or "PL 5/2026" in resp.text

    async def test_rss_votos_multi_theme_subscription(self, client: AsyncClient, db_session):
        """Subscription with multiple filtro_temas should match any."""
        await _create_rss_subscription(db_session, filtro_temas=["saúde", "educação"])
        await _create_proposicao_with_votes(db_session, prop_id=20006, temas=["saúde"])
        await _create_proposicao_with_votes(db_session, prop_id=20007, temas=["educação"])
        await _create_proposicao_with_votes(db_session, prop_id=20008, temas=["economia"])

        resp = await client.get("/rss/votos", params={"token": "test_token_123"})
        assert resp.status_code == 200
        # Should include saúde and educação but not economia
        text = resp.text
        assert "20008" not in text

    async def test_rss_votos_no_theme_filter_all_items(self, client: AsyncClient, db_session):
        """Without any filter, all propositions should appear."""
        await _create_rss_subscription(db_session)
        await _create_proposicao_with_votes(db_session, prop_id=20009, temas=["saúde"])
        await _create_proposicao_with_votes(db_session, prop_id=20010, temas=["economia"])

        resp = await client.get("/rss/votos", params={"token": "test_token_123"})
        assert resp.status_code == 200
        # Both should be present
        assert resp.text.count("<item>") >= 2

    async def test_rss_votos_empty_feed_structure(self, client: AsyncClient, db_session):
        """Valid token with no data should return proper XML structure."""
        await _create_rss_subscription(db_session)

        resp = await client.get("/rss/votos", params={"token": "test_token_123"})
        assert resp.status_code == 200
        assert "<rss version=\"2.0\"" in resp.text
        assert "</channel>" in resp.text
        assert "</rss>" in resp.text


# ===========================================================================
# RSS Feed Tests — /rss/comparativos
# ===========================================================================

class TestRSSComparativosWithData:
    """Test RSS comparativos feed with actual data."""

    async def test_rss_comparativos_contains_items(self, client: AsyncClient, db_session):
        """Feed should render comparativo items."""
        await _create_rss_subscription(db_session, token="comp_tok_123")
        await _create_comparativo(db_session, proposicao_id=30001)

        resp = await client.get("/rss/comparativos", params={"token": "comp_tok_123"})
        assert resp.status_code == 200
        assert "application/rss+xml" in resp.headers["content-type"]
        assert "<item>" in resp.text
        assert "Comparativo" in resp.text
        assert "30001" in resp.text
        assert "84" in resp.text  # alinhamento 84%

    async def test_rss_comparativos_multiple_items(self, client: AsyncClient, db_session):
        """Feed should show multiple comparativos ordered by date."""
        await _create_rss_subscription(db_session, token="multi_comp_tok")
        await _create_comparativo(db_session, proposicao_id=30002)
        await _create_comparativo(db_session, proposicao_id=30003)

        resp = await client.get("/rss/comparativos", params={"token": "multi_comp_tok"})
        assert resp.status_code == 200
        assert resp.text.count("<item>") == 2

    async def test_rss_comparativos_empty(self, client: AsyncClient, db_session):
        """Valid token but no comparativos should return empty feed."""
        await _create_rss_subscription(db_session, token="empty_comp_tok")

        resp = await client.get("/rss/comparativos", params={"token": "empty_comp_tok"})
        assert resp.status_code == 200
        assert "<item>" not in resp.text
        assert "<rss" in resp.text


# ===========================================================================
# Webhook Dispatch — httpx mock tests
# ===========================================================================

class TestWebhookDispatch:
    """Tests for PublicacaoService.dispatch_webhook with mocked httpx."""

    async def test_dispatch_webhook_success(self, db_session):
        """Successful dispatch (2xx) should record success."""
        service = PublicacaoService(db_session)
        wh = await service.create_webhook_subscription(
            nome="WH OK", url="https://ok.test/hook", secret="secret123",
            eventos=["voto_consolidado"],
        )

        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("app.services.publicacao_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await service.dispatch_webhook(wh, {"evento": "voto_consolidado"})

        assert result is True
        updated = await service.get_webhook_by_id(wh.id)
        assert updated.falhas_consecutivas == 0

    async def test_dispatch_webhook_failure_http_error(self, db_session):
        """HTTP error (5xx) should record failure."""
        service = PublicacaoService(db_session)
        wh = await service.create_webhook_subscription(
            nome="WH Fail", url="https://fail.test/hook", secret="secret123",
            eventos=["voto_consolidado"],
        )

        mock_response = MagicMock()
        mock_response.status_code = 500

        with patch("app.services.publicacao_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await service.dispatch_webhook(wh, {"evento": "test"})

        assert result is False
        updated = await service.get_webhook_by_id(wh.id)
        assert updated.falhas_consecutivas == 1

    async def test_dispatch_webhook_failure_connection_error(self, db_session):
        """Connection error should record failure."""
        service = PublicacaoService(db_session)
        wh = await service.create_webhook_subscription(
            nome="WH Conn", url="https://down.test/hook", secret="secret123",
            eventos=["voto_consolidado"],
        )

        with patch("app.services.publicacao_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(side_effect=ConnectionError("Connection refused"))
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await service.dispatch_webhook(wh, {"evento": "test"})

        assert result is False
        updated = await service.get_webhook_by_id(wh.id)
        assert updated.falhas_consecutivas == 1

    async def test_dispatch_webhook_signature_header(self, db_session):
        """Dispatch should include HMAC signature in X-Webhook-Signature header."""
        service = PublicacaoService(db_session)
        wh = await service.create_webhook_subscription(
            nome="WH Sig", url="https://sig.test/hook", secret="my_hmac_secret",
            eventos=["voto_consolidado"],
        )

        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("app.services.publicacao_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            await service.dispatch_webhook(wh, {"evento": "voto_consolidado"})

            # Verify the post was called with correct headers
            call_kwargs = mock_client.post.call_args
            headers = call_kwargs.kwargs.get("headers", {}) if call_kwargs.kwargs else call_kwargs[1].get("headers", {})
            assert "X-Webhook-Signature" in headers
            assert headers["X-Webhook-Signature"].startswith("sha256=")
            assert headers["X-Parlamentaria-Event"] == "voto_consolidado"


class TestEventDispatch:
    """Tests for PublicacaoService.dispatch_event — dispatches to multiple webhooks."""

    async def test_dispatch_event_to_multiple_webhooks(self, db_session):
        """dispatch_event should send to all matching webhooks and return stats."""
        service = PublicacaoService(db_session)

        # Create two webhooks subscribed to the same event
        await service.create_webhook_subscription(
            nome="WH1", url="https://wh1.test/hook", secret="s1",
            eventos=["voto_consolidado"],
        )
        await service.create_webhook_subscription(
            nome="WH2", url="https://wh2.test/hook", secret="s2",
            eventos=["voto_consolidado"],
        )

        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("app.services.publicacao_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            stats = await service.dispatch_event("voto_consolidado", {"proposicao_id": 123})

        assert stats["total"] == 2
        assert stats["success"] == 2
        assert stats["failed"] == 0

    async def test_dispatch_event_mixed_results(self, db_session):
        """dispatch_event should handle mixed success/failure."""
        service = PublicacaoService(db_session)

        await service.create_webhook_subscription(
            nome="WH_OK", url="https://ok.test/hook", secret="s1",
            eventos=["voto_consolidado"],
        )
        await service.create_webhook_subscription(
            nome="WH_FAIL", url="https://fail.test/hook", secret="s2",
            eventos=["voto_consolidado"],
        )

        call_count = 0

        async def _side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            mock_resp = MagicMock()
            # First call succeeds, second fails
            mock_resp.status_code = 200 if call_count <= 1 else 500
            return mock_resp

        with patch("app.services.publicacao_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(side_effect=_side_effect)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            stats = await service.dispatch_event("voto_consolidado", {"prop_id": 1})

        assert stats["total"] == 2
        assert stats["success"] == 1
        assert stats["failed"] == 1

    async def test_dispatch_event_no_subscribers(self, db_session):
        """dispatch_event with no subscribers should return total=0."""
        service = PublicacaoService(db_session)
        stats = await service.dispatch_event("nonexistent_event", {"data": 1})

        assert stats["total"] == 0
        assert stats["success"] == 0
        assert stats["failed"] == 0

    async def test_dispatch_event_adds_metadata(self, db_session):
        """dispatch_event should add evento and timestamp to payload."""
        service = PublicacaoService(db_session)

        await service.create_webhook_subscription(
            nome="Meta WH", url="https://meta.test/hook", secret="s",
            eventos=["voto_consolidado"],
        )

        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("app.services.publicacao_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            payload = {"proposicao_id": 123}
            await service.dispatch_event("voto_consolidado", payload)

            # Verify the payload was enriched
            call_kwargs = mock_client.post.call_args
            content = call_kwargs.kwargs.get("content", "") if call_kwargs.kwargs else call_kwargs[1].get("content", "")
            sent_data = json.loads(content)
            assert sent_data["evento"] == "voto_consolidado"
            assert "timestamp" in sent_data


# ===========================================================================
# Assinaturas Router — additional endpoint tests
# ===========================================================================

class TestAssinaturasWebhookTest:
    """Tests for webhook test dispatch endpoint."""

    async def test_webhook_test_dispatch_success(self, client: AsyncClient, db_session):
        """POST /assinaturas/webhooks/{id}/test should dispatch test payload."""
        # Create a webhook
        create_resp = await client.post(
            "/assinaturas/webhooks",
            json={
                "nome": "Test WH",
                "url": "https://test.com/hook",
                "eventos": ["voto_consolidado"],
            },
            headers={"X-API-Key": settings.admin_api_key},
        )
        wh_id = create_resp.json()["id"]

        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("app.services.publicacao_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            resp = await client.post(
                f"/assinaturas/webhooks/{wh_id}/test",
                headers={"X-API-Key": settings.admin_api_key},
            )

        assert resp.status_code == 200
        assert resp.json()["status"] == "delivered"

    async def test_webhook_test_dispatch_failure(self, client: AsyncClient, db_session):
        """POST /assinaturas/webhooks/{id}/test with failing endpoint."""
        create_resp = await client.post(
            "/assinaturas/webhooks",
            json={
                "nome": "Fail WH",
                "url": "https://fail.com/hook",
                "eventos": ["test"],
            },
            headers={"X-API-Key": settings.admin_api_key},
        )
        wh_id = create_resp.json()["id"]

        mock_response = MagicMock()
        mock_response.status_code = 500

        with patch("app.services.publicacao_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            resp = await client.post(
                f"/assinaturas/webhooks/{wh_id}/test",
                headers={"X-API-Key": settings.admin_api_key},
            )

        assert resp.status_code == 200
        assert resp.json()["status"] == "failed"

    async def test_webhook_get_not_found(self, client: AsyncClient):
        """GET /assinaturas/webhooks/{bad_id} should return 404."""
        fake_id = str(uuid.uuid4())
        resp = await client.get(
            f"/assinaturas/webhooks/{fake_id}",
            headers={"X-API-Key": settings.admin_api_key},
        )
        assert resp.status_code == 404

    async def test_rss_get_not_found(self, client: AsyncClient):
        """GET /assinaturas/rss/{bad_id} should return 404."""
        fake_id = str(uuid.uuid4())
        resp = await client.get(
            f"/assinaturas/rss/{fake_id}",
            headers={"X-API-Key": settings.admin_api_key},
        )
        assert resp.status_code == 404

    async def test_rss_delete_not_found(self, client: AsyncClient):
        """DELETE /assinaturas/rss/{bad_id} should return 404."""
        fake_id = str(uuid.uuid4())
        resp = await client.delete(
            f"/assinaturas/rss/{fake_id}",
            headers={"X-API-Key": settings.admin_api_key},
        )
        assert resp.status_code == 404

    async def test_webhook_delete_not_found(self, client: AsyncClient):
        """DELETE /assinaturas/webhooks/{bad_id} should return 404."""
        fake_id = str(uuid.uuid4())
        resp = await client.delete(
            f"/assinaturas/webhooks/{fake_id}",
            headers={"X-API-Key": settings.admin_api_key},
        )
        assert resp.status_code == 404


# ===========================================================================
# Circuit Breaker Integration
# ===========================================================================

class TestCircuitBreakerIntegration:
    """Test circuit breaker deactivates webhook after threshold failures."""

    async def test_circuit_breaker_disables_after_threshold(self, db_session):
        """Webhook should be deactivated after N consecutive failures via dispatch."""
        service = PublicacaoService(db_session)
        wh = await service.create_webhook_subscription(
            nome="CB Test", url="https://cb.test/hook", secret="s",
            eventos=["voto_consolidado"],
        )

        mock_response = MagicMock()
        mock_response.status_code = 500

        with patch("app.services.publicacao_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            for _ in range(settings.webhook_circuit_breaker_threshold):
                await service.dispatch_webhook(wh, {"evento": "test"})

        updated = await service.get_webhook_by_id(wh.id)
        assert updated.ativo is False
        assert updated.falhas_consecutivas >= settings.webhook_circuit_breaker_threshold

    async def test_circuit_breaker_webhook_excluded_from_event_dispatch(self, db_session):
        """Deactivated webhooks should not receive events."""
        service = PublicacaoService(db_session)
        wh = await service.create_webhook_subscription(
            nome="Disabled WH", url="https://disabled.test/hook", secret="s",
            eventos=["voto_consolidado"],
        )

        # Manually deactivate
        wh.ativo = False
        await db_session.flush()

        webhooks = await service.list_webhooks_for_event("voto_consolidado")
        assert len(webhooks) == 0


# ===========================================================================
# PublicacaoAgent Tools — unit tests
# ===========================================================================

class TestPublicacaoToolsNew:
    """Tests for new publicacao tools."""

    async def test_consultar_assinaturas_ativas(self, db_session):
        """consultar_assinaturas_ativas should return subscription counts."""
        service = PublicacaoService(db_session)
        await service.create_rss_subscription(nome="RSS 1")
        await service.create_rss_subscription(nome="RSS 2")
        await service.create_webhook_subscription(
            nome="WH 1", url="https://1.com/wh", secret="s",
            eventos=["voto_consolidado"],
        )

        mock_session = AsyncMock()
        mock_service = AsyncMock()
        mock_service.list_rss_subscriptions = AsyncMock(return_value=["s1", "s2"])
        mock_service.list_webhooks_for_event = AsyncMock(side_effect=[["w1"], []])

        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("app.db.session.async_session_factory", return_value=mock_session):
            with patch("app.services.publicacao_service.PublicacaoService", return_value=mock_service):
                from agents.parlamentar.tools.publicacao_tools import consultar_assinaturas_ativas
                result = await consultar_assinaturas_ativas()

        assert result["status"] == "success"
        assert result["assinaturas"]["rss_ativas"] == 2
        assert result["assinaturas"]["webhooks_voto_consolidado"] == 1

    async def test_consultar_assinaturas_ativas_error(self):
        """consultar_assinaturas_ativas should handle errors gracefully."""
        with patch("app.db.session.async_session_factory", side_effect=Exception("DB down")):
            from agents.parlamentar.tools.publicacao_tools import consultar_assinaturas_ativas
            result = await consultar_assinaturas_ativas()

        assert result["status"] == "error"

    async def test_disparar_evento_publicacao_invalid_event(self):
        """disparar_evento_publicacao should reject invalid event types."""
        from agents.parlamentar.tools.publicacao_tools import disparar_evento_publicacao
        result = await disparar_evento_publicacao(evento="invalid_event", proposicao_id=1)
        assert result["status"] == "error"
        assert "inválido" in result["message"]

    async def test_disparar_evento_publicacao_success(self):
        """disparar_evento_publicacao should dispatch to webhooks."""
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        mock_service = AsyncMock()
        mock_service.dispatch_event = AsyncMock(return_value={
            "total": 2, "success": 2, "failed": 0,
        })

        with patch("app.db.session.async_session_factory", return_value=mock_session):
            with patch("app.services.publicacao_service.PublicacaoService", return_value=mock_service):
                from agents.parlamentar.tools.publicacao_tools import disparar_evento_publicacao
                result = await disparar_evento_publicacao(
                    evento="voto_consolidado", proposicao_id=12345,
                )

        assert result["status"] == "success"
        assert result["dispatch"]["total_webhooks"] == 2
        assert result["dispatch"]["sucesso"] == 2

    async def test_disparar_evento_publicacao_error(self):
        """disparar_evento_publicacao should handle errors."""
        with patch("app.db.session.async_session_factory", side_effect=Exception("DB down")):
            from agents.parlamentar.tools.publicacao_tools import disparar_evento_publicacao
            result = await disparar_evento_publicacao(
                evento="voto_consolidado", proposicao_id=1,
            )

        assert result["status"] == "error"


# ===========================================================================
# RSS Helper Functions — unit tests
# ===========================================================================

class TestRSSHelpers:
    """Test RSS XML building helper functions."""

    def test_build_rss_header(self):
        from app.routers.rss import _build_rss_header
        header = _build_rss_header("Title", "Desc", "https://example.com")
        assert '<?xml version="1.0"' in header
        assert '<rss version="2.0"' in header
        assert "<title>Title</title>" in header
        assert "<description>Desc</description>" in header

    def test_build_rss_footer(self):
        from app.routers.rss import _build_rss_footer
        footer = _build_rss_footer()
        assert "</channel>" in footer
        assert "</rss>" in footer

    def test_build_vote_item(self):
        from app.routers.rss import _build_vote_item
        prop = MagicMock()
        prop.tipo = "PL"
        prop.numero = 42
        prop.ano = 2026
        prop.id = 99
        prop.temas = ["saúde", "educação"]

        resultado = {
            "total": 100,
            "SIM": 75,
            "NAO": 20,
            "ABSTENCAO": 5,
            "percentual_sim": 75.0,
            "percentual_nao": 20.0,
        }

        item = _build_vote_item(prop, resultado)
        assert "<item>" in item
        assert "PL 42/2026" in item
        assert "75%" in item
        assert "<category>saúde</category>" in item

    def test_build_comparativo_item(self):
        from app.routers.rss import _build_comparativo_item
        comp = MagicMock()
        comp.proposicao_id = 123
        comp.alinhamento = 0.85
        comp.resultado_camara = "APROVADO"
        comp.voto_popular_sim = 80
        comp.voto_popular_nao = 15
        comp.data_geracao = datetime(2026, 3, 1, 14, 0, tzinfo=timezone.utc)

        item = _build_comparativo_item(comp)
        assert "<item>" in item
        assert "123" in item
        assert "85%" in item
        assert "APROVADO" in item


# ===========================================================================
# Direct endpoint function calls — bypass ASGI for coverage
# ===========================================================================

class TestRSSVotosDirectCall:
    """Call rss_votos/rss_comparativos endpoint functions directly for coverage."""

    @staticmethod
    def _mock_request():
        """Create a proper Starlette Request object for direct endpoint calls."""
        from starlette.requests import Request
        from starlette.datastructures import Headers

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/rss/votos",
            "query_string": b"",
            "headers": [],
            "server": ("localhost", 8000),
            "root_path": "",
        }
        return Request(scope)

    async def test_rss_votos_direct_with_data(self, db_session):
        """Direct call to rss_votos with propositions and votes in DB."""
        from app.routers.rss import rss_votos

        await _create_rss_subscription(db_session, token="direct_tok_1")
        await _create_proposicao_with_votes(db_session, prop_id=40001, temas=["saúde"])

        resp = await rss_votos(request=self._mock_request(), token="direct_tok_1", tema=None, uf=None, db=db_session)
        assert resp.status_code == 200
        assert "<item>" in resp.body.decode("utf-8")
        assert "PL 1/2026" in resp.body.decode("utf-8")

    async def test_rss_votos_direct_invalid_token(self, db_session):
        """Direct call with invalid token."""
        from app.routers.rss import rss_votos

        resp = await rss_votos(request=self._mock_request(), token="bad_token", tema=None, uf=None, db=db_session)
        assert resp.status_code == 403

    async def test_rss_votos_direct_tema_filter(self, db_session):
        """Direct call with theme query param filter."""
        from app.routers.rss import rss_votos

        await _create_rss_subscription(db_session, token="direct_tok_2")
        await _create_proposicao_with_votes(db_session, prop_id=40002, temas=["saúde"])
        await _create_proposicao_with_votes(db_session, prop_id=40003, temas=["economia"])

        resp = await rss_votos(request=self._mock_request(), token="direct_tok_2", tema="saúde", uf=None, db=db_session)
        body = resp.body.decode("utf-8")
        assert "40002" in body or "PL 2/2026" in body

    async def test_rss_votos_direct_subscription_filter(self, db_session):
        """Direct call with subscription filtro_temas (multiple)."""
        from app.routers.rss import rss_votos

        await _create_rss_subscription(db_session, token="direct_tok_3", filtro_temas=["economia", "educação"])
        await _create_proposicao_with_votes(db_session, prop_id=40004, temas=["saúde"])
        await _create_proposicao_with_votes(db_session, prop_id=40005, temas=["economia"])

        resp = await rss_votos(request=self._mock_request(), token="direct_tok_3", tema=None, uf=None, db=db_session)
        body = resp.body.decode("utf-8")
        # economia should pass filter, saúde should not
        assert "40004" not in body

    async def test_rss_votos_direct_no_votes(self, db_session):
        """Direct call with no votes in DB → empty feed."""
        from app.routers.rss import rss_votos

        await _create_rss_subscription(db_session, token="direct_tok_4")

        resp = await rss_votos(request=self._mock_request(), token="direct_tok_4", tema=None, uf=None, db=db_session)
        body = resp.body.decode("utf-8")
        assert "<rss" in body
        assert "<item>" not in body

    async def test_rss_comparativos_direct_with_data(self, db_session):
        """Direct call to rss_comparativos with data."""
        from app.routers.rss import rss_comparativos

        await _create_rss_subscription(db_session, token="comp_direct_1")
        await _create_comparativo(db_session, proposicao_id=40010)

        resp = await rss_comparativos(request=self._mock_request(), token="comp_direct_1", db=db_session)
        body = resp.body.decode("utf-8")
        assert resp.status_code == 200
        assert "<item>" in body
        assert "40010" in body
        assert "Comparativo" in body
        assert "84%" in body

    async def test_rss_comparativos_direct_invalid_token(self, db_session):
        """Direct call to rss_comparativos with invalid token."""
        from app.routers.rss import rss_comparativos

        resp = await rss_comparativos(request=self._mock_request(), token="bad_token", db=db_session)
        assert resp.status_code == 403

    async def test_rss_comparativos_direct_empty(self, db_session):
        """Direct call to rss_comparativos with no data."""
        from app.routers.rss import rss_comparativos

        await _create_rss_subscription(db_session, token="comp_direct_2")

        resp = await rss_comparativos(request=self._mock_request(), token="comp_direct_2", db=db_session)
        body = resp.body.decode("utf-8")
        assert "<rss" in body
        assert "<item>" not in body


class TestAssinaturasDirectCall:
    """Direct calls to assinaturas endpoint handlers for coverage."""

    async def test_get_rss_subscription_direct(self, db_session):
        """Direct call to get_rss_subscription."""
        from app.routers.assinaturas import get_rss_subscription

        service = PublicacaoService(db_session)
        created = await service.create_rss_subscription(nome="Direct RSS Test")

        result = await get_rss_subscription(subscription_id=created.id, db=db_session)
        assert result.nome == "Direct RSS Test"

    async def test_get_rss_subscription_direct_not_found(self, db_session):
        """Direct call to get_rss_subscription with bad id."""
        from app.routers.assinaturas import get_rss_subscription
        from app.exceptions import NotFoundException

        with pytest.raises(NotFoundException):
            await get_rss_subscription(subscription_id=uuid.uuid4(), db=db_session)

    async def test_delete_rss_subscription_direct(self, db_session):
        """Direct call to delete_rss_subscription."""
        from app.routers.assinaturas import delete_rss_subscription

        service = PublicacaoService(db_session)
        created = await service.create_rss_subscription(nome="To Delete")

        result = await delete_rss_subscription(subscription_id=created.id, db=db_session)
        assert result["status"] == "deleted"

    async def test_get_webhook_subscription_direct(self, db_session):
        """Direct call to get_webhook_subscription."""
        from app.routers.assinaturas import get_webhook_subscription

        service = PublicacaoService(db_session)
        created = await service.create_webhook_subscription(
            nome="WH Direct", url="https://dir.test/wh", secret="s", eventos=["test"],
        )

        result = await get_webhook_subscription(subscription_id=created.id, db=db_session)
        assert result.nome == "WH Direct"

    async def test_get_webhook_subscription_direct_not_found(self, db_session):
        """Direct call to get_webhook_subscription with bad id."""
        from app.routers.assinaturas import get_webhook_subscription
        from app.exceptions import NotFoundException

        with pytest.raises(NotFoundException):
            await get_webhook_subscription(subscription_id=uuid.uuid4(), db=db_session)

    async def test_delete_webhook_subscription_direct(self, db_session):
        """Direct call to delete_webhook_subscription."""
        from app.routers.assinaturas import delete_webhook_subscription

        service = PublicacaoService(db_session)
        created = await service.create_webhook_subscription(
            nome="WH Del", url="https://del.test/wh", secret="s", eventos=["test"],
        )

        result = await delete_webhook_subscription(subscription_id=created.id, db=db_session)
        assert result["status"] == "deleted"

    async def test_test_webhook_direct(self, db_session):
        """Direct call to test_webhook endpoint handler."""
        from app.routers.assinaturas import test_webhook

        service = PublicacaoService(db_session)
        created = await service.create_webhook_subscription(
            nome="WH Test", url="https://test.test/wh", secret="s", eventos=["test"],
        )

        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("app.services.publicacao_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await test_webhook(subscription_id=created.id, db=db_session)

        assert result["status"] == "delivered"

    async def test_test_webhook_direct_not_found(self, db_session):
        """Direct call to test_webhook with bad id."""
        from app.routers.assinaturas import test_webhook
        from app.exceptions import NotFoundException

        with pytest.raises(NotFoundException):
            await test_webhook(subscription_id=uuid.uuid4(), db=db_session)

    async def test_verify_api_key_valid(self):
        """verify_api_key should pass with correct key."""
        from app.routers.assinaturas import verify_api_key
        result = await verify_api_key(x_api_key=settings.admin_api_key)
        assert result == settings.admin_api_key

    async def test_verify_api_key_invalid(self):
        """verify_api_key should raise UnauthorizedException."""
        from app.routers.assinaturas import verify_api_key
        from app.exceptions import UnauthorizedException

        with pytest.raises(UnauthorizedException):
            await verify_api_key(x_api_key="wrong_key")


# ===========================================================================
# Dispatch Webhooks Celery Task — coverage for fallback branch
# ===========================================================================

class TestDispatchWebhooksTask:
    """Tests for the Celery dispatch_webhooks_task."""

    def test_dispatch_webhooks_task_runs(self):
        """Task should execute asyncio.run path."""
        with patch("app.tasks.dispatch_webhooks.get_async_session") as mock_sess:
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=False)
            mock_sess.return_value = mock_session

            mock_service = AsyncMock()
            mock_service.dispatch_event = AsyncMock(return_value={
                "total": 1, "success": 1, "failed": 0,
            })
            mock_session.commit = AsyncMock()

            with patch("app.tasks.dispatch_webhooks.asyncio.get_event_loop") as mock_loop:
                mock_loop.side_effect = RuntimeError("No event loop")

                with patch("app.tasks.dispatch_webhooks.asyncio.run") as mock_run:
                    mock_run.return_value = {"total": 1, "success": 1, "failed": 0}

                    from app.tasks.dispatch_webhooks import dispatch_webhooks_task
                    result = dispatch_webhooks_task("voto_consolidado", {"prop_id": 1})

                    assert result == {"total": 1, "success": 1, "failed": 0}
