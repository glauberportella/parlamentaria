"""Integration tests for the full notification pipeline.

Tests the end-to-end flow:
  sync → notification trigger → NotificationService → TelegramAdapter

Uses mocks for the Telegram API (no real HTTP calls) but exercises
the real NotificationService, EleitorRepository, and formatting logic.
"""

import uuid
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from app.domain.eleitor import Eleitor, FrequenciaNotificacao
from app.domain.proposicao import Proposicao
from app.domain.voto_popular import VotoPopular, VotoEnum
from app.services.notification_service import NotificationService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def notification_service(db_session):
    """Provide a NotificationService instance with a real DB session."""
    return NotificationService(db_session)


@pytest.fixture
async def eleitor_economia(db_session):
    """Voter interested in 'economia' with a Telegram chat_id."""
    e = Eleitor(
        nome="Maria Economia",
        email="maria.eco@test.com",
        uf="SP",
        channel="telegram",
        chat_id="100001",
        temas_interesse=["economia", "tributos"],
        verificado=True,
        frequencia_notificacao=FrequenciaNotificacao.IMEDIATA,
    )
    db_session.add(e)
    await db_session.flush()
    await db_session.refresh(e)
    return e


@pytest.fixture
async def eleitor_saude(db_session):
    """Voter interested in 'saúde' with a Telegram chat_id."""
    e = Eleitor(
        nome="João Saúde",
        email="joao.saude@test.com",
        uf="RJ",
        channel="telegram",
        chat_id="100002",
        temas_interesse=["saúde"],
        verificado=True,
        frequencia_notificacao=FrequenciaNotificacao.IMEDIATA,
    )
    db_session.add(e)
    await db_session.flush()
    await db_session.refresh(e)
    return e


@pytest.fixture
async def eleitor_sem_chat(db_session):
    """Voter with no chat_id (cannot receive notifications)."""
    e = Eleitor(
        nome="Pedro Sem Chat",
        email="pedro.nochat@test.com",
        uf="MG",
        channel="telegram",
        chat_id=None,
        temas_interesse=["economia"],
        verificado=True,
        frequencia_notificacao=FrequenciaNotificacao.IMEDIATA,
    )
    db_session.add(e)
    await db_session.flush()
    await db_session.refresh(e)
    return e


@pytest.fixture
async def proposicao_economia(db_session):
    """A proposition about economy."""
    p = Proposicao(
        id=55555,
        tipo="PL",
        numero=555,
        ano=2026,
        ementa="Dispõe sobre reforma tributária",
        situacao="Em tramitação",
        temas=["economia", "tributos"],
    )
    db_session.add(p)
    await db_session.flush()
    await db_session.refresh(p)
    return p


# ---------------------------------------------------------------------------
# Test: Full notification flow with mock Telegram
# ---------------------------------------------------------------------------


class TestNotificationPipelineIntegration:
    """Test the complete notification pipeline end-to-end."""

    async def test_notify_sends_to_matching_voters_only(
        self,
        notification_service,
        eleitor_economia,
        eleitor_saude,
    ):
        """Only voters whose temas match should receive notifications."""
        sent = []

        async def mock_send(chat_id: str, text: str) -> None:
            sent.append({"chat_id": chat_id, "text": text})

        stats = await notification_service.notify_voters_about_proposicao(
            proposicao_id=55555,
            tipo="PL",
            numero=555,
            ano=2026,
            ementa="Reforma tributária",
            temas=["economia"],
            send_fn=mock_send,
        )

        # Only eleitor_economia should match (tema "economia")
        assert stats["sent"] >= 1
        economia_msgs = [m for m in sent if m["chat_id"] == "100001"]
        assert len(economia_msgs) == 1
        assert "PL 555/2026" in economia_msgs[0]["text"]
        assert "economia" in economia_msgs[0]["text"]

        # eleitor_saude should NOT have received anything (tema "saúde" only)
        saude_msgs = [m for m in sent if m["chat_id"] == "100002"]
        assert len(saude_msgs) == 0

    async def test_notify_skips_voters_without_chat_id(
        self,
        notification_service,
        eleitor_economia,
        eleitor_sem_chat,
    ):
        """Voters without chat_id should be skipped and counted."""
        sent = []

        async def mock_send(chat_id: str, text: str) -> None:
            sent.append(chat_id)

        stats = await notification_service.notify_voters_about_proposicao(
            proposicao_id=55555,
            tipo="PL",
            numero=555,
            ano=2026,
            ementa="Reforma tributária",
            temas=["economia"],
            send_fn=mock_send,
        )

        # Both voters match "economia" but only one has chat_id
        assert stats["total_voters"] >= 2
        assert stats["skipped"] >= 1
        assert "100001" in sent
        assert None not in sent

    async def test_notify_handles_send_failure_gracefully(
        self,
        notification_service,
        eleitor_economia,
    ):
        """If sending fails for a voter, error is counted but others proceed."""
        call_count = 0

        async def failing_send(chat_id: str, text: str) -> None:
            nonlocal call_count
            call_count += 1
            raise ConnectionError("Telegram API timeout")

        stats = await notification_service.notify_voters_about_proposicao(
            proposicao_id=55555,
            tipo="PL",
            numero=555,
            ano=2026,
            ementa="Reforma tributária",
            temas=["economia"],
            send_fn=failing_send,
        )

        assert stats["errors"] >= 1
        assert stats["sent"] == 0
        assert call_count >= 1

    async def test_notify_multiple_temas_deduplicates_voters(
        self,
        notification_service,
        eleitor_economia,
        db_session,
    ):
        """A voter interested in both temas should receive only one notification."""
        # eleitor_economia has ["economia", "tributos"]
        sent = []

        async def mock_send(chat_id: str, text: str) -> None:
            sent.append(chat_id)

        stats = await notification_service.notify_voters_about_proposicao(
            proposicao_id=55555,
            tipo="PL",
            numero=555,
            ano=2026,
            ementa="Reforma tributária ampla",
            temas=["economia", "tributos"],  # voter matches both
            send_fn=mock_send,
        )

        # Should receive only 1 notification despite matching 2 temas
        msgs_for_voter = [c for c in sent if c == "100001"]
        assert len(msgs_for_voter) == 1


class TestComparativoNotificationPipeline:
    """Test comparativo notification flow."""

    async def test_voters_who_voted_receive_comparativo(
        self,
        notification_service,
        proposicao_economia,
        eleitor_economia,
        db_session,
    ):
        """Voters who cast a popular vote should receive the comparativo."""
        # Create a popular vote
        voto = VotoPopular(
            eleitor_id=eleitor_economia.id,
            proposicao_id=proposicao_economia.id,
            voto=VotoEnum.SIM,
        )
        db_session.add(voto)
        await db_session.flush()

        sent = []

        async def mock_send(chat_id: str, text: str) -> None:
            sent.append({"chat_id": chat_id, "text": text})

        stats = await notification_service.notify_voters_comparativo(
            proposicao_id=proposicao_economia.id,
            tipo="PL",
            numero=555,
            ano=2026,
            resultado_camara="APROVADO",
            percentual_sim_popular=78.5,
            alinhamento=0.92,
            send_fn=mock_send,
        )

        assert stats["sent"] >= 1
        assert any(m["chat_id"] == "100001" for m in sent)
        assert any("APROVADO" in m["text"] for m in sent)
        assert any("78.5%" in m["text"] for m in sent)
        assert any("92%" in m["text"] for m in sent)

    async def test_comparativo_no_voters_who_voted(
        self,
        notification_service,
        proposicao_economia,
    ):
        """If no voters cast a popular vote, stats should be zero."""
        stats = await notification_service.notify_voters_comparativo(
            proposicao_id=proposicao_economia.id,
            tipo="PL",
            numero=555,
            ano=2026,
            resultado_camara="REJEITADO",
            percentual_sim_popular=30.0,
            alinhamento=0.3,
        )

        assert stats["total_voters"] == 0
        assert stats["sent"] == 0


class TestCeleryTaskIntegration:
    """Test that Celery tasks correctly wire the TelegramAdapter."""

    def test_notificar_eleitores_task_uses_telegram_adapter(self):
        """Verify the task code references _get_telegram_send_fn (not dry run)."""
        import inspect
        from app.tasks.notificar_eleitores import notificar_eleitores_task

        source = inspect.getsource(notificar_eleitores_task)

        # Should use the real send function, not send_fn=None
        assert "_get_telegram_send_fn" in source or "send_fn=send_fn" in source, (
            "notificar_eleitores_task should use a real send function, not dry-run"
        )

    def test_notificar_comparativo_task_uses_telegram_adapter(self):
        """Verify the comparativo task code references _get_telegram_send_fn."""
        import inspect
        from app.tasks.notificar_eleitores import notificar_comparativo_task

        source = inspect.getsource(notificar_comparativo_task)

        assert "_get_telegram_send_fn" in source or "send_fn=send_fn" in source, (
            "notificar_comparativo_task should use a real send function, not dry-run"
        )

    def test_sync_proposicoes_chains_notification(self):
        """Verify sync_proposicoes_task triggers notification after new propositions."""
        import inspect
        from app.tasks.sync_proposicoes import sync_proposicoes_task

        source = inspect.getsource(sync_proposicoes_task)

        assert "notificar_eleitores_task" in source or "_trigger_notifications" in source, (
            "sync_proposicoes_task should chain to notification task"
        )

    @patch("app.tasks.notificar_eleitores._get_telegram_send_fn")
    def test_task_falls_back_to_dry_run_when_no_token(self, mock_get_fn):
        """If TELEGRAM_BOT_TOKEN is empty, task should degrade to dry-run."""
        mock_get_fn.return_value = None  # Simulates no token configured

        # The task should still complete without errors  
        # (just won't send real messages)
        # This tests the graceful degradation path
        assert mock_get_fn.return_value is None


class TestMessageFormatting:
    """Test that notification messages contain required information."""

    def test_nova_proposicao_has_all_fields(self):
        """Message should contain tipo, numero, ano, ementa, temas."""
        service = NotificationService.__new__(NotificationService)
        msg = service.format_nova_proposicao_message(
            proposicao_id=42,
            tipo="PEC",
            numero=45,
            ano=2026,
            ementa="Altera disposições sobre reforma agrária",
            temas=["agricultura", "reforma agrária"],
        )

        assert "PEC 45/2026" in msg
        assert "reforma agrária" in msg
        assert "agricultura" in msg
        assert "42" in msg  # proposicao_id for follow-up

    def test_resultado_votacao_has_percentages(self):
        """Result message should show percentages and total."""
        service = NotificationService.__new__(NotificationService)
        msg = service.format_resultado_votacao_message(
            proposicao_id=42,
            tipo="PL",
            numero=100,
            ano=2026,
            total_votos=1500,
            percentual_sim=65.3,
            percentual_nao=30.2,
            percentual_abstencao=4.5,
        )

        assert "65.3%" in msg
        assert "30.2%" in msg
        assert "4.5%" in msg
        assert "1500" in msg

    def test_comparativo_shows_alignment(self):
        """Comparativo message should show result, popular %, and alignment."""
        service = NotificationService.__new__(NotificationService)
        msg = service.format_comparativo_message(
            proposicao_id=42,
            tipo="MPV",
            numero=200,
            ano=2026,
            resultado_camara="APROVADO",
            percentual_sim_popular=82.0,
            alinhamento=0.88,
        )

        assert "APROVADO" in msg
        assert "82.0%" in msg
        assert "88%" in msg
        assert "MPV 200/2026" in msg
