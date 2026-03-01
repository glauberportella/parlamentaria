"""Tests for the CamaraClient integration layer."""

import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock

from app.exceptions import ExternalAPIException
from app.integrations.camara_client import CamaraClient
from app.integrations.camara_types import (
    ProposicaoResumoAPI,
    ProposicaoDetalhadaAPI,
    AutorAPI,
    TemaAPI,
    VotacaoResumoAPI,
    VotacaoDetalhadaAPI,
    DeputadoResumoAPI,
    DeputadoDetalhadoAPI,
    EventoResumoAPI,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_response(data: list | dict, status: int = 200) -> httpx.Response:
    """Build a mock httpx.Response."""
    if isinstance(data, list):
        body = {"dados": data, "links": []}
    else:
        body = {"dados": data}
    resp = httpx.Response(status_code=status, json=body)
    return resp


def make_error_response(status: int = 500) -> httpx.Response:
    """Build an error httpx.Response."""
    return httpx.Response(status_code=status, json={"detail": "error"})


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestCamaraClientInit:
    """Test client initialization."""

    async def test_context_manager(self):
        """Client should initialize and close properly."""
        async with CamaraClient() as client:
            assert client._client is not None
        assert client._client is None

    async def test_client_property_raises_without_init(self):
        """Accessing .client without context manager should raise."""
        c = CamaraClient()
        with pytest.raises(RuntimeError, match="not initialized"):
            _ = c.client

    async def test_custom_base_url(self):
        """Should accept a custom base URL."""
        async with CamaraClient(base_url="https://custom.api/v2/") as client:
            assert client._base_url == "https://custom.api/v2"


class TestCamaraClientProposicoes:
    """Test proposition endpoints."""

    async def test_listar_proposicoes(self):
        """Should return list of ProposicaoResumoAPI."""
        async with CamaraClient() as client:
            mock_response = make_response([
                {"id": 1, "siglaTipo": "PL", "codTipo": 139, "numero": 100, "ano": 2024, "ementa": "Teste"},
                {"id": 2, "siglaTipo": "PEC", "codTipo": 136, "numero": 200, "ano": 2024, "ementa": "Outra"},
            ])
            client._client.get = AsyncMock(return_value=mock_response)

            result = await client.listar_proposicoes(ano=2024)
            assert len(result) == 2
            assert isinstance(result[0], ProposicaoResumoAPI)
            assert result[0].siglaTipo == "PL"

    async def test_obter_proposicao(self):
        """Should return ProposicaoDetalhadaAPI."""
        async with CamaraClient() as client:
            mock_response = make_response(
                {"id": 1, "siglaTipo": "PL", "numero": 100, "ano": 2024, "ementa": "Teste"}
            )
            client._client.get = AsyncMock(return_value=mock_response)

            result = await client.obter_proposicao(1)
            assert isinstance(result, ProposicaoDetalhadaAPI)
            assert result.id == 1

    async def test_obter_autores(self):
        """Should return list of AutorAPI."""
        async with CamaraClient() as client:
            mock_response = make_response([
                {"nome": "Autor 1", "tipo": "Deputado"},
            ])
            client._client.get = AsyncMock(return_value=mock_response)

            result = await client.obter_autores(1)
            assert len(result) == 1
            assert isinstance(result[0], AutorAPI)

    async def test_obter_temas(self):
        """Should return list of TemaAPI."""
        async with CamaraClient() as client:
            mock_response = make_response([
                {"codTema": 40, "tema": "Educação"},
            ])
            client._client.get = AsyncMock(return_value=mock_response)

            result = await client.obter_temas(1)
            assert len(result) == 1
            assert result[0].tema == "Educação"


class TestCamaraClientVotacoes:
    """Test vote session endpoints."""

    async def test_listar_votacoes(self):
        """Should return list of VotacaoResumoAPI."""
        async with CamaraClient() as client:
            mock_response = make_response([
                {"id": "v1", "descricao": "Votação 1"},
            ])
            client._client.get = AsyncMock(return_value=mock_response)

            result = await client.listar_votacoes()
            assert len(result) == 1
            assert isinstance(result[0], VotacaoResumoAPI)

    async def test_obter_votacao(self):
        """Should return VotacaoDetalhadaAPI."""
        async with CamaraClient() as client:
            mock_response = make_response(
                {"id": "v1", "descricao": "Votação 1"}
            )
            client._client.get = AsyncMock(return_value=mock_response)

            result = await client.obter_votacao("v1")
            assert isinstance(result, VotacaoDetalhadaAPI)
            assert result.id == "v1"


class TestCamaraClientDeputados:
    """Test deputy endpoints."""

    async def test_listar_deputados(self):
        """Should return list of DeputadoResumoAPI."""
        async with CamaraClient() as client:
            mock_response = make_response([
                {"id": 1, "nome": "Dep. Teste", "siglaPartido": "PT", "siglaUf": "SP"},
            ])
            client._client.get = AsyncMock(return_value=mock_response)

            result = await client.listar_deputados(sigla_uf="SP")
            assert len(result) == 1
            assert isinstance(result[0], DeputadoResumoAPI)

    async def test_obter_deputado(self):
        """Should return DeputadoDetalhadoAPI."""
        async with CamaraClient() as client:
            mock_response = make_response(
                {"id": 1, "nomeCivil": "João Silva"}
            )
            client._client.get = AsyncMock(return_value=mock_response)

            result = await client.obter_deputado(1)
            assert isinstance(result, DeputadoDetalhadoAPI)


class TestCamaraClientEventos:
    """Test event endpoints."""

    async def test_listar_eventos(self):
        """Should return list of EventoResumoAPI."""
        async with CamaraClient() as client:
            mock_response = make_response([
                {"id": 1, "descricao": "Evento teste"},
            ])
            client._client.get = AsyncMock(return_value=mock_response)

            result = await client.listar_eventos()
            assert len(result) == 1
            assert isinstance(result[0], EventoResumoAPI)


class TestCamaraClientErrors:
    """Test error handling and retry behavior."""

    async def test_http_error_raises_external_api_exception(self):
        """HTTP errors should raise ExternalAPIException."""
        async with CamaraClient() as client:
            client._client.get = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))

            with pytest.raises(ExternalAPIException, match="conexão"):
                await client.listar_proposicoes()

    async def test_non_retryable_error(self):
        """Non-retryable HTTP status should raise immediately."""
        async with CamaraClient() as client:
            mock_response = httpx.Response(status_code=404, json={"detail": "not found"})
            client._client.get = AsyncMock(return_value=mock_response)

            with pytest.raises(ExternalAPIException, match="inesperado"):
                await client.listar_proposicoes()

    async def test_retryable_error_exhausts_retries(self):
        """Retryable status codes should retry up to 3 times then raise."""
        async with CamaraClient() as client:
            mock_response = httpx.Response(status_code=500, json={"detail": "error"})
            client._client.get = AsyncMock(return_value=mock_response)

            with pytest.raises(ExternalAPIException, match="500"):
                # tenacity will retry 3 times (wait is exponential, but in tests it's quick)
                await client._get("/test")

            # Should have been called 3 times (initial + 2 retries)
            assert client._client.get.call_count == 3

    async def test_missing_dados_key(self):
        """Missing 'dados' key for single resource should raise."""
        async with CamaraClient() as client:
            mock_response = httpx.Response(status_code=200, json={"links": []})
            client._client.get = AsyncMock(return_value=mock_response)

            with pytest.raises(ExternalAPIException, match="inesperada"):
                await client.obter_proposicao(1)

    async def test_clean_params_removes_none(self):
        """_clean_params should strip None values."""
        result = CamaraClient._clean_params({
            "a": 1,
            "b": None,
            "c": "test",
            "d": None,
        })
        assert result == {"a": 1, "c": "test"}
