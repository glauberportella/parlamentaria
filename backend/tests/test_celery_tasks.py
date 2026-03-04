"""Tests for Celery tasks — sync, notifications, webhooks, comparativos."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Test notificar_eleitores tasks
# ---------------------------------------------------------------------------

class TestNotificarEleitoresTask:
    """Tests for notificar_eleitores_task."""

    @patch("app.tasks.notificar_eleitores.get_async_session")
    def test_task_runs_with_no_temas(self, mock_session_ctx):
        """Task with empty temas should return 0 notifications."""
        from app.tasks.notificar_eleitores import notificar_eleitores_task

        mock_session = AsyncMock()
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_session_ctx.return_value = mock_ctx

        # Mock NotificationService
        with patch(
            "app.services.notification_service.NotificationService"
        ) as MockService:
            mock_service = AsyncMock()
            mock_service.notify_voters_about_proposicao = AsyncMock(
                return_value={"total_voters": 0, "sent": 0, "errors": 0, "skipped": 0}
            )
            MockService.return_value = mock_service

            result = notificar_eleitores_task(proposicao_id=123, temas=[])
            assert result["sent"] == 0

    @patch("app.tasks.notificar_eleitores.get_async_session")
    def test_task_runs_with_temas(self, mock_session_ctx):
        """Task with temas should call NotificationService."""
        from app.tasks.notificar_eleitores import notificar_eleitores_task

        mock_session = AsyncMock()
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_session_ctx.return_value = mock_ctx

        with patch(
            "app.services.notification_service.NotificationService"
        ) as MockService:
            mock_service = AsyncMock()
            mock_service.notify_voters_about_proposicao = AsyncMock(
                return_value={"total_voters": 5, "sent": 5, "errors": 0, "skipped": 0}
            )
            MockService.return_value = mock_service

            result = notificar_eleitores_task(
                proposicao_id=456,
                temas=["economia", "saúde"],
                tipo="PL",
                numero=100,
                ano=2024,
                ementa="Test",
            )
            assert result["sent"] == 5
            assert result["total_voters"] == 5


class TestNotificarComparativoTask:
    """Tests for notificar_comparativo_task."""

    @patch("app.tasks.notificar_eleitores.get_async_session")
    def test_task_calls_notification_service(self, mock_session_ctx):
        """Task should call NotificationService for comparativo notifications."""
        from app.tasks.notificar_eleitores import notificar_comparativo_task

        mock_session = AsyncMock()
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_session_ctx.return_value = mock_ctx

        with patch(
            "app.services.notification_service.NotificationService"
        ) as MockService:
            mock_service = AsyncMock()
            mock_service.notify_voters_comparativo = AsyncMock(
                return_value={"total_voters": 3, "sent": 3, "errors": 0, "skipped": 0}
            )
            MockService.return_value = mock_service

            result = notificar_comparativo_task(
                proposicao_id=789,
                tipo="PEC",
                numero=50,
                ano=2024,
                resultado_camara="APROVADO",
                percentual_sim_popular=73.0,
                alinhamento=0.95,
            )
            assert result["sent"] == 3


# ---------------------------------------------------------------------------
# Test dispatch_webhooks task
# ---------------------------------------------------------------------------

class TestDispatchWebhooksTask:
    """Tests for dispatch_webhooks_task."""

    @patch("app.tasks.dispatch_webhooks.get_async_session")
    def test_task_dispatches_event(self, mock_session_ctx):
        """Task should call PublicacaoService.dispatch_event."""
        from app.tasks.dispatch_webhooks import dispatch_webhooks_task

        mock_session = AsyncMock()
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_session_ctx.return_value = mock_ctx

        with patch(
            "app.services.publicacao_service.PublicacaoService"
        ) as MockService:
            mock_service = AsyncMock()
            mock_service.dispatch_event = AsyncMock(
                return_value={"dispatched": 2, "errors": 0}
            )
            MockService.return_value = mock_service

            result = dispatch_webhooks_task(
                evento="voto_consolidado",
                payload={"proposicao_id": 123, "resultado": {"total": 10}},
            )
            assert result["dispatched"] == 2


# ---------------------------------------------------------------------------
# Test sync_proposicoes task
# ---------------------------------------------------------------------------

class TestSyncProposicoesTask:
    """Tests for sync_proposicoes_task."""

    @patch("app.tasks.sync_proposicoes.get_async_session")
    def test_task_calls_sync_service(self, mock_session_ctx):
        """Task should call SyncService.sync_proposicoes."""
        from app.tasks.sync_proposicoes import sync_proposicoes_task

        mock_session = AsyncMock()
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_session_ctx.return_value = mock_ctx

        with patch(
            "app.services.sync_service.SyncService"
        ) as MockService:
            mock_service = AsyncMock()
            mock_service.sync_proposicoes = AsyncMock(
                return_value={"total_fetched": 10, "errors": 0}
            )
            MockService.return_value = mock_service

            result = sync_proposicoes_task(ano=2024)
            assert result["total_fetched"] == 10


# ---------------------------------------------------------------------------
# Test sync_votacoes task
# ---------------------------------------------------------------------------

class TestSyncVotacoesTask:
    """Tests for sync_votacoes_task."""

    @patch("app.tasks.sync_votacoes.get_async_session")
    def test_task_calls_sync_service(self, mock_session_ctx):
        """Task should call SyncService.sync_votacoes."""
        from app.tasks.sync_votacoes import sync_votacoes_task

        mock_session = AsyncMock()
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_session_ctx.return_value = mock_ctx

        with patch(
            "app.services.sync_service.SyncService"
        ) as MockService:
            mock_service = AsyncMock()
            mock_service.sync_votacoes = AsyncMock(
                return_value={"total_fetched": 5, "errors": 0}
            )
            MockService.return_value = mock_service

            result = sync_votacoes_task()
            assert result["total_fetched"] == 5


# ---------------------------------------------------------------------------
# Test gerar_comparativos task
# ---------------------------------------------------------------------------

class TestGerarComparativosTask:
    """Tests for gerar_comparativos_task."""

    @patch("app.tasks.gerar_comparativos.get_async_session")
    def test_task_runs_and_generates(self, mock_session_ctx):
        """Task should generate comparativos for votacoes with results."""
        from app.tasks.gerar_comparativos import gerar_comparativos_task

        mock_session = AsyncMock()
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_session_ctx.return_value = mock_ctx

        # Mock the internal DB queries
        mock_votacao = MagicMock()
        mock_votacao.id = 111
        mock_votacao.proposicao_id = 222
        mock_votacao.aprovacao = True
        mock_votacao.votos_sim = 300
        mock_votacao.votos_nao = 150

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_votacao]
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Mock proposicao fetch for notifications
        mock_proposicao = MagicMock()
        mock_proposicao.tipo = "PL"
        mock_proposicao.numero = 1234
        mock_proposicao.ano = 2026
        mock_session.get = AsyncMock(return_value=mock_proposicao)

        with patch(
            "app.services.comparativo_service.ComparativoService"
        ) as MockService:
            mock_service = AsyncMock()
            mock_service.exists_for_votacao = AsyncMock(return_value=False)
            mock_comparativo = MagicMock()
            mock_comparativo.voto_popular_sim = 100
            mock_comparativo.voto_popular_nao = 50
            mock_comparativo.voto_popular_abstencao = 10
            mock_comparativo.alinhamento = 0.8
            mock_service.gerar_comparativo = AsyncMock(return_value=mock_comparativo)
            MockService.return_value = mock_service

            with patch("app.tasks.dispatch_webhooks.dispatch_webhooks_task") as mock_dispatch, \
                 patch("app.tasks.notificar_eleitores.notificar_comparativo_task") as mock_notif:
                mock_dispatch.delay = MagicMock()
                mock_notif.delay = MagicMock()

                result = gerar_comparativos_task()
                assert result["generated"] == 1
                assert result["skipped"] == 0
                assert result["webhooks_dispatched"] == 1
                assert result["notifications_triggered"] == 1

    @patch("app.tasks.gerar_comparativos.get_async_session")
    def test_task_skips_existing_comparativos(self, mock_session_ctx):
        """Task should skip votacoes that already have comparativos."""
        from app.tasks.gerar_comparativos import gerar_comparativos_task

        mock_session = AsyncMock()
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_session_ctx.return_value = mock_ctx

        mock_votacao = MagicMock()
        mock_votacao.id = 111
        mock_votacao.proposicao_id = 222
        mock_votacao.aprovacao = True

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_votacao]
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch(
            "app.services.comparativo_service.ComparativoService"
        ) as MockService:
            mock_service = AsyncMock()
            mock_service.exists_for_votacao = AsyncMock(return_value=True)  # Already exists
            MockService.return_value = mock_service

            result = gerar_comparativos_task()
            assert result["skipped"] == 1
            assert result["generated"] == 0

    @patch("app.tasks.gerar_comparativos.get_async_session")
    def test_task_no_votacoes(self, mock_session_ctx):
        """Task with no votacoes should return empty stats."""
        from app.tasks.gerar_comparativos import gerar_comparativos_task

        mock_session = AsyncMock()
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_session_ctx.return_value = mock_ctx

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = gerar_comparativos_task()
        assert result["generated"] == 0
        assert result["skipped"] == 0


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

class TestHelpers:
    """Tests for task helpers."""

    @patch("app.tasks.helpers.async_session_factory")
    async def test_get_async_session_yields_session(self, mock_factory):
        """get_async_session should yield a database session."""
        from app.tasks.helpers import get_async_session

        mock_session = AsyncMock()
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_factory.return_value = mock_ctx

        async with get_async_session() as session:
            assert session is mock_session

    @patch("app.tasks.helpers.async_session_factory")
    async def test_get_async_session_rollback_on_error(self, mock_factory):
        """get_async_session should rollback on exception."""
        from app.tasks.helpers import get_async_session

        mock_session = AsyncMock()
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_factory.return_value = mock_ctx

        with pytest.raises(ValueError):
            async with get_async_session() as session:
                raise ValueError("test error")

        mock_session.rollback.assert_awaited_once()


# ---------------------------------------------------------------------------
# Test celery_app configuration
# ---------------------------------------------------------------------------

class TestCeleryAppConfig:
    """Tests for Celery app configuration."""

    def test_celery_app_name(self):
        from app.tasks.celery_app import celery_app

        assert celery_app.main == "parlamentaria"

    def test_celery_includes_all_tasks(self):
        from app.tasks.celery_app import celery_app

        includes = celery_app.conf.get("include", [])
        expected = [
            "app.tasks.sync_proposicoes",
            "app.tasks.sync_votacoes",
            "app.tasks.notificar_eleitores",
            "app.tasks.dispatch_webhooks",
            "app.tasks.gerar_comparativos",
        ]
        for task_module in expected:
            assert task_module in includes, f"Missing task module: {task_module}"

    def test_celery_beat_schedule_exists(self):
        from app.tasks.celery_app import celery_app

        schedule = celery_app.conf.beat_schedule
        # Manhã (6h-7h)
        assert "sync-proposicoes-morning" in schedule
        assert "sync-votacoes-morning" in schedule
        assert "gerar-comparativos-morning" in schedule
        # Noite (20h-21h)
        assert "sync-proposicoes-evening" in schedule
        assert "sync-votacoes-evening" in schedule
        assert "gerar-comparativos-evening" in schedule
        # Madrugada
        assert "reindex-embeddings-daily" in schedule

    def test_celery_uses_json_serializer(self):
        from app.tasks.celery_app import celery_app

        assert celery_app.conf.task_serializer == "json"
        assert "json" in celery_app.conf.accept_content
