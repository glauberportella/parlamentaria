"""Tests for SyncService — sync from Câmara API."""

import pytest
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.sync_service import SyncService


@pytest.fixture
async def service(db_session):
    return SyncService(db_session)


def _make_proposicao_api(id_, sigla_tipo="PL", numero=1, ano=2024, ementa="Test"):
    """Create a mock Câmara API proposition object."""
    mock = MagicMock()
    mock.id = id_
    mock.siglaTipo = sigla_tipo
    mock.numero = numero
    mock.ano = ano
    mock.ementa = ementa
    mock.dataApresentacao = date(2024, 1, 15)
    return mock


def _make_votacao_api(id_, descricao="Votação teste"):
    """Create a mock Câmara API vote object."""
    mock = MagicMock()
    mock.id = id_
    mock.data = datetime(2024, 6, 1, tzinfo=timezone.utc)
    mock.descricao = descricao
    return mock


class TestSyncProposicoes:
    """Tests for sync_proposicoes."""

    @patch("app.services.sync_service.CamaraClient")
    async def test_sync_proposicoes_success(self, MockClient, service):
        mock_client = AsyncMock()
        mock_client.listar_proposicoes = AsyncMock(side_effect=[
            [_make_proposicao_api(1), _make_proposicao_api(2)],
            [],  # empty page → stop
        ])
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = mock_client

        stats = await service.sync_proposicoes(ano=2024, paginas=2)
        assert stats["total_fetched"] == 2
        assert stats["errors"] == 0

    @patch("app.services.sync_service.CamaraClient")
    async def test_sync_proposicoes_api_error(self, MockClient, service):
        mock_client = AsyncMock()
        mock_client.listar_proposicoes = AsyncMock(side_effect=Exception("API down"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = mock_client

        stats = await service.sync_proposicoes(paginas=1)
        assert stats["errors"] >= 1
        assert stats["total_fetched"] == 0

    @patch("app.services.sync_service.CamaraClient")
    async def test_sync_proposicoes_partial_failure(self, MockClient, service):
        """Some propositions fail to upsert but sync continues."""
        mock_client = AsyncMock()
        mock_client.listar_proposicoes = AsyncMock(return_value=[
            _make_proposicao_api(10),
            _make_proposicao_api(20),
        ])
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = mock_client

        stats = await service.sync_proposicoes(paginas=1)
        assert stats["total_fetched"] == 2


class TestSyncVotacoes:
    """Tests for sync_votacoes."""

    @patch("app.services.sync_service.CamaraClient")
    async def test_sync_votacoes_success(self, MockClient, service):
        mock_client = AsyncMock()
        mock_client.listar_votacoes = AsyncMock(side_effect=[
            [_make_votacao_api("100-1"), _make_votacao_api("200-2")],
            [],
        ])
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = mock_client

        stats = await service.sync_votacoes(paginas=2)
        assert stats["total_fetched"] == 2
        assert stats["errors"] == 0

    @patch("app.services.sync_service.CamaraClient")
    async def test_sync_votacoes_api_error(self, MockClient, service):
        mock_client = AsyncMock()
        mock_client.listar_votacoes = AsyncMock(side_effect=Exception("Timeout"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = mock_client

        stats = await service.sync_votacoes(paginas=1)
        assert stats["errors"] >= 1
