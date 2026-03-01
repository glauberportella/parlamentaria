"""Tests for repository layer."""

import uuid
from datetime import date, datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.proposicao import Proposicao
from app.domain.eleitor import Eleitor
from app.domain.deputado import Deputado
from app.domain.votacao import Votacao
from app.domain.voto_popular import VotoPopular, VotoEnum
from app.domain.analise_ia import AnaliseIA
from app.exceptions import NotFoundException
from app.repositories.base import BaseRepository
from app.repositories.proposicao import ProposicaoRepository
from app.repositories.eleitor import EleitorRepository
from app.repositories.deputado import DeputadoRepository
from app.repositories.votacao import VotacaoRepository
from app.repositories.voto_popular import VotoPopularRepository
from app.repositories.analise_ia import AnaliseIARepository


# ---------------------------------------------------------------------------
# BaseRepository
# ---------------------------------------------------------------------------


class TestBaseRepository:
    """Test generic BaseRepository operations."""

    async def test_create_and_get_by_id(self, db_session: AsyncSession, sample_proposicao_data: dict):
        """create() followed by get_by_id() should return the same entity."""
        repo = BaseRepository(Proposicao, db_session)
        prop = Proposicao(**sample_proposicao_data)
        created = await repo.create(prop)
        assert created.id == 12345

        fetched = await repo.get_by_id(12345)
        assert fetched is not None
        assert fetched.id == created.id

    async def test_get_by_id_returns_none(self, db_session: AsyncSession):
        """get_by_id() should return None for non-existent ID."""
        repo = BaseRepository(Proposicao, db_session)
        result = await repo.get_by_id(99999)
        assert result is None

    async def test_get_by_id_or_raise(self, db_session: AsyncSession):
        """get_by_id_or_raise() should raise NotFoundException."""
        repo = BaseRepository(Proposicao, db_session)
        with pytest.raises(NotFoundException, match="Proposicao"):
            await repo.get_by_id_or_raise(99999)

    async def test_list_all(self, db_session: AsyncSession, sample_proposicao_data: dict):
        """list_all() should return paginated results."""
        repo = BaseRepository(Proposicao, db_session)

        # Create 3 propositions
        for i in range(3):
            data = {**sample_proposicao_data, "id": 100 + i, "numero": 100 + i}
            await repo.create(Proposicao(**data))

        all_items = await repo.list_all(offset=0, limit=10)
        assert len(all_items) == 3

        page = await repo.list_all(offset=0, limit=2)
        assert len(page) == 2

    async def test_count(self, db_session: AsyncSession, sample_proposicao_data: dict):
        """count() should return total number of records."""
        repo = BaseRepository(Proposicao, db_session)
        assert await repo.count() == 0

        await repo.create(Proposicao(**sample_proposicao_data))
        assert await repo.count() == 1

    async def test_update(self, db_session: AsyncSession, sample_proposicao_data: dict):
        """update() should modify the entity in place."""
        repo = BaseRepository(Proposicao, db_session)
        prop = await repo.create(Proposicao(**sample_proposicao_data))

        updated = await repo.update(prop, {"ementa": "Nova ementa"})
        assert updated.ementa == "Nova ementa"

    async def test_delete(self, db_session: AsyncSession, sample_proposicao_data: dict):
        """delete() should remove the entity."""
        repo = BaseRepository(Proposicao, db_session)
        prop = await repo.create(Proposicao(**sample_proposicao_data))

        await repo.delete(prop)
        assert await repo.get_by_id(prop.id) is None

    async def test_exists(self, db_session: AsyncSession, sample_proposicao_data: dict):
        """exists() should check for presence."""
        repo = BaseRepository(Proposicao, db_session)
        assert await repo.exists(12345) is False

        await repo.create(Proposicao(**sample_proposicao_data))
        assert await repo.exists(12345) is True

    async def test_create_many(self, db_session: AsyncSession, sample_proposicao_data: dict):
        """create_many() should insert multiple records."""
        repo = BaseRepository(Proposicao, db_session)
        items = [
            Proposicao(**{**sample_proposicao_data, "id": 200 + i, "numero": 200 + i})
            for i in range(3)
        ]
        created = await repo.create_many(items)
        assert len(created) == 3
        assert await repo.count() == 3


# ---------------------------------------------------------------------------
# ProposicaoRepository
# ---------------------------------------------------------------------------


class TestProposicaoRepository:
    """Test ProposicaoRepository specific queries."""

    async def test_find_by_tipo_numero_ano(self, db_session: AsyncSession, sample_proposicao_data: dict):
        """Should find by type, number, and year."""
        repo = ProposicaoRepository(db_session)
        await repo.create(Proposicao(**sample_proposicao_data))

        found = await repo.find_by_tipo_numero_ano("PL", 100, 2024)
        assert found is not None
        assert found.id == 12345

    async def test_find_by_tipo_numero_ano_not_found(self, db_session: AsyncSession):
        """Should return None when not found."""
        repo = ProposicaoRepository(db_session)
        result = await repo.find_by_tipo_numero_ano("PL", 999, 2024)
        assert result is None

    async def test_find_by_ano(self, db_session: AsyncSession, sample_proposicao_data: dict):
        """Should filter by year."""
        repo = ProposicaoRepository(db_session)
        await repo.create(Proposicao(**sample_proposicao_data))
        await repo.create(Proposicao(**{**sample_proposicao_data, "id": 99, "ano": 2023, "numero": 50}))

        results = await repo.find_by_ano(2024)
        assert len(results) == 1
        assert results[0].ano == 2024


# ---------------------------------------------------------------------------
# EleitorRepository
# ---------------------------------------------------------------------------


class TestEleitorRepository:
    """Test EleitorRepository specific queries."""

    async def test_find_by_email(self, db_session: AsyncSession, sample_eleitor_data: dict):
        """Should find by email."""
        repo = EleitorRepository(db_session)
        await repo.create(Eleitor(**sample_eleitor_data))

        found = await repo.find_by_email("maria@example.com")
        assert found is not None
        assert found.nome == "Maria Silva"

    async def test_find_by_email_not_found(self, db_session: AsyncSession):
        """Should return None when not found."""
        repo = EleitorRepository(db_session)
        assert await repo.find_by_email("nobody@example.com") is None

    async def test_find_by_chat_id(self, db_session: AsyncSession, sample_eleitor_data: dict):
        """Should find by chat ID."""
        repo = EleitorRepository(db_session)
        await repo.create(Eleitor(**sample_eleitor_data))

        found = await repo.find_by_chat_id("12345678")
        assert found is not None
        assert found.nome == "Maria Silva"

    async def test_find_by_uf(self, db_session: AsyncSession, sample_eleitor_data: dict):
        """Should filter by state."""
        repo = EleitorRepository(db_session)
        await repo.create(Eleitor(**sample_eleitor_data))
        await repo.create(Eleitor(
            nome="João RJ", email="joao@test.com", uf="RJ", channel="telegram"
        ))

        sp_voters = await repo.find_by_uf("SP")
        assert len(sp_voters) == 1
        assert sp_voters[0].uf == "SP"


# ---------------------------------------------------------------------------
# DeputadoRepository
# ---------------------------------------------------------------------------


class TestDeputadoRepository:
    """Test DeputadoRepository specific queries."""

    async def test_find_by_nome(self, db_session: AsyncSession, sample_deputado_data: dict):
        """Should search by name (case-insensitive)."""
        repo = DeputadoRepository(db_session)
        await repo.create(Deputado(**sample_deputado_data))

        results = await repo.find_by_nome("joão")
        assert len(results) == 1
        assert results[0].nome == "João Exemplo"

    async def test_find_by_partido(self, db_session: AsyncSession, sample_deputado_data: dict):
        """Should filter by party."""
        repo = DeputadoRepository(db_session)
        await repo.create(Deputado(**sample_deputado_data))
        await repo.create(Deputado(id=99999, nome="Ana PL", sigla_partido="PL", sigla_uf="SP"))

        pt_deps = await repo.find_by_partido("PT")
        assert len(pt_deps) == 1
        assert pt_deps[0].sigla_partido == "PT"

    async def test_find_by_uf(self, db_session: AsyncSession, sample_deputado_data: dict):
        """Should filter by state."""
        repo = DeputadoRepository(db_session)
        await repo.create(Deputado(**sample_deputado_data))

        rj_deps = await repo.find_by_uf("RJ")
        assert len(rj_deps) == 1


# ---------------------------------------------------------------------------
# VotacaoRepository
# ---------------------------------------------------------------------------


class TestVotacaoRepository:
    """Test VotacaoRepository specific queries."""

    async def test_find_by_proposicao(
        self, db_session: AsyncSession, sample_proposicao_data: dict, sample_votacao_data: dict
    ):
        """Should find vote sessions for a proposition."""
        prop = Proposicao(**sample_proposicao_data)
        db_session.add(prop)
        await db_session.flush()

        repo = VotacaoRepository(db_session)
        await repo.create(Votacao(**sample_votacao_data))

        results = await repo.find_by_proposicao(12345)
        assert len(results) == 1
        assert results[0].proposicao_id == 12345


# ---------------------------------------------------------------------------
# VotoPopularRepository
# ---------------------------------------------------------------------------


class TestVotoPopularRepository:
    """Test VotoPopularRepository specific queries."""

    async def _setup_vote(self, db_session: AsyncSession, sample_proposicao_data: dict, sample_eleitor_data: dict):
        """Helper to create prerequisite entities and a vote."""
        prop = Proposicao(**sample_proposicao_data)
        eleitor = Eleitor(**sample_eleitor_data)
        db_session.add_all([prop, eleitor])
        await db_session.flush()

        voto = VotoPopular(
            eleitor_id=eleitor.id,
            proposicao_id=prop.id,
            voto=VotoEnum.SIM,
        )
        repo = VotoPopularRepository(db_session)
        await repo.create(voto)
        return prop, eleitor, voto, repo

    async def test_find_by_eleitor_proposicao(
        self, db_session: AsyncSession, sample_proposicao_data: dict, sample_eleitor_data: dict
    ):
        """Should find vote by voter and proposition."""
        prop, eleitor, voto, repo = await self._setup_vote(
            db_session, sample_proposicao_data, sample_eleitor_data
        )

        found = await repo.find_by_eleitor_proposicao(eleitor.id, prop.id)
        assert found is not None
        assert found.voto == VotoEnum.SIM

    async def test_count_by_proposicao(
        self, db_session: AsyncSession, sample_proposicao_data: dict, sample_eleitor_data: dict
    ):
        """Should count votes grouped by type."""
        prop, eleitor, voto, repo = await self._setup_vote(
            db_session, sample_proposicao_data, sample_eleitor_data
        )

        # Add another vote
        eleitor2 = Eleitor(
            nome="Ana", email="ana@test.com", uf="RJ", channel="telegram"
        )
        db_session.add(eleitor2)
        await db_session.flush()

        voto2 = VotoPopular(
            eleitor_id=eleitor2.id,
            proposicao_id=prop.id,
            voto=VotoEnum.NAO,
        )
        await repo.create(voto2)

        counts = await repo.count_by_proposicao(prop.id)
        assert counts["SIM"] == 1
        assert counts["NAO"] == 1
        assert counts["ABSTENCAO"] == 0
        assert counts["total"] == 2

    async def test_list_by_eleitor(
        self, db_session: AsyncSession, sample_proposicao_data: dict, sample_eleitor_data: dict
    ):
        """Should list all votes by a voter."""
        prop, eleitor, voto, repo = await self._setup_vote(
            db_session, sample_proposicao_data, sample_eleitor_data
        )
        results = await repo.list_by_eleitor(eleitor.id)
        assert len(results) == 1


# ---------------------------------------------------------------------------
# AnaliseIARepository
# ---------------------------------------------------------------------------


class TestAnaliseIARepository:
    """Test AnaliseIARepository specific queries."""

    async def _create_analysis(self, db_session: AsyncSession, proposicao_id: int, versao: int = 1):
        """Helper to create an analysis."""
        analise = AnaliseIA(
            proposicao_id=proposicao_id,
            resumo_leigo=f"Resumo v{versao}",
            impacto_esperado="Impacto",
            areas_afetadas=["Área"],
            argumentos_favor=["Favor"],
            argumentos_contra=["Contra"],
            provedor_llm="google",
            modelo="gemini",
            versao=versao,
        )
        db_session.add(analise)
        await db_session.flush()
        return analise

    async def test_find_latest_by_proposicao(
        self, db_session: AsyncSession, sample_proposicao_data: dict
    ):
        """Should return the latest version."""
        prop = Proposicao(**sample_proposicao_data)
        db_session.add(prop)
        await db_session.flush()

        repo = AnaliseIARepository(db_session)
        await self._create_analysis(db_session, prop.id, versao=1)
        await self._create_analysis(db_session, prop.id, versao=2)

        latest = await repo.find_latest_by_proposicao(prop.id)
        assert latest is not None
        assert latest.versao == 2

    async def test_list_by_proposicao(
        self, db_session: AsyncSession, sample_proposicao_data: dict
    ):
        """Should return all versions ordered by version desc."""
        prop = Proposicao(**sample_proposicao_data)
        db_session.add(prop)
        await db_session.flush()

        repo = AnaliseIARepository(db_session)
        await self._create_analysis(db_session, prop.id, versao=1)
        await self._create_analysis(db_session, prop.id, versao=2)

        results = await repo.list_by_proposicao(prop.id)
        assert len(results) == 2
        assert results[0].versao == 2  # Desc order
