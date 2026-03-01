"""Tests for VotoPopularService."""

import pytest
import uuid
from datetime import date

from app.domain.eleitor import Eleitor
from app.domain.proposicao import Proposicao
from app.domain.voto_popular import VotoEnum
from app.exceptions import NotFoundException
from app.services.voto_popular_service import VotoPopularService


@pytest.fixture
async def service(db_session):
    """Provide a VotoPopularService instance."""
    return VotoPopularService(db_session)


@pytest.fixture
async def proposicao(db_session, sample_proposicao_data):
    """Create a proposition in the database."""
    prop = Proposicao(**sample_proposicao_data)
    db_session.add(prop)
    await db_session.flush()
    await db_session.refresh(prop)
    return prop


@pytest.fixture
async def eleitor(db_session, sample_eleitor_data):
    """Create a voter in the database."""
    e = Eleitor(**sample_eleitor_data)
    db_session.add(e)
    await db_session.flush()
    await db_session.refresh(e)
    return e


class TestVotoPopularRegistrar:
    """Tests for registrar_voto."""

    async def test_registrar_primeiro_voto(self, service, eleitor, proposicao):
        result = await service.registrar_voto(
            eleitor_id=eleitor.id,
            proposicao_id=proposicao.id,
            voto=VotoEnum.SIM,
        )
        assert result.voto == VotoEnum.SIM
        assert result.eleitor_id == eleitor.id
        assert result.proposicao_id == proposicao.id

    async def test_registrar_voto_com_justificativa(self, service, eleitor, proposicao):
        result = await service.registrar_voto(
            eleitor_id=eleitor.id,
            proposicao_id=proposicao.id,
            voto=VotoEnum.NAO,
            justificativa="Discordo da medida",
        )
        assert result.voto == VotoEnum.NAO
        assert result.justificativa == "Discordo da medida"

    async def test_registrar_voto_idempotente_atualiza(self, service, eleitor, proposicao):
        # First vote
        await service.registrar_voto(
            eleitor_id=eleitor.id,
            proposicao_id=proposicao.id,
            voto=VotoEnum.SIM,
        )
        # Second vote on same proposition — should update
        result = await service.registrar_voto(
            eleitor_id=eleitor.id,
            proposicao_id=proposicao.id,
            voto=VotoEnum.NAO,
        )
        assert result.voto == VotoEnum.NAO

        # Should have only 1 vote total
        votos = await service.list_by_eleitor(eleitor.id)
        assert len(votos) == 1

    async def test_registrar_voto_proposicao_inexistente(self, service, eleitor):
        with pytest.raises(NotFoundException):
            await service.registrar_voto(
                eleitor_id=eleitor.id,
                proposicao_id=99999,
                voto=VotoEnum.SIM,
            )


class TestVotoPopularResultado:
    """Tests for obter_resultado."""

    async def test_resultado_sem_votos(self, service, proposicao):
        result = await service.obter_resultado(proposicao.id)
        assert result["total"] == 0
        assert result["percentual_sim"] == 0.0
        assert result["percentual_nao"] == 0.0

    async def test_resultado_com_votos(self, service, eleitor, proposicao, db_session):
        await service.registrar_voto(
            eleitor_id=eleitor.id, proposicao_id=proposicao.id, voto=VotoEnum.SIM,
        )
        # Create second voter
        e2 = Eleitor(
            nome="José", email="jose@test.com", uf="RJ", chat_id="2222", channel="telegram",
        )
        db_session.add(e2)
        await db_session.flush()
        await db_session.refresh(e2)

        await service.registrar_voto(
            eleitor_id=e2.id, proposicao_id=proposicao.id, voto=VotoEnum.NAO,
        )

        result = await service.obter_resultado(proposicao.id)
        assert result["total"] == 2
        assert result["SIM"] == 1
        assert result["NAO"] == 1
        assert result["percentual_sim"] == 50.0
        assert result["percentual_nao"] == 50.0


class TestVotoPopularGetVoto:
    """Tests for get_voto."""

    async def test_get_voto_existing(self, service, eleitor, proposicao):
        await service.registrar_voto(
            eleitor_id=eleitor.id, proposicao_id=proposicao.id, voto=VotoEnum.ABSTENCAO,
        )
        result = await service.get_voto(eleitor.id, proposicao.id)
        assert result is not None
        assert result.voto == VotoEnum.ABSTENCAO

    async def test_get_voto_not_found(self, service, eleitor, proposicao):
        result = await service.get_voto(eleitor.id, proposicao.id)
        assert result is None


class TestVotoPopularListByEleitor:
    """Tests for list_by_eleitor."""

    async def test_list_by_eleitor_empty(self, service, eleitor):
        result = await service.list_by_eleitor(eleitor.id)
        assert len(result) == 0

    async def test_list_by_eleitor_with_votes(self, service, eleitor, proposicao, db_session):
        await service.registrar_voto(
            eleitor_id=eleitor.id, proposicao_id=proposicao.id, voto=VotoEnum.SIM,
        )
        # Create second proposition
        p2 = Proposicao(
            id=22222, tipo="PEC", numero=5, ano=2024,
            ementa="Outra proposição", data_apresentacao=date(2024, 1, 1),
            situacao="Em tramitação",
        )
        db_session.add(p2)
        await db_session.flush()

        await service.registrar_voto(
            eleitor_id=eleitor.id, proposicao_id=p2.id, voto=VotoEnum.NAO,
        )

        result = await service.list_by_eleitor(eleitor.id)
        assert len(result) == 2
