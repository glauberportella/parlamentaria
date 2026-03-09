"""Tests for Fase 5 — Polimento: PUT /auth/me + Export CSV endpoints."""

import uuid
from datetime import date, datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.comparativo import ComparativoVotacao
from app.domain.deputado import Deputado
from app.domain.eleitor import Eleitor, NivelVerificacao
from app.domain.parlamentar_user import ParlamentarUser, TipoParlamentarUser
from app.domain.proposicao import Proposicao
from app.domain.votacao import Votacao
from app.domain.voto_popular import VotoPopular, VotoEnum
from app.services.parlamentar_auth_service import ParlamentarAuthService


# ---------------------------------------------------------------------------
#  Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def parlamentar_user(db_session: AsyncSession) -> ParlamentarUser:
    """Create a basic ParlamentarUser."""
    user = ParlamentarUser(
        email="fase5@camara.leg.br",
        nome="Teste Fase5",
        cargo="Assessor Parlamentar",
        tipo=TipoParlamentarUser.ASSESSOR,
        ativo=True,
        convite_usado=True,
        temas_acompanhados=["economia"],
        notificacoes_email=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.fixture
async def deputado(db_session: AsyncSession) -> Deputado:
    """Create a Deputado."""
    dep = Deputado(
        id=55555,
        nome="Dep. Fase5",
        sigla_partido="MDB",
        sigla_uf="SP",
        email="dep@camara.leg.br",
        situacao="Exercício",
    )
    db_session.add(dep)
    await db_session.flush()
    return dep


@pytest.fixture
async def proposicao(db_session: AsyncSession) -> Proposicao:
    """Create a test proposição."""
    prop = Proposicao(
        id=50001,
        tipo="PL",
        numero=200,
        ano=2024,
        ementa="Proposição de teste para exportação",
        data_apresentacao=date(2024, 2, 10),
        situacao="Em tramitação",
        temas=["Economia", "Trabalho"],
    )
    db_session.add(prop)
    await db_session.flush()
    return prop


@pytest.fixture
async def proposicao2(db_session: AsyncSession) -> Proposicao:
    """Create a second proposição."""
    prop = Proposicao(
        id=50002,
        tipo="PEC",
        numero=10,
        ano=2024,
        ementa="Segunda proposição teste",
        data_apresentacao=date(2024, 4, 1),
        situacao="Em tramitação",
        temas=["Saúde"],
    )
    db_session.add(prop)
    await db_session.flush()
    return prop


@pytest.fixture
async def eleitor(db_session: AsyncSession) -> Eleitor:
    """Create a test eleitor."""
    e = Eleitor(
        nome="Eleitor Teste",
        email="eleitor@test.com",
        uf="SP",
        channel="telegram",
        chat_id="exp_111",
        cidadao_brasileiro=True,
        data_nascimento=date(1985, 6, 15),
        verificado=True,
        cpf_hash="e" * 64,
        nivel_verificacao=NivelVerificacao.AUTO_DECLARADO,
    )
    db_session.add(e)
    await db_session.flush()
    return e


@pytest.fixture
async def voto(
    db_session: AsyncSession, eleitor: Eleitor, proposicao: Proposicao
) -> VotoPopular:
    """Create a vote for the test proposição."""
    v = VotoPopular(
        eleitor_id=eleitor.id,
        proposicao_id=proposicao.id,
        voto=VotoEnum.SIM,
    )
    db_session.add(v)
    await db_session.flush()
    return v


@pytest.fixture
async def votacao(
    db_session: AsyncSession, proposicao: Proposicao
) -> Votacao:
    """Create a votação."""
    vot = Votacao(
        id="exp_v1",
        proposicao_id=proposicao.id,
        data=datetime(2024, 6, 10, 14, 0, tzinfo=timezone.utc),
        descricao="Votação PL 200/2024",
        aprovacao=True,
        votos_sim=300,
        votos_nao=100,
        abstencoes=5,
    )
    db_session.add(vot)
    await db_session.flush()
    return vot


@pytest.fixture
async def comparativo(
    db_session: AsyncSession, proposicao: Proposicao, votacao: Votacao
) -> ComparativoVotacao:
    """Create a comparativo."""
    comp = ComparativoVotacao(
        proposicao_id=proposicao.id,
        votacao_camara_id=votacao.id,
        voto_popular_sim=800,
        voto_popular_nao=200,
        voto_popular_abstencao=50,
        resultado_camara="APROVADO",
        votos_camara_sim=300,
        votos_camara_nao=100,
        alinhamento=0.9,
        resumo_ia="Alinhado com a vontade popular.",
        data_geracao=datetime(2024, 6, 15, 12, 0, tzinfo=timezone.utc),
    )
    db_session.add(comp)
    await db_session.flush()
    return comp


# ===========================================================================
# Tests — PUT /parlamentar/auth/me
# ===========================================================================


class TestUpdateProfile:
    """Test PUT /parlamentar/auth/me endpoint."""

    async def test_update_nome(
        self, client: AsyncClient, parlamentar_user: ParlamentarUser
    ) -> None:
        """Update user nome via PUT /me."""
        access = ParlamentarAuthService.create_access_token(parlamentar_user)

        response = await client.put(
            "/parlamentar/auth/me",
            headers={"Authorization": f"Bearer {access}"},
            json={"nome": "Novo Nome"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["nome"] == "Novo Nome"
        # Other fields unchanged
        assert data["email"] == "fase5@camara.leg.br"
        assert data["notificacoes_email"] is True

    async def test_update_temas(
        self, client: AsyncClient, parlamentar_user: ParlamentarUser
    ) -> None:
        """Update temas_acompanhados."""
        access = ParlamentarAuthService.create_access_token(parlamentar_user)

        response = await client.put(
            "/parlamentar/auth/me",
            headers={"Authorization": f"Bearer {access}"},
            json={"temas_acompanhados": ["saúde", "educação", "segurança"]},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["temas_acompanhados"] == ["saúde", "educação", "segurança"]

    async def test_update_notificacoes(
        self, client: AsyncClient, parlamentar_user: ParlamentarUser
    ) -> None:
        """Toggle notificacoes_email off."""
        access = ParlamentarAuthService.create_access_token(parlamentar_user)

        response = await client.put(
            "/parlamentar/auth/me",
            headers={"Authorization": f"Bearer {access}"},
            json={"notificacoes_email": False},
        )

        assert response.status_code == 200
        assert response.json()["notificacoes_email"] is False

    async def test_update_partial(
        self, client: AsyncClient, parlamentar_user: ParlamentarUser
    ) -> None:
        """Partial update (only cargo) keeps other fields."""
        access = ParlamentarAuthService.create_access_token(parlamentar_user)

        response = await client.put(
            "/parlamentar/auth/me",
            headers={"Authorization": f"Bearer {access}"},
            json={"cargo": "Chefe de Gabinete"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["cargo"] == "Chefe de Gabinete"
        assert data["nome"] == "Teste Fase5"  # unchanged

    async def test_update_empty_body(
        self, client: AsyncClient, parlamentar_user: ParlamentarUser
    ) -> None:
        """Empty body returns unchanged user (no error)."""
        access = ParlamentarAuthService.create_access_token(parlamentar_user)

        response = await client.put(
            "/parlamentar/auth/me",
            headers={"Authorization": f"Bearer {access}"},
            json={},
        )

        assert response.status_code == 200
        assert response.json()["nome"] == "Teste Fase5"

    async def test_update_unauthenticated(self, client: AsyncClient) -> None:
        """PUT /me without auth returns 401."""
        response = await client.put(
            "/parlamentar/auth/me",
            json={"nome": "Hacker"},
        )
        assert response.status_code in (401, 422)


# ===========================================================================
# Tests — GET /parlamentar/exportar/votos
# ===========================================================================


class TestExportarVotos:
    """Test GET /parlamentar/exportar/votos CSV export."""

    async def test_export_empty(
        self, client: AsyncClient, parlamentar_user: ParlamentarUser
    ) -> None:
        """Empty DB returns CSV with header only."""
        access = ParlamentarAuthService.create_access_token(parlamentar_user)

        response = await client.get(
            "/parlamentar/exportar/votos",
            headers={"Authorization": f"Bearer {access}"},
        )

        assert response.status_code == 200
        assert "text/csv" in response.headers.get("content-type", "")
        assert "attachment" in response.headers.get("content-disposition", "")

        lines = response.text.strip().split("\n")
        assert len(lines) == 1  # header only
        assert "tipo" in lines[0]
        assert "voto" in lines[0]

    async def test_export_with_data(
        self,
        client: AsyncClient,
        parlamentar_user: ParlamentarUser,
        voto: VotoPopular,
    ) -> None:
        """Export CSV includes vote data row."""
        access = ParlamentarAuthService.create_access_token(parlamentar_user)

        response = await client.get(
            "/parlamentar/exportar/votos",
            headers={"Authorization": f"Bearer {access}"},
        )

        assert response.status_code == 200
        lines = response.text.strip().split("\n")
        assert len(lines) == 2  # header + 1 data row
        assert "PL" in lines[1]
        assert "SIM" in lines[1]
        assert "SP" in lines[1]  # UF from eleitor

    async def test_export_filter_proposicao(
        self,
        client: AsyncClient,
        parlamentar_user: ParlamentarUser,
        voto: VotoPopular,
    ) -> None:
        """Filter export by proposicao_id."""
        access = ParlamentarAuthService.create_access_token(parlamentar_user)

        # Existing proposicao
        response = await client.get(
            "/parlamentar/exportar/votos?proposicao_id=50001",
            headers={"Authorization": f"Bearer {access}"},
        )
        assert response.status_code == 200
        lines = response.text.strip().split("\n")
        assert len(lines) == 2

        # Non-existing proposicao
        response = await client.get(
            "/parlamentar/exportar/votos?proposicao_id=99999",
            headers={"Authorization": f"Bearer {access}"},
        )
        assert response.status_code == 200
        lines = response.text.strip().split("\n")
        assert len(lines) == 1  # header only

    async def test_export_unauthenticated(self, client: AsyncClient) -> None:
        """CSV export requires auth."""
        response = await client.get("/parlamentar/exportar/votos")
        assert response.status_code in (401, 422)


# ===========================================================================
# Tests — GET /parlamentar/exportar/comparativos
# ===========================================================================


class TestExportarComparativos:
    """Test GET /parlamentar/exportar/comparativos CSV export."""

    async def test_export_empty(
        self, client: AsyncClient, parlamentar_user: ParlamentarUser
    ) -> None:
        """Empty DB returns CSV with header only."""
        access = ParlamentarAuthService.create_access_token(parlamentar_user)

        response = await client.get(
            "/parlamentar/exportar/comparativos",
            headers={"Authorization": f"Bearer {access}"},
        )

        assert response.status_code == 200
        assert "text/csv" in response.headers.get("content-type", "")
        lines = response.text.strip().split("\n")
        assert len(lines) == 1
        assert "proposicao" in lines[0]
        assert "alinhamento" in lines[0]

    async def test_export_with_data(
        self,
        client: AsyncClient,
        parlamentar_user: ParlamentarUser,
        comparativo: ComparativoVotacao,
    ) -> None:
        """Export CSV includes comparativo data row."""
        access = ParlamentarAuthService.create_access_token(parlamentar_user)

        response = await client.get(
            "/parlamentar/exportar/comparativos",
            headers={"Authorization": f"Bearer {access}"},
        )

        assert response.status_code == 200
        lines = response.text.strip().split("\n")
        assert len(lines) == 2
        assert "PL 200/2024" in lines[1]
        assert "APROVADO" in lines[1]
        assert "0.9" in lines[1]

    async def test_export_filter_resultado(
        self,
        client: AsyncClient,
        parlamentar_user: ParlamentarUser,
        comparativo: ComparativoVotacao,
    ) -> None:
        """Filter comparativos by resultado."""
        access = ParlamentarAuthService.create_access_token(parlamentar_user)

        response = await client.get(
            "/parlamentar/exportar/comparativos?resultado=APROVADO",
            headers={"Authorization": f"Bearer {access}"},
        )
        assert response.status_code == 200
        lines = response.text.strip().split("\n")
        assert len(lines) == 2

        response = await client.get(
            "/parlamentar/exportar/comparativos?resultado=REJEITADO",
            headers={"Authorization": f"Bearer {access}"},
        )
        assert response.status_code == 200
        lines = response.text.strip().split("\n")
        assert len(lines) == 1  # header only — our single comparativo is APROVADO

    async def test_export_unauthenticated(self, client: AsyncClient) -> None:
        """CSV export requires auth."""
        response = await client.get("/parlamentar/exportar/comparativos")
        assert response.status_code in (401, 422)
