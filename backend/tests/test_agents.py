"""Tests for Parlamentaria ADK agents — structure, tools, and integration.

Tests validate:
- Agent structure (names, descriptions, tools, sub-agents)
- FunctionTools behavior with mocked services
- Runner integration
- Prompts and eval datasets
"""

import json
import uuid
from datetime import datetime, date, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest

# Project root (one level above backend/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


# ---------------------------------------------------------------------------
# Helper — mock CamaraClient as async context manager
# ---------------------------------------------------------------------------

def _mock_camara_client(**methods):
    """Create a mock that works as ``async with CamaraClient() as client:``"""
    mock_client = AsyncMock()
    for name, return_value in methods.items():
        getattr(mock_client, name).return_value = return_value

    mock_class = MagicMock()
    mock_instance = MagicMock()
    mock_instance.__aenter__ = AsyncMock(return_value=mock_client)
    mock_instance.__aexit__ = AsyncMock(return_value=False)
    mock_class.return_value = mock_instance
    return mock_class, mock_client


# ---------------------------------------------------------------------------
# Agent Structure Tests
# ---------------------------------------------------------------------------

class TestAgentStructure:
    """Validate agent configuration follows ADK best practices."""

    def test_root_agent_exists(self):
        from agents.parlamentar.agent import root_agent

        assert root_agent.name == "ParlamentarAgent"
        assert root_agent.model is not None
        assert root_agent.instruction is not None
        assert root_agent.description is not None
        assert len(root_agent.sub_agents) == 5

    def test_root_agent_has_output_key(self):
        from agents.parlamentar.agent import root_agent

        assert root_agent.output_key == "last_response"

    def test_root_agent_has_direct_tools(self):
        from agents.parlamentar.agent import root_agent

        tool_names = [t.__name__ if callable(t) else str(t) for t in root_agent.tools]
        assert "buscar_eventos_pauta" in tool_names

    def test_sub_agent_names_unique(self):
        from agents.parlamentar.agent import root_agent

        names = [sa.name for sa in root_agent.sub_agents]
        assert len(names) == len(set(names)), f"Duplicate names: {names}"

    def test_sub_agents_have_descriptions(self):
        from agents.parlamentar.agent import root_agent

        for sa in root_agent.sub_agents:
            assert sa.description, f"{sa.name} missing description"
            assert len(sa.description) > 20, f"{sa.name} description too short"

    def test_sub_agents_have_tools(self):
        from agents.parlamentar.agent import root_agent

        for sa in root_agent.sub_agents:
            assert len(sa.tools) > 0, f"{sa.name} has no tools"

    def test_proposicao_agent_config(self):
        from agents.parlamentar.sub_agents.proposicao_agent import proposicao_agent

        assert proposicao_agent.name == "ProposicaoAgent"
        tool_names = [t.__name__ if callable(t) else str(t) for t in proposicao_agent.tools]
        assert "buscar_proposicoes" in tool_names
        assert "obter_detalhes_proposicao" in tool_names
        assert "obter_analise_ia" in tool_names

    def test_votacao_agent_config(self):
        from agents.parlamentar.sub_agents.votacao_agent import votacao_agent

        assert votacao_agent.name == "VotacaoAgent"
        tool_names = [t.__name__ if callable(t) else str(t) for t in votacao_agent.tools]
        assert "registrar_voto" in tool_names
        assert "obter_resultado_votacao" in tool_names

    def test_deputado_agent_config(self):
        from agents.parlamentar.sub_agents.deputado_agent import deputado_agent

        assert deputado_agent.name == "DeputadoAgent"
        tool_names = [t.__name__ if callable(t) else str(t) for t in deputado_agent.tools]
        assert "buscar_deputado" in tool_names
        assert "obter_perfil_deputado" in tool_names
        assert "obter_despesas_deputado" in tool_names

    def test_eleitor_agent_config(self):
        from agents.parlamentar.sub_agents.eleitor_agent import eleitor_agent

        assert eleitor_agent.name == "EleitorAgent"
        tool_names = [t.__name__ if callable(t) else str(t) for t in eleitor_agent.tools]
        assert "cadastrar_eleitor" in tool_names
        assert "consultar_perfil_eleitor" in tool_names

    def test_publicacao_agent_config(self):
        from agents.parlamentar.sub_agents.publicacao_agent import publicacao_agent

        assert publicacao_agent.name == "PublicacaoAgent"
        tool_names = [t.__name__ if callable(t) else str(t) for t in publicacao_agent.tools]
        assert "obter_comparativo" in tool_names
        assert "status_publicacao" in tool_names

    def test_all_agents_use_same_model(self):
        from agents.parlamentar.agent import root_agent
        from app.config import settings

        assert root_agent.model == settings.agent_model
        for sa in root_agent.sub_agents:
            assert sa.model == settings.agent_model, f"{sa.name} uses {sa.model}"


# ---------------------------------------------------------------------------
# Prompts Tests
# ---------------------------------------------------------------------------

class TestPrompts:
    """Validate prompt content."""

    def test_root_instruction_has_key_elements(self):
        from agents.parlamentar.prompts import ROOT_AGENT_INSTRUCTION

        assert "Parlamentar de IA" in ROOT_AGENT_INSTRUCTION
        assert "apartidário" in ROOT_AGENT_INSTRUCTION.lower()

    def test_all_instructions_are_nonempty(self):
        from agents.parlamentar.prompts import (
            ROOT_AGENT_INSTRUCTION,
            PROPOSICAO_AGENT_INSTRUCTION,
            VOTACAO_AGENT_INSTRUCTION,
            DEPUTADO_AGENT_INSTRUCTION,
            ELEITOR_AGENT_INSTRUCTION,
            PUBLICACAO_AGENT_INSTRUCTION,
        )

        for name, instruction in [
            ("root", ROOT_AGENT_INSTRUCTION),
            ("proposicao", PROPOSICAO_AGENT_INSTRUCTION),
            ("votacao", VOTACAO_AGENT_INSTRUCTION),
            ("deputado", DEPUTADO_AGENT_INSTRUCTION),
            ("eleitor", ELEITOR_AGENT_INSTRUCTION),
            ("publicacao", PUBLICACAO_AGENT_INSTRUCTION),
        ]:
            assert len(instruction) > 100, f"{name} instruction too short"

    def test_votacao_instruction_mentions_voto_options(self):
        from agents.parlamentar.prompts import VOTACAO_AGENT_INSTRUCTION

        content = VOTACAO_AGENT_INSTRUCTION.upper()
        assert "SIM" in content
        assert "NAO" in content or "NÃO" in content


# ---------------------------------------------------------------------------
# Eval Datasets Tests
# ---------------------------------------------------------------------------

class TestEvalDatasets:
    """Validate evaluation dataset structure."""

    def test_proposicao_eval_valid_json(self):
        with open(PROJECT_ROOT / "agents" / "eval" / "proposicao_eval.json") as f:
            data = json.load(f)

        assert isinstance(data, list)
        assert len(data) >= 3
        for item in data:
            assert "name" in item
            assert "initial_prompt" in item
            assert "tags" in item

    def test_votacao_eval_valid_json(self):
        with open(PROJECT_ROOT / "agents" / "eval" / "votacao_eval.json") as f:
            data = json.load(f)

        assert isinstance(data, list)
        assert len(data) >= 3

    def test_conversational_eval_valid_json(self):
        with open(PROJECT_ROOT / "agents" / "eval" / "conversational_eval.json") as f:
            data = json.load(f)

        assert isinstance(data, list)
        assert len(data) >= 5

        intents = {item.get("expected_intent") for item in data}
        assert "greeting" in intents
        assert "cadastro" in intents
        assert "out_of_scope" in intents


# ---------------------------------------------------------------------------
# FunctionTools Tests — Câmara Tools
# ---------------------------------------------------------------------------

class TestCamaraTools:
    """Test Câmara API tools with mocked HTTP client."""

    @pytest.mark.asyncio
    async def test_buscar_proposicoes_success(self):
        mock_props = [
            MagicMock(id=1, siglaTipo="PL", numero=123, ano=2024, ementa="Teste proposição"),
            MagicMock(id=2, siglaTipo="PEC", numero=45, ano=2024, ementa="Outra proposição"),
        ]

        mock_class, _ = _mock_camara_client(listar_proposicoes=mock_props)

        with patch("agents.parlamentar.tools.camara_tools.CamaraClient", mock_class):
            from agents.parlamentar.tools.camara_tools import buscar_proposicoes

            result = await buscar_proposicoes(tema="saúde")

            assert result["status"] == "success"
            assert len(result["proposicoes"]) == 2
            assert result["proposicoes"][0]["tipo"] == "PL"

    @pytest.mark.asyncio
    async def test_buscar_proposicoes_error(self):
        mock_class = MagicMock()
        mock_class.return_value.__aenter__ = AsyncMock(
            side_effect=Exception("API indisponível")
        )

        with patch("agents.parlamentar.tools.camara_tools.CamaraClient", mock_class):
            from agents.parlamentar.tools.camara_tools import buscar_proposicoes

            result = await buscar_proposicoes()

            assert result["status"] == "error"

    @pytest.mark.asyncio
    async def test_obter_detalhes_proposicao_success(self):
        mock_prop = MagicMock(
            id=1234, siglaTipo="PL", numero=1234, ano=2024,
            ementa="Proposição de teste",
            urlInteiroTeor="https://example.com/text.pdf",
            statusProposicao={"descricaoSituacao": "Em tramitação"},
            dataApresentacao="2024-01-15",
        )
        mock_autores = [MagicMock(nome="Dep. Teste", tipo="Autor")]
        mock_temas = [MagicMock(tema="Saúde")]

        mock_class, _ = _mock_camara_client(
            obter_proposicao=mock_prop,
            obter_autores=mock_autores,
            obter_temas=mock_temas,
        )

        with patch("agents.parlamentar.tools.camara_tools.CamaraClient", mock_class):
            from agents.parlamentar.tools.camara_tools import obter_detalhes_proposicao

            result = await obter_detalhes_proposicao(1234)

            assert result["status"] == "success"
            assert result["proposicao"]["id"] == 1234
            assert result["proposicao"]["autores"][0]["nome"] == "Dep. Teste"
            assert result["proposicao"]["temas"] == ["Saúde"]

    @pytest.mark.asyncio
    async def test_buscar_deputado_success(self):
        mock_deps = [
            MagicMock(id=100, nome="Dep. Teste", siglaPartido="PT", siglaUf="SP", urlFoto=""),
        ]

        mock_class, _ = _mock_camara_client(listar_deputados=mock_deps)

        with patch("agents.parlamentar.tools.camara_tools.CamaraClient", mock_class):
            from agents.parlamentar.tools.camara_tools import buscar_deputado

            result = await buscar_deputado(nome="Teste")

            assert result["status"] == "success"
            assert result["deputados"][0]["nome"] == "Dep. Teste"

    @pytest.mark.asyncio
    async def test_obter_despesas_deputado_success(self):
        mock_despesas = [
            MagicMock(tipoDespesa="COMBUSTÍVEIS", nomeFornecedor="Posto X",
                     valorDocumento=150.50, dataDocumento="2024-01-15"),
            MagicMock(tipoDespesa="TELEFONIA", nomeFornecedor="Tel Y",
                     valorDocumento=200.00, dataDocumento="2024-01-20"),
        ]

        mock_class, _ = _mock_camara_client(obter_despesas=mock_despesas)

        with patch("agents.parlamentar.tools.camara_tools.CamaraClient", mock_class):
            from agents.parlamentar.tools.camara_tools import obter_despesas_deputado

            result = await obter_despesas_deputado(100, ano=2024)

            assert result["status"] == "success"
            assert result["total_gasto"] == 350.50
            assert len(result["despesas"]) == 2

    @pytest.mark.asyncio
    async def test_buscar_votacoes_recentes_success(self):
        mock_votacoes = [
            MagicMock(id="10", data="2024-03-01", descricao="Votação teste", aprovacao=1),
        ]

        mock_class, _ = _mock_camara_client(listar_votacoes=mock_votacoes)

        with patch("agents.parlamentar.tools.camara_tools.CamaraClient", mock_class):
            from agents.parlamentar.tools.camara_tools import buscar_votacoes_recentes

            result = await buscar_votacoes_recentes()

            assert result["status"] == "success"
            assert len(result["votacoes"]) == 1

    @pytest.mark.asyncio
    async def test_listar_tramitacoes_success(self):
        mock_tramitacoes = [
            MagicMock(
                dataHora="2024-03-01", descricaoSituacao="Em análise",
                despacho="Aprovado", descricaoTramitacao="Tramitação X",
            ),
        ]

        mock_class, _ = _mock_camara_client(obter_tramitacoes=mock_tramitacoes)

        with patch("agents.parlamentar.tools.camara_tools.CamaraClient", mock_class):
            from agents.parlamentar.tools.camara_tools import listar_tramitacoes_proposicao

            result = await listar_tramitacoes_proposicao(1234)

            assert result["status"] == "success"
            assert len(result["tramitacoes"]) == 1
            assert result["tramitacoes"][0]["descricao"] == "Em análise"

    @pytest.mark.asyncio
    async def test_obter_votos_parlamentares_success(self):
        mock_votos = [
            MagicMock(
                deputado_={"nome": "Dep. X", "siglaPartido": "PT", "siglaUf": "SP"},
                tipoVoto="Sim",
            ),
        ]
        mock_orientacoes = [
            MagicMock(nomeBancada="PT", orientacao="Sim"),
        ]

        mock_class, _ = _mock_camara_client(
            obter_votos=mock_votos, obter_orientacoes=mock_orientacoes,
        )

        with patch("agents.parlamentar.tools.camara_tools.CamaraClient", mock_class):
            from agents.parlamentar.tools.camara_tools import obter_votos_parlamentares

            result = await obter_votos_parlamentares(10)

            assert result["status"] == "success"
            assert result["votos"][0]["deputado"] == "Dep. X"
            assert result["orientacoes"][0]["bancada"] == "PT"

    @pytest.mark.asyncio
    async def test_obter_perfil_deputado_success(self):
        mock_dep = MagicMock(
            id=100, nomeCivil="João da Silva",
            dataNascimento="1970-01-01",
            ultimoStatus={
                "nomeEleitoral": "João Silva",
                "siglaPartido": "PT",
                "siglaUf": "SP",
                "situacao": "Exercício",
                "gabinete": {"email": "joao@camara.leg.br"},
                "urlFoto": "https://example.com/photo.jpg",
            },
        )

        mock_class, _ = _mock_camara_client(obter_deputado=mock_dep)

        with patch("agents.parlamentar.tools.camara_tools.CamaraClient", mock_class):
            from agents.parlamentar.tools.camara_tools import obter_perfil_deputado

            result = await obter_perfil_deputado(100)

            assert result["status"] == "success"
            assert result["deputado"]["nome_civil"] == "João da Silva"
            assert result["deputado"]["partido"] == "PT"

    @pytest.mark.asyncio
    async def test_buscar_eventos_pauta_success(self):
        mock_eventos = [
            MagicMock(
                id=1, dataHoraInicio="2024-03-01T10:00:00",
                descricao="Sessão Plenária", situacao="Convocada",
                descricaoTipo="Sessão Deliberativa",
            ),
        ]

        mock_class, _ = _mock_camara_client(listar_eventos=mock_eventos)

        with patch("agents.parlamentar.tools.camara_tools.CamaraClient", mock_class):
            from agents.parlamentar.tools.camara_tools import buscar_eventos_pauta

            result = await buscar_eventos_pauta(dias=7)

            assert result["status"] == "success"
            assert len(result["eventos"]) == 1
            assert result["eventos"][0]["tipo"] == "Sessão Deliberativa"


# ---------------------------------------------------------------------------
# FunctionTools Tests — DB Tools
# ---------------------------------------------------------------------------

class TestDBTools:
    """Test database tools with mocked services."""

    @pytest.mark.asyncio
    async def test_consultar_proposicao_local_success(self):
        mock_prop = MagicMock(
            id=1, tipo="PL", numero=123, ano=2024,
            ementa="Teste", situacao="Em tramitação",
            temas=["saúde"], resumo_ia="Resumo de teste",
            data_apresentacao=date(2024, 1, 15),
        )

        mock_sf = MagicMock()
        mock_session = AsyncMock()
        mock_sf.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_sf.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch("agents.parlamentar.tools.db_tools.async_session_factory", mock_sf), \
             patch("agents.parlamentar.tools.db_tools.ProposicaoService") as MockService:
            mock_svc = AsyncMock()
            mock_svc.get_by_id = AsyncMock(return_value=mock_prop)
            MockService.return_value = mock_svc

            from agents.parlamentar.tools.db_tools import consultar_proposicao_local

            result = await consultar_proposicao_local(1)

            assert result["status"] == "success"
            assert result["proposicao"]["resumo_ia"] == "Resumo de teste"

    @pytest.mark.asyncio
    async def test_consultar_proposicao_local_not_found(self):
        mock_sf = MagicMock()
        mock_session = AsyncMock()
        mock_sf.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_sf.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch("agents.parlamentar.tools.db_tools.async_session_factory", mock_sf), \
             patch("agents.parlamentar.tools.db_tools.ProposicaoService") as MockService:
            from app.exceptions import NotFoundException

            mock_svc = AsyncMock()
            mock_svc.get_by_id = AsyncMock(side_effect=NotFoundException())
            MockService.return_value = mock_svc

            from agents.parlamentar.tools.db_tools import consultar_proposicao_local

            result = await consultar_proposicao_local(999)

            assert result["status"] == "not_found"

    @pytest.mark.asyncio
    async def test_obter_analise_ia_success(self):
        mock_analise = MagicMock(
            resumo_leigo="Resumo acessível",
            impacto_esperado="Grande impacto",
            areas_afetadas=["saúde", "educação"],
            argumentos_favor=["arg1"],
            argumentos_contra=["arg2"],
            provedor_llm="gemini",
            modelo="gemini-2.0-flash",
            versao=1,
            data_geracao=datetime(2024, 3, 1, tzinfo=timezone.utc),
        )

        mock_sf = MagicMock()
        mock_session = AsyncMock()
        mock_sf.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_sf.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch("agents.parlamentar.tools.db_tools.async_session_factory", mock_sf), \
             patch("agents.parlamentar.tools.db_tools.AnaliseIAService") as MockService:
            mock_svc = AsyncMock()
            mock_svc.get_latest = AsyncMock(return_value=mock_analise)
            MockService.return_value = mock_svc

            from agents.parlamentar.tools.db_tools import obter_analise_ia

            result = await obter_analise_ia(1)

            assert result["status"] == "success"
            assert result["analise"]["resumo_leigo"] == "Resumo acessível"
            assert result["analise"]["areas_afetadas"] == ["saúde", "educação"]

    @pytest.mark.asyncio
    async def test_obter_analise_ia_not_found(self):
        mock_sf = MagicMock()
        mock_session = AsyncMock()
        mock_sf.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_sf.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch("agents.parlamentar.tools.db_tools.async_session_factory", mock_sf), \
             patch("agents.parlamentar.tools.db_tools.AnaliseIAService") as MockService:
            mock_svc = AsyncMock()
            mock_svc.get_latest = AsyncMock(return_value=None)
            MockService.return_value = mock_svc

            from agents.parlamentar.tools.db_tools import obter_analise_ia

            result = await obter_analise_ia(999)

            assert result["status"] == "not_found"

    @pytest.mark.asyncio
    async def test_consultar_perfil_eleitor_found(self):
        mock_eleitor = MagicMock(
            id=uuid.uuid4(), nome="João Silva", uf="SP",
            verificado=True, temas_interesse=["saúde"], channel="telegram",
        )

        mock_sf = MagicMock()
        mock_session = AsyncMock()
        mock_sf.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_sf.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch("agents.parlamentar.tools.db_tools.async_session_factory", mock_sf), \
             patch("agents.parlamentar.tools.db_tools.EleitorService") as MockService:
            mock_svc = AsyncMock()
            mock_svc.get_by_chat_id = AsyncMock(return_value=mock_eleitor)
            MockService.return_value = mock_svc

            from agents.parlamentar.tools.db_tools import consultar_perfil_eleitor

            result = await consultar_perfil_eleitor("123456")

            assert result["status"] == "success"
            assert result["eleitor"]["nome"] == "João Silva"

    @pytest.mark.asyncio
    async def test_consultar_perfil_eleitor_not_found(self):
        mock_sf = MagicMock()
        mock_session = AsyncMock()
        mock_sf.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_sf.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch("agents.parlamentar.tools.db_tools.async_session_factory", mock_sf), \
             patch("agents.parlamentar.tools.db_tools.EleitorService") as MockService:
            mock_svc = AsyncMock()
            mock_svc.get_by_chat_id = AsyncMock(return_value=None)
            MockService.return_value = mock_svc

            from agents.parlamentar.tools.db_tools import consultar_perfil_eleitor

            result = await consultar_perfil_eleitor("unknown")

            assert result["status"] == "not_found"

    @pytest.mark.asyncio
    async def test_cadastrar_eleitor_invalid_uf(self):
        from agents.parlamentar.tools.db_tools import cadastrar_eleitor

        result = await cadastrar_eleitor("123", "João", "XX")

        assert result["status"] == "error"
        assert "UF inválida" in result["error"]

    @pytest.mark.asyncio
    async def test_cadastrar_eleitor_success(self):
        mock_eleitor = MagicMock(id=uuid.uuid4(), nome="", uf="XX", verificado=False)
        mock_updated = MagicMock(id=mock_eleitor.id, nome="João", uf="SP", verificado=False)

        mock_sf = MagicMock()
        mock_session = AsyncMock()
        mock_sf.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_sf.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch("agents.parlamentar.tools.db_tools.async_session_factory", mock_sf), \
             patch("agents.parlamentar.tools.db_tools.EleitorService") as MockService:
            mock_svc = AsyncMock()
            mock_svc.get_or_create_by_chat_id = AsyncMock(return_value=(mock_eleitor, True))
            mock_svc.update_profile = AsyncMock(return_value=mock_updated)
            MockService.return_value = mock_svc

            from agents.parlamentar.tools.db_tools import cadastrar_eleitor

            result = await cadastrar_eleitor("123", "João", "SP")

            assert result["status"] == "success"
            assert "realizado" in result["message"].lower() or "Cadastro" in result["message"]
            assert result["eleitor"]["nome"] == "João"

    @pytest.mark.asyncio
    async def test_listar_proposicoes_local_success(self):
        mock_props = [
            MagicMock(id=1, tipo="PL", numero=100, ano=2024, ementa="Teste", resumo_ia="Resumo"),
        ]

        mock_sf = MagicMock()
        mock_session = AsyncMock()
        mock_sf.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_sf.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch("agents.parlamentar.tools.db_tools.async_session_factory", mock_sf), \
             patch("agents.parlamentar.tools.db_tools.ProposicaoService") as MockService:
            mock_svc = AsyncMock()
            mock_svc.list_proposicoes = AsyncMock(return_value=mock_props)
            MockService.return_value = mock_svc

            from agents.parlamentar.tools.db_tools import listar_proposicoes_local

            result = await listar_proposicoes_local(tema="saúde")

            assert result["status"] == "success"
            assert len(result["proposicoes"]) == 1

    @pytest.mark.asyncio
    async def test_atualizar_temas_interesse_success(self):
        mock_eleitor = MagicMock(id=uuid.uuid4())

        mock_sf = MagicMock()
        mock_session = AsyncMock()
        mock_sf.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_sf.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch("agents.parlamentar.tools.db_tools.async_session_factory", mock_sf), \
             patch("agents.parlamentar.tools.db_tools.EleitorService") as MockService:
            mock_svc = AsyncMock()
            mock_svc.get_by_chat_id = AsyncMock(return_value=mock_eleitor)
            mock_svc.update_profile = AsyncMock(return_value=mock_eleitor)
            MockService.return_value = mock_svc

            from agents.parlamentar.tools.db_tools import atualizar_temas_interesse

            result = await atualizar_temas_interesse("123", "saúde, educação, economia")

            assert result["status"] == "success"
            assert "saúde" in result["temas"]
            assert len(result["temas"]) == 3

    @pytest.mark.asyncio
    async def test_atualizar_temas_interesse_not_registered(self):
        mock_sf = MagicMock()
        mock_session = AsyncMock()
        mock_sf.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_sf.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch("agents.parlamentar.tools.db_tools.async_session_factory", mock_sf), \
             patch("agents.parlamentar.tools.db_tools.EleitorService") as MockService:
            mock_svc = AsyncMock()
            mock_svc.get_by_chat_id = AsyncMock(return_value=None)
            MockService.return_value = mock_svc

            from agents.parlamentar.tools.db_tools import atualizar_temas_interesse

            result = await atualizar_temas_interesse("unknown", "saúde")

            assert result["status"] == "not_found"


# ---------------------------------------------------------------------------
# FunctionTools Tests — Votação Tools
# ---------------------------------------------------------------------------

class TestVotacaoTools:
    """Test popular voting tools."""

    @pytest.mark.asyncio
    async def test_registrar_voto_invalid_option(self):
        from agents.parlamentar.tools.votacao_tools import registrar_voto

        result = await registrar_voto("123", 1, "TALVEZ")

        assert result["status"] == "error"
        assert "inválido" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_registrar_voto_not_registered(self):
        mock_sf = MagicMock()
        mock_session = AsyncMock()
        mock_sf.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_sf.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch("agents.parlamentar.tools.votacao_tools.async_session_factory", mock_sf), \
             patch("agents.parlamentar.tools.votacao_tools.EleitorService") as MockEleitor:
            mock_svc = AsyncMock()
            mock_svc.get_by_chat_id = AsyncMock(return_value=None)
            MockEleitor.return_value = mock_svc

            from agents.parlamentar.tools.votacao_tools import registrar_voto

            result = await registrar_voto("unknown", 1, "SIM")

            assert result["status"] == "error"
            assert "cadastrar" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_registrar_voto_success(self):
        mock_eleitor = MagicMock(id=uuid.uuid4(), nome="João", verificado=True)
        mock_voto = MagicMock(data_voto=datetime(2024, 3, 1, tzinfo=timezone.utc))

        mock_sf = MagicMock()
        mock_session = AsyncMock()
        mock_sf.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_sf.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch("agents.parlamentar.tools.votacao_tools.async_session_factory", mock_sf), \
             patch("agents.parlamentar.tools.votacao_tools.EleitorService") as MockEleitor, \
             patch("agents.parlamentar.tools.votacao_tools.VotoPopularService") as MockVoto:
            eleitor_svc = AsyncMock()
            eleitor_svc.get_by_chat_id = AsyncMock(return_value=mock_eleitor)
            MockEleitor.return_value = eleitor_svc

            voto_svc = AsyncMock()
            voto_svc.registrar_voto = AsyncMock(return_value=mock_voto)
            MockVoto.return_value = voto_svc

            from agents.parlamentar.tools.votacao_tools import registrar_voto

            result = await registrar_voto("123", 1234, "SIM")

            assert result["status"] == "success"
            assert "SIM" in result["message"]
            assert result["voto"]["proposicao_id"] == 1234

    @pytest.mark.asyncio
    async def test_obter_resultado_votacao_success(self):
        mock_resultado = {
            "total": 100, "SIM": 73, "NAO": 21, "ABSTENCAO": 6,
            "percentual_sim": 73.0, "percentual_nao": 21.0, "percentual_abstencao": 6.0,
        }

        mock_sf = MagicMock()
        mock_session = AsyncMock()
        mock_sf.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_sf.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch("agents.parlamentar.tools.votacao_tools.async_session_factory", mock_sf), \
             patch("agents.parlamentar.tools.votacao_tools.VotoPopularService") as MockService:
            mock_svc = AsyncMock()
            mock_svc.obter_resultado = AsyncMock(return_value=mock_resultado)
            MockService.return_value = mock_svc

            from agents.parlamentar.tools.votacao_tools import obter_resultado_votacao

            result = await obter_resultado_votacao(1234)

            assert result["status"] == "success"
            assert result["resultado"]["total_votos"] == 100
            assert result["resultado"]["percentual_sim"] == 73.0

    @pytest.mark.asyncio
    async def test_consultar_meu_voto_success(self):
        mock_eleitor = MagicMock(id=uuid.uuid4())
        mock_voto = MagicMock(
            voto=MagicMock(value="SIM"),
            data_voto=datetime(2024, 3, 1, tzinfo=timezone.utc),
            justificativa="Concordo com a proposta",
        )

        mock_sf = MagicMock()
        mock_session = AsyncMock()
        mock_sf.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_sf.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch("agents.parlamentar.tools.votacao_tools.async_session_factory", mock_sf), \
             patch("agents.parlamentar.tools.votacao_tools.EleitorService") as MockEleitor, \
             patch("agents.parlamentar.tools.votacao_tools.VotoPopularService") as MockVoto:
            eleitor_svc = AsyncMock()
            eleitor_svc.get_by_chat_id = AsyncMock(return_value=mock_eleitor)
            MockEleitor.return_value = eleitor_svc

            voto_svc = AsyncMock()
            voto_svc.get_voto = AsyncMock(return_value=mock_voto)
            MockVoto.return_value = voto_svc

            from agents.parlamentar.tools.votacao_tools import consultar_meu_voto

            result = await consultar_meu_voto("123", 1234)

            assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_historico_votos_eleitor_success(self):
        mock_eleitor = MagicMock(id=uuid.uuid4())
        mock_votos = [
            MagicMock(
                proposicao_id=1,
                voto=MagicMock(value="SIM"),
                data_voto=datetime(2024, 3, 1, tzinfo=timezone.utc),
            ),
        ]

        mock_sf = MagicMock()
        mock_session = AsyncMock()
        mock_sf.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_sf.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch("agents.parlamentar.tools.votacao_tools.async_session_factory", mock_sf), \
             patch("agents.parlamentar.tools.votacao_tools.EleitorService") as MockEleitor, \
             patch("agents.parlamentar.tools.votacao_tools.VotoPopularService") as MockVoto:
            eleitor_svc = AsyncMock()
            eleitor_svc.get_by_chat_id = AsyncMock(return_value=mock_eleitor)
            MockEleitor.return_value = eleitor_svc

            voto_svc = AsyncMock()
            voto_svc.list_by_eleitor = AsyncMock(return_value=mock_votos)
            MockVoto.return_value = voto_svc

            from agents.parlamentar.tools.votacao_tools import historico_votos_eleitor

            result = await historico_votos_eleitor("123")

            assert result["status"] == "success"
            assert len(result["votos"]) == 1


# ---------------------------------------------------------------------------
# FunctionTools Tests — Publicacao Tools
# ---------------------------------------------------------------------------

class TestPublicacaoTools:
    """Test publication and comparative tools."""

    @pytest.mark.asyncio
    async def test_obter_comparativo_not_found(self):
        mock_sf = MagicMock()
        mock_session = AsyncMock()
        mock_sf.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_sf.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch("agents.parlamentar.tools.publicacao_tools.async_session_factory", mock_sf), \
             patch("agents.parlamentar.tools.publicacao_tools.ComparativoService") as MockService:
            mock_svc = AsyncMock()
            mock_svc.get_by_proposicao = AsyncMock(return_value=None)
            MockService.return_value = mock_svc

            from agents.parlamentar.tools.publicacao_tools import obter_comparativo

            result = await obter_comparativo(999)

            assert result["status"] == "not_found"

    @pytest.mark.asyncio
    async def test_obter_comparativo_success(self):
        mock_comp = MagicMock(
            proposicao_id=1234,
            voto_popular_sim=73, voto_popular_nao=21, voto_popular_abstencao=6,
            resultado_camara="APROVADO",
            votos_camara_sim=300, votos_camara_nao=150,
            alinhamento=0.95,
            resumo_ia="Resumo do comparativo",
            data_geracao=datetime(2024, 3, 1, tzinfo=timezone.utc),
        )

        mock_sf = MagicMock()
        mock_session = AsyncMock()
        mock_sf.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_sf.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch("agents.parlamentar.tools.publicacao_tools.async_session_factory", mock_sf), \
             patch("agents.parlamentar.tools.publicacao_tools.ComparativoService") as MockService:
            mock_svc = AsyncMock()
            mock_svc.get_by_proposicao = AsyncMock(return_value=mock_comp)
            MockService.return_value = mock_svc

            from agents.parlamentar.tools.publicacao_tools import obter_comparativo

            result = await obter_comparativo(1234)

            assert result["status"] == "success"
            assert result["comparativo"]["alinhamento"] == 95.0

    @pytest.mark.asyncio
    async def test_status_publicacao(self):
        from agents.parlamentar.tools.publicacao_tools import status_publicacao

        result = await status_publicacao()

        assert result["status"] == "success"
        assert "rss_feed" in result["publicacao"]
        assert "webhooks" in result["publicacao"]
        assert "voto_consolidado" in result["publicacao"]["webhooks"]["eventos"]


# ---------------------------------------------------------------------------
# FunctionTools Tests — Notification Tools
# ---------------------------------------------------------------------------

class TestNotificationTools:
    """Test notification management tools."""

    @pytest.mark.asyncio
    async def test_verificar_notificacoes_not_registered(self):
        mock_sf = MagicMock()
        mock_session = AsyncMock()
        mock_sf.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_sf.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch("app.db.session.async_session_factory", mock_sf), \
             patch("app.services.eleitor_service.EleitorService") as MockService:
            mock_svc = AsyncMock()
            mock_svc.get_by_chat_id = AsyncMock(return_value=None)
            MockService.return_value = mock_svc

            from agents.parlamentar.tools.notification_tools import verificar_notificacoes

            result = await verificar_notificacoes("unknown")

            assert result["status"] == "not_found"

    @pytest.mark.asyncio
    async def test_verificar_notificacoes_with_temas(self):
        mock_eleitor = MagicMock(temas_interesse=["saúde", "educação"])

        mock_sf = MagicMock()
        mock_session = AsyncMock()
        mock_sf.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_sf.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch("app.db.session.async_session_factory", mock_sf), \
             patch("app.services.eleitor_service.EleitorService") as MockService:
            mock_svc = AsyncMock()
            mock_svc.get_by_chat_id = AsyncMock(return_value=mock_eleitor)
            MockService.return_value = mock_svc

            from agents.parlamentar.tools.notification_tools import verificar_notificacoes

            result = await verificar_notificacoes("123")

            assert result["status"] == "success"
            assert result["notificacoes"]["ativas"] is True
            assert "saúde" in result["notificacoes"]["temas"]

    @pytest.mark.asyncio
    async def test_verificar_notificacoes_no_temas(self):
        mock_eleitor = MagicMock(temas_interesse=[])

        mock_sf = MagicMock()
        mock_session = AsyncMock()
        mock_sf.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_sf.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch("app.db.session.async_session_factory", mock_sf), \
             patch("app.services.eleitor_service.EleitorService") as MockService:
            mock_svc = AsyncMock()
            mock_svc.get_by_chat_id = AsyncMock(return_value=mock_eleitor)
            MockService.return_value = mock_svc

            from agents.parlamentar.tools.notification_tools import verificar_notificacoes

            result = await verificar_notificacoes("123")

            assert result["status"] == "success"
            assert result["notificacoes"]["ativas"] is False


# ---------------------------------------------------------------------------
# Runner Module Tests
# ---------------------------------------------------------------------------

class TestRunnerModule:
    """Test the runner integration module."""

    def test_app_name_constant(self):
        from agents.parlamentar.runner import APP_NAME

        assert APP_NAME == "parlamentaria"

    def test_get_session_service_returns_inmemory_for_dev(self):
        from agents.parlamentar import runner as runner_mod
        from google.adk.sessions import InMemorySessionService

        runner_mod._session_service = None
        runner_mod._runner = None

        mock_settings = MagicMock()
        mock_settings.is_production = False
        mock_settings.database_url = "sqlite+aiosqlite:///test.db"

        with patch("agents.parlamentar.runner.settings", mock_settings):
            service = runner_mod.get_session_service()
            assert isinstance(service, InMemorySessionService)

        runner_mod._session_service = None

    def test_get_session_service_singleton(self):
        from agents.parlamentar import runner as runner_mod

        runner_mod._session_service = None
        runner_mod._runner = None

        mock_settings = MagicMock()
        mock_settings.is_production = False

        with patch("agents.parlamentar.runner.settings", mock_settings):
            svc1 = runner_mod.get_session_service()
            svc2 = runner_mod.get_session_service()
            assert svc1 is svc2

        runner_mod._session_service = None

    def test_get_runner_creates_runner(self):
        from agents.parlamentar import runner as runner_mod
        from google.adk.runners import Runner

        runner_mod._session_service = None
        runner_mod._runner = None

        mock_settings = MagicMock()
        mock_settings.is_production = False

        with patch("agents.parlamentar.runner.settings", mock_settings):
            r = runner_mod.get_runner()
            assert isinstance(r, Runner)

        runner_mod._session_service = None
        runner_mod._runner = None

    def test_get_runner_singleton(self):
        from agents.parlamentar import runner as runner_mod

        runner_mod._session_service = None
        runner_mod._runner = None

        mock_settings = MagicMock()
        mock_settings.is_production = False

        with patch("agents.parlamentar.runner.settings", mock_settings):
            r1 = runner_mod.get_runner()
            r2 = runner_mod.get_runner()
            assert r1 is r2

        runner_mod._session_service = None
        runner_mod._runner = None
