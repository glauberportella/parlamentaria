"""Tests for PublicacaoService."""

import pytest
import uuid

from app.domain.assinatura import AssinaturaRSS, AssinaturaWebhook
from app.exceptions import NotFoundException
from app.services.publicacao_service import PublicacaoService


@pytest.fixture
async def service(db_session):
    return PublicacaoService(db_session)


class TestRSSSubscriptions:
    """Tests for RSS subscription management."""

    async def test_create_rss_subscription(self, service):
        result = await service.create_rss_subscription(
            nome="Deputado X",
            email="dep@camara.leg.br",
            filtro_temas=["saúde"],
            filtro_uf="SP",
        )
        assert result.nome == "Deputado X"
        assert result.token is not None
        assert len(result.token) == 32  # uuid4 hex
        assert result.ativo is True

    async def test_get_rss_by_token(self, service):
        created = await service.create_rss_subscription(nome="Test")
        result = await service.get_rss_by_token(created.token)
        assert result is not None
        assert result.id == created.id

    async def test_get_rss_by_token_invalid(self, service):
        result = await service.get_rss_by_token("nonexistent_token")
        assert result is None

    async def test_get_rss_by_id(self, service):
        created = await service.create_rss_subscription(nome="Test")
        result = await service.get_rss_by_id(created.id)
        assert result.nome == "Test"

    async def test_get_rss_by_id_not_found(self, service):
        with pytest.raises(NotFoundException):
            await service.get_rss_by_id(uuid.uuid4())

    async def test_delete_rss(self, service):
        created = await service.create_rss_subscription(nome="To Delete")
        await service.delete_rss(created.id)
        with pytest.raises(NotFoundException):
            await service.get_rss_by_id(created.id)

    async def test_list_rss_subscriptions(self, service):
        await service.create_rss_subscription(nome="Sub 1")
        await service.create_rss_subscription(nome="Sub 2")
        result = await service.list_rss_subscriptions()
        assert len(result) == 2


class TestWebhookSubscriptions:
    """Tests for webhook subscription management."""

    async def test_create_webhook_subscription(self, service):
        result = await service.create_webhook_subscription(
            nome="Sistema Externo",
            url="https://example.com/webhook",
            secret="my_secret_123",
            eventos=["voto_consolidado"],
            filtro_temas=["economia"],
        )
        assert result.nome == "Sistema Externo"
        assert result.url == "https://example.com/webhook"
        assert result.ativo is True
        assert result.falhas_consecutivas == 0

    async def test_get_webhook_by_id(self, service):
        created = await service.create_webhook_subscription(
            nome="Test", url="https://test.com/wh", secret="s", eventos=["test"],
        )
        result = await service.get_webhook_by_id(created.id)
        assert result.nome == "Test"

    async def test_get_webhook_by_id_not_found(self, service):
        with pytest.raises(NotFoundException):
            await service.get_webhook_by_id(uuid.uuid4())

    async def test_update_webhook(self, service):
        created = await service.create_webhook_subscription(
            nome="Old Name", url="https://old.com/wh", secret="s", eventos=["test"],
        )
        updated = await service.update_webhook(created.id, {"nome": "New Name"})
        assert updated.nome == "New Name"

    async def test_delete_webhook(self, service):
        created = await service.create_webhook_subscription(
            nome="ToDelete", url="https://del.com/wh", secret="s", eventos=["test"],
        )
        await service.delete_webhook(created.id)
        with pytest.raises(NotFoundException):
            await service.get_webhook_by_id(created.id)


class TestWebhookDispatch:
    """Tests for webhook dispatch and circuit breaker logic."""

    async def test_list_webhooks_for_event(self, service):
        await service.create_webhook_subscription(
            nome="WH1", url="https://1.com/wh", secret="s",
            eventos=["voto_consolidado", "comparativo_gerado"],
        )
        await service.create_webhook_subscription(
            nome="WH2", url="https://2.com/wh", secret="s",
            eventos=["comparativo_gerado"],
        )

        voto_hooks = await service.list_webhooks_for_event("voto_consolidado")
        assert len(voto_hooks) == 1

        comp_hooks = await service.list_webhooks_for_event("comparativo_gerado")
        assert len(comp_hooks) == 2

        nada = await service.list_webhooks_for_event("nonexistent")
        assert len(nada) == 0

    async def test_record_webhook_failure_increments(self, service):
        wh = await service.create_webhook_subscription(
            nome="Fail", url="https://fail.com/wh", secret="s", eventos=["test"],
        )
        await service.record_webhook_failure(wh.id)
        updated = await service.get_webhook_by_id(wh.id)
        assert updated.falhas_consecutivas == 1
        assert updated.ativo is True

    async def test_record_webhook_failure_circuit_breaker(self, service, db_session):
        from app.config import settings

        wh = await service.create_webhook_subscription(
            nome="Breaker", url="https://break.com/wh", secret="s", eventos=["test"],
        )
        # Record enough failures to trigger circuit breaker
        for _ in range(settings.webhook_circuit_breaker_threshold):
            await service.record_webhook_failure(wh.id)

        updated = await service.get_webhook_by_id(wh.id)
        assert updated.ativo is False
        assert updated.falhas_consecutivas >= settings.webhook_circuit_breaker_threshold

    async def test_record_webhook_success_resets_counter(self, service):
        wh = await service.create_webhook_subscription(
            nome="Reset", url="https://reset.com/wh", secret="s", eventos=["test"],
        )
        await service.record_webhook_failure(wh.id)
        await service.record_webhook_failure(wh.id)
        await service.record_webhook_success(wh.id)

        updated = await service.get_webhook_by_id(wh.id)
        assert updated.falhas_consecutivas == 0

    def test_sign_payload(self):
        signature = PublicacaoService.sign_payload('{"test": true}', "secret_key")
        assert isinstance(signature, str)
        assert len(signature) == 64  # SHA-256 hex digest

    def test_sign_payload_deterministic(self):
        sig1 = PublicacaoService.sign_payload("payload", "key")
        sig2 = PublicacaoService.sign_payload("payload", "key")
        assert sig1 == sig2

    def test_sign_payload_different_secrets(self):
        sig1 = PublicacaoService.sign_payload("payload", "key1")
        sig2 = PublicacaoService.sign_payload("payload", "key2")
        assert sig1 != sig2
