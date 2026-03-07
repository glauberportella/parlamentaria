"""Tests for ComparativoService and calcular_alinhamento."""

import pytest
from datetime import date

from app.domain.eleitor import Eleitor
from app.domain.proposicao import Proposicao
from app.domain.votacao import Votacao
from app.domain.voto_popular import VotoEnum
from app.exceptions import NotFoundException
from app.services.comparativo_service import ComparativoService, calcular_alinhamento
from app.services.voto_popular_service import VotoPopularService


class TestCalcularAlinhamento:
    """Unit tests for the standalone calcular_alinhamento function."""

    def test_total_alinhamento_sim_aprovado(self):
        result = calcular_alinhamento({"SIM": 100, "NAO": 0}, "APROVADO")
        assert result == 1.0

    def test_total_alinhamento_nao_rejeitado(self):
        result = calcular_alinhamento({"SIM": 0, "NAO": 100}, "REJEITADO")
        assert result == 1.0

    def test_total_divergencia_sim_rejeitado(self):
        result = calcular_alinhamento({"SIM": 100, "NAO": 0}, "REJEITADO")
        assert result == 0.0

    def test_total_divergencia_nao_aprovado(self):
        result = calcular_alinhamento({"SIM": 0, "NAO": 100}, "APROVADO")
        assert result == 0.0

    def test_maioria_parcial_alinhada(self):
        result = calcular_alinhamento({"SIM": 75, "NAO": 25}, "APROVADO")
        assert result == 0.75

    def test_maioria_parcial_divergente(self):
        result = calcular_alinhamento({"SIM": 75, "NAO": 25}, "REJEITADO")
        assert result == 0.25

    def test_empate_sem_votos(self):
        result = calcular_alinhamento({"SIM": 0, "NAO": 0}, "APROVADO")
        assert result == 0.5

    def test_50_50(self):
        # SIM == NAO → majority is "NAO" (else branch)
        result = calcular_alinhamento({"SIM": 50, "NAO": 50}, "REJEITADO")
        assert result == 0.5


@pytest.fixture
async def comparativo_service(db_session):
    return ComparativoService(db_session)


@pytest.fixture
async def proposicao(db_session, sample_proposicao_data):
    prop = Proposicao(**sample_proposicao_data)
    db_session.add(prop)
    await db_session.flush()
    await db_session.refresh(prop)
    return prop


@pytest.fixture
async def eleitor(db_session, sample_eleitor_data):
    e = Eleitor(**sample_eleitor_data)
    db_session.add(e)
    await db_session.flush()
    await db_session.refresh(e)
    return e


@pytest.fixture
async def votacao(db_session, proposicao, sample_votacao_data):
    sample_votacao_data["proposicao_id"] = proposicao.id
    v = Votacao(**sample_votacao_data)
    db_session.add(v)
    await db_session.flush()
    await db_session.refresh(v)
    return v


class TestComparativoServiceGerar:
    """Tests for gerar_comparativo."""

    async def test_gerar_comparativo_sem_votos_populares(
        self, comparativo_service, proposicao, votacao,
    ):
        result = await comparativo_service.gerar_comparativo(
            proposicao_id=proposicao.id,
            votacao_camara_id=votacao.id,
            resultado_camara="APROVADO",
            votos_camara_sim=300,
            votos_camara_nao=150,
        )
        assert result.proposicao_id == proposicao.id
        assert result.resultado_camara == "APROVADO"
        assert result.alinhamento == 0.5  # No popular votes → 0.5

    async def test_gerar_comparativo_com_votos_populares(
        self, db_session, comparativo_service, proposicao, votacao, eleitor,
    ):
        voto_service = VotoPopularService(db_session)
        await voto_service.registrar_voto(
            eleitor_id=eleitor.id, proposicao_id=proposicao.id, voto=VotoEnum.SIM,
        )

        result = await comparativo_service.gerar_comparativo(
            proposicao_id=proposicao.id,
            votacao_camara_id=votacao.id,
            resultado_camara="APROVADO",
            votos_camara_sim=300,
            votos_camara_nao=150,
        )
        assert result.voto_popular_sim == 1
        assert result.voto_popular_nao == 0
        assert result.alinhamento == 1.0  # SIM majority + APROVADO = 1.0

    async def test_gerar_comparativo_proposicao_inexistente(self, comparativo_service):
        with pytest.raises(NotFoundException):
            await comparativo_service.gerar_comparativo(
                proposicao_id=99999,
                votacao_camara_id="1",
                resultado_camara="APROVADO",
                votos_camara_sim=10,
                votos_camara_nao=5,
            )


class TestComparativoServiceGetByProposicao:
    """Tests for get_by_proposicao."""

    async def test_get_none_when_empty(self, comparativo_service, proposicao):
        result = await comparativo_service.get_by_proposicao(proposicao.id)
        assert result is None

    async def test_get_after_creation(
        self, comparativo_service, proposicao, votacao,
    ):
        await comparativo_service.gerar_comparativo(
            proposicao_id=proposicao.id,
            votacao_camara_id=votacao.id,
            resultado_camara="REJEITADO",
            votos_camara_sim=100,
            votos_camara_nao=200,
        )
        result = await comparativo_service.get_by_proposicao(proposicao.id)
        assert result is not None
        assert result.resultado_camara == "REJEITADO"
