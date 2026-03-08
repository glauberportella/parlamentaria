"""Tests for the listar_temas feature.

Covers:
- CamaraClient.listar_temas_referencia()
- ProposicaoRepository.listar_temas_distintos()
- FunctionTool listar_temas_disponiveis()
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.integrations.camara_types import ReferenciaAPI


# ---------------------------------------------------------------------------
# CamaraClient.listar_temas_referencia
# ---------------------------------------------------------------------------


class TestCamaraClientListarTemasReferencia:
    """Test the listar_temas_referencia method of CamaraClient."""

    async def test_listar_temas_referencia_returns_list(self):
        """Should parse API response into list of ReferenciaAPI."""
        from app.integrations.camara_client import CamaraClient

        fake_response = [
            {"cod": "40", "sigla": None, "nome": "Educação", "descricao": "Temas de educação"},
            {"cod": "46", "sigla": None, "nome": "Saúde", "descricao": "Temas de saúde"},
            {"cod": "34", "sigla": None, "nome": "Economia", "descricao": "Temas econômicos"},
        ]

        client = CamaraClient()
        client._get_dados = AsyncMock(return_value=fake_response)

        result = await client.listar_temas_referencia()

        assert len(result) == 3
        assert all(isinstance(r, ReferenciaAPI) for r in result)
        assert result[0].cod == "40"
        assert result[0].nome == "Educação"
        assert result[1].nome == "Saúde"
        client._get_dados.assert_called_once_with("/referencias/proposicoes/codTema")

    async def test_listar_temas_referencia_empty(self):
        """Should return empty list when API returns no data."""
        from app.integrations.camara_client import CamaraClient

        client = CamaraClient()
        client._get_dados = AsyncMock(return_value=[])

        result = await client.listar_temas_referencia()

        assert result == []

    async def test_listar_temas_referencia_partial_fields(self):
        """Should handle items with missing optional fields."""
        from app.integrations.camara_client import CamaraClient

        fake_response = [
            {"cod": "40", "nome": "Educação"},
        ]

        client = CamaraClient()
        client._get_dados = AsyncMock(return_value=fake_response)

        result = await client.listar_temas_referencia()

        assert len(result) == 1
        assert result[0].cod == "40"
        assert result[0].nome == "Educação"
        assert result[0].sigla is None
        assert result[0].descricao is None


# ---------------------------------------------------------------------------
# ProposicaoRepository.listar_temas_distintos
# ---------------------------------------------------------------------------


class TestProposicaoRepositoryListarTemasDistintos:
    """Test the listar_temas_distintos method.

    Since tests use SQLite (which lacks PostgreSQL unnest()),
    we mock the session.execute to simulate the query result.
    """

    async def test_listar_temas_distintos_returns_sorted_unique(self):
        """Should return sorted unique theme names."""
        from app.repositories.proposicao import ProposicaoRepository

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = [
            ("Economia",),
            ("Educação",),
            ("Saúde",),
            ("Transparência",),
        ]
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = ProposicaoRepository(mock_session)
        result = await repo.listar_temas_distintos()

        assert result == ["Economia", "Educação", "Saúde", "Transparência"]
        mock_session.execute.assert_called_once()

    async def test_listar_temas_distintos_empty(self):
        """Should return empty list when no themes exist."""
        from app.repositories.proposicao import ProposicaoRepository

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = ProposicaoRepository(mock_session)
        result = await repo.listar_temas_distintos()

        assert result == []

    async def test_listar_temas_distintos_single_theme(self):
        """Should handle single theme."""
        from app.repositories.proposicao import ProposicaoRepository

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = [("Saúde",)]
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = ProposicaoRepository(mock_session)
        result = await repo.listar_temas_distintos()

        assert result == ["Saúde"]


# ---------------------------------------------------------------------------
# FunctionTool listar_temas_disponiveis
# ---------------------------------------------------------------------------


class TestListarTemasDisponiveisTool:
    """Test the listar_temas_disponiveis FunctionTool."""

    @patch("agents.parlamentar.tools.db_tools.async_session_factory")
    async def test_basic_local_themes(self, mock_factory):
        """Should return local themes without official reference."""
        from agents.parlamentar.tools.db_tools import listar_temas_disponiveis

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = [
            ("Economia",),
            ("Educação",),
            ("Saúde",),
        ]
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await listar_temas_disponiveis()

        assert result["status"] == "success"
        assert result["total"] == 3
        assert "Economia" in result["temas_disponiveis"]
        assert "Educação" in result["temas_disponiveis"]
        assert "Saúde" in result["temas_disponiveis"]
        assert "temas_oficiais" not in result

    @patch("agents.parlamentar.tools.db_tools.async_session_factory")
    async def test_empty_themes(self, mock_factory):
        """Should return empty list when no themes exist locally."""
        from agents.parlamentar.tools.db_tools import listar_temas_disponiveis

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await listar_temas_disponiveis()

        assert result["status"] == "success"
        assert result["total"] == 0
        assert result["temas_disponiveis"] == []

    @patch("agents.parlamentar.tools.db_tools.CamaraClient", create=True)
    @patch("agents.parlamentar.tools.db_tools.async_session_factory")
    async def test_with_official_reference(self, mock_factory, mock_client_cls):
        """Should include official themes when incluir_referencia_oficial=True."""
        from agents.parlamentar.tools.db_tools import listar_temas_disponiveis

        # Mock local DB
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = [
            ("Economia",),
            ("Saúde",),
        ]
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        # Mock CamaraClient
        mock_client_instance = AsyncMock()
        mock_client_instance.listar_temas_referencia = AsyncMock(return_value=[
            ReferenciaAPI(cod="40", nome="Educação"),
            ReferenciaAPI(cod="46", nome="Saúde"),
            ReferenciaAPI(cod="34", nome="Economia"),
        ])

        # Patch the import inside the function
        with patch(
            "app.integrations.camara_client.CamaraClient"
        ) as patched_client:
            patched_client.return_value.__aenter__ = AsyncMock(
                return_value=mock_client_instance
            )
            patched_client.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await listar_temas_disponiveis(incluir_referencia_oficial=True)

        assert result["status"] == "success"
        assert result["total"] == 2
        assert "Economia" in result["temas_disponiveis"]
        assert "Saúde" in result["temas_disponiveis"]
        assert "temas_oficiais" in result
        assert result["total_oficiais"] == 3

    @patch("agents.parlamentar.tools.db_tools.async_session_factory")
    async def test_official_reference_failure_graceful(self, mock_factory):
        """Should still work if official reference API fails."""
        from agents.parlamentar.tools.db_tools import listar_temas_disponiveis

        # Mock local DB
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = [("Saúde",)]
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        # Mock CamaraClient to raise an error
        with patch(
            "app.integrations.camara_client.CamaraClient"
        ) as patched_client:
            patched_client.return_value.__aenter__ = AsyncMock(
                side_effect=Exception("Connection error")
            )

            result = await listar_temas_disponiveis(incluir_referencia_oficial=True)

        assert result["status"] == "success"
        assert result["total"] == 1
        assert "Saúde" in result["temas_disponiveis"]
        assert "temas_oficiais_erro" in result

    @patch("agents.parlamentar.tools.db_tools.async_session_factory")
    async def test_db_error_returns_friendly_message(self, mock_factory):
        """Should return user-friendly error when DB fails."""
        from agents.parlamentar.tools.db_tools import listar_temas_disponiveis

        mock_factory.return_value.__aenter__ = AsyncMock(
            side_effect=Exception("DB connection failed")
        )

        result = await listar_temas_disponiveis()

        assert result["status"] == "error"
        assert "Não foi possível listar os temas" in result["error"]
        # Should NOT expose raw exception message
        assert "DB connection failed" not in result["error"]

    @patch("agents.parlamentar.tools.db_tools.async_session_factory")
    async def test_result_has_description(self, mock_factory):
        """Should include a helpful description for the agent."""
        from agents.parlamentar.tools.db_tools import listar_temas_disponiveis

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = [("Saúde",)]
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await listar_temas_disponiveis()

        assert "descricao" in result
        assert "temas" in result["descricao"].lower()

    @patch("agents.parlamentar.tools.db_tools.async_session_factory")
    async def test_default_no_official(self, mock_factory):
        """Default call should NOT include official themes."""
        from agents.parlamentar.tools.db_tools import listar_temas_disponiveis

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = [("Economia",)]
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await listar_temas_disponiveis(incluir_referencia_oficial=False)

        assert "temas_oficiais" not in result
        assert "total_oficiais" not in result


# ---------------------------------------------------------------------------
# ProposicaoAgent tools registration
# ---------------------------------------------------------------------------


class TestProposicaoAgentToolRegistration:
    """Verify the new tool is registered in ProposicaoAgent."""

    def test_listar_temas_in_agent_tools(self):
        """ProposicaoAgent should have listar_temas_disponiveis in tools."""
        from agents.parlamentar.sub_agents.proposicao_agent import proposicao_agent

        tool_names = []
        for tool in proposicao_agent.tools:
            if callable(tool):
                tool_names.append(tool.__name__)
            elif hasattr(tool, "name"):
                tool_names.append(tool.name)

        assert "listar_temas_disponiveis" in tool_names
