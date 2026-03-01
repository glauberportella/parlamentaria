"""Tests for ProposicaoService."""

import pytest
from datetime import date, datetime, timezone

from app.domain.proposicao import Proposicao
from app.exceptions import NotFoundException
from app.schemas.proposicao import ProposicaoCreate, ProposicaoUpdate
from app.services.proposicao_service import ProposicaoService


@pytest.fixture
async def service(db_session):
    """Provide a ProposicaoService instance."""
    return ProposicaoService(db_session)


@pytest.fixture
async def proposicao_in_db(db_session, sample_proposicao_data):
    """Create and return a proposition in the database."""
    proposicao = Proposicao(**sample_proposicao_data)
    db_session.add(proposicao)
    await db_session.flush()
    await db_session.refresh(proposicao)
    return proposicao


class TestProposicaoServiceGetById:
    """Tests for get_by_id."""

    async def test_get_by_id_existing(self, service, proposicao_in_db):
        result = await service.get_by_id(proposicao_in_db.id)
        assert result.id == proposicao_in_db.id
        assert result.tipo == "PL"

    async def test_get_by_id_not_found(self, service):
        with pytest.raises(NotFoundException):
            await service.get_by_id(99999)


class TestProposicaoServiceList:
    """Tests for list_proposicoes."""

    async def test_list_empty(self, service):
        result = await service.list_proposicoes()
        assert len(result) == 0

    async def test_list_with_data(self, service, proposicao_in_db):
        result = await service.list_proposicoes()
        assert len(result) == 1

    async def test_list_filter_by_ano(self, service, proposicao_in_db):
        result = await service.list_proposicoes(ano=2024)
        assert len(result) == 1

    async def test_list_filter_by_ano_no_match(self, service, proposicao_in_db):
        result = await service.list_proposicoes(ano=1999)
        assert len(result) == 0


class TestProposicaoServiceCreate:
    """Tests for create."""

    async def test_create_proposicao(self, service):
        data = ProposicaoCreate(
            id=99999,
            tipo="PEC",
            numero=55,
            ano=2025,
            ementa="Emenda constitucional sobre educação",
            data_apresentacao=date(2025, 1, 10),
        )
        result = await service.create(data)
        assert result.id == 99999
        assert result.tipo == "PEC"
        assert result.numero == 55


class TestProposicaoServiceUpdate:
    """Tests for update."""

    async def test_update_proposicao(self, service, proposicao_in_db):
        data = ProposicaoUpdate(ementa="Nova ementa atualizada")
        result = await service.update(proposicao_in_db.id, data)
        assert result.ementa == "Nova ementa atualizada"

    async def test_update_no_changes(self, service, proposicao_in_db):
        data = ProposicaoUpdate()
        result = await service.update(proposicao_in_db.id, data)
        assert result.id == proposicao_in_db.id

    async def test_update_not_found(self, service):
        data = ProposicaoUpdate(ementa="test")
        with pytest.raises(NotFoundException):
            await service.update(99999, data)


class TestProposicaoServiceUpsert:
    """Tests for upsert_from_api."""

    async def test_upsert_creates_new(self, service):
        api_data = {
            "id": 77777,
            "tipo": "PL",
            "numero": 777,
            "ano": 2024,
            "ementa": "Lei complementar",
            "data_apresentacao": date(2024, 5, 1),
            "situacao": "Em tramitação",
        }
        result = await service.upsert_from_api(api_data)
        assert result.id == 77777
        assert result.ementa == "Lei complementar"

    async def test_upsert_updates_existing(self, service, proposicao_in_db):
        api_data = {
            "id": proposicao_in_db.id,
            "tipo": "PL",
            "numero": 100,
            "ano": 2024,
            "ementa": "Ementa atualizada via API",
            "data_apresentacao": date(2024, 3, 15),
            "situacao": "Aprovada",
        }
        result = await service.upsert_from_api(api_data)
        assert result.id == proposicao_in_db.id
        assert result.ementa == "Ementa atualizada via API"


class TestProposicaoServiceDelete:
    """Tests for delete."""

    async def test_delete_proposicao(self, service, proposicao_in_db):
        await service.delete(proposicao_in_db.id)
        with pytest.raises(NotFoundException):
            await service.get_by_id(proposicao_in_db.id)

    async def test_delete_not_found(self, service):
        with pytest.raises(NotFoundException):
            await service.delete(99999)


class TestProposicaoServiceCount:
    """Tests for count."""

    async def test_count_empty(self, service):
        assert await service.count() == 0

    async def test_count_with_data(self, service, proposicao_in_db):
        assert await service.count() == 1
