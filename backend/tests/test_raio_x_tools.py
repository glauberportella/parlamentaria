"""Tests for Raio-X do Deputado tool functions."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.integrations.camara_types import (
    DeputadoDetalhadoAPI,
    OrgaoDeputadoAPI,
    FrenteAPI,
    ProfissaoAPI,
    EventoDeputadoAPI,
)


# ---------------------------------------------------------------------------
# Fixtures / Helpers
# ---------------------------------------------------------------------------

def _make_orgaos() -> list[OrgaoDeputadoAPI]:
    return [
        OrgaoDeputadoAPI(
            idOrgao=1,
            siglaOrgao="CCJC",
            nomeOrgao="Comissão de Constituição e Justiça",
            titulo="Titular",
            dataInicio="2023-02-01",
            dataFim=None,
        ),
        OrgaoDeputadoAPI(
            idOrgao=2,
            siglaOrgao="CEDU",
            nomeOrgao="Comissão de Educação",
            titulo="Suplente",
            dataInicio="2023-03-01",
            dataFim="2024-01-01",
        ),
    ]


def _make_frentes() -> list[FrenteAPI]:
    return [
        FrenteAPI(id=10, titulo="Frente Parlamentar da Educação"),
        FrenteAPI(id=20, titulo="Frente Parlamentar do Meio Ambiente"),
    ]


def _make_profissoes() -> list[ProfissaoAPI]:
    return [ProfissaoAPI(titulo="Advogado"), ProfissaoAPI(titulo="Professor")]


def _make_eventos() -> list[EventoDeputadoAPI]:
    return [
        EventoDeputadoAPI(
            id=100,
            dataHoraInicio="2024-03-01T10:00:00",
            descricaoTipo="Sessão Deliberativa",
            descricao="Sessão ordinária",
        ),
        EventoDeputadoAPI(
            id=101,
            dataHoraInicio="2024-03-02T14:00:00",
            descricaoTipo="Audiência Pública",
            descricao="Audiência sobre educação",
        ),
        EventoDeputadoAPI(
            id=102,
            dataHoraInicio="2024-03-03T09:00:00",
            descricaoTipo="Sessão Deliberativa",
            descricao="Sessão extraordinária",
        ),
    ]


def _make_perfil() -> DeputadoDetalhadoAPI:
    return DeputadoDetalhadoAPI(
        id=123,
        nomeCivil="João da Silva",
        dataNascimento="1970-05-15",
        ultimoStatus={
            "nomeEleitoral": "João Silva",
            "siglaPartido": "PT",
            "siglaUf": "SP",
            "situacao": "Exercício",
            "urlFoto": "https://example.com/foto.jpg",
            "gabinete": {"email": "joao@camara.leg.br"},
        },
    )


# ---------------------------------------------------------------------------
# Tests: obter_comissoes_deputado
# ---------------------------------------------------------------------------

class TestObterComissoesDeputado:

    async def test_success(self):
        from agents.parlamentar.tools.camara_tools import obter_comissoes_deputado

        mock_client = AsyncMock()
        mock_client.obter_orgaos_deputado = AsyncMock(return_value=_make_orgaos())
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("agents.parlamentar.tools.camara_tools.CamaraClient", return_value=mock_client):
            result = await obter_comissoes_deputado(deputado_id=123)

        assert result["status"] == "success"
        assert result["total"] == 2
        assert result["comissoes"][0]["sigla"] == "CCJC"
        assert result["comissoes"][0]["cargo"] == "Titular"
        assert result["comissoes"][1]["cargo"] == "Suplente"

    async def test_empty_result(self):
        from agents.parlamentar.tools.camara_tools import obter_comissoes_deputado

        mock_client = AsyncMock()
        mock_client.obter_orgaos_deputado = AsyncMock(return_value=[])
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("agents.parlamentar.tools.camara_tools.CamaraClient", return_value=mock_client):
            result = await obter_comissoes_deputado(deputado_id=999)

        assert result["status"] == "success"
        assert result["total"] == 0
        assert result["comissoes"] == []

    async def test_error_returns_friendly_message(self):
        from agents.parlamentar.tools.camara_tools import obter_comissoes_deputado

        mock_client = AsyncMock()
        mock_client.obter_orgaos_deputado = AsyncMock(side_effect=Exception("API error"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("agents.parlamentar.tools.camara_tools.CamaraClient", return_value=mock_client):
            result = await obter_comissoes_deputado(deputado_id=123)

        assert result["status"] == "error"
        assert "comissões" in result["error"].lower()
        # Should NOT expose raw exception message
        assert "API error" not in result["error"]


# ---------------------------------------------------------------------------
# Tests: obter_frentes_deputado
# ---------------------------------------------------------------------------

class TestObterFrentesDeputado:

    async def test_success(self):
        from agents.parlamentar.tools.camara_tools import obter_frentes_deputado

        mock_client = AsyncMock()
        mock_client.obter_frentes_deputado = AsyncMock(return_value=_make_frentes())
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("agents.parlamentar.tools.camara_tools.CamaraClient", return_value=mock_client):
            result = await obter_frentes_deputado(deputado_id=123)

        assert result["status"] == "success"
        assert result["total"] == 2
        assert result["frentes"][0]["titulo"] == "Frente Parlamentar da Educação"

    async def test_error_returns_friendly_message(self):
        from agents.parlamentar.tools.camara_tools import obter_frentes_deputado

        mock_client = AsyncMock()
        mock_client.obter_frentes_deputado = AsyncMock(side_effect=Exception("timeout"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("agents.parlamentar.tools.camara_tools.CamaraClient", return_value=mock_client):
            result = await obter_frentes_deputado(deputado_id=123)

        assert result["status"] == "error"
        assert "frentes" in result["error"].lower()


# ---------------------------------------------------------------------------
# Tests: obter_presenca_deputado
# ---------------------------------------------------------------------------

class TestObterPresencaDeputado:

    async def test_success(self):
        from agents.parlamentar.tools.camara_tools import obter_presenca_deputado

        mock_client = AsyncMock()
        mock_client.obter_eventos_deputado = AsyncMock(return_value=_make_eventos())
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("agents.parlamentar.tools.camara_tools.CamaraClient", return_value=mock_client):
            result = await obter_presenca_deputado(deputado_id=123, dias=30)

        assert result["status"] == "success"
        assert result["total_eventos"] == 3
        assert "Sessão Deliberativa" in result["por_tipo"]
        assert result["por_tipo"]["Sessão Deliberativa"] == 2
        assert result["por_tipo"]["Audiência Pública"] == 1
        assert len(result["ultimos_eventos"]) == 3

    async def test_caps_dias_at_90(self):
        from agents.parlamentar.tools.camara_tools import obter_presenca_deputado

        mock_client = AsyncMock()
        mock_client.obter_eventos_deputado = AsyncMock(return_value=[])
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("agents.parlamentar.tools.camara_tools.CamaraClient", return_value=mock_client):
            result = await obter_presenca_deputado(deputado_id=123, dias=365)

        assert result["status"] == "success"
        # Verify the period is ~90 days, not 365
        periodo = result["periodo"]
        assert " a " in periodo

    async def test_error_returns_friendly_message(self):
        from agents.parlamentar.tools.camara_tools import obter_presenca_deputado

        mock_client = AsyncMock()
        mock_client.obter_eventos_deputado = AsyncMock(side_effect=Exception("fail"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("agents.parlamentar.tools.camara_tools.CamaraClient", return_value=mock_client):
            result = await obter_presenca_deputado(deputado_id=123)

        assert result["status"] == "error"
        assert "presença" in result["error"].lower()


# ---------------------------------------------------------------------------
# Tests: obter_raio_x_deputado
# ---------------------------------------------------------------------------

class TestObterRaioXDeputado:

    async def test_success(self):
        from agents.parlamentar.tools.camara_tools import obter_raio_x_deputado

        mock_client = AsyncMock()
        mock_client.obter_deputado = AsyncMock(return_value=_make_perfil())
        mock_client.obter_orgaos_deputado = AsyncMock(return_value=_make_orgaos())
        mock_client.obter_frentes_deputado = AsyncMock(return_value=_make_frentes())
        mock_client.obter_profissoes_deputado = AsyncMock(return_value=_make_profissoes())
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("agents.parlamentar.tools.camara_tools.CamaraClient", return_value=mock_client):
            result = await obter_raio_x_deputado(deputado_id=123)

        assert result["status"] == "success"
        rx = result["raio_x"]
        assert rx["id"] == 123
        assert rx["nome_civil"] == "João da Silva"
        assert rx["nome_parlamentar"] == "João Silva"
        assert rx["partido"] == "PT"
        assert rx["uf"] == "SP"
        assert rx["profissoes"] == ["Advogado", "Professor"]
        assert rx["total_comissoes"] == 2
        assert rx["total_frentes"] == 2
        assert len(rx["comissoes"]) == 2
        assert rx["comissoes"][0]["sigla"] == "CCJC"
        assert rx["frentes_parlamentares"][0] == "Frente Parlamentar da Educação"

    async def test_parallel_requests(self):
        """All 4 client methods should be called (parallel via asyncio.gather)."""
        from agents.parlamentar.tools.camara_tools import obter_raio_x_deputado

        mock_client = AsyncMock()
        mock_client.obter_deputado = AsyncMock(return_value=_make_perfil())
        mock_client.obter_orgaos_deputado = AsyncMock(return_value=[])
        mock_client.obter_frentes_deputado = AsyncMock(return_value=[])
        mock_client.obter_profissoes_deputado = AsyncMock(return_value=[])
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("agents.parlamentar.tools.camara_tools.CamaraClient", return_value=mock_client):
            await obter_raio_x_deputado(deputado_id=123)

        mock_client.obter_deputado.assert_called_once_with(123)
        mock_client.obter_orgaos_deputado.assert_called_once_with(123)
        mock_client.obter_frentes_deputado.assert_called_once_with(123)
        mock_client.obter_profissoes_deputado.assert_called_once_with(123)

    async def test_error_returns_friendly_message(self):
        from agents.parlamentar.tools.camara_tools import obter_raio_x_deputado

        mock_client = AsyncMock()
        mock_client.obter_deputado = AsyncMock(side_effect=Exception("API unreachable"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("agents.parlamentar.tools.camara_tools.CamaraClient", return_value=mock_client):
            result = await obter_raio_x_deputado(deputado_id=123)

        assert result["status"] == "error"
        assert "raio-x" in result["error"].lower() or "raio" in result["error"].lower()
        assert "API unreachable" not in result["error"]

    async def test_limits_comissoes_and_frentes(self):
        """Should cap at 15 comissões and frentes in output."""
        from agents.parlamentar.tools.camara_tools import obter_raio_x_deputado

        many_orgaos = [
            OrgaoDeputadoAPI(idOrgao=i, siglaOrgao=f"C{i}", nomeOrgao=f"Comissão {i}", titulo="Titular")
            for i in range(20)
        ]
        many_frentes = [
            FrenteAPI(id=i, titulo=f"Frente {i}")
            for i in range(20)
        ]

        mock_client = AsyncMock()
        mock_client.obter_deputado = AsyncMock(return_value=_make_perfil())
        mock_client.obter_orgaos_deputado = AsyncMock(return_value=many_orgaos)
        mock_client.obter_frentes_deputado = AsyncMock(return_value=many_frentes)
        mock_client.obter_profissoes_deputado = AsyncMock(return_value=[])
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("agents.parlamentar.tools.camara_tools.CamaraClient", return_value=mock_client):
            result = await obter_raio_x_deputado(deputado_id=123)

        rx = result["raio_x"]
        assert len(rx["comissoes"]) == 15
        assert len(rx["frentes_parlamentares"]) == 15
        assert rx["total_comissoes"] == 20
        assert rx["total_frentes"] == 20


# ---------------------------------------------------------------------------
# Tests: DeputadoAgent has new tools
# ---------------------------------------------------------------------------

class TestDeputadoAgentRaioXTools:

    def test_deputado_agent_has_raio_x_tools(self):
        from agents.parlamentar.sub_agents.deputado_agent import deputado_agent

        tool_names = [t.__name__ if callable(t) else str(t) for t in deputado_agent.tools]
        assert "obter_comissoes_deputado" in tool_names
        assert "obter_frentes_deputado" in tool_names
        assert "obter_presenca_deputado" in tool_names
        assert "obter_raio_x_deputado" in tool_names

    def test_deputado_agent_description_mentions_raio_x(self):
        from agents.parlamentar.sub_agents.deputado_agent import deputado_agent

        desc = deputado_agent.description.lower()
        assert "raio" in desc or "comiss" in desc or "frente" in desc
