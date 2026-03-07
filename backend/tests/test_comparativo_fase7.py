"""Comprehensive tests for Fase 7 — Comparativo e Feedback.

Tests the full cycle: comparativo generation, webhook dispatch,
voter notifications, new agent tools, and the ComparativoRepository.
"""

import uuid
from datetime import datetime, timezone, date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.comparativo import ComparativoVotacao
from app.domain.proposicao import Proposicao
from app.domain.votacao import Votacao
from app.domain.eleitor import Eleitor
from app.domain.voto_popular import VotoPopular, VotoEnum, TipoVoto


# ---------------------------------------------------------------------------
# Helper: Seed a full cycle scenario (proposicao + votacao + votos + eleitor)
# ---------------------------------------------------------------------------

async def _seed_full_cycle(session: AsyncSession) -> dict:
    """Seed DB with a complete cycle: proposicao, votacao, eleitor, votos."""
    prop = Proposicao(
        id=1001,
        tipo="PL",
        numero=42,
        ano=2026,
        ementa="Dispõe sobre transparência digital",
        data_apresentacao=date(2026, 1, 15),
        situacao="Em tramitação",
        temas=["tecnologia", "transparência"],
    )
    session.add(prop)

    votacao = Votacao(
        id="2001",
        proposicao_id=1001,
        data=datetime(2026, 2, 20, 14, 0, tzinfo=timezone.utc),
        descricao="Votação do PL 42/2026",
        aprovacao=True,
        votos_sim=300,
        votos_nao=150,
        abstencoes=10,
    )
    session.add(votacao)

    eleitor = Eleitor(
        nome="Ana Teste",
        email="ana@test.com",
        uf="SP",
        channel="telegram",
        chat_id="999888",
        cidadao_brasileiro=True,
        data_nascimento=date(1990, 3, 15),
        verificado=True,
    )
    session.add(eleitor)
    await session.flush()

    voto1 = VotoPopular(
        eleitor_id=eleitor.id,
        proposicao_id=1001,
        voto=VotoEnum.SIM,
        tipo_voto=TipoVoto.OFICIAL,
        data_voto=datetime(2026, 2, 15, tzinfo=timezone.utc),
    )
    voto2_eleitor = Eleitor(
        nome="Bruno Teste",
        email="bruno@test.com",
        uf="RJ",
        channel="telegram",
        chat_id="777666",
        cidadao_brasileiro=True,
        data_nascimento=date(1992, 7, 20),
        verificado=True,
    )
    session.add(voto2_eleitor)
    await session.flush()

    voto2 = VotoPopular(
        eleitor_id=voto2_eleitor.id,
        proposicao_id=1001,
        voto=VotoEnum.NAO,
        tipo_voto=TipoVoto.OFICIAL,
        data_voto=datetime(2026, 2, 16, tzinfo=timezone.utc),
    )
    session.add_all([voto1, voto2])
    await session.commit()

    return {
        "proposicao": prop,
        "votacao": votacao,
        "eleitor": eleitor,
        "eleitor2": voto2_eleitor,
    }


# ===========================================================================
# 1. ComparativoRepository Tests
# ===========================================================================

class TestComparativoRepository:
    """Tests for the ComparativoRepository."""

    async def test_get_by_proposicao_returns_none_when_empty(self, db_session):
        """Should return None when no comparativo exists."""
        from app.repositories.comparativo import ComparativoRepository

        repo = ComparativoRepository(db_session)
        result = await repo.get_by_proposicao(999)
        assert result is None

    async def test_get_by_proposicao_returns_most_recent(self, db_session):
        """Should return the most recent comparativo for a proposition."""
        from app.repositories.comparativo import ComparativoRepository

        data = await _seed_full_cycle(db_session)

        comp1 = ComparativoVotacao(
            proposicao_id=1001,
            votacao_camara_id="2001",
            voto_popular_sim=1,
            voto_popular_nao=1,
            resultado_camara="APROVADO",
            votos_camara_sim=300,
            votos_camara_nao=150,
            alinhamento=0.5,
        )
        db_session.add(comp1)
        await db_session.flush()

        repo = ComparativoRepository(db_session)
        result = await repo.get_by_proposicao(1001)
        assert result is not None
        assert result.proposicao_id == 1001

    async def test_list_recent(self, db_session):
        """Should list recent comparatives in descending order."""
        from app.repositories.comparativo import ComparativoRepository

        data = await _seed_full_cycle(db_session)

        for i in range(3):
            comp = ComparativoVotacao(
                proposicao_id=1001,
                votacao_camara_id="2001",
                voto_popular_sim=i + 1,
                voto_popular_nao=1,
                resultado_camara="APROVADO",
                votos_camara_sim=300,
                votos_camara_nao=150,
                alinhamento=0.5 + i * 0.1,
            )
            db_session.add(comp)
        await db_session.flush()

        repo = ComparativoRepository(db_session)
        recent = await repo.list_recent(limit=2)
        assert len(recent) == 2

    async def test_list_by_proposicao_ids(self, db_session):
        """Should filter comparatives by proposition IDs."""
        from app.repositories.comparativo import ComparativoRepository

        data = await _seed_full_cycle(db_session)

        comp = ComparativoVotacao(
            proposicao_id=1001,
            votacao_camara_id="2001",
            voto_popular_sim=1,
            voto_popular_nao=1,
            resultado_camara="APROVADO",
            votos_camara_sim=300,
            votos_camara_nao=150,
            alinhamento=0.7,
        )
        db_session.add(comp)
        await db_session.flush()

        repo = ComparativoRepository(db_session)
        results = await repo.list_by_proposicao_ids([1001])
        assert len(results) == 1
        assert results[0].proposicao_id == 1001

    async def test_list_by_proposicao_ids_empty(self, db_session):
        """Should return empty list for empty input."""
        from app.repositories.comparativo import ComparativoRepository

        repo = ComparativoRepository(db_session)
        results = await repo.list_by_proposicao_ids([])
        assert results == []

    async def test_exists_for_votacao_true(self, db_session):
        """Should return True when comparativo exists for votacao."""
        from app.repositories.comparativo import ComparativoRepository

        data = await _seed_full_cycle(db_session)

        comp = ComparativoVotacao(
            proposicao_id=1001,
            votacao_camara_id="2001",
            voto_popular_sim=1,
            voto_popular_nao=1,
            resultado_camara="APROVADO",
            votos_camara_sim=300,
            votos_camara_nao=150,
            alinhamento=0.8,
        )
        db_session.add(comp)
        await db_session.flush()

        repo = ComparativoRepository(db_session)
        assert await repo.exists_for_votacao("2001") is True

    async def test_exists_for_votacao_false(self, db_session):
        """Should return False when no comparativo exists."""
        from app.repositories.comparativo import ComparativoRepository

        repo = ComparativoRepository(db_session)
        assert await repo.exists_for_votacao("9999") is False


# ===========================================================================
# 2. Enhanced ComparativoService Tests
# ===========================================================================

class TestComparativoServiceEnhanced:
    """Tests for the enhanced ComparativoService methods."""

    async def test_list_comparativos(self, db_session):
        """Should list all comparatives with pagination."""
        from app.services.comparativo_service import ComparativoService

        data = await _seed_full_cycle(db_session)

        service = ComparativoService(db_session)
        comparativo = await service.gerar_comparativo(
            proposicao_id=1001,
            votacao_camara_id="2001",
            resultado_camara="APROVADO",
            votos_camara_sim=300,
            votos_camara_nao=150,
        )

        result = await service.list_comparativos(offset=0, limit=10)
        assert len(result) >= 1

    async def test_list_recent(self, db_session):
        """Should list recent comparatives."""
        from app.services.comparativo_service import ComparativoService

        data = await _seed_full_cycle(db_session)

        service = ComparativoService(db_session)
        await service.gerar_comparativo(
            proposicao_id=1001,
            votacao_camara_id="2001",
            resultado_camara="APROVADO",
            votos_camara_sim=300,
            votos_camara_nao=150,
        )

        recent = await service.list_recent(limit=5)
        assert len(recent) == 1
        assert recent[0].proposicao_id == 1001

    async def test_exists_for_votacao(self, db_session):
        """Should check existence via service."""
        from app.services.comparativo_service import ComparativoService

        data = await _seed_full_cycle(db_session)

        service = ComparativoService(db_session)
        assert await service.exists_for_votacao("2001") is False

        await service.gerar_comparativo(
            proposicao_id=1001,
            votacao_camara_id="2001",
            resultado_camara="APROVADO",
            votos_camara_sim=300,
            votos_camara_nao=150,
        )

        assert await service.exists_for_votacao("2001") is True

    async def test_get_comparativo_with_proposicao(self, db_session):
        """Should return enriched comparativo with proposicao details."""
        from app.services.comparativo_service import ComparativoService

        data = await _seed_full_cycle(db_session)

        service = ComparativoService(db_session)
        await service.gerar_comparativo(
            proposicao_id=1001,
            votacao_camara_id="2001",
            resultado_camara="APROVADO",
            votos_camara_sim=300,
            votos_camara_nao=150,
        )

        result = await service.get_comparativo_with_proposicao(1001)
        assert result is not None
        assert result["tipo"] == "PL"
        assert result["numero"] == 42
        assert result["ano"] == 2026
        assert result["resultado_camara"] == "APROVADO"
        assert "alinhamento" in result
        assert "voto_popular" in result
        assert result["voto_popular"]["total"] > 0

    async def test_get_comparativo_with_proposicao_not_found(self, db_session):
        """Should return None when no comparativo exists."""
        from app.services.comparativo_service import ComparativoService

        service = ComparativoService(db_session)
        result = await service.get_comparativo_with_proposicao(9999)
        assert result is None


# ===========================================================================
# 3. Gerar Comparativos Task — Full Cycle
# ===========================================================================

class TestGerarComparativosTaskFullCycle:
    """Tests for the full comparativo generation cycle with webhook + notification."""

    @patch("app.tasks.gerar_comparativos.get_async_session")
    def test_task_dispatches_webhook_on_generation(self, mock_session_ctx):
        """Task should dispatch comparativo_gerado webhook after generation."""
        from app.tasks.gerar_comparativos import gerar_comparativos_task

        mock_session = AsyncMock()
        mock_session.begin_nested = MagicMock(return_value=AsyncMock())
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_session_ctx.return_value = mock_ctx

        mock_votacao = MagicMock()
        mock_votacao.id = "111"
        mock_votacao.proposicao_id = 222
        mock_votacao.aprovacao = True
        mock_votacao.votos_sim = 300
        mock_votacao.votos_nao = 150

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_votacao]
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_proposicao = MagicMock()
        mock_proposicao.tipo = "PL"
        mock_proposicao.numero = 100
        mock_proposicao.ano = 2026
        mock_session.get = AsyncMock(return_value=mock_proposicao)

        with patch("app.services.comparativo_service.ComparativoService") as MockService:
            mock_service = AsyncMock()
            mock_service.exists_for_votacao = AsyncMock(return_value=False)
            mock_comparativo = MagicMock()
            mock_comparativo.voto_popular_sim = 80
            mock_comparativo.voto_popular_nao = 20
            mock_comparativo.voto_popular_abstencao = 5
            mock_comparativo.alinhamento = 0.95
            mock_service.gerar_comparativo = AsyncMock(return_value=mock_comparativo)
            MockService.return_value = mock_service

            with patch("app.tasks.dispatch_webhooks.dispatch_webhooks_task") as mock_dispatch, \
                 patch("app.tasks.notificar_eleitores.notificar_comparativo_task") as mock_notif:
                mock_dispatch.delay = MagicMock()
                mock_notif.delay = MagicMock()

                result = gerar_comparativos_task()

                # Webhook should have been dispatched
                mock_dispatch.delay.assert_called_once()
                call_args = mock_dispatch.delay.call_args
                assert call_args[0][0] == "comparativo_gerado"
                assert call_args[0][1]["proposicao_id"] == 222

                # Notification should have been triggered
                mock_notif.delay.assert_called_once()
                notif_kwargs = mock_notif.delay.call_args[1]
                assert notif_kwargs["proposicao_id"] == 222
                assert notif_kwargs["tipo"] == "PL"
                assert notif_kwargs["resultado_camara"] == "APROVADO"

    @patch("app.tasks.gerar_comparativos.get_async_session")
    def test_task_handles_webhook_dispatch_error(self, mock_session_ctx):
        """Task should continue even if webhook dispatch fails."""
        from app.tasks.gerar_comparativos import gerar_comparativos_task

        mock_session = AsyncMock()
        mock_session.begin_nested = MagicMock(return_value=AsyncMock())
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_session_ctx.return_value = mock_ctx

        mock_votacao = MagicMock()
        mock_votacao.id = "111"
        mock_votacao.proposicao_id = 222
        mock_votacao.aprovacao = False
        mock_votacao.votos_sim = 100
        mock_votacao.votos_nao = 200

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_votacao]
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.get = AsyncMock(return_value=None)

        with patch("app.services.comparativo_service.ComparativoService") as MockService:
            mock_service = AsyncMock()
            mock_service.exists_for_votacao = AsyncMock(return_value=False)
            mock_comparativo = MagicMock()
            mock_comparativo.voto_popular_sim = 60
            mock_comparativo.voto_popular_nao = 40
            mock_comparativo.voto_popular_abstencao = 5
            mock_comparativo.alinhamento = 0.3
            mock_service.gerar_comparativo = AsyncMock(return_value=mock_comparativo)
            MockService.return_value = mock_service

            with patch("app.tasks.dispatch_webhooks.dispatch_webhooks_task") as mock_dispatch, \
                 patch("app.tasks.notificar_eleitores.notificar_comparativo_task") as mock_notif:
                # Simulate dispatch failure
                mock_dispatch.delay = MagicMock(side_effect=Exception("Redis down"))
                mock_notif.delay = MagicMock()

                result = gerar_comparativos_task()
                assert result["generated"] == 1
                assert result["webhooks_dispatched"] == 0
                assert result["notifications_triggered"] == 1

    @patch("app.tasks.gerar_comparativos.get_async_session")
    def test_task_handles_notification_error(self, mock_session_ctx):
        """Task should continue even if notification dispatch fails."""
        from app.tasks.gerar_comparativos import gerar_comparativos_task

        mock_session = AsyncMock()
        mock_session.begin_nested = MagicMock(return_value=AsyncMock())
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_session_ctx.return_value = mock_ctx

        mock_votacao = MagicMock()
        mock_votacao.id = "111"
        mock_votacao.proposicao_id = 222
        mock_votacao.aprovacao = True
        mock_votacao.votos_sim = 250
        mock_votacao.votos_nao = 100

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_votacao]
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.get = AsyncMock(return_value=MagicMock(tipo="PEC", numero=5, ano=2026))

        with patch("app.services.comparativo_service.ComparativoService") as MockService:
            mock_service = AsyncMock()
            mock_service.exists_for_votacao = AsyncMock(return_value=False)
            mock_comparativo = MagicMock()
            mock_comparativo.voto_popular_sim = 80
            mock_comparativo.voto_popular_nao = 20
            mock_comparativo.voto_popular_abstencao = 0
            mock_comparativo.alinhamento = 0.9
            mock_service.gerar_comparativo = AsyncMock(return_value=mock_comparativo)
            MockService.return_value = mock_service

            with patch("app.tasks.dispatch_webhooks.dispatch_webhooks_task") as mock_dispatch, \
                 patch("app.tasks.notificar_eleitores.notificar_comparativo_task") as mock_notif:
                mock_dispatch.delay = MagicMock()
                mock_notif.delay = MagicMock(side_effect=Exception("Celery down"))

                result = gerar_comparativos_task()
                assert result["generated"] == 1
                assert result["webhooks_dispatched"] == 1
                assert result["notifications_triggered"] == 0

    @patch("app.tasks.gerar_comparativos.get_async_session")
    def test_task_zero_popular_votes(self, mock_session_ctx):
        """Task should handle zero popular votes gracefully (pct_sim=0.0)."""
        from app.tasks.gerar_comparativos import gerar_comparativos_task

        mock_session = AsyncMock()
        mock_session.begin_nested = MagicMock(return_value=AsyncMock())
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_session_ctx.return_value = mock_ctx

        mock_votacao = MagicMock()
        mock_votacao.id = "111"
        mock_votacao.proposicao_id = 222
        mock_votacao.aprovacao = True
        mock_votacao.votos_sim = 300
        mock_votacao.votos_nao = 100

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_votacao]
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.get = AsyncMock(return_value=MagicMock(tipo="PL", numero=1, ano=2026))

        with patch("app.services.comparativo_service.ComparativoService") as MockService:
            mock_service = AsyncMock()
            mock_service.exists_for_votacao = AsyncMock(return_value=False)
            mock_comparativo = MagicMock()
            mock_comparativo.voto_popular_sim = 0
            mock_comparativo.voto_popular_nao = 0
            mock_comparativo.voto_popular_abstencao = 0
            mock_comparativo.alinhamento = 0.5
            mock_service.gerar_comparativo = AsyncMock(return_value=mock_comparativo)
            MockService.return_value = mock_service

            with patch("app.tasks.dispatch_webhooks.dispatch_webhooks_task") as mock_dispatch, \
                 patch("app.tasks.notificar_eleitores.notificar_comparativo_task") as mock_notif:
                mock_dispatch.delay = MagicMock()
                mock_notif.delay = MagicMock()

                result = gerar_comparativos_task()
                assert result["generated"] == 1
                # Ensure pct_sim=0.0 was passed correctly
                notif_kwargs = mock_notif.delay.call_args[1]
                assert notif_kwargs["percentual_sim_popular"] == 0.0


# ===========================================================================
# 4. NotificationService Comparativo Tests
# ===========================================================================

class TestNotificationServiceComparativo:
    """Tests for the comparativo notification flow in NotificationService."""

    async def test_notify_voters_comparativo_with_send_fn(self, db_session):
        """Should send comparativo messages to voters who voted."""
        from app.services.notification_service import NotificationService

        data = await _seed_full_cycle(db_session)

        service = NotificationService(db_session)
        mock_send = AsyncMock()

        stats = await service.notify_voters_comparativo(
            proposicao_id=1001,
            tipo="PL",
            numero=42,
            ano=2026,
            resultado_camara="APROVADO",
            percentual_sim_popular=73.0,
            alinhamento=0.95,
            send_fn=mock_send,
        )

        assert stats["total_voters"] == 2
        assert stats["sent"] == 2
        assert stats["errors"] == 0
        assert mock_send.call_count == 2

    async def test_notify_voters_comparativo_send_error(self, db_session):
        """Should track errors when send_fn raises."""
        from app.services.notification_service import NotificationService

        data = await _seed_full_cycle(db_session)

        service = NotificationService(db_session)
        mock_send = AsyncMock(side_effect=Exception("Send failed"))

        stats = await service.notify_voters_comparativo(
            proposicao_id=1001,
            tipo="PL",
            numero=42,
            ano=2026,
            resultado_camara="REJEITADO",
            percentual_sim_popular=30.0,
            alinhamento=0.3,
            send_fn=mock_send,
        )

        assert stats["total_voters"] == 2
        assert stats["errors"] == 2
        assert stats["sent"] == 0

    async def test_notify_voters_comparativo_dry_run(self, db_session):
        """Should count as sent in dry-run mode (no send_fn)."""
        from app.services.notification_service import NotificationService

        data = await _seed_full_cycle(db_session)

        service = NotificationService(db_session)
        stats = await service.notify_voters_comparativo(
            proposicao_id=1001,
            tipo="PL",
            numero=42,
            ano=2026,
            resultado_camara="APROVADO",
            percentual_sim_popular=60.0,
            alinhamento=0.6,
            send_fn=None,
        )

        assert stats["sent"] == 2
        assert stats["errors"] == 0

    async def test_notify_voters_comparativo_no_voters(self, db_session):
        """Should handle case with no voters for the proposition."""
        from app.services.notification_service import NotificationService

        # Seed proposition without any votes
        prop = Proposicao(
            id=9001,
            tipo="PL",
            numero=999,
            ano=2026,
            ementa="Proposição sem votos",
            data_apresentacao=date(2026, 1, 1),
            situacao="Em tramitação",
        )
        db_session.add(prop)
        await db_session.commit()

        service = NotificationService(db_session)
        stats = await service.notify_voters_comparativo(
            proposicao_id=9001,
            tipo="PL",
            numero=999,
            ano=2026,
            resultado_camara="APROVADO",
            percentual_sim_popular=0.0,
            alinhamento=0.5,
            send_fn=AsyncMock(),
        )

        assert stats["total_voters"] == 0
        assert stats["sent"] == 0

    async def test_format_comparativo_message_approved(self, db_session):
        """Should format a message for an approved proposition."""
        from app.services.notification_service import NotificationService

        service = NotificationService(db_session)
        msg = service.format_comparativo_message(
            proposicao_id=1001,
            tipo="PL",
            numero=42,
            ano=2026,
            resultado_camara="APROVADO",
            percentual_sim_popular=73.0,
            alinhamento=0.95,
        )

        assert "PL 42/2026" in msg
        assert "APROVADO" in msg
        assert "73.0% SIM" in msg
        assert "95%" in msg
        assert "✅" in msg

    async def test_format_comparativo_message_rejected(self, db_session):
        """Should format a message for a rejected proposition."""
        from app.services.notification_service import NotificationService

        service = NotificationService(db_session)
        msg = service.format_comparativo_message(
            proposicao_id=1001,
            tipo="PEC",
            numero=5,
            ano=2026,
            resultado_camara="REJEITADO",
            percentual_sim_popular=25.0,
            alinhamento=0.8,
        )

        assert "PEC 5/2026" in msg
        assert "REJEITADO" in msg
        assert "❌" in msg


# ===========================================================================
# 5. Notificar Comparativo Task
# ===========================================================================

class TestNotificarComparativoTask:
    """Tests for the notificar_comparativo_task."""

    @patch("app.tasks.notificar_eleitores.get_async_session")
    def test_task_runs_notification(self, mock_session_ctx):
        """Should run the notification service for comparativo."""
        from app.tasks.notificar_eleitores import notificar_comparativo_task

        mock_session = AsyncMock()
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_session_ctx.return_value = mock_ctx

        with patch("app.services.notification_service.NotificationService") as MockService:
            mock_service = AsyncMock()
            mock_service.notify_voters_comparativo = AsyncMock(
                return_value={"total_voters": 5, "sent": 5, "errors": 0, "skipped": 0}
            )
            MockService.return_value = mock_service

            result = notificar_comparativo_task(
                proposicao_id=1001,
                tipo="PL",
                numero=42,
                ano=2026,
                resultado_camara="APROVADO",
                percentual_sim_popular=73.0,
                alinhamento=0.95,
            )

            assert result["sent"] == 5
            assert result["total_voters"] == 5


# ===========================================================================
# 6. New PublicacaoTools Tests
# ===========================================================================

class TestListarComparativosRecentesTool:
    """Tests for the listar_comparativos_recentes tool."""

    async def test_success_with_data(self):
        """Should return recent comparatives."""
        mock_comparativo = MagicMock()
        mock_comparativo.proposicao_id = 1001
        mock_comparativo.resultado_camara = "APROVADO"
        mock_comparativo.voto_popular_sim = 80
        mock_comparativo.voto_popular_nao = 15
        mock_comparativo.voto_popular_abstencao = 5
        mock_comparativo.alinhamento = 0.85
        mock_comparativo.data_geracao = datetime(2026, 2, 20, tzinfo=timezone.utc)

        with patch("app.db.session.async_session_factory") as mock_factory, \
             patch("app.services.comparativo_service.ComparativoService") as MockService:
            mock_session = AsyncMock()
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
            mock_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_factory.return_value = mock_ctx

            mock_service = AsyncMock()
            mock_service.list_recent = AsyncMock(return_value=[mock_comparativo])
            MockService.return_value = mock_service

            from agents.parlamentar.tools.publicacao_tools import listar_comparativos_recentes

            result = await listar_comparativos_recentes(5)
            assert result["status"] == "success"
            assert result["total"] == 1
            assert result["comparativos"][0]["proposicao_id"] == 1001
            assert result["comparativos"][0]["alinhamento"] == 85.0

    async def test_success_empty(self):
        """Should return empty list when no comparatives exist."""
        with patch("app.db.session.async_session_factory") as mock_factory, \
             patch("app.services.comparativo_service.ComparativoService") as MockService:
            mock_session = AsyncMock()
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
            mock_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_factory.return_value = mock_ctx

            mock_service = AsyncMock()
            mock_service.list_recent = AsyncMock(return_value=[])
            MockService.return_value = mock_service

            from agents.parlamentar.tools.publicacao_tools import listar_comparativos_recentes

            result = await listar_comparativos_recentes()
            assert result["status"] == "success"
            assert result["total"] == 0
            assert "Nenhum comparativo" in result["mensagem"]

    async def test_error_handling(self):
        """Should handle errors gracefully."""
        with patch("app.db.session.async_session_factory", side_effect=Exception("DB error")):
            from agents.parlamentar.tools.publicacao_tools import listar_comparativos_recentes

            result = await listar_comparativos_recentes()
            assert result["status"] == "error"


class TestConsultarHistoricoVotosTool:
    """Tests for the consultar_historico_votos tool."""

    async def test_not_found_eleitor(self):
        """Should return not_found when voter doesn't exist."""
        with patch("app.db.session.async_session_factory") as mock_factory, \
             patch("app.services.eleitor_service.EleitorService") as MockEleitorService:
            mock_session = AsyncMock()
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
            mock_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_factory.return_value = mock_ctx

            mock_service = AsyncMock()
            mock_service.get_by_chat_id = AsyncMock(return_value=None)
            MockEleitorService.return_value = mock_service

            from agents.parlamentar.tools.publicacao_tools import consultar_historico_votos

            result = await consultar_historico_votos("unknown_chat")
            assert result["status"] == "not_found"

    async def test_no_votes(self):
        """Should handle voter with no votes."""
        mock_eleitor = MagicMock()
        mock_eleitor.id = uuid.uuid4()

        with patch("app.db.session.async_session_factory") as mock_factory, \
             patch("app.services.eleitor_service.EleitorService") as MockEleitorService, \
             patch("app.repositories.voto_popular.VotoPopularRepository") as MockVotoRepo:
            mock_session = AsyncMock()
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
            mock_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_factory.return_value = mock_ctx

            mock_eleitor_svc = AsyncMock()
            mock_eleitor_svc.get_by_chat_id = AsyncMock(return_value=mock_eleitor)
            MockEleitorService.return_value = mock_eleitor_svc

            mock_voto_repo = AsyncMock()
            mock_voto_repo.list_by_eleitor = AsyncMock(return_value=[])
            MockVotoRepo.return_value = mock_voto_repo

            from agents.parlamentar.tools.publicacao_tools import consultar_historico_votos

            result = await consultar_historico_votos("chat123")
            assert result["status"] == "success"
            assert result["total"] == 0

    async def test_with_votes_and_comparativo(self):
        """Should return voter's vote history with comparativo data."""
        mock_eleitor = MagicMock()
        mock_eleitor.id = uuid.uuid4()

        mock_voto = MagicMock()
        mock_voto.proposicao_id = 1001
        mock_voto.voto = VotoEnum.SIM
        mock_voto.data_voto = datetime(2026, 2, 15, tzinfo=timezone.utc)

        mock_comp = MagicMock()
        mock_comp.resultado_camara = "APROVADO"
        mock_comp.alinhamento = 0.9

        with patch("app.db.session.async_session_factory") as mock_factory, \
             patch("app.services.eleitor_service.EleitorService") as MockEleitorService, \
             patch("app.repositories.voto_popular.VotoPopularRepository") as MockVotoRepo, \
             patch("app.services.comparativo_service.ComparativoService") as MockCompService:
            mock_session = AsyncMock()
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
            mock_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_factory.return_value = mock_ctx

            mock_eleitor_svc = AsyncMock()
            mock_eleitor_svc.get_by_chat_id = AsyncMock(return_value=mock_eleitor)
            MockEleitorService.return_value = mock_eleitor_svc

            mock_voto_repo = AsyncMock()
            mock_voto_repo.list_by_eleitor = AsyncMock(return_value=[mock_voto])
            MockVotoRepo.return_value = mock_voto_repo

            mock_comp_svc = AsyncMock()
            mock_comp_svc.get_by_proposicao = AsyncMock(return_value=mock_comp)
            MockCompService.return_value = mock_comp_svc

            from agents.parlamentar.tools.publicacao_tools import consultar_historico_votos

            result = await consultar_historico_votos("chat123")
            assert result["status"] == "success"
            assert result["total"] == 1
            assert result["com_comparativo"] == 1
            assert result["votos"][0]["seu_voto"] == "SIM"
            assert result["votos"][0]["comparativo"]["alinhamento"] == 90.0

    async def test_with_votes_no_comparativo(self):
        """Should handle votes without comparativo."""
        mock_eleitor = MagicMock()
        mock_eleitor.id = uuid.uuid4()

        mock_voto = MagicMock()
        mock_voto.proposicao_id = 2002
        mock_voto.voto = VotoEnum.NAO
        mock_voto.data_voto = datetime(2026, 2, 20, tzinfo=timezone.utc)

        with patch("app.db.session.async_session_factory") as mock_factory, \
             patch("app.services.eleitor_service.EleitorService") as MockEleitorService, \
             patch("app.repositories.voto_popular.VotoPopularRepository") as MockVotoRepo, \
             patch("app.services.comparativo_service.ComparativoService") as MockCompService:
            mock_session = AsyncMock()
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
            mock_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_factory.return_value = mock_ctx

            mock_eleitor_svc = AsyncMock()
            mock_eleitor_svc.get_by_chat_id = AsyncMock(return_value=mock_eleitor)
            MockEleitorService.return_value = mock_eleitor_svc

            mock_voto_repo = AsyncMock()
            mock_voto_repo.list_by_eleitor = AsyncMock(return_value=[mock_voto])
            MockVotoRepo.return_value = mock_voto_repo

            mock_comp_svc = AsyncMock()
            mock_comp_svc.get_by_proposicao = AsyncMock(return_value=None)
            MockCompService.return_value = mock_comp_svc

            from agents.parlamentar.tools.publicacao_tools import consultar_historico_votos

            result = await consultar_historico_votos("chat123")
            assert result["status"] == "success"
            assert result["total"] == 1
            assert result["com_comparativo"] == 0
            assert result["votos"][0]["comparativo"] is None

    async def test_error_handling(self):
        """Should handle errors gracefully."""
        with patch("app.db.session.async_session_factory", side_effect=Exception("DB connection failed")):
            from agents.parlamentar.tools.publicacao_tools import consultar_historico_votos

            result = await consultar_historico_votos("chat123")
            assert result["status"] == "error"


# ===========================================================================
# 7. Admin Router — Comparativos
# ===========================================================================

class TestAdminComparativos:
    """Tests for the admin comparativos endpoint."""

    async def test_list_comparativos_empty(self, client):
        """Should return empty list when no comparativos exist."""
        response = await client.get(
            "/admin/comparativos",
            headers={"X-API-Key": "change-me-random-64-chars"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []

    async def test_list_comparativos_with_data(self, client, db_session):
        """Should return comparativos with data."""
        data = await _seed_full_cycle(db_session)

        from app.services.comparativo_service import ComparativoService
        service = ComparativoService(db_session)
        await service.gerar_comparativo(
            proposicao_id=1001,
            votacao_camara_id="2001",
            resultado_camara="APROVADO",
            votos_camara_sim=300,
            votos_camara_nao=150,
        )
        await db_session.commit()

        response = await client.get(
            "/admin/comparativos",
            headers={"X-API-Key": "change-me-random-64-chars"},
        )
        assert response.status_code == 200
        json_data = response.json()
        assert json_data["total"] == 1
        assert json_data["items"][0]["proposicao_id"] == 1001
        assert json_data["items"][0]["resultado_camara"] == "APROVADO"


# ===========================================================================
# 8. End-to-End Cycle: Seed → Generate → Verify
# ===========================================================================

class TestFullCycleEndToEnd:
    """Integration tests for the complete comparativo cycle."""

    async def test_full_cycle_generate_and_query(self, db_session):
        """Full cycle: seed data → generate comparativo → query via service."""
        from app.services.comparativo_service import ComparativoService, calcular_alinhamento

        data = await _seed_full_cycle(db_session)

        service = ComparativoService(db_session)

        # Generate comparativo
        comparativo = await service.gerar_comparativo(
            proposicao_id=1001,
            votacao_camara_id="2001",
            resultado_camara="APROVADO",
            votos_camara_sim=300,
            votos_camara_nao=150,
        )

        assert comparativo.proposicao_id == 1001
        assert comparativo.resultado_camara == "APROVADO"
        assert comparativo.voto_popular_sim == 1  # Ana voted SIM
        assert comparativo.voto_popular_nao == 1  # Bruno voted NAO
        assert 0.0 <= comparativo.alinhamento <= 1.0

        # Query via service
        retrieved = await service.get_by_proposicao(1001)
        assert retrieved is not None
        assert retrieved.id == comparativo.id

        # List recent
        recent = await service.list_recent(limit=10)
        assert len(recent) == 1

        # Exists check
        assert await service.exists_for_votacao("2001") is True
        assert await service.exists_for_votacao("9999") is False

    async def test_full_cycle_enriched_comparativo(self, db_session):
        """Full cycle with enriched proposicao details."""
        from app.services.comparativo_service import ComparativoService

        data = await _seed_full_cycle(db_session)

        service = ComparativoService(db_session)
        await service.gerar_comparativo(
            proposicao_id=1001,
            votacao_camara_id="2001",
            resultado_camara="REJEITADO",
            votos_camara_sim=100,
            votos_camara_nao=350,
        )

        enriched = await service.get_comparativo_with_proposicao(1001)
        assert enriched is not None
        assert enriched["tipo"] == "PL"
        assert enriched["numero"] == 42
        assert enriched["ano"] == 2026
        assert enriched["resultado_camara"] == "REJEITADO"
        assert enriched["voto_popular"]["total"] == 2
        assert 0.0 <= enriched["alinhamento"] <= 100.0

    async def test_full_cycle_notification_to_voters(self, db_session):
        """Full cycle: generate comparativo → notify voters."""
        from app.services.comparativo_service import ComparativoService
        from app.services.notification_service import NotificationService

        data = await _seed_full_cycle(db_session)

        comp_service = ComparativoService(db_session)
        comparativo = await comp_service.gerar_comparativo(
            proposicao_id=1001,
            votacao_camara_id="2001",
            resultado_camara="APROVADO",
            votos_camara_sim=300,
            votos_camara_nao=150,
        )

        total_pop = comparativo.voto_popular_sim + comparativo.voto_popular_nao + comparativo.voto_popular_abstencao
        pct_sim = round(comparativo.voto_popular_sim / total_pop * 100, 1) if total_pop > 0 else 0.0

        notif_service = NotificationService(db_session)
        mock_send = AsyncMock()

        stats = await notif_service.notify_voters_comparativo(
            proposicao_id=1001,
            tipo="PL",
            numero=42,
            ano=2026,
            resultado_camara="APROVADO",
            percentual_sim_popular=pct_sim,
            alinhamento=comparativo.alinhamento,
            send_fn=mock_send,
        )

        assert stats["total_voters"] == 2
        assert stats["sent"] == 2
        # Verify message content
        sent_msg = mock_send.call_args_list[0][0][1]
        assert "PL 42/2026" in sent_msg
        assert "APROVADO" in sent_msg

    async def test_full_cycle_rss_feed_includes_comparativo(self, client, db_session):
        """Full cycle: generate comparativo → check RSS feed."""
        from app.domain.assinatura import AssinaturaRSS

        data = await _seed_full_cycle(db_session)

        # Create RSS subscription for token validation
        assinatura = AssinaturaRSS(
            nome="Feed Teste",
            token="test-rss-token-fase7",
            ativo=True,
        )
        db_session.add(assinatura)
        await db_session.flush()

        from app.services.comparativo_service import ComparativoService
        service = ComparativoService(db_session)
        await service.gerar_comparativo(
            proposicao_id=1001,
            votacao_camara_id="2001",
            resultado_camara="APROVADO",
            votos_camara_sim=300,
            votos_camara_nao=150,
        )
        await db_session.commit()

        response = await client.get("/rss/comparativos?token=test-rss-token-fase7")
        assert response.status_code == 200
        assert "xml" in response.headers.get("content-type", "")
        body = response.text
        assert "1001" in body


# ===========================================================================
# 9. Calcular Alinhamento edge cases
# ===========================================================================

class TestCalcularAlinhamentoEdgeCases:
    """Additional edge case tests for calcular_alinhamento."""

    def test_exact_tie(self):
        """Should return 0.5 for an exact tie."""
        from app.services.comparativo_service import calcular_alinhamento

        result = calcular_alinhamento({"SIM": 100, "NAO": 100}, "APROVADO")
        assert result == 0.5

    def test_unanimous_approved_aligned(self):
        """100% SIM + APROVADO = 1.0 alignment."""
        from app.services.comparativo_service import calcular_alinhamento

        result = calcular_alinhamento({"SIM": 1000, "NAO": 0}, "APROVADO")
        assert result == 1.0

    def test_unanimous_rejected_aligned(self):
        """100% NAO + REJEITADO = 1.0 alignment."""
        from app.services.comparativo_service import calcular_alinhamento

        result = calcular_alinhamento({"SIM": 0, "NAO": 1000}, "REJEITADO")
        assert result == 1.0

    def test_total_misalignment(self):
        """100% SIM + REJEITADO = 0.0 alignment."""
        from app.services.comparativo_service import calcular_alinhamento

        result = calcular_alinhamento({"SIM": 1000, "NAO": 0}, "REJEITADO")
        assert result == 0.0

    def test_slight_majority_aligned(self):
        """Slight majority aligned should be slightly above 0.5."""
        from app.services.comparativo_service import calcular_alinhamento

        result = calcular_alinhamento({"SIM": 510, "NAO": 490}, "APROVADO")
        assert result == 0.51  # 510/1000

    def test_missing_keys(self):
        """Should handle missing keys gracefully."""
        from app.services.comparativo_service import calcular_alinhamento

        result = calcular_alinhamento({}, "APROVADO")
        assert result == 0.5
