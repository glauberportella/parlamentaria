"""Tests for AnaliseIAService."""

import pytest
from datetime import date

from app.domain.proposicao import Proposicao
from app.exceptions import NotFoundException
from app.schemas.analise_ia import AnaliseIACreate
from app.services.analise_service import AnaliseIAService


@pytest.fixture
async def service(db_session):
    """Provide an AnaliseIAService instance."""
    return AnaliseIAService(db_session)


@pytest.fixture
async def proposicao(db_session, sample_proposicao_data):
    """Create a proposition in the database."""
    prop = Proposicao(**sample_proposicao_data)
    db_session.add(prop)
    await db_session.flush()
    await db_session.refresh(prop)
    return prop


@pytest.fixture
def analise_data(proposicao):
    """Return valid AnaliseIACreate data."""
    return AnaliseIACreate(
        proposicao_id=proposicao.id,
        resumo_leigo="Esta lei propõe mais transparência",
        impacto_esperado="Maior acesso à informação pública",
        areas_afetadas=["Transparência", "Governo"],
        argumentos_favor=["Mais transparência", "Controle social"],
        argumentos_contra=["Custo de implementação"],
        provedor_llm="gemini",
        modelo="gemini-2.0-flash",
    )


class TestAnaliseIAServiceGetLatest:
    """Tests for get_latest."""

    async def test_get_latest_none(self, service, proposicao):
        result = await service.get_latest(proposicao.id)
        assert result is None

    async def test_get_latest_with_analysis(self, service, analise_data):
        await service.create_analysis(analise_data)
        result = await service.get_latest(analise_data.proposicao_id)
        assert result is not None
        assert result.versao == 1


class TestAnaliseIAServiceGetLatestOrRaise:
    """Tests for get_latest_or_raise."""

    async def test_raises_when_none(self, service, proposicao):
        with pytest.raises(NotFoundException, match="Nenhuma análise"):
            await service.get_latest_or_raise(proposicao.id)

    async def test_returns_when_exists(self, service, analise_data):
        await service.create_analysis(analise_data)
        result = await service.get_latest_or_raise(analise_data.proposicao_id)
        assert result.resumo_leigo == "Esta lei propõe mais transparência"


class TestAnaliseIAServiceCreate:
    """Tests for create_analysis."""

    async def test_creates_first_version(self, service, analise_data):
        result = await service.create_analysis(analise_data)
        assert result.versao == 1
        assert result.provedor_llm == "gemini"

    async def test_increments_version(self, service, analise_data):
        await service.create_analysis(analise_data)
        result = await service.create_analysis(analise_data)
        assert result.versao == 2

    async def test_updates_proposicao_resumo(self, service, analise_data, db_session):
        from app.repositories.proposicao import ProposicaoRepository
        await service.create_analysis(analise_data)

        repo = ProposicaoRepository(db_session)
        prop = await repo.get_by_id(analise_data.proposicao_id)
        assert prop.resumo_ia == "Esta lei propõe mais transparência"

    async def test_create_for_nonexistent_proposicao(self, service):
        data = AnaliseIACreate(
            proposicao_id=99999,
            resumo_leigo="Test",
            impacto_esperado="Test",
            areas_afetadas=["Test"],
            argumentos_favor=["Test"],
            argumentos_contra=["Test"],
            provedor_llm="test",
            modelo="test",
        )
        with pytest.raises(NotFoundException):
            await service.create_analysis(data)


class TestAnaliseIAServiceListVersions:
    """Tests for list_versions."""

    async def test_list_versions_empty(self, service, proposicao):
        result = await service.list_versions(proposicao.id)
        assert len(result) == 0

    async def test_list_versions_multiple(self, service, analise_data):
        await service.create_analysis(analise_data)
        await service.create_analysis(analise_data)
        await service.create_analysis(analise_data)

        result = await service.list_versions(analise_data.proposicao_id)
        assert len(result) == 3
        # Should be ordered desc
        assert result[0].versao == 3
        assert result[2].versao == 1
