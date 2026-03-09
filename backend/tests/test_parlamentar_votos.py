"""Tests for the parlamentar votos analíticos endpoints.

Covers: /parlamentar/votos/por-tema, /por-uf, /timeline, /ranking
"""

import secrets
import uuid
from datetime import date, datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.eleitor import Eleitor, NivelVerificacao
from app.domain.parlamentar_user import ParlamentarUser, TipoParlamentarUser
from app.domain.proposicao import Proposicao
from app.domain.voto_popular import VotoPopular, VotoEnum
from app.services.parlamentar_auth_service import ParlamentarAuthService


# ---------------------------------------------------------------------------
# Fixtures (scoped to this module)
# ---------------------------------------------------------------------------


@pytest.fixture
async def parlamentar_user(db_session: AsyncSession) -> ParlamentarUser:
    """Create and persist a ParlamentarUser for testing."""
    user = ParlamentarUser(
        email="parlamentar-votos@camara.leg.br",
        nome="João Votos Test",
        cargo="Deputado Federal",
        tipo=TipoParlamentarUser.DEPUTADO,
        ativo=True,
        convite_usado=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user


async def _create_proposicao(
    db_session: AsyncSession,
    *,
    id: int,
    temas: list[str] | None = None,
    tipo: str = "PL",
    numero: int = 1,
    ano: int = 2024,
    ementa: str = "Proposição de teste",
) -> Proposicao:
    """Helper to create a proposição."""
    prop = Proposicao(
        id=id,
        tipo=tipo,
        numero=numero,
        ano=ano,
        ementa=ementa,
        data_apresentacao=date(2024, 1, 1),
        situacao="Em tramitação",
        temas=temas,
    )
    db_session.add(prop)
    await db_session.flush()
    return prop


async def _create_eleitor(
    db_session: AsyncSession,
    *,
    uf: str = "SP",
    email: str | None = None,
    nome: str = "Eleitor Teste",
) -> Eleitor:
    """Helper to create an eleitor."""
    eleitor = Eleitor(
        nome=nome,
        email=email or f"{uuid.uuid4().hex[:8]}@test.com",
        uf=uf,
        channel="telegram",
        cidadao_brasileiro=True,
        data_nascimento=date(1990, 6, 15),
        verificado=True,
        cpf_hash=uuid.uuid4().hex + uuid.uuid4().hex[:32],  # 64 chars
        nivel_verificacao=NivelVerificacao.AUTO_DECLARADO,
    )
    db_session.add(eleitor)
    await db_session.flush()
    return eleitor


async def _create_voto(
    db_session: AsyncSession,
    *,
    eleitor_id: uuid.UUID,
    proposicao_id: int,
    voto: VotoEnum = VotoEnum.SIM,
    data_voto: datetime | None = None,
) -> VotoPopular:
    """Helper to create a vote."""
    v = VotoPopular(
        eleitor_id=eleitor_id,
        proposicao_id=proposicao_id,
        voto=voto,
    )
    if data_voto is not None:
        v.data_voto = data_voto
    db_session.add(v)
    await db_session.flush()
    return v


# ===========================================================================
# Votos Por Tema
# ===========================================================================


class TestVotosPorTema:
    """Test GET /parlamentar/votos/por-tema."""

    async def test_empty(
        self,
        client: AsyncClient,
        parlamentar_user: ParlamentarUser,
    ) -> None:
        """No votes returns empty list."""
        access = ParlamentarAuthService.create_access_token(parlamentar_user)
        response = await client.get(
            "/parlamentar/votos/por-tema",
            headers={"Authorization": f"Bearer {access}"},
        )
        assert response.status_code == 200
        assert response.json() == []

    async def test_single_tema(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        parlamentar_user: ParlamentarUser,
    ) -> None:
        """Votes on a proposição with temas are aggregated correctly."""
        prop = await _create_proposicao(db_session, id=1, temas=["Saúde"])
        eleitor = await _create_eleitor(db_session, uf="SP")
        await _create_voto(db_session, eleitor_id=eleitor.id, proposicao_id=prop.id, voto=VotoEnum.SIM)

        access = ParlamentarAuthService.create_access_token(parlamentar_user)
        response = await client.get(
            "/parlamentar/votos/por-tema",
            headers={"Authorization": f"Bearer {access}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["tema"] == "Saúde"
        assert data[0]["total_votos"] == 1
        assert data[0]["sim"] == 1
        assert data[0]["nao"] == 0

    async def test_multiple_temas(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        parlamentar_user: ParlamentarUser,
    ) -> None:
        """Proposição with multiple temas splits votes across all temas."""
        prop = await _create_proposicao(db_session, id=1, temas=["Economia", "Tributos"])
        eleitor = await _create_eleitor(db_session, uf="RJ")
        await _create_voto(db_session, eleitor_id=eleitor.id, proposicao_id=prop.id, voto=VotoEnum.NAO)

        access = ParlamentarAuthService.create_access_token(parlamentar_user)
        response = await client.get(
            "/parlamentar/votos/por-tema",
            headers={"Authorization": f"Bearer {access}"},
        )

        data = response.json()
        assert len(data) == 2
        temas = {item["tema"] for item in data}
        assert temas == {"Economia", "Tributos"}
        # Each tema gets the same vote
        for item in data:
            assert item["total_votos"] == 1
            assert item["nao"] == 1

    async def test_unauthenticated(self, client: AsyncClient) -> None:
        """Unauthenticated request returns 422."""
        response = await client.get("/parlamentar/votos/por-tema")
        assert response.status_code == 422


# ===========================================================================
# Votos Por UF
# ===========================================================================


class TestVotosPorUF:
    """Test GET /parlamentar/votos/por-uf."""

    async def test_empty(
        self,
        client: AsyncClient,
        parlamentar_user: ParlamentarUser,
    ) -> None:
        """No votes returns empty list."""
        access = ParlamentarAuthService.create_access_token(parlamentar_user)
        response = await client.get(
            "/parlamentar/votos/por-uf",
            headers={"Authorization": f"Bearer {access}"},
        )
        assert response.status_code == 200
        assert response.json() == []

    async def test_single_uf(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        parlamentar_user: ParlamentarUser,
    ) -> None:
        """Votes from a single UF are aggregated."""
        prop = await _create_proposicao(db_session, id=1)
        e1 = await _create_eleitor(db_session, uf="SP", email="a@test.com")
        e2 = await _create_eleitor(db_session, uf="SP", email="b@test.com")
        await _create_voto(db_session, eleitor_id=e1.id, proposicao_id=prop.id, voto=VotoEnum.SIM)
        await _create_voto(db_session, eleitor_id=e2.id, proposicao_id=prop.id, voto=VotoEnum.NAO)

        access = ParlamentarAuthService.create_access_token(parlamentar_user)
        response = await client.get(
            "/parlamentar/votos/por-uf",
            headers={"Authorization": f"Bearer {access}"},
        )

        data = response.json()
        assert len(data) == 1
        assert data[0]["uf"] == "SP"
        assert data[0]["total_votos"] == 2
        assert data[0]["sim"] == 1
        assert data[0]["nao"] == 1

    async def test_multiple_ufs(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        parlamentar_user: ParlamentarUser,
    ) -> None:
        """Votes from different UFs are grouped separately."""
        prop = await _create_proposicao(db_session, id=1)
        e_sp = await _create_eleitor(db_session, uf="SP")
        e_rj = await _create_eleitor(db_session, uf="RJ")
        await _create_voto(db_session, eleitor_id=e_sp.id, proposicao_id=prop.id, voto=VotoEnum.SIM)
        await _create_voto(db_session, eleitor_id=e_rj.id, proposicao_id=prop.id, voto=VotoEnum.ABSTENCAO)

        access = ParlamentarAuthService.create_access_token(parlamentar_user)
        response = await client.get(
            "/parlamentar/votos/por-uf",
            headers={"Authorization": f"Bearer {access}"},
        )

        data = response.json()
        assert len(data) == 2
        ufs = {item["uf"] for item in data}
        assert ufs == {"SP", "RJ"}

    async def test_unauthenticated(self, client: AsyncClient) -> None:
        """Unauthenticated request returns 422."""
        response = await client.get("/parlamentar/votos/por-uf")
        assert response.status_code == 422


# ===========================================================================
# Votos Timeline
# ===========================================================================


class TestVotosTimeline:
    """Test GET /parlamentar/votos/timeline."""

    async def test_empty(
        self,
        client: AsyncClient,
        parlamentar_user: ParlamentarUser,
    ) -> None:
        """No votes returns empty list."""
        access = ParlamentarAuthService.create_access_token(parlamentar_user)
        response = await client.get(
            "/parlamentar/votos/timeline",
            headers={"Authorization": f"Bearer {access}"},
        )
        assert response.status_code == 200
        assert response.json() == []

    async def test_recent_vote(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        parlamentar_user: ParlamentarUser,
    ) -> None:
        """Vote from today appears in 30-day timeline."""
        prop = await _create_proposicao(db_session, id=1)
        eleitor = await _create_eleitor(db_session)
        await _create_voto(
            db_session,
            eleitor_id=eleitor.id,
            proposicao_id=prop.id,
            voto=VotoEnum.SIM,
            data_voto=datetime.now(timezone.utc),
        )

        access = ParlamentarAuthService.create_access_token(parlamentar_user)
        response = await client.get(
            "/parlamentar/votos/timeline?dias=30",
            headers={"Authorization": f"Bearer {access}"},
        )

        data = response.json()
        assert len(data) >= 1
        assert data[0]["total_votos"] == 1
        assert data[0]["sim"] == 1

    async def test_custom_dias(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        parlamentar_user: ParlamentarUser,
    ) -> None:
        """Custom dias parameter works."""
        prop = await _create_proposicao(db_session, id=1)
        eleitor = await _create_eleitor(db_session)
        await _create_voto(
            db_session,
            eleitor_id=eleitor.id,
            proposicao_id=prop.id,
            voto=VotoEnum.NAO,
            data_voto=datetime.now(timezone.utc),
        )

        access = ParlamentarAuthService.create_access_token(parlamentar_user)
        response = await client.get(
            "/parlamentar/votos/timeline?dias=7",
            headers={"Authorization": f"Bearer {access}"},
        )

        data = response.json()
        assert len(data) >= 1

    async def test_unauthenticated(self, client: AsyncClient) -> None:
        """Unauthenticated request returns 422."""
        response = await client.get("/parlamentar/votos/timeline")
        assert response.status_code == 422


# ===========================================================================
# Votos Ranking
# ===========================================================================


class TestVotosRanking:
    """Test GET /parlamentar/votos/ranking."""

    async def test_empty(
        self,
        client: AsyncClient,
        parlamentar_user: ParlamentarUser,
    ) -> None:
        """No votes returns empty list (proposições without votes are excluded)."""
        access = ParlamentarAuthService.create_access_token(parlamentar_user)
        response = await client.get(
            "/parlamentar/votos/ranking",
            headers={"Authorization": f"Bearer {access}"},
        )
        assert response.status_code == 200
        assert response.json() == []

    async def test_ranking_order(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        parlamentar_user: ParlamentarUser,
    ) -> None:
        """Proposições are ordered by total votes descending."""
        prop1 = await _create_proposicao(db_session, id=1, ementa="Menos votos")
        prop2 = await _create_proposicao(db_session, id=2, ementa="Mais votos", numero=2)

        e1 = await _create_eleitor(db_session, email="r1@test.com")
        e2 = await _create_eleitor(db_session, email="r2@test.com")
        e3 = await _create_eleitor(db_session, email="r3@test.com")

        # prop1 gets 1 vote, prop2 gets 2
        await _create_voto(db_session, eleitor_id=e1.id, proposicao_id=prop1.id, voto=VotoEnum.SIM)
        await _create_voto(db_session, eleitor_id=e2.id, proposicao_id=prop2.id, voto=VotoEnum.SIM)
        await _create_voto(db_session, eleitor_id=e3.id, proposicao_id=prop2.id, voto=VotoEnum.NAO)

        access = ParlamentarAuthService.create_access_token(parlamentar_user)
        response = await client.get(
            "/parlamentar/votos/ranking",
            headers={"Authorization": f"Bearer {access}"},
        )

        data = response.json()
        assert len(data) == 2
        assert data[0]["proposicao_id"] == 2
        assert data[0]["total_votos"] == 2
        assert data[1]["proposicao_id"] == 1
        assert data[1]["total_votos"] == 1

    async def test_ranking_percentuais(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        parlamentar_user: ParlamentarUser,
    ) -> None:
        """Ranking includes correct percentuais."""
        prop = await _create_proposicao(db_session, id=1)
        e1 = await _create_eleitor(db_session, email="p1@test.com")
        e2 = await _create_eleitor(db_session, email="p2@test.com")
        e3 = await _create_eleitor(db_session, email="p3@test.com")
        e4 = await _create_eleitor(db_session, email="p4@test.com")

        await _create_voto(db_session, eleitor_id=e1.id, proposicao_id=prop.id, voto=VotoEnum.SIM)
        await _create_voto(db_session, eleitor_id=e2.id, proposicao_id=prop.id, voto=VotoEnum.SIM)
        await _create_voto(db_session, eleitor_id=e3.id, proposicao_id=prop.id, voto=VotoEnum.SIM)
        await _create_voto(db_session, eleitor_id=e4.id, proposicao_id=prop.id, voto=VotoEnum.NAO)

        access = ParlamentarAuthService.create_access_token(parlamentar_user)
        response = await client.get(
            "/parlamentar/votos/ranking",
            headers={"Authorization": f"Bearer {access}"},
        )

        data = response.json()
        assert len(data) == 1
        assert data[0]["total_votos"] == 4
        assert data[0]["sim"] == 3
        assert data[0]["nao"] == 1
        assert data[0]["percentual_sim"] == 75.0
        assert data[0]["percentual_nao"] == 25.0

    async def test_ranking_limite(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        parlamentar_user: ParlamentarUser,
    ) -> None:
        """Limite parameter restricts result count."""
        eleitor = await _create_eleitor(db_session)
        for i in range(5):
            prop = await _create_proposicao(db_session, id=i + 1, numero=i + 1, ementa=f"Prop {i+1}")
            await _create_voto(db_session, eleitor_id=eleitor.id, proposicao_id=prop.id, voto=VotoEnum.SIM)

        access = ParlamentarAuthService.create_access_token(parlamentar_user)
        response = await client.get(
            "/parlamentar/votos/ranking?limite=3",
            headers={"Authorization": f"Bearer {access}"},
        )

        data = response.json()
        assert len(data) == 3

    async def test_unauthenticated(self, client: AsyncClient) -> None:
        """Unauthenticated request returns 422."""
        response = await client.get("/parlamentar/votos/ranking")
        assert response.status_code == 422
