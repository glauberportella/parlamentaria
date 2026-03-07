"""Tests for Pydantic schemas (DTOs)."""

import uuid
from datetime import date, datetime, timezone

import pytest
from pydantic import ValidationError

from app.schemas.proposicao import ProposicaoCreate, ProposicaoUpdate, ProposicaoResponse
from app.schemas.votacao import VotacaoCreate, VotacaoResponse
from app.schemas.deputado import DeputadoCreate, DeputadoResponse
from app.schemas.eleitor import EleitorCreate, EleitorUpdate, EleitorResponse
from app.schemas.voto_popular import VotoPopularCreate, VotoPopularResponse, ResultadoVotacaoPopular
from app.schemas.analise_ia import AnaliseIACreate, AnaliseIAResponse
from app.schemas.assinatura import (
    AssinaturaRSSCreate,
    AssinaturaRSSResponse,
    AssinaturaWebhookCreate,
    AssinaturaWebhookResponse,
)
from app.schemas.comparativo import ComparativoCreate, ComparativoResponse
from app.domain.voto_popular import VotoEnum


class TestProposicaoSchema:
    """Test Proposicao DTOs."""

    def test_create_valid(self):
        """Should validate correct data."""
        dto = ProposicaoCreate(
            id=123,
            tipo="PL",
            numero=100,
            ano=2024,
            ementa="Ementa teste",
            data_apresentacao=date(2024, 3, 15),
        )
        assert dto.id == 123
        assert dto.tipo == "PL"

    def test_create_missing_required(self):
        """Should reject missing required fields."""
        with pytest.raises(ValidationError):
            ProposicaoCreate(tipo="PL", numero=100)  # missing ano, ementa, etc.

    def test_update_partial(self):
        """Update DTO should accept partial data."""
        dto = ProposicaoUpdate(ementa="Nova ementa")
        assert dto.ementa == "Nova ementa"
        assert dto.situacao is None

    def test_response_from_attributes(self):
        """Response DTO should support from_attributes."""
        data = {
            "id": 123,
            "tipo": "PL",
            "numero": 100,
            "ano": 2024,
            "ementa": "Teste",
            "data_apresentacao": date(2024, 1, 1),
            "situacao": "Em tramitação",
            "ultima_sincronizacao": datetime.now(timezone.utc),
            "created_at": datetime.now(timezone.utc),
        }
        dto = ProposicaoResponse(**data)
        assert dto.id == 123


class TestVotacaoSchema:
    """Test Votacao DTOs."""

    def test_create_valid(self):
        dto = VotacaoCreate(
            id="111",
            data=datetime.now(timezone.utc),
            descricao="Votação teste",
        )
        assert dto.id == "111"
        assert dto.votos_sim == 0

    def test_response(self):
        dto = VotacaoResponse(
            id="111",
            data=datetime.now(timezone.utc),
            descricao="Votação",
            votos_sim=100,
            votos_nao=50,
            abstencoes=5,
            created_at=datetime.now(timezone.utc),
        )
        assert dto.votos_sim == 100


class TestDeputadoSchema:
    """Test Deputado DTOs."""

    def test_create_valid(self):
        dto = DeputadoCreate(id=1, nome="Dep. Teste")
        assert dto.id == 1

    def test_response(self):
        dto = DeputadoResponse(
            id=1,
            nome="Dep. Teste",
            sigla_partido="PT",
            sigla_uf="SP",
            created_at=datetime.now(timezone.utc),
        )
        assert dto.sigla_partido == "PT"


class TestEleitorSchema:
    """Test Eleitor DTOs."""

    def test_create_valid(self):
        dto = EleitorCreate(
            nome="Maria",
            email="maria@test.com",
            uf="SP",
        )
        assert dto.channel == "telegram"

    def test_create_invalid_uf(self):
        """UF should be exactly 2 characters."""
        with pytest.raises(ValidationError):
            EleitorCreate(nome="Maria", email="maria@test.com", uf="SPP")

    def test_update_partial(self):
        dto = EleitorUpdate(verificado=True)
        assert dto.verificado is True
        assert dto.nome is None

    def test_response(self):
        dto = EleitorResponse(
            id=uuid.uuid4(),
            nome="Maria",
            email="m@test.com",
            uf="SP",
            channel="telegram",
            verificado=False,
            data_cadastro=datetime.now(timezone.utc),
        )
        assert dto.verificado is False


class TestVotoPopularSchema:
    """Test VotoPopular DTOs."""

    def test_create_valid(self):
        dto = VotoPopularCreate(
            eleitor_id=uuid.uuid4(),
            proposicao_id=123,
            voto=VotoEnum.SIM,
        )
        assert dto.voto == VotoEnum.SIM

    def test_resultado_aggregation(self):
        dto = ResultadoVotacaoPopular(
            proposicao_id=123,
            total_sim=100,
            total_nao=50,
            total_abstencao=10,
            total_votos=160,
            percentual_sim=62.5,
            percentual_nao=31.25,
            percentual_abstencao=6.25,
        )
        assert dto.total_votos == 160


class TestAnaliseIASchema:
    """Test AnaliseIA DTOs."""

    def test_create_valid(self):
        dto = AnaliseIACreate(
            proposicao_id=123,
            resumo_leigo="Resumo",
            impacto_esperado="Impacto",
            areas_afetadas=["Saúde"],
            argumentos_favor=["Arg 1"],
            argumentos_contra=["Arg 2"],
            provedor_llm="google",
            modelo="gemini-2.0-flash",
        )
        assert dto.provedor_llm == "google"

    def test_response(self):
        dto = AnaliseIAResponse(
            id=uuid.uuid4(),
            proposicao_id=123,
            resumo_leigo="R",
            impacto_esperado="I",
            areas_afetadas=["A"],
            argumentos_favor=["F"],
            argumentos_contra=["C"],
            provedor_llm="google",
            modelo="gemini",
            data_geracao=datetime.now(timezone.utc),
            versao=1,
        )
        assert dto.versao == 1


class TestAssinaturaSchema:
    """Test Assinatura DTOs."""

    def test_rss_create(self):
        dto = AssinaturaRSSCreate(nome="Portal", filtro_temas=["Saúde"])
        assert dto.nome == "Portal"

    def test_rss_response(self):
        dto = AssinaturaRSSResponse(
            id=uuid.uuid4(),
            nome="Portal",
            token="abc123",
            ativo=True,
            data_criacao=datetime.now(timezone.utc),
        )
        assert dto.ativo is True

    def test_webhook_create(self):
        dto = AssinaturaWebhookCreate(
            nome="My Webhook",
            url="https://example.com/hook",
            eventos=["nova_proposicao"],
        )
        assert len(dto.eventos) == 1

    def test_webhook_create_empty_eventos_fails(self):
        """eventos should require at least 1 item."""
        with pytest.raises(ValidationError):
            AssinaturaWebhookCreate(
                nome="My Webhook",
                url="https://example.com/hook",
                eventos=[],
            )

    def test_webhook_response(self):
        dto = AssinaturaWebhookResponse(
            id=uuid.uuid4(),
            nome="WH",
            url="https://example.com",
            eventos=["e"],
            ativo=True,
            data_criacao=datetime.now(timezone.utc),
            falhas_consecutivas=0,
        )
        assert dto.falhas_consecutivas == 0


class TestComparativoSchema:
    """Test Comparativo DTOs."""

    def test_create_valid(self):
        dto = ComparativoCreate(
            proposicao_id=123,
            votacao_camara_id="456",
            resultado_camara="APROVADO",
            alinhamento=0.8,
        )
        assert dto.alinhamento == 0.8

    def test_create_alinhamento_out_of_range(self):
        """alinhamento should be between 0.0 and 1.0."""
        with pytest.raises(ValidationError):
            ComparativoCreate(
                proposicao_id=123,
                votacao_camara_id="456",
                resultado_camara="APROVADO",
                alinhamento=1.5,
            )

    def test_response(self):
        dto = ComparativoResponse(
            id=uuid.uuid4(),
            proposicao_id=123,
            votacao_camara_id="456",
            voto_popular_sim=100,
            voto_popular_nao=50,
            voto_popular_abstencao=10,
            resultado_camara="APROVADO",
            votos_camara_sim=300,
            votos_camara_nao=150,
            alinhamento=0.75,
            data_geracao=datetime.now(timezone.utc),
        )
        assert dto.alinhamento == 0.75
