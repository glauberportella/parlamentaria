"""Tests for Fase 4 — Comparativos and Meu Mandato endpoints."""

import uuid
from datetime import date, datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.comparativo import ComparativoVotacao
from app.domain.deputado import Deputado
from app.domain.parlamentar_user import ParlamentarUser, TipoParlamentarUser
from app.domain.proposicao import Proposicao
from app.domain.votacao import Votacao
from app.domain.voto_popular import VotoPopular, VotoEnum
from app.services.parlamentar_auth_service import ParlamentarAuthService


# ---------------------------------------------------------------------------
#  Module-level fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_parlamentar_user_data() -> dict:
    """ParlamentarUser data for testing."""
    return {
        "email": "parlamentar@camara.leg.br",
        "nome": "João Deputado",
        "cargo": "Deputado Federal",
        "tipo": TipoParlamentarUser.DEPUTADO,
        "ativo": True,
        "convite_usado": True,
    }


@pytest.fixture
async def deputado(db_session: AsyncSession) -> Deputado:
    """Create a Deputado in the test database."""
    dep = Deputado(
        id=67890,
        nome="João Exemplo",
        sigla_partido="PT",
        sigla_uf="RJ",
        email="joao@camara.leg.br",
        situacao="Exercício",
    )
    db_session.add(dep)
    await db_session.flush()
    return dep


@pytest.fixture
async def parlamentar_user(
    db_session: AsyncSession,
    sample_parlamentar_user_data: dict,
) -> ParlamentarUser:
    """Create a ParlamentarUser without linked deputado."""
    user = ParlamentarUser(**sample_parlamentar_user_data)
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.fixture
async def parlamentar_user_with_deputado(
    db_session: AsyncSession,
    deputado: Deputado,
) -> ParlamentarUser:
    """Create a ParlamentarUser linked to a Deputado."""
    user = ParlamentarUser(
        email="deputado@camara.leg.br",
        nome="Dep. João Exemplo",
        cargo="Deputado Federal",
        tipo=TipoParlamentarUser.DEPUTADO,
        ativo=True,
        convite_usado=True,
        deputado_id=deputado.id,
        temas_acompanhados=["economia", "saúde"],
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.fixture
async def proposicao(db_session: AsyncSession) -> Proposicao:
    """Create a test proposição."""
    prop = Proposicao(
        id=12345,
        tipo="PL",
        numero=100,
        ano=2024,
        ementa="Dispõe sobre a transparência legislativa",
        data_apresentacao=date(2024, 3, 15),
        situacao="Em tramitação",
        temas=["Transparência", "Governo"],
    )
    db_session.add(prop)
    await db_session.flush()
    return prop


@pytest.fixture
async def proposicao_saude(db_session: AsyncSession) -> Proposicao:
    """Create a second proposição about health."""
    prop = Proposicao(
        id=12346,
        tipo="PEC",
        numero=45,
        ano=2024,
        ementa="Altera regras do SUS",
        data_apresentacao=date(2024, 5, 1),
        situacao="Em tramitação",
        temas=["Saúde"],
    )
    db_session.add(prop)
    await db_session.flush()
    return prop


@pytest.fixture
async def votacao(
    db_session: AsyncSession, proposicao: Proposicao
) -> Votacao:
    """Create a test votação linked to the proposição."""
    vot = Votacao(
        id="11111",
        proposicao_id=proposicao.id,
        data=datetime(2024, 6, 10, 14, 0, tzinfo=timezone.utc),
        descricao="Votação do PL 100/2024",
        aprovacao=True,
        votos_sim=300,
        votos_nao=150,
        abstencoes=10,
    )
    db_session.add(vot)
    await db_session.flush()
    return vot


@pytest.fixture
async def votacao_saude(
    db_session: AsyncSession, proposicao_saude: Proposicao
) -> Votacao:
    """Create a votação for the health proposição."""
    vot = Votacao(
        id="22222",
        proposicao_id=proposicao_saude.id,
        data=datetime(2024, 7, 5, 10, 0, tzinfo=timezone.utc),
        descricao="Votação da PEC 45/2024",
        aprovacao=False,
        votos_sim=120,
        votos_nao=340,
        abstencoes=5,
    )
    db_session.add(vot)
    await db_session.flush()
    return vot


@pytest.fixture
async def comparativo(
    db_session: AsyncSession,
    proposicao: Proposicao,
    votacao: Votacao,
) -> ComparativoVotacao:
    """Create a comparativo with high alignment (popular SIM + Câmara APROVADO)."""
    comp = ComparativoVotacao(
        proposicao_id=proposicao.id,
        votacao_camara_id=votacao.id,
        voto_popular_sim=910,
        voto_popular_nao=262,
        voto_popular_abstencao=75,
        resultado_camara="APROVADO",
        votos_camara_sim=300,
        votos_camara_nao=150,
        alinhamento=0.85,
        resumo_ia="O resultado parlamentar está alinhado com a vontade popular.",
        data_geracao=datetime(2024, 6, 15, 12, 0, tzinfo=timezone.utc),
    )
    db_session.add(comp)
    await db_session.flush()
    return comp


@pytest.fixture
async def comparativo_divergente(
    db_session: AsyncSession,
    proposicao_saude: Proposicao,
    votacao_saude: Votacao,
) -> ComparativoVotacao:
    """Create a comparativo with low alignment (popular SIM + Câmara REJEITADO)."""
    comp = ComparativoVotacao(
        proposicao_id=proposicao_saude.id,
        votacao_camara_id=votacao_saude.id,
        voto_popular_sim=800,
        voto_popular_nao=200,
        voto_popular_abstencao=50,
        resultado_camara="REJEITADO",
        votos_camara_sim=120,
        votos_camara_nao=340,
        alinhamento=0.2,
        resumo_ia="O resultado parlamentar diverge da vontade popular.",
        data_geracao=datetime(2024, 7, 10, 12, 0, tzinfo=timezone.utc),
    )
    db_session.add(comp)
    await db_session.flush()
    return comp


@pytest.fixture
async def voto_popular(
    db_session: AsyncSession,
    proposicao: Proposicao,
) -> VotoPopular:
    """Create a popular vote for the test proposição."""
    from app.domain.eleitor import Eleitor, NivelVerificacao

    eleitor = Eleitor(
        nome="Maria Teste",
        email="maria@test.com",
        uf="SP",
        channel="telegram",
        chat_id="999888",
        cidadao_brasileiro=True,
        data_nascimento=date(1990, 1, 1),
        verificado=True,
        cpf_hash="b" * 64,
        nivel_verificacao=NivelVerificacao.AUTO_DECLARADO,
    )
    db_session.add(eleitor)
    await db_session.flush()

    voto = VotoPopular(
        eleitor_id=eleitor.id,
        proposicao_id=proposicao.id,
        voto=VotoEnum.SIM,
    )
    db_session.add(voto)
    await db_session.flush()
    return voto


# ===========================================================================
# Tests — GET /parlamentar/comparativos
# ===========================================================================


class TestListarComparativos:
    """Test GET /parlamentar/comparativos endpoint."""

    async def test_list_empty(
        self,
        client: AsyncClient,
        parlamentar_user: ParlamentarUser,
    ) -> None:
        """Empty DB returns paginated response with zero items."""
        access = ParlamentarAuthService.create_access_token(parlamentar_user)

        response = await client.get(
            "/parlamentar/comparativos",
            headers={"Authorization": f"Bearer {access}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []
        assert data["pagina"] == 1

    async def test_list_with_data(
        self,
        client: AsyncClient,
        parlamentar_user: ParlamentarUser,
        comparativo: ComparativoVotacao,
    ) -> None:
        """Returns comparativos with proposição context."""
        access = ParlamentarAuthService.create_access_token(parlamentar_user)

        response = await client.get(
            "/parlamentar/comparativos",
            headers={"Authorization": f"Bearer {access}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1

        item = data["items"][0]
        assert item["proposicao_id"] == 12345
        assert item["tipo"] == "PL"
        assert item["numero"] == 100
        assert item["ano"] == 2024
        assert item["resultado_camara"] == "APROVADO"
        assert item["alinhamento"] == 0.85
        assert item["voto_popular_sim"] == 910
        assert item["votos_camara_sim"] == 300

    async def test_list_multiple(
        self,
        client: AsyncClient,
        parlamentar_user: ParlamentarUser,
        comparativo: ComparativoVotacao,
        comparativo_divergente: ComparativoVotacao,
    ) -> None:
        """Returns multiple comparativos ordered by most recent."""
        access = ParlamentarAuthService.create_access_token(parlamentar_user)

        response = await client.get(
            "/parlamentar/comparativos",
            headers={"Authorization": f"Bearer {access}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        # Most recent first (julho > junho)
        assert data["items"][0]["resultado_camara"] == "REJEITADO"
        assert data["items"][1]["resultado_camara"] == "APROVADO"

    async def test_filter_by_resultado(
        self,
        client: AsyncClient,
        parlamentar_user: ParlamentarUser,
        comparativo: ComparativoVotacao,
        comparativo_divergente: ComparativoVotacao,
    ) -> None:
        """Filter by resultado_camara returns filtered results."""
        access = ParlamentarAuthService.create_access_token(parlamentar_user)

        response = await client.get(
            "/parlamentar/comparativos?resultado=APROVADO",
            headers={"Authorization": f"Bearer {access}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["resultado_camara"] == "APROVADO"

    async def test_filter_by_alinhamento_range(
        self,
        client: AsyncClient,
        parlamentar_user: ParlamentarUser,
        comparativo: ComparativoVotacao,
        comparativo_divergente: ComparativoVotacao,
    ) -> None:
        """Filter by alinhamento min/max returns filtered results."""
        access = ParlamentarAuthService.create_access_token(parlamentar_user)

        response = await client.get(
            "/parlamentar/comparativos?alinhamento_min=0.5&alinhamento_max=1.0",
            headers={"Authorization": f"Bearer {access}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["alinhamento"] >= 0.5

    async def test_filter_by_tema(
        self,
        client: AsyncClient,
        parlamentar_user: ParlamentarUser,
        comparativo: ComparativoVotacao,
        comparativo_divergente: ComparativoVotacao,
    ) -> None:
        """Filter by tema returns matching proposições."""
        access = ParlamentarAuthService.create_access_token(parlamentar_user)

        response = await client.get(
            "/parlamentar/comparativos?tema=Saúde",
            headers={"Authorization": f"Bearer {access}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["proposicao_id"] == 12346

    async def test_order_by_alinhamento_asc(
        self,
        client: AsyncClient,
        parlamentar_user: ParlamentarUser,
        comparativo: ComparativoVotacao,
        comparativo_divergente: ComparativoVotacao,
    ) -> None:
        """Order by alinhamento ascending."""
        access = ParlamentarAuthService.create_access_token(parlamentar_user)

        response = await client.get(
            "/parlamentar/comparativos?ordenar=alinhamento_asc",
            headers={"Authorization": f"Bearer {access}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["items"][0]["alinhamento"] < data["items"][1]["alinhamento"]

    async def test_order_by_alinhamento_desc(
        self,
        client: AsyncClient,
        parlamentar_user: ParlamentarUser,
        comparativo: ComparativoVotacao,
        comparativo_divergente: ComparativoVotacao,
    ) -> None:
        """Order by alinhamento descending."""
        access = ParlamentarAuthService.create_access_token(parlamentar_user)

        response = await client.get(
            "/parlamentar/comparativos?ordenar=alinhamento_desc",
            headers={"Authorization": f"Bearer {access}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["items"][0]["alinhamento"] > data["items"][1]["alinhamento"]

    async def test_pagination(
        self,
        client: AsyncClient,
        parlamentar_user: ParlamentarUser,
        comparativo: ComparativoVotacao,
        comparativo_divergente: ComparativoVotacao,
    ) -> None:
        """Pagination returns correct page and page size."""
        access = ParlamentarAuthService.create_access_token(parlamentar_user)

        response = await client.get(
            "/parlamentar/comparativos?pagina=1&itens=1",
            headers={"Authorization": f"Bearer {access}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["items"]) == 1
        assert data["pagina"] == 1
        assert data["itens_por_pagina"] == 1

    async def test_unauthenticated(self, client: AsyncClient) -> None:
        """GET /parlamentar/comparativos without auth returns 422."""
        response = await client.get("/parlamentar/comparativos")
        assert response.status_code == 422

    async def test_resumo_ia_included(
        self,
        client: AsyncClient,
        parlamentar_user: ParlamentarUser,
        comparativo: ComparativoVotacao,
    ) -> None:
        """Response includes resumo_ia field from comparativo."""
        access = ParlamentarAuthService.create_access_token(parlamentar_user)

        response = await client.get(
            "/parlamentar/comparativos",
            headers={"Authorization": f"Bearer {access}"},
        )

        assert response.status_code == 200
        item = response.json()["items"][0]
        assert item["resumo_ia"] is not None
        assert "alinhado" in item["resumo_ia"]


# ===========================================================================
# Tests — GET /parlamentar/comparativos/evolucao
# ===========================================================================


class TestEvolucaoAlinhamento:
    """Test GET /parlamentar/comparativos/evolucao endpoint."""

    async def test_evolucao_empty(
        self,
        client: AsyncClient,
        parlamentar_user: ParlamentarUser,
    ) -> None:
        """Empty DB returns empty evolution list."""
        access = ParlamentarAuthService.create_access_token(parlamentar_user)

        response = await client.get(
            "/parlamentar/comparativos/evolucao",
            headers={"Authorization": f"Bearer {access}"},
        )

        assert response.status_code == 200
        assert response.json() == []

    async def test_evolucao_with_data(
        self,
        client: AsyncClient,
        parlamentar_user: ParlamentarUser,
        comparativo: ComparativoVotacao,
        comparativo_divergente: ComparativoVotacao,
    ) -> None:
        """Returns monthly evolution data."""
        access = ParlamentarAuthService.create_access_token(parlamentar_user)

        response = await client.get(
            "/parlamentar/comparativos/evolucao",
            headers={"Authorization": f"Bearer {access}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1  # At least one month with data
        for item in data:
            assert "mes" in item
            assert "alinhamento_medio" in item
            assert "total_comparativos" in item
            assert 0.0 <= item["alinhamento_medio"] <= 1.0

    async def test_evolucao_unauthenticated(self, client: AsyncClient) -> None:
        """GET /parlamentar/comparativos/evolucao without auth returns 422."""
        response = await client.get("/parlamentar/comparativos/evolucao")
        assert response.status_code == 422


# ===========================================================================
# Tests — GET /parlamentar/meu-mandato/resumo
# ===========================================================================


class TestMeuMandatoResumo:
    """Test GET /parlamentar/meu-mandato/resumo endpoint."""

    async def test_resumo_empty(
        self,
        client: AsyncClient,
        parlamentar_user: ParlamentarUser,
    ) -> None:
        """User without deputado returns basic resumo with zero stats."""
        access = ParlamentarAuthService.create_access_token(parlamentar_user)

        response = await client.get(
            "/parlamentar/meu-mandato/resumo",
            headers={"Authorization": f"Bearer {access}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["deputado"] is None
        assert data["total_comparativos"] == 0
        assert data["alinhamento_medio"] == 0.5
        assert data["total_votos_populares_recebidos"] == 0

    async def test_resumo_with_deputado(
        self,
        client: AsyncClient,
        parlamentar_user_with_deputado: ParlamentarUser,
    ) -> None:
        """User with linked deputado includes deputy info."""
        access = ParlamentarAuthService.create_access_token(
            parlamentar_user_with_deputado
        )

        response = await client.get(
            "/parlamentar/meu-mandato/resumo",
            headers={"Authorization": f"Bearer {access}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["deputado"] is not None
        assert data["deputado"]["nome"] == "João Exemplo"
        assert data["deputado"]["sigla_partido"] == "PT"
        assert data["deputado"]["sigla_uf"] == "RJ"
        assert data["temas_acompanhados"] == ["economia", "saúde"]

    async def test_resumo_with_comparativos(
        self,
        client: AsyncClient,
        parlamentar_user: ParlamentarUser,
        comparativo: ComparativoVotacao,
        comparativo_divergente: ComparativoVotacao,
    ) -> None:
        """Resumo includes aggregated comparativo statistics."""
        access = ParlamentarAuthService.create_access_token(parlamentar_user)

        response = await client.get(
            "/parlamentar/meu-mandato/resumo",
            headers={"Authorization": f"Bearer {access}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_comparativos"] == 2
        assert data["comparativos_alinhados"] == 1  # alinhamento >= 0.5
        assert data["comparativos_divergentes"] == 1  # alinhamento < 0.5
        # Average of 0.85 and 0.2 = 0.525
        assert 0.4 <= data["alinhamento_medio"] <= 0.6
        assert data["proposicoes_acompanhadas"] == 2

    async def test_resumo_with_votos_populares(
        self,
        client: AsyncClient,
        parlamentar_user: ParlamentarUser,
        voto_popular: VotoPopular,
    ) -> None:
        """Resumo counts total popular votes."""
        access = ParlamentarAuthService.create_access_token(parlamentar_user)

        response = await client.get(
            "/parlamentar/meu-mandato/resumo",
            headers={"Authorization": f"Bearer {access}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_votos_populares_recebidos"] == 1

    async def test_resumo_unauthenticated(self, client: AsyncClient) -> None:
        """GET /parlamentar/meu-mandato/resumo without auth returns 422."""
        response = await client.get("/parlamentar/meu-mandato/resumo")
        assert response.status_code == 422


# ===========================================================================
# Tests — GET /parlamentar/meu-mandato/alinhamento
# ===========================================================================


class TestMeuMandatoAlinhamento:
    """Test GET /parlamentar/meu-mandato/alinhamento endpoint."""

    async def test_alinhamento_empty(
        self,
        client: AsyncClient,
        parlamentar_user: ParlamentarUser,
    ) -> None:
        """Empty DB returns default alignment structure."""
        access = ParlamentarAuthService.create_access_token(parlamentar_user)

        response = await client.get(
            "/parlamentar/meu-mandato/alinhamento",
            headers={"Authorization": f"Bearer {access}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["pessoal"] == []
        assert data["partido"] == []
        assert data["uf"] == []
        assert data["alinhamento_medio_pessoal"] == 0.5
        assert data["sigla_partido"] is None
        assert data["sigla_uf"] is None

    async def test_alinhamento_with_deputado(
        self,
        client: AsyncClient,
        parlamentar_user_with_deputado: ParlamentarUser,
        comparativo: ComparativoVotacao,
    ) -> None:
        """User with deputado includes party/state labels."""
        access = ParlamentarAuthService.create_access_token(
            parlamentar_user_with_deputado
        )

        response = await client.get(
            "/parlamentar/meu-mandato/alinhamento",
            headers={"Authorization": f"Bearer {access}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["sigla_partido"] == "PT"
        assert data["sigla_uf"] == "RJ"
        assert len(data["pessoal"]) >= 1

    async def test_alinhamento_series_structure(
        self,
        client: AsyncClient,
        parlamentar_user: ParlamentarUser,
        comparativo: ComparativoVotacao,
        comparativo_divergente: ComparativoVotacao,
    ) -> None:
        """Series items have correct structure."""
        access = ParlamentarAuthService.create_access_token(parlamentar_user)

        response = await client.get(
            "/parlamentar/meu-mandato/alinhamento",
            headers={"Authorization": f"Bearer {access}"},
        )

        assert response.status_code == 200
        data = response.json()
        for item in data["pessoal"]:
            assert "mes" in item
            assert "alinhamento" in item
            assert "total" in item
            assert 0.0 <= item["alinhamento"] <= 1.0

    async def test_alinhamento_meses_param(
        self,
        client: AsyncClient,
        parlamentar_user: ParlamentarUser,
        comparativo: ComparativoVotacao,
    ) -> None:
        """The meses parameter controls time window."""
        access = ParlamentarAuthService.create_access_token(parlamentar_user)

        response = await client.get(
            "/parlamentar/meu-mandato/alinhamento?meses=6",
            headers={"Authorization": f"Bearer {access}"},
        )

        assert response.status_code == 200
        # Should still return data (comparativos are from 2024 which may be in range)
        # The important thing is the request succeeds and returns valid structure
        data = response.json()
        assert "pessoal" in data
        assert "partido" in data
        assert "uf" in data

    async def test_alinhamento_unauthenticated(self, client: AsyncClient) -> None:
        """GET /parlamentar/meu-mandato/alinhamento without auth returns 422."""
        response = await client.get("/parlamentar/meu-mandato/alinhamento")
        assert response.status_code == 422
