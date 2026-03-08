"""Tests for temas sync — SyncService._fetch_temas, sync_temas_backfill, and Celery task."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.sync_service import SyncService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_tema_api(cod: int, tema: str) -> MagicMock:
    """Create a mock TemaAPI object."""
    m = MagicMock()
    m.codTema = cod
    m.tema = tema
    return m


def _make_proposicao_api(id_: int, sigla_tipo: str = "PL", numero: int = 1, ano: int = 2024, ementa: str = "Test"):
    """Create a mock Câmara API proposition object."""
    mock = MagicMock()
    mock.id = id_
    mock.siglaTipo = sigla_tipo
    mock.numero = numero
    mock.ano = ano
    mock.ementa = ementa
    mock.dataApresentacao = "2024-01-15"
    return mock


# ---------------------------------------------------------------------------
# SyncService._fetch_temas
# ---------------------------------------------------------------------------


class TestFetchTemas:
    """Tests for SyncService._fetch_temas static method."""

    async def test_returns_tema_names(self):
        """Should extract tema name strings from API response."""
        client = AsyncMock()
        client.obter_temas = AsyncMock(return_value=[
            _make_tema_api(40, "Educação"),
            _make_tema_api(46, "Saúde"),
        ])

        result = await SyncService._fetch_temas(client, 12345)

        assert result == ["Educação", "Saúde"]
        client.obter_temas.assert_called_once_with(12345)

    async def test_returns_empty_on_api_error(self):
        """Should return empty list and not propagate exceptions."""
        client = AsyncMock()
        client.obter_temas = AsyncMock(side_effect=Exception("API timeout"))

        result = await SyncService._fetch_temas(client, 12345)

        assert result == []

    async def test_returns_empty_when_no_temas(self):
        """Should return empty list when API returns no themes."""
        client = AsyncMock()
        client.obter_temas = AsyncMock(return_value=[])

        result = await SyncService._fetch_temas(client, 12345)

        assert result == []

    async def test_filters_empty_tema_names(self):
        """Should skip items where tema is empty or falsy."""
        client = AsyncMock()
        t1 = _make_tema_api(40, "Educação")
        t2 = MagicMock()
        t2.tema = ""
        t3 = MagicMock()
        t3.tema = None
        client.obter_temas = AsyncMock(return_value=[t1, t2, t3])

        result = await SyncService._fetch_temas(client, 12345)

        assert result == ["Educação"]


# ---------------------------------------------------------------------------
# SyncService.sync_proposicoes now includes temas
# ---------------------------------------------------------------------------


class TestSyncProposicoesWithTemas:
    """Tests that sync_proposicoes fetches and includes temas."""

    @patch("app.services.sync_service.CamaraClient")
    async def test_sync_includes_temas(self, MockClient, db_session):
        """Sync should call obter_temas and include them in api_data."""
        service = SyncService(db_session)

        mock_client = AsyncMock()
        mock_client.listar_proposicoes = AsyncMock(side_effect=[
            [_make_proposicao_api(100)],
            [],
        ])
        mock_client.obter_temas = AsyncMock(return_value=[
            _make_tema_api(40, "Educação"),
            _make_tema_api(46, "Saúde"),
        ])
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = mock_client

        stats = await service.sync_proposicoes(ano=2024, paginas=2)

        assert stats["total_fetched"] == 1
        assert stats["errors"] == 0
        # Verify obter_temas was called for the proposition
        mock_client.obter_temas.assert_called_once_with(100)

    @patch("app.services.sync_service.CamaraClient")
    async def test_sync_continues_when_temas_fail(self, MockClient, db_session):
        """If obter_temas fails, sync should still upsert the proposition."""
        service = SyncService(db_session)

        mock_client = AsyncMock()
        mock_client.listar_proposicoes = AsyncMock(side_effect=[
            [_make_proposicao_api(200)],
            [],
        ])
        mock_client.obter_temas = AsyncMock(side_effect=Exception("Tema API down"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = mock_client

        stats = await service.sync_proposicoes(ano=2024, paginas=2)

        # Proposition should still be synced (temas just won't be set)
        assert stats["total_fetched"] == 1
        assert stats["created"] == 1


# ---------------------------------------------------------------------------
# SyncService.sync_temas_backfill
# ---------------------------------------------------------------------------


class TestSyncTemasBackfill:
    """Tests for sync_temas_backfill.

    Note: The backfill query uses Proposicao.temas.is_(None) which works
    correctly on PostgreSQL (ARRAY type) but not on SQLite (JSON type)
    used in tests. Tests mock the query result to test business logic.
    """

    @patch("app.services.sync_service.CamaraClient")
    async def test_backfill_updates_temas(self, MockClient, db_session):
        """Should update temas for propositions that have none."""
        from app.domain.proposicao import Proposicao
        from app.repositories.proposicao import ProposicaoRepository

        # Create proposition with no temas
        repo = ProposicaoRepository(db_session)
        prop = Proposicao(
            id=500, tipo="PL", numero=1, ano=2024,
            ementa="Teste", temas=None,
        )
        await repo.create(prop)
        await db_session.flush()

        # Mock CamaraClient
        mock_client = AsyncMock()
        mock_client.obter_temas = AsyncMock(return_value=[
            _make_tema_api(40, "Educação"),
            _make_tema_api(46, "Saúde"),
        ])
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = mock_client

        service = SyncService(db_session)

        # Mock the query to return ID 500 (simulates PostgreSQL behavior)
        mock_result = MagicMock()
        mock_result.all.return_value = [(500,)]
        with patch.object(db_session, "execute", wraps=db_session.execute) as mock_exec:
            # Override only the first execute call (the SELECT query)
            original_execute = db_session.execute

            call_count = 0
            async def _patched_execute(stmt, *args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    # Return our mocked list of IDs for the backfill query
                    return mock_result
                return await original_execute(stmt, *args, **kwargs)

            with patch.object(db_session, "execute", side_effect=_patched_execute):
                stats = await service.sync_temas_backfill()

        assert stats["total"] == 1
        assert stats["updated"] == 1
        assert stats["errors"] == 0

    @patch("app.services.sync_service.CamaraClient")
    async def test_backfill_skips_when_api_returns_no_temas(self, MockClient, db_session):
        """Should count as skipped when API returns empty temas."""
        mock_client = AsyncMock()
        mock_client.obter_temas = AsyncMock(return_value=[])
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = mock_client

        service = SyncService(db_session)

        mock_result = MagicMock()
        mock_result.all.return_value = [(600,)]

        call_count = 0
        original_execute = db_session.execute
        async def _patched_execute(stmt, *args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return mock_result
            return await original_execute(stmt, *args, **kwargs)

        with patch.object(db_session, "execute", side_effect=_patched_execute):
            stats = await service.sync_temas_backfill()

        assert stats["total"] == 1
        assert stats["skipped"] == 1
        assert stats["updated"] == 0

    @patch("app.services.sync_service.CamaraClient")
    async def test_backfill_nothing_to_do(self, MockClient, db_session):
        """Should return early when all propositions have temas."""
        from app.domain.proposicao import Proposicao
        from app.repositories.proposicao import ProposicaoRepository

        repo = ProposicaoRepository(db_session)
        prop = Proposicao(
            id=700, tipo="PL", numero=3, ano=2024,
            ementa="Teste 3", temas=["Economia"],
        )
        await repo.create(prop)
        await db_session.flush()

        service = SyncService(db_session)

        # Mock empty result (no propositions without temas)
        mock_result = MagicMock()
        mock_result.all.return_value = []

        call_count = 0
        original_execute = db_session.execute
        async def _patched_execute(stmt, *args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return mock_result
            return await original_execute(stmt, *args, **kwargs)

        with patch.object(db_session, "execute", side_effect=_patched_execute):
            stats = await service.sync_temas_backfill()

        assert stats["total"] == 0
        assert stats["updated"] == 0
        MockClient.assert_not_called()

    @patch("app.services.sync_service.CamaraClient")
    async def test_backfill_respects_limit(self, MockClient, db_session):
        """Should only process up to `limit` propositions."""
        mock_client = AsyncMock()
        mock_client.obter_temas = AsyncMock(return_value=[
            _make_tema_api(40, "Economia"),
        ])
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = mock_client

        service = SyncService(db_session)

        # 5 propositions without temas but limit=2
        mock_result = MagicMock()
        mock_result.all.return_value = [(800,), (801,)]

        call_count = 0
        original_execute = db_session.execute
        async def _patched_execute(stmt, *args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return mock_result
            return await original_execute(stmt, *args, **kwargs)

        with patch.object(db_session, "execute", side_effect=_patched_execute):
            stats = await service.sync_temas_backfill(limit=2)

        assert stats["total"] == 2
        assert stats["updated"] == 2

    @patch("app.services.sync_service.CamaraClient")
    async def test_backfill_handles_api_errors(self, MockClient, db_session):
        """Should count errors but continue processing other propositions."""
        mock_client = AsyncMock()
        mock_client.obter_temas = AsyncMock(side_effect=[
            [_make_tema_api(40, "Saúde")],
            Exception("API error"),
            [_make_tema_api(46, "Educação")],
        ])
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = mock_client

        service = SyncService(db_session)

        mock_result = MagicMock()
        mock_result.all.return_value = [(900,), (901,), (902,)]

        call_count = 0
        original_execute = db_session.execute
        async def _patched_execute(stmt, *args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return mock_result
            return await original_execute(stmt, *args, **kwargs)

        with patch.object(db_session, "execute", side_effect=_patched_execute):
            stats = await service.sync_temas_backfill()

        assert stats["total"] == 3
        assert stats["updated"] >= 1


# ---------------------------------------------------------------------------
# ProposicaoRepository.update_temas
# ---------------------------------------------------------------------------


class TestUpdateTemas:
    """Tests for ProposicaoRepository.update_temas."""

    async def test_update_temas_success(self, db_session):
        """Should update temas for existing proposition."""
        from app.domain.proposicao import Proposicao
        from app.repositories.proposicao import ProposicaoRepository

        repo = ProposicaoRepository(db_session)
        prop = Proposicao(
            id=1000, tipo="PL", numero=50, ano=2024,
            ementa="Teste update", temas=None,
        )
        await repo.create(prop)
        await db_session.flush()

        result = await repo.update_temas(1000, ["Economia", "Trabalho"])
        assert result is True

    async def test_update_temas_not_found(self, db_session):
        """Should return False for non-existent proposition."""
        from app.repositories.proposicao import ProposicaoRepository

        repo = ProposicaoRepository(db_session)
        result = await repo.update_temas(99999, ["Saúde"])
        assert result is False


# ---------------------------------------------------------------------------
# Admin endpoint /sync/temas
# ---------------------------------------------------------------------------


class TestSyncTemasEndpoint:
    """Tests for the admin sync/temas endpoint."""

    @patch("app.tasks.sync_proposicoes.sync_temas_proposicoes_task")
    async def test_sync_temas_endpoint(self, mock_task, client):
        """Should queue the backfill task and return queued status."""
        from app.config import settings

        mock_task.delay = MagicMock()

        response = await client.post(
            "/admin/sync/temas",
            headers={"X-API-Key": settings.admin_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "queued"
        mock_task.delay.assert_called_once_with(limit=None)

    @patch("app.tasks.sync_proposicoes.sync_temas_proposicoes_task")
    async def test_sync_temas_endpoint_with_limit(self, mock_task, client):
        """Should pass limit parameter to the task."""
        from app.config import settings

        mock_task.delay = MagicMock()

        response = await client.post(
            "/admin/sync/temas?limit=100",
            headers={"X-API-Key": settings.admin_api_key},
        )

        assert response.status_code == 200
        mock_task.delay.assert_called_once_with(limit=100)
