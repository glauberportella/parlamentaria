"""Tests for Câmara API type models."""

import pytest

from app.integrations.camara_types import (
    AutorAPI,
    CamaraAPIResponse,
    DeputadoDetalhadoAPI,
    DeputadoResumoAPI,
    DespesaAPI,
    EventoResumoAPI,
    ItemPautaAPI,
    OrientacaoAPI,
    ProposicaoDetalhadaAPI,
    ProposicaoResumoAPI,
    TemaAPI,
    TramitacaoAPI,
    VotacaoDetalhadaAPI,
    VotacaoResumoAPI,
    VotoParlamentarAPI,
)


class TestProposicaoTypes:
    """Test proposition-related types."""

    def test_resumo(self):
        dto = ProposicaoResumoAPI(
            id=1, siglaTipo="PL", numero=100, ano=2024, ementa="Teste"
        )
        assert dto.id == 1
        assert dto.siglaTipo == "PL"

    def test_detalhada(self):
        dto = ProposicaoDetalhadaAPI(
            id=1, siglaTipo="PL", numero=100, ano=2024, ementa="Teste",
            urlInteiroTeor="https://example.com/teor.pdf"
        )
        assert dto.urlInteiroTeor is not None

    def test_autor(self):
        dto = AutorAPI(nome="Dep. Teste", tipo="Deputado")
        assert dto.nome == "Dep. Teste"

    def test_tema(self):
        dto = TemaAPI(codTema=40, tema="Educação")
        assert dto.codTema == 40

    def test_tramitacao(self):
        dto = TramitacaoAPI(descricaoSituacao="Aguardando votação")
        assert dto.descricaoSituacao is not None


class TestVotacaoTypes:
    """Test vote-related types."""

    def test_resumo(self):
        dto = VotacaoResumoAPI(id="v1", descricao="Votação 1")
        assert dto.id == "v1"

    def test_detalhada(self):
        dto = VotacaoDetalhadaAPI(id="v1", descricao="Votação 1")
        assert dto.id == "v1"

    def test_orientacao(self):
        dto = OrientacaoAPI(
            nomeBancada="Governo",
            orientacao="Sim"
        )
        assert dto.orientacao == "Sim"

    def test_voto_parlamentar(self):
        dto = VotoParlamentarAPI(tipoVoto="Sim")
        assert dto.tipoVoto == "Sim"


class TestDeputadoTypes:
    """Test deputy-related types."""

    def test_resumo(self):
        dto = DeputadoResumoAPI(id=1, nome="Dep. Teste")
        assert dto.id == 1

    def test_detalhado(self):
        dto = DeputadoDetalhadoAPI(id=1, nomeCivil="João da Silva")
        assert dto.nomeCivil == "João da Silva"

    def test_despesa(self):
        dto = DespesaAPI(
            ano=2024, mes=6, tipoDespesa="Combustível", valorDocumento=150.0
        )
        assert dto.valorDocumento == 150.0


class TestEventoTypes:
    """Test event-related types."""

    def test_evento_resumo(self):
        dto = EventoResumoAPI(id=1, descricao="Sessão Plenária")
        assert dto.id == 1

    def test_item_pauta(self):
        dto = ItemPautaAPI(ordem=1, topico="PL 100/2024")
        assert dto.ordem == 1


class TestCamaraAPIResponse:
    """Test generic response wrapper."""

    def test_with_dados(self):
        dto = CamaraAPIResponse(dados=[{"id": 1}], links=[])
        assert len(dto.dados) == 1

    def test_empty(self):
        dto = CamaraAPIResponse(dados=[])
        assert len(dto.dados) == 0
        assert len(dto.links) == 0
