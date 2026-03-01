"""Tests for VotacaoService."""

import pytest
from datetime import datetime, timezone

from app.domain.votacao import Votacao
from app.exceptions import NotFoundException
from app.schemas.votacao import VotacaoCreate
from app.services.votacao_service import VotacaoService


@pytest.fixture
async def service(db_session):
    return VotacaoService(db_session)


@pytest.fixture
async def votacao_in_db(db_session, sample_votacao_data):
    votacao = Votacao(**sample_votacao_data)
    db_session.add(votacao)
    await db_session.flush()
    await db_session.refresh(votacao)
    return votacao


class TestVotacaoServiceGetById:
    """Tests for get_by_id."""

    async def test_get_by_id_existing(self, service, votacao_in_db):
        result = await service.get_by_id(votacao_in_db.id)
        assert result.descricao == "Votação do PL 100/2024"

    async def test_get_by_id_not_found(self, service):
        with pytest.raises(NotFoundException):
            await service.get_by_id(99999)


class TestVotacaoServiceList:
    """Tests for list_votacoes and list_by_proposicao."""

    async def test_list_empty(self, service):
        result = await service.list_votacoes()
        assert len(result) == 0

    async def test_list_with_data(self, service, votacao_in_db):
        result = await service.list_votacoes()
        assert len(result) == 1

    async def test_list_by_proposicao(self, service, votacao_in_db):
        result = await service.list_by_proposicao(12345)
        assert len(result) == 1

    async def test_list_by_proposicao_no_match(self, service, votacao_in_db):
        result = await service.list_by_proposicao(99999)
        assert len(result) == 0


class TestVotacaoServiceCreate:
    """Tests for create."""

    async def test_create_votacao(self, service):
        data = VotacaoCreate(
            id=22222,
            data=datetime(2024, 7, 1, 10, 0, tzinfo=timezone.utc),
            descricao="Nova votação",
            votos_sim=200,
            votos_nao=100,
        )
        result = await service.create(data)
        assert result.id == 22222
        assert result.descricao == "Nova votação"


class TestVotacaoServiceUpsert:
    """Tests for upsert_from_api."""

    async def test_upsert_creates_new(self, service):
        api_data = {
            "id": 33333,
            "data": datetime(2024, 8, 1, tzinfo=timezone.utc),
            "descricao": "Votação vinda da API",
        }
        result = await service.upsert_from_api(api_data)
        assert result.id == 33333

    async def test_upsert_updates_existing(self, service, votacao_in_db):
        api_data = {
            "id": votacao_in_db.id,
            "descricao": "Descrição atualizada",
        }
        result = await service.upsert_from_api(api_data)
        assert result.descricao == "Descrição atualizada"
