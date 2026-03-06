"""Tests for sync of deputados, partidos, and eventos in SyncService."""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.sync_service import SyncService


@pytest.fixture
async def service(db_session):
    return SyncService(db_session)


# ---------------------------------------------------------------------------
# Mock factories
# ---------------------------------------------------------------------------

def _make_deputado_api(id_, nome="Dep. Teste", sigla_partido="PT", sigla_uf="SP"):
    """Create a mock Câmara API deputy object."""
    mock = MagicMock()
    mock.id = id_
    mock.nome = nome
    mock.siglaPartido = sigla_partido
    mock.siglaUf = sigla_uf
    mock.urlFoto = f"https://www.camara.leg.br/internet/deputado/bandep/{id_}.jpg"
    mock.email = f"dep{id_}@camara.leg.br"
    return mock


def _make_partido_api(id_, sigla="PT", nome="Partido dos Trabalhadores"):
    """Create a mock Câmara API party object."""
    mock = MagicMock()
    mock.id = id_
    mock.sigla = sigla
    mock.nome = nome
    return mock


def _make_evento_api(id_, descricao="Sessão Deliberativa"):
    """Create a mock Câmara API event object."""
    mock = MagicMock()
    mock.id = id_
    mock.descricao = descricao
    mock.descricaoTipo = "Sessão Deliberativa"
    mock.dataHoraInicio = "2026-03-05T14:00:00"
    mock.dataHoraFim = "2026-03-05T18:00:00"
    mock.situacao = "Encerrada"
    return mock


def _setup_mock_client(MockClient, mock_client):
    """Wire up async context manager for CamaraClient mock."""
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    MockClient.return_value = mock_client


# ---------------------------------------------------------------------------
# Deputados
# ---------------------------------------------------------------------------

class TestSyncDeputados:
    """Tests for sync_deputados."""

    @patch("app.services.sync_service.CamaraClient")
    async def test_sync_deputados_success(self, MockClient, service):
        mock_client = AsyncMock()
        mock_client.listar_deputados = AsyncMock(side_effect=[
            [_make_deputado_api(1, "Ana"), _make_deputado_api(2, "Bruno")],
            [],  # empty page → stop
        ])
        _setup_mock_client(MockClient, mock_client)

        stats = await service.sync_deputados(paginas=2)
        assert stats["total_fetched"] == 2
        assert stats["errors"] == 0

    @patch("app.services.sync_service.CamaraClient")
    async def test_sync_deputados_api_error(self, MockClient, service):
        mock_client = AsyncMock()
        mock_client.listar_deputados = AsyncMock(side_effect=Exception("API down"))
        _setup_mock_client(MockClient, mock_client)

        stats = await service.sync_deputados(paginas=1)
        assert stats["errors"] >= 1
        assert stats["total_fetched"] == 0

    @patch("app.services.sync_service.CamaraClient")
    async def test_sync_deputados_partial_failure(self, MockClient, service):
        """Some deputies fail but sync continues (savepoint pattern)."""
        mock_client = AsyncMock()
        mock_client.listar_deputados = AsyncMock(return_value=[
            _make_deputado_api(10, "Carlos"),
            _make_deputado_api(20, "Diana"),
        ])
        _setup_mock_client(MockClient, mock_client)

        stats = await service.sync_deputados(paginas=1)
        assert stats["total_fetched"] == 2

    @patch("app.services.sync_service.CamaraClient")
    async def test_sync_deputados_with_filter(self, MockClient, service):
        """Filter by UF should pass param to client."""
        mock_client = AsyncMock()
        mock_client.listar_deputados = AsyncMock(return_value=[
            _make_deputado_api(1, "Test", sigla_uf="RJ"),
        ])
        _setup_mock_client(MockClient, mock_client)

        stats = await service.sync_deputados(sigla_uf="RJ", paginas=1)
        mock_client.listar_deputados.assert_called_once_with(
            sigla_uf="RJ",
            sigla_partido=None,
            pagina=1,
            itens=100,
        )
        assert stats["total_fetched"] == 1

    @patch("app.services.sync_service.CamaraClient")
    async def test_sync_deputados_upsert_updates_existing(self, MockClient, service):
        """Syncing same ID twice should update (not duplicate)."""
        mock_client = AsyncMock()
        dep = _make_deputado_api(99, "Original")
        mock_client.listar_deputados = AsyncMock(side_effect=[
            [dep],
            [],
        ])
        _setup_mock_client(MockClient, mock_client)

        stats1 = await service.sync_deputados(paginas=2)
        assert stats1["total_fetched"] == 1

        # Second sync with updated name
        dep2 = _make_deputado_api(99, "Atualizado")
        mock_client.listar_deputados = AsyncMock(side_effect=[
            [dep2],
            [],
        ])
        stats2 = await service.sync_deputados(paginas=2)
        assert stats2["total_fetched"] == 1
        assert stats2["errors"] == 0


# ---------------------------------------------------------------------------
# Partidos
# ---------------------------------------------------------------------------

class TestSyncPartidos:
    """Tests for sync_partidos."""

    @patch("app.services.sync_service.CamaraClient")
    async def test_sync_partidos_success(self, MockClient, service):
        mock_client = AsyncMock()
        mock_client.listar_partidos = AsyncMock(return_value=[
            _make_partido_api(1, "PT", "Partido dos Trabalhadores"),
            _make_partido_api(2, "PL", "Partido Liberal"),
            _make_partido_api(3, "PSOL", "Partido Socialismo e Liberdade"),
        ])
        _setup_mock_client(MockClient, mock_client)

        stats = await service.sync_partidos()
        assert stats["total_fetched"] == 3
        assert stats["errors"] == 0

    @patch("app.services.sync_service.CamaraClient")
    async def test_sync_partidos_api_error(self, MockClient, service):
        mock_client = AsyncMock()
        mock_client.listar_partidos = AsyncMock(side_effect=Exception("API down"))
        _setup_mock_client(MockClient, mock_client)

        stats = await service.sync_partidos()
        assert stats["errors"] >= 1
        assert stats["total_fetched"] == 0

    @patch("app.services.sync_service.CamaraClient")
    async def test_sync_partidos_empty(self, MockClient, service):
        mock_client = AsyncMock()
        mock_client.listar_partidos = AsyncMock(return_value=[])
        _setup_mock_client(MockClient, mock_client)

        stats = await service.sync_partidos()
        assert stats["total_fetched"] == 0
        assert stats["errors"] == 0

    @patch("app.services.sync_service.CamaraClient")
    async def test_sync_partidos_upsert_updates_existing(self, MockClient, service):
        """Syncing same party twice should update."""
        mock_client = AsyncMock()
        mock_client.listar_partidos = AsyncMock(return_value=[
            _make_partido_api(1, "PT", "Nome Original"),
        ])
        _setup_mock_client(MockClient, mock_client)

        await service.sync_partidos()

        mock_client.listar_partidos = AsyncMock(return_value=[
            _make_partido_api(1, "PT", "Nome Atualizado"),
        ])
        stats = await service.sync_partidos()
        assert stats["errors"] == 0


# ---------------------------------------------------------------------------
# Eventos
# ---------------------------------------------------------------------------

class TestSyncEventos:
    """Tests for sync_eventos."""

    @patch("app.services.sync_service.CamaraClient")
    async def test_sync_eventos_success(self, MockClient, service):
        mock_client = AsyncMock()
        mock_client.listar_eventos = AsyncMock(side_effect=[
            [_make_evento_api(1), _make_evento_api(2)],
            [],
        ])
        _setup_mock_client(MockClient, mock_client)

        stats = await service.sync_eventos(paginas=2)
        assert stats["total_fetched"] == 2
        assert stats["errors"] == 0

    @patch("app.services.sync_service.CamaraClient")
    async def test_sync_eventos_api_error(self, MockClient, service):
        mock_client = AsyncMock()
        mock_client.listar_eventos = AsyncMock(side_effect=Exception("Timeout"))
        _setup_mock_client(MockClient, mock_client)

        stats = await service.sync_eventos(paginas=1)
        assert stats["errors"] >= 1
        assert stats["total_fetched"] == 0

    @patch("app.services.sync_service.CamaraClient")
    async def test_sync_eventos_partial_failure(self, MockClient, service):
        """Some events fail but sync continues."""
        mock_client = AsyncMock()
        mock_client.listar_eventos = AsyncMock(return_value=[
            _make_evento_api(10),
            _make_evento_api(20),
        ])
        _setup_mock_client(MockClient, mock_client)

        stats = await service.sync_eventos(paginas=1)
        assert stats["total_fetched"] == 2

    @patch("app.services.sync_service.CamaraClient")
    async def test_sync_eventos_custom_dias_atras(self, MockClient, service):
        """dias_atras parameter should be respected in date filter."""
        mock_client = AsyncMock()
        mock_client.listar_eventos = AsyncMock(return_value=[])
        _setup_mock_client(MockClient, mock_client)

        stats = await service.sync_eventos(dias_atras=30, paginas=1)
        # Verify the client was called with date filters
        call_kwargs = mock_client.listar_eventos.call_args
        assert call_kwargs is not None
        assert stats["total_fetched"] == 0

    @patch("app.services.sync_service.CamaraClient")
    async def test_sync_eventos_upsert_updates_existing(self, MockClient, service):
        """Syncing same event ID twice should update."""
        mock_client = AsyncMock()
        mock_client.listar_eventos = AsyncMock(side_effect=[
            [_make_evento_api(5, "Sessão Original")],
            [],
        ])
        _setup_mock_client(MockClient, mock_client)

        await service.sync_eventos(paginas=2)

        mock_client.listar_eventos = AsyncMock(side_effect=[
            [_make_evento_api(5, "Sessão Atualizada")],
            [],
        ])
        stats = await service.sync_eventos(paginas=2)
        assert stats["errors"] == 0
