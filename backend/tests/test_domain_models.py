"""Tests for domain models — validation and relationships."""

import uuid
from datetime import date, datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.proposicao import Proposicao
from app.domain.votacao import Votacao
from app.domain.deputado import Deputado
from app.domain.eleitor import Eleitor
from app.domain.voto_popular import VotoPopular, VotoEnum
from app.domain.analise_ia import AnaliseIA
from app.domain.evento import Evento
from app.domain.partido import Partido
from app.domain.assinatura import AssinaturaRSS, AssinaturaWebhook
from app.domain.comparativo import ComparativoVotacao


class TestProposicao:
    """Test Proposicao model."""

    async def test_create_proposicao(self, db_session: AsyncSession, sample_proposicao_data: dict):
        """Should persist a proposition."""
        prop = Proposicao(**sample_proposicao_data)
        db_session.add(prop)
        await db_session.flush()

        assert prop.id == 12345
        assert prop.tipo == "PL"
        assert prop.numero == 100
        assert prop.ano == 2024
        assert prop.ementa == "Dispõe sobre a transparência legislativa"

    async def test_proposicao_repr(self, sample_proposicao_data: dict):
        """repr should show type, number and year."""
        prop = Proposicao(**sample_proposicao_data)
        assert "PL" in repr(prop)
        assert "100" in repr(prop)
        assert "2024" in repr(prop)

    async def test_proposicao_tablename(self):
        """Table name should be 'proposicoes'."""
        assert Proposicao.__tablename__ == "proposicoes"


class TestVotacao:
    """Test Votacao model."""

    async def test_create_votacao(self, db_session: AsyncSession, sample_proposicao_data: dict, sample_votacao_data: dict):
        """Should persist a vote session."""
        prop = Proposicao(**sample_proposicao_data)
        db_session.add(prop)
        await db_session.flush()

        vot = Votacao(**sample_votacao_data)
        db_session.add(vot)
        await db_session.flush()

        assert vot.id == 11111
        assert vot.proposicao_id == 12345
        assert vot.votos_sim == 300

    async def test_votacao_repr(self, sample_votacao_data: dict):
        """repr should show ID and description."""
        vot = Votacao(**sample_votacao_data)
        assert "11111" in repr(vot)


class TestDeputado:
    """Test Deputado model."""

    async def test_create_deputado(self, db_session: AsyncSession, sample_deputado_data: dict):
        """Should persist a deputy."""
        dep = Deputado(**sample_deputado_data)
        db_session.add(dep)
        await db_session.flush()

        assert dep.id == 67890
        assert dep.nome == "João Exemplo"
        assert dep.sigla_partido == "PT"

    async def test_deputado_repr(self, sample_deputado_data: dict):
        """repr should show name, party, and state."""
        dep = Deputado(**sample_deputado_data)
        assert "João Exemplo" in repr(dep)
        assert "PT" in repr(dep)
        assert "RJ" in repr(dep)


class TestEleitor:
    """Test Eleitor model."""

    async def test_create_eleitor(self, db_session: AsyncSession, sample_eleitor_data: dict):
        """Should persist a voter."""
        eleitor = Eleitor(**sample_eleitor_data)
        db_session.add(eleitor)
        await db_session.flush()

        assert eleitor.id is not None
        assert eleitor.nome == "Maria Silva"
        assert eleitor.email == "maria@example.com"
        assert eleitor.uf == "SP"

    async def test_eleitor_uuid_auto_generated(self, db_session: AsyncSession, sample_eleitor_data: dict):
        """ID should be a UUID (or UUID string in SQLite)."""
        eleitor = Eleitor(**sample_eleitor_data)
        db_session.add(eleitor)
        await db_session.flush()
        # In SQLite, UUID columns are stored as strings; in PostgreSQL they are uuid.UUID
        uid = eleitor.id
        if isinstance(uid, str):
            uid = uuid.UUID(uid)
        assert isinstance(uid, uuid.UUID)

    async def test_eleitor_repr(self, sample_eleitor_data: dict):
        """repr should show name and state."""
        eleitor = Eleitor(**sample_eleitor_data)
        assert "Maria Silva" in repr(eleitor)
        assert "SP" in repr(eleitor)


class TestVotoPopular:
    """Test VotoPopular model."""

    async def test_create_voto_popular(self, db_session: AsyncSession, sample_proposicao_data: dict, sample_eleitor_data: dict):
        """Should persist a popular vote."""
        prop = Proposicao(**sample_proposicao_data)
        eleitor = Eleitor(**sample_eleitor_data)
        db_session.add_all([prop, eleitor])
        await db_session.flush()

        voto = VotoPopular(
            eleitor_id=eleitor.id,
            proposicao_id=prop.id,
            voto=VotoEnum.SIM,
            justificativa="Concordo com a transparência",
        )
        db_session.add(voto)
        await db_session.flush()

        assert voto.id is not None
        assert voto.voto == VotoEnum.SIM
        assert voto.eleitor_id == eleitor.id

    async def test_voto_enum_values(self):
        """VotoEnum should have SIM, NAO, ABSTENCAO."""
        assert VotoEnum.SIM.value == "SIM"
        assert VotoEnum.NAO.value == "NAO"
        assert VotoEnum.ABSTENCAO.value == "ABSTENCAO"

    async def test_voto_repr(self, db_session: AsyncSession, sample_proposicao_data: dict, sample_eleitor_data: dict):
        """repr should show the vote value."""
        prop = Proposicao(**sample_proposicao_data)
        eleitor = Eleitor(**sample_eleitor_data)
        db_session.add_all([prop, eleitor])
        await db_session.flush()

        voto = VotoPopular(
            eleitor_id=eleitor.id,
            proposicao_id=prop.id,
            voto=VotoEnum.NAO,
        )
        db_session.add(voto)
        await db_session.flush()
        assert "NAO" in repr(voto)


class TestAnaliseIA:
    """Test AnaliseIA model."""

    async def test_create_analise(self, db_session: AsyncSession, sample_proposicao_data: dict):
        """Should persist an AI analysis."""
        prop = Proposicao(**sample_proposicao_data)
        db_session.add(prop)
        await db_session.flush()

        analise = AnaliseIA(
            proposicao_id=prop.id,
            resumo_leigo="Resumo simples do projeto",
            impacto_esperado="Impacto positivo na transparência",
            areas_afetadas=["Governo", "Transparência"],
            argumentos_favor=["Mais transparência"],
            argumentos_contra=["Custo de implementação"],
            provedor_llm="google",
            modelo="gemini-2.0-flash",
        )
        db_session.add(analise)
        await db_session.flush()

        assert analise.id is not None
        assert analise.proposicao_id == prop.id
        assert analise.versao == 1

    async def test_analise_repr(self, db_session: AsyncSession, sample_proposicao_data: dict):
        """repr should show proposition ID and version."""
        prop = Proposicao(**sample_proposicao_data)
        db_session.add(prop)
        await db_session.flush()

        analise = AnaliseIA(
            proposicao_id=prop.id,
            resumo_leigo="R",
            impacto_esperado="I",
            areas_afetadas=["A"],
            argumentos_favor=["F"],
            argumentos_contra=["C"],
            provedor_llm="google",
            modelo="gemini",
        )
        db_session.add(analise)
        await db_session.flush()
        assert str(prop.id) in repr(analise)


class TestEvento:
    """Test Evento model."""

    async def test_create_evento(self, db_session: AsyncSession):
        """Should persist an event."""
        evento = Evento(
            id=999,
            data_inicio=datetime(2024, 6, 1, 10, 0, tzinfo=timezone.utc),
            tipo_evento="Seminário",
            descricao="Seminário de Transparência",
        )
        db_session.add(evento)
        await db_session.flush()
        assert evento.id == 999

    async def test_evento_repr(self):
        """repr should show ID and description."""
        evento = Evento(
            id=888,
            data_inicio=datetime(2024, 6, 1, 10, 0, tzinfo=timezone.utc),
            descricao="Sessão Plenária",
        )
        assert "888" in repr(evento)


class TestPartido:
    """Test Partido model."""

    async def test_create_partido(self, db_session: AsyncSession):
        """Should persist a party."""
        partido = Partido(id=1, sigla="PT", nome="Partido dos Trabalhadores")
        db_session.add(partido)
        await db_session.flush()
        assert partido.sigla == "PT"

    async def test_partido_repr(self):
        """repr should show abbreviation."""
        partido = Partido(id=2, sigla="PL", nome="Partido Liberal")
        assert "PL" in repr(partido)


class TestAssinaturaRSS:
    """Test AssinaturaRSS model."""

    async def test_create_assinatura_rss(self, db_session: AsyncSession):
        """Should persist an RSS subscription."""
        ass = AssinaturaRSS(
            nome="Portal Legislativo",
            token="abc123def456",
            filtro_temas=["Educação"],
            filtro_uf="MG",
        )
        db_session.add(ass)
        await db_session.flush()
        assert ass.id is not None
        assert ass.ativo is True

    async def test_rss_repr(self):
        """repr should show name and active status."""
        ass = AssinaturaRSS(nome="Test", token="tok")
        assert "Test" in repr(ass)


class TestAssinaturaWebhook:
    """Test AssinaturaWebhook model."""

    async def test_create_assinatura_webhook(self, db_session: AsyncSession):
        """Should persist a webhook subscription."""
        wh = AssinaturaWebhook(
            nome="CI/CD System",
            url="https://example.com/webhook",
            secret="super-secret",
            eventos=["nova_proposicao", "votacao_concluida"],
        )
        db_session.add(wh)
        await db_session.flush()
        assert wh.id is not None
        assert wh.falhas_consecutivas == 0

    async def test_webhook_repr(self):
        """repr should show name and active status."""
        wh = AssinaturaWebhook(
            nome="Test WH",
            url="https://example.com",
            secret="s",
            eventos=["e"],
        )
        assert "Test WH" in repr(wh)


class TestComparativoVotacao:
    """Test ComparativoVotacao model."""

    async def test_create_comparativo(
        self, db_session: AsyncSession, sample_proposicao_data: dict, sample_votacao_data: dict
    ):
        """Should persist a comparative analysis."""
        prop = Proposicao(**sample_proposicao_data)
        db_session.add(prop)
        await db_session.flush()

        vot = Votacao(**sample_votacao_data)
        db_session.add(vot)
        await db_session.flush()

        comp = ComparativoVotacao(
            proposicao_id=prop.id,
            votacao_camara_id=vot.id,
            voto_popular_sim=150,
            voto_popular_nao=50,
            resultado_camara="APROVADO",
            votos_camara_sim=300,
            votos_camara_nao=150,
            alinhamento=0.8,
        )
        db_session.add(comp)
        await db_session.flush()

        assert comp.id is not None
        assert comp.alinhamento == 0.8

    async def test_comparativo_repr(self):
        """repr should show proposition and alignment."""
        comp = ComparativoVotacao(
            proposicao_id=1,
            votacao_camara_id=2,
            resultado_camara="APROVADO",
            alinhamento=0.75,
        )
        assert "0.75" in repr(comp)
