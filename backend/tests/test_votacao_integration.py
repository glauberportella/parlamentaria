"""Integration tests for the Votação Popular flow — end-to-end.

Tests the complete voting cycle:
1. Voter registration → Vote → Result → Notification
2. Webhook callback → Agent routing → Vote registration
3. Vote consolidation and result retrieval
"""

import uuid

import pytest
from datetime import date

from app.domain.eleitor import Eleitor, FrequenciaNotificacao
from app.domain.proposicao import Proposicao
from app.domain.voto_popular import VotoEnum
from app.services.eleitor_service import EleitorService
from app.services.voto_popular_service import VotoPopularService
from app.services.notification_service import NotificationService


@pytest.fixture
async def eleitor_service(db_session):
    return EleitorService(db_session)


@pytest.fixture
async def voto_service(db_session):
    return VotoPopularService(db_session)


@pytest.fixture
async def notif_service(db_session):
    return NotificationService(db_session)


@pytest.fixture
async def proposicao(db_session, sample_proposicao_data):
    prop = Proposicao(**sample_proposicao_data)
    db_session.add(prop)
    await db_session.flush()
    await db_session.refresh(prop)
    return prop


@pytest.fixture
async def proposicao_2(db_session):
    prop = Proposicao(
        id=54321,
        tipo="PEC",
        numero=50,
        ano=2024,
        ementa="Reforma administrativa",
        data_apresentacao=date(2024, 5, 1),
        situacao="Em tramitação",
        temas=["administração", "governo"],
    )
    db_session.add(prop)
    await db_session.flush()
    await db_session.refresh(prop)
    return prop


# ---------------------------------------------------------------------------
# Integration: Full voting cycle
# ---------------------------------------------------------------------------

class TestFullVotingCycle:
    """Integration test: entire voting flow from registration to result."""

    async def test_register_vote_and_get_result(
        self, eleitor_service, voto_service, db_session, proposicao
    ):
        """E2E: Create voter → Vote SIM → Check result."""
        # Step 1: Create voter via chat_id (simulates first Telegram interaction)
        eleitor, created = await eleitor_service.get_or_create_by_chat_id(
            "telegram_user_001", "telegram"
        )
        assert created is True
        await db_session.flush()

        # Step 2: Register vote
        voto = await voto_service.registrar_voto(
            eleitor_id=eleitor.id,
            proposicao_id=proposicao.id,
            voto=VotoEnum.SIM,
            justificativa="Apoio a transparência",
        )
        await db_session.flush()
        assert voto.voto == VotoEnum.SIM
        assert voto.justificativa == "Apoio a transparência"

        # Step 3: Check result
        resultado = await voto_service.obter_resultado(proposicao.id)
        assert resultado["total"] == 1
        assert resultado["SIM"] == 1
        assert resultado["percentual_sim"] == 100.0
        assert resultado["NAO"] == 0
        assert resultado["ABSTENCAO"] == 0

    async def test_multiple_voters_consolidation(
        self, voto_service, db_session, proposicao
    ):
        """E2E: Multiple voters → Consolidated result with percentages."""
        voters = []
        for i in range(5):
            e = Eleitor(
                nome=f"Eleitor {i}",
                email=f"eleitor{i}@test.com",
                uf="SP",
                channel="telegram",
                chat_id=f"chat_{i}",
            )
            db_session.add(e)
            await db_session.flush()
            await db_session.refresh(e)
            voters.append(e)

        # 3 SIM, 1 NAO, 1 ABSTENCAO
        votes = [VotoEnum.SIM, VotoEnum.SIM, VotoEnum.SIM, VotoEnum.NAO, VotoEnum.ABSTENCAO]
        for voter, voto in zip(voters, votes):
            await voto_service.registrar_voto(
                eleitor_id=voter.id,
                proposicao_id=proposicao.id,
                voto=voto,
            )
        await db_session.flush()

        resultado = await voto_service.obter_resultado(proposicao.id)
        assert resultado["total"] == 5
        assert resultado["SIM"] == 3
        assert resultado["NAO"] == 1
        assert resultado["ABSTENCAO"] == 1
        assert resultado["percentual_sim"] == 60.0
        assert resultado["percentual_nao"] == 20.0
        assert resultado["percentual_abstencao"] == 20.0

    async def test_idempotent_vote_update(
        self, eleitor_service, voto_service, db_session, proposicao
    ):
        """E2E: Voter changes their vote — last vote wins."""
        eleitor, _ = await eleitor_service.get_or_create_by_chat_id("chat_update", "telegram")
        await db_session.flush()

        # Vote SIM first
        await voto_service.registrar_voto(
            eleitor_id=eleitor.id,
            proposicao_id=proposicao.id,
            voto=VotoEnum.SIM,
        )
        await db_session.flush()

        # Change to NAO
        voto = await voto_service.registrar_voto(
            eleitor_id=eleitor.id,
            proposicao_id=proposicao.id,
            voto=VotoEnum.NAO,
        )
        await db_session.flush()

        assert voto.voto == VotoEnum.NAO

        # Result shows only 1 vote, NAO
        resultado = await voto_service.obter_resultado(proposicao.id)
        assert resultado["total"] == 1
        assert resultado["NAO"] == 1
        assert resultado["SIM"] == 0


# ---------------------------------------------------------------------------
# Integration: Vote history
# ---------------------------------------------------------------------------

class TestVoteHistory:
    """Integration test: vote history tracking."""

    async def test_voter_history_across_proposicoes(
        self, eleitor_service, voto_service, db_session, proposicao, proposicao_2
    ):
        """E2E: Voter votes on multiple propositions, history shows all."""
        eleitor, _ = await eleitor_service.get_or_create_by_chat_id("chat_history", "telegram")
        await db_session.flush()

        await voto_service.registrar_voto(
            eleitor_id=eleitor.id,
            proposicao_id=proposicao.id,
            voto=VotoEnum.SIM,
        )
        await voto_service.registrar_voto(
            eleitor_id=eleitor.id,
            proposicao_id=proposicao_2.id,
            voto=VotoEnum.NAO,
        )
        await db_session.flush()

        votos = await voto_service.list_by_eleitor(eleitor.id)
        assert len(votos) == 2

        # Check individual votes
        voto_1 = await voto_service.get_voto(eleitor.id, proposicao.id)
        assert voto_1 is not None
        assert voto_1.voto == VotoEnum.SIM

        voto_2 = await voto_service.get_voto(eleitor.id, proposicao_2.id)
        assert voto_2 is not None
        assert voto_2.voto == VotoEnum.NAO

    async def test_get_voto_returns_none_when_not_voted(
        self, eleitor_service, voto_service, db_session, proposicao
    ):
        """E2E: Checking vote before voting returns None."""
        eleitor, _ = await eleitor_service.get_or_create_by_chat_id("chat_novote", "telegram")
        await db_session.flush()

        voto = await voto_service.get_voto(eleitor.id, proposicao.id)
        assert voto is None


# ---------------------------------------------------------------------------
# Integration: Notification with voting
# ---------------------------------------------------------------------------

class TestNotificationIntegration:
    """Integration test: notifications triggered by voting activity."""

    async def test_notify_interested_voters(
        self, notif_service, db_session, proposicao
    ):
        """E2E: Voter with matching themes gets notification."""
        # Create voter with interest in 'Transparência' (matches proposicao tema)
        e = Eleitor(
            nome="Notificada",
            email="notificada@test.com",
            uf="SP",
            channel="telegram",
            chat_id="notif_chat_001",
            temas_interesse=["Transparência"],
            frequencia_notificacao=FrequenciaNotificacao.IMEDIATA,
        )
        db_session.add(e)
        await db_session.flush()

        sent = []

        async def mock_send(chat_id: str, text: str) -> None:
            sent.append((chat_id, text))

        stats = await notif_service.notify_voters_about_proposicao(
            proposicao_id=proposicao.id,
            tipo=proposicao.tipo,
            numero=proposicao.numero,
            ano=proposicao.ano,
            ementa=proposicao.ementa,
            temas=proposicao.temas,
            send_fn=mock_send,
        )
        assert stats["sent"] >= 1
        assert len(sent) >= 1
        assert sent[0][0] == "notif_chat_001"

    async def test_no_notification_for_uninterested_voter(
        self, notif_service, db_session, proposicao
    ):
        """E2E: Voter without matching themes gets no notification."""
        e = Eleitor(
            nome="Desinteressada",
            email="desinteressada@test.com",
            uf="MG",
            channel="telegram",
            chat_id="notif_chat_002",
            temas_interesse=["defesa"],
        )
        db_session.add(e)
        await db_session.flush()

        sent = []

        async def mock_send(chat_id: str, text: str) -> None:
            sent.append((chat_id, text))

        stats = await notif_service.notify_voters_about_proposicao(
            proposicao_id=proposicao.id,
            tipo=proposicao.tipo,
            numero=proposicao.numero,
            ano=proposicao.ano,
            ementa=proposicao.ementa,
            temas=proposicao.temas,
            send_fn=mock_send,
        )
        assert stats["sent"] == 0
        assert len(sent) == 0


# ---------------------------------------------------------------------------
# Integration: Admin endpoint for results
# ---------------------------------------------------------------------------

class TestAdminResultadoEndpoint:
    """Integration test: admin endpoint for consolidated vote results."""

    async def test_admin_resultado_endpoint(self, client, db_session, sample_proposicao_data, sample_eleitor_data):
        """E2E: Admin can retrieve consolidated vote result via API."""
        # Create proposition and voter
        prop = Proposicao(**sample_proposicao_data)
        db_session.add(prop)
        eleitor = Eleitor(**sample_eleitor_data)
        db_session.add(eleitor)
        await db_session.flush()
        await db_session.refresh(prop)
        await db_session.refresh(eleitor)

        # Register a vote — eleitor is eligible (conftest fixture), so
        # the vote needs tipo_voto=OFICIAL for official counts.
        from app.domain.voto_popular import VotoPopular, TipoVoto
        voto = VotoPopular(
            eleitor_id=eleitor.id,
            proposicao_id=prop.id,
            voto=VotoEnum.SIM,
            tipo_voto=TipoVoto.OFICIAL,
        )
        db_session.add(voto)
        await db_session.flush()

        # Query admin endpoint — use the default admin key from Settings
        from app.config import settings

        response = await client.get(
            f"/admin/votacoes/resultado/{prop.id}",
            headers={"X-API-Key": settings.admin_api_key},
        )
        assert response.status_code == 200
        data = response.json()
        # Admin endpoint now returns dual result: oficial + consultivo
        assert data["proposicao_id"] == prop.id
        assert data["oficial"]["total"] == 1
        assert data["oficial"]["SIM"] == 1
        assert data["oficial"]["percentual_sim"] == 100.0
        assert data["consultivo"]["total"] == 1


# ---------------------------------------------------------------------------
# Integration: Voting tools (ADK FunctionTool layer)
# ---------------------------------------------------------------------------

class TestVotacaoToolsIntegration:
    """Integration tests for votacao_tools functions with real DB."""

    async def test_registrar_voto_tool_success(self, db_session, proposicao):
        """Tool successfully registers a vote when voter exists."""
        # Create a verified voter
        eleitor = Eleitor(
            nome="Tool Voter",
            email="tool@example.com",
            uf="SP",
            channel="telegram",
            chat_id="tool_chat_001",
            verificado=True,
        )
        db_session.add(eleitor)
        await db_session.flush()

        from unittest.mock import patch, AsyncMock
        from agents.parlamentar.tools.votacao_tools import registrar_voto

        # Mock the async_session_factory to use our test session
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=db_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "agents.parlamentar.tools.votacao_tools.async_session_factory",
            return_value=mock_ctx,
        ):
            result = await registrar_voto(
                chat_id="tool_chat_001",
                proposicao_id=proposicao.id,
                voto="SIM",
                justificativa="Concordo",
            )

        assert result["status"] == "success"
        assert "SIM" in result["message"]

    async def test_registrar_voto_tool_invalid_voto(self, db_session):
        """Tool rejects invalid vote value."""
        from unittest.mock import patch, AsyncMock
        from agents.parlamentar.tools.votacao_tools import registrar_voto

        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=db_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "app.db.session.async_session_factory",
            return_value=mock_ctx,
        ):
            result = await registrar_voto(
                chat_id="any",
                proposicao_id=1,
                voto="TALVEZ",
            )

        assert result["status"] == "error"
        assert "inválido" in result["error"].lower()

    async def test_obter_resultado_tool(self, db_session, proposicao):
        """Tool returns consolidated voting result."""
        from unittest.mock import patch, AsyncMock
        from agents.parlamentar.tools.votacao_tools import obter_resultado_votacao

        # Create eligible voter and vote
        eleitor = Eleitor(
            nome="Result Voter",
            email="result@example.com",
            uf="SP",
            channel="telegram",
            chat_id="result_chat_001",
            cidadao_brasileiro=True,
            data_nascimento=date(1990, 1, 1),
            verificado=True,
        )
        db_session.add(eleitor)
        await db_session.flush()
        await db_session.refresh(eleitor)

        from app.domain.voto_popular import VotoPopular, TipoVoto
        voto = VotoPopular(
            eleitor_id=eleitor.id,
            proposicao_id=proposicao.id,
            voto=VotoEnum.NAO,
            tipo_voto=TipoVoto.OFICIAL,
        )
        db_session.add(voto)
        await db_session.flush()

        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=db_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "agents.parlamentar.tools.votacao_tools.async_session_factory",
            return_value=mock_ctx,
        ):
            result = await obter_resultado_votacao(proposicao_id=proposicao.id)

        assert result["status"] == "success"
        assert result["resultado_oficial"]["total_votos"] == 1
        assert result["resultado_oficial"]["nao"] == 1
        assert result["resultado_consultivo"]["total_votos"] == 1

    async def test_consultar_meu_voto_tool(self, db_session, proposicao):
        """Tool returns the voter's existing vote."""
        from unittest.mock import patch, AsyncMock
        from agents.parlamentar.tools.votacao_tools import consultar_meu_voto

        eleitor = Eleitor(
            nome="My Vote",
            email="myvote@example.com",
            uf="RJ",
            channel="telegram",
            chat_id="myvote_chat",
        )
        db_session.add(eleitor)
        await db_session.flush()
        await db_session.refresh(eleitor)

        from app.domain.voto_popular import VotoPopular
        voto = VotoPopular(
            eleitor_id=eleitor.id,
            proposicao_id=proposicao.id,
            voto=VotoEnum.ABSTENCAO,
        )
        db_session.add(voto)
        await db_session.flush()

        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=db_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "agents.parlamentar.tools.votacao_tools.async_session_factory",
            return_value=mock_ctx,
        ):
            result = await consultar_meu_voto(
                chat_id="myvote_chat",
                proposicao_id=proposicao.id,
            )

        assert result["status"] == "success"
        assert result["voto"]["voto"] == "ABSTENCAO"

    async def test_historico_votos_tool(self, db_session, proposicao):
        """Tool returns vote history for a voter."""
        from unittest.mock import patch, AsyncMock
        from agents.parlamentar.tools.votacao_tools import historico_votos_eleitor

        eleitor = Eleitor(
            nome="History Voter",
            email="history@example.com",
            uf="SP",
            channel="telegram",
            chat_id="history_chat",
        )
        db_session.add(eleitor)
        await db_session.flush()
        await db_session.refresh(eleitor)

        from app.domain.voto_popular import VotoPopular
        voto = VotoPopular(
            eleitor_id=eleitor.id,
            proposicao_id=proposicao.id,
            voto=VotoEnum.SIM,
        )
        db_session.add(voto)
        await db_session.flush()

        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=db_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "agents.parlamentar.tools.votacao_tools.async_session_factory",
            return_value=mock_ctx,
        ):
            result = await historico_votos_eleitor(
                chat_id="history_chat",
                limite=10,
            )

        assert result["status"] == "success"
        assert result["total"] == 1
        assert result["votos"][0]["voto"] == "SIM"


# ---------------------------------------------------------------------------
# Integration: Notification tools
# ---------------------------------------------------------------------------

class TestNotificationToolsIntegration:
    """Integration tests for notification FunctionTools."""

    async def test_enviar_resultado_votacao_tool(self, db_session, proposicao):
        """Tool returns formatted vote result."""
        from unittest.mock import patch, AsyncMock
        from agents.parlamentar.tools.notification_tools import enviar_resultado_votacao

        # Create voter and vote
        eleitor = Eleitor(
            nome="Notif Voter",
            email="notifvote@example.com",
            uf="SP",
            channel="telegram",
            chat_id="notif_chat",
        )
        db_session.add(eleitor)
        await db_session.flush()
        await db_session.refresh(eleitor)

        from app.domain.voto_popular import VotoPopular
        voto = VotoPopular(
            eleitor_id=eleitor.id,
            proposicao_id=proposicao.id,
            voto=VotoEnum.SIM,
        )
        db_session.add(voto)
        await db_session.flush()

        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=db_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "app.db.session.async_session_factory",
            return_value=mock_ctx,
        ):
            result = await enviar_resultado_votacao(proposicao_id=proposicao.id)

        assert result["status"] == "success"
        assert "SIM" in result["message"]
        assert result["maioria"] == "SIM"

    async def test_enviar_resultado_votacao_no_votes(self, db_session, proposicao):
        """Tool handles propositions with no votes."""
        from unittest.mock import patch, AsyncMock
        from agents.parlamentar.tools.notification_tools import enviar_resultado_votacao

        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=db_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "app.db.session.async_session_factory",
            return_value=mock_ctx,
        ):
            result = await enviar_resultado_votacao(proposicao_id=proposicao.id)

        assert result["status"] == "success"
        assert "Nenhum voto" in result["message"]
