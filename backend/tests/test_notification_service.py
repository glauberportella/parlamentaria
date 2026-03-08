"""Tests for NotificationService — proactive voter notifications."""

import uuid

import pytest

from app.domain.eleitor import Eleitor, FrequenciaNotificacao
from app.domain.proposicao import Proposicao
from app.domain.voto_popular import VotoPopular, VotoEnum
from app.services.notification_service import NotificationService


@pytest.fixture
async def service(db_session):
    """Provide a NotificationService instance."""
    return NotificationService(db_session)


@pytest.fixture
async def proposicao(db_session, sample_proposicao_data):
    """Create a proposition in the database."""
    prop = Proposicao(**sample_proposicao_data)
    db_session.add(prop)
    await db_session.flush()
    await db_session.refresh(prop)
    return prop


@pytest.fixture
async def eleitor_com_temas(db_session):
    """Create a voter with interest themes configured."""
    e = Eleitor(
        nome="Ana Souza",
        email="ana@example.com",
        uf="SP",
        channel="telegram",
        chat_id="11111111",
        temas_interesse=["economia", "saúde"],
        verificado=True,
        frequencia_notificacao=FrequenciaNotificacao.IMEDIATA,
    )
    db_session.add(e)
    await db_session.flush()
    await db_session.refresh(e)
    return e


@pytest.fixture
async def eleitor_sem_temas(db_session):
    """Create a voter without interest themes."""
    e = Eleitor(
        nome="João Lima",
        email="joao.lima@example.com",
        uf="RJ",
        channel="telegram",
        chat_id="22222222",
        temas_interesse=[],
    )
    db_session.add(e)
    await db_session.flush()
    await db_session.refresh(e)
    return e


@pytest.fixture
async def eleitor_sem_chat_id(db_session):
    """Create a voter without a chat_id."""
    e = Eleitor(
        nome="Carlos Neto",
        email="carlos.neto@example.com",
        uf="MG",
        channel="telegram",
        chat_id=None,
        temas_interesse=["economia"],
    )
    db_session.add(e)
    await db_session.flush()
    await db_session.refresh(e)
    return e


# ---------------------------------------------------------------------------
# Tests: find_voters_by_tema
# ---------------------------------------------------------------------------

class TestFindVotersByTema:
    """Tests for find_voters_by_tema."""

    async def test_finds_voters_with_matching_tema(self, service, eleitor_com_temas):
        result = await service.find_voters_by_tema("economia")
        assert len(result) >= 1
        assert any(v.id == eleitor_com_temas.id for v in result)

    async def test_no_match_returns_empty(self, service, eleitor_com_temas):
        result = await service.find_voters_by_tema("defesa")
        assert len(result) == 0

    async def test_does_not_find_voter_without_temas(
        self, service, eleitor_sem_temas
    ):
        result = await service.find_voters_by_tema("economia")
        assert not any(v.id == eleitor_sem_temas.id for v in result)


# ---------------------------------------------------------------------------
# Tests: find_voters_for_proposicao
# ---------------------------------------------------------------------------

class TestFindVotersForProposicao:
    """Tests for find_voters_for_proposicao."""

    async def test_finds_voters_for_multiple_temas(
        self, service, eleitor_com_temas, db_session
    ):
        # Add another voter interested in 'educação'
        e2 = Eleitor(
            nome="Paulo",
            email="paulo@example.com",
            uf="BA",
            channel="telegram",
            chat_id="33333333",
            temas_interesse=["educação"],
        )
        db_session.add(e2)
        await db_session.flush()

        result = await service.find_voters_for_proposicao(["economia", "educação"])
        ids = [v.id for v in result]
        assert eleitor_com_temas.id in ids
        assert e2.id in ids

    async def test_deduplicates_voters(self, service, eleitor_com_temas):
        # Voter is interested in both economia and saúde
        result = await service.find_voters_for_proposicao(["economia", "saúde"])
        ids = [v.id for v in result]
        assert ids.count(eleitor_com_temas.id) == 1

    async def test_empty_temas_returns_empty(self, service):
        result = await service.find_voters_for_proposicao([])
        assert len(result) == 0


# ---------------------------------------------------------------------------
# Tests: format_nova_proposicao_message
# ---------------------------------------------------------------------------

class TestFormatNovaProposicaoMessage:
    """Tests for message formatting."""

    def test_format_contains_tipo_numero_ano(self):
        service = NotificationService.__new__(NotificationService)
        msg = service.format_nova_proposicao_message(
            proposicao_id=123,
            tipo="PL",
            numero=100,
            ano=2024,
            ementa="Teste de ementa",
            temas=["economia"],
        )
        assert "PL 100/2024" in msg
        assert "Teste de ementa" in msg
        assert "economia" in msg
        assert "123" in msg

    def test_format_handles_no_temas(self):
        service = NotificationService.__new__(NotificationService)
        msg = service.format_nova_proposicao_message(
            proposicao_id=1, tipo="PEC", numero=1, ano=2025,
            ementa="Ementa", temas=[],
        )
        assert "Sem tema definido" in msg

    def test_format_resultado(self):
        service = NotificationService.__new__(NotificationService)
        msg = service.format_resultado_votacao_message(
            proposicao_id=456,
            tipo="PL",
            numero=200,
            ano=2024,
            total_votos=100,
            percentual_sim=73.5,
            percentual_nao=21.0,
            percentual_abstencao=5.5,
        )
        assert "73.5%" in msg
        assert "21.0%" in msg
        assert "100" in msg

    def test_format_comparativo(self):
        service = NotificationService.__new__(NotificationService)
        msg = service.format_comparativo_message(
            proposicao_id=789,
            tipo="PL",
            numero=300,
            ano=2024,
            resultado_camara="APROVADO",
            percentual_sim_popular=73.0,
            alinhamento=0.95,
        )
        assert "APROVADO" in msg
        assert "73.0%" in msg
        assert "95%" in msg

    def test_format_comparativo_rejeitado(self):
        service = NotificationService.__new__(NotificationService)
        msg = service.format_comparativo_message(
            proposicao_id=789,
            tipo="PEC",
            numero=10,
            ano=2024,
            resultado_camara="REJEITADO",
            percentual_sim_popular=30.0,
            alinhamento=0.3,
        )
        assert "REJEITADO" in msg
        assert "❌" in msg


# ---------------------------------------------------------------------------
# Tests: notify_voters_about_proposicao
# ---------------------------------------------------------------------------

class TestNotifyVotersAboutProposicao:
    """Tests for the full notification flow."""

    async def test_dry_run_logs_only(self, service, eleitor_com_temas):
        stats = await service.notify_voters_about_proposicao(
            proposicao_id=123,
            tipo="PL",
            numero=100,
            ano=2024,
            ementa="Teste",
            temas=["economia"],
            send_fn=None,  # Dry run
        )
        assert stats["total_voters"] >= 1
        assert stats["sent"] >= 1
        assert stats["errors"] == 0

    async def test_sends_via_callback(self, service, eleitor_com_temas):
        sent_messages = []

        async def mock_send(chat_id: str, text: str) -> None:
            sent_messages.append((chat_id, text))

        stats = await service.notify_voters_about_proposicao(
            proposicao_id=123,
            tipo="PL",
            numero=100,
            ano=2024,
            ementa="Teste ementa",
            temas=["economia"],
            send_fn=mock_send,
        )
        assert stats["sent"] >= 1
        assert len(sent_messages) >= 1
        assert sent_messages[0][0] == "11111111"  # eleitor_com_temas.chat_id
        assert "PL 100/2024" in sent_messages[0][1]

    async def test_skips_voter_without_chat_id(
        self, service, eleitor_sem_chat_id
    ):
        stats = await service.notify_voters_about_proposicao(
            proposicao_id=123,
            tipo="PL",
            numero=100,
            ano=2024,
            ementa="Teste",
            temas=["economia"],
            send_fn=None,
        )
        assert stats["skipped"] >= 1

    async def test_no_temas_returns_empty_stats(self, service):
        stats = await service.notify_voters_about_proposicao(
            proposicao_id=123,
            tipo="PL",
            numero=100,
            ano=2024,
            ementa="Teste",
            temas=[],
        )
        assert stats["total_voters"] == 0
        assert stats["sent"] == 0

    async def test_handles_send_error(self, service, eleitor_com_temas):
        async def failing_send(chat_id: str, text: str) -> None:
            raise Exception("Connection timeout")

        stats = await service.notify_voters_about_proposicao(
            proposicao_id=123,
            tipo="PL",
            numero=100,
            ano=2024,
            ementa="Teste",
            temas=["economia"],
            send_fn=failing_send,
        )
        assert stats["errors"] >= 1
        assert stats["sent"] == 0


# ---------------------------------------------------------------------------
# Tests: notify_voters_comparativo
# ---------------------------------------------------------------------------

class TestNotifyVotersComparativo:
    """Tests for comparativo notification."""

    async def test_notifies_voters_who_voted(
        self, service, proposicao, eleitor_com_temas, db_session
    ):
        # Create a vote so there's a voter to notify
        voto = VotoPopular(
            eleitor_id=eleitor_com_temas.id,
            proposicao_id=proposicao.id,
            voto=VotoEnum.SIM,
        )
        db_session.add(voto)
        await db_session.flush()

        sent_messages = []

        async def mock_send(chat_id: str, text: str) -> None:
            sent_messages.append((chat_id, text))

        stats = await service.notify_voters_comparativo(
            proposicao_id=proposicao.id,
            tipo="PL",
            numero=100,
            ano=2024,
            resultado_camara="APROVADO",
            percentual_sim_popular=73.0,
            alinhamento=0.95,
            send_fn=mock_send,
        )
        assert stats["sent"] >= 1
        assert len(sent_messages) >= 1
        assert "APROVADO" in sent_messages[0][1]

    async def test_no_voters_returns_empty(self, service, proposicao):
        stats = await service.notify_voters_comparativo(
            proposicao_id=proposicao.id,
            tipo="PL",
            numero=100,
            ano=2024,
            resultado_camara="REJEITADO",
            percentual_sim_popular=30.0,
            alinhamento=0.3,
        )
        assert stats["total_voters"] == 0
        assert stats["sent"] == 0
