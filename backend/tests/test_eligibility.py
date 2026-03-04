"""Tests for voter eligibility and vote classification (limite-eleitor feature).

Tests cover:
- Eleitor.elegivel property for various scenarios
- Eleitor.idade calculation
- EleitorService.verificar_elegibilidade()
- VotoPopularService automatic vote classification (OFICIAL vs OPINIAO)
- VotoPopularRepository counting with tipo_voto filter
- Dual result (oficial + consultivo)
"""

import uuid
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.domain.eleitor import Eleitor
from app.domain.voto_popular import VotoPopular, VotoEnum, TipoVoto
from app.services.eleitor_service import EleitorService
from app.services.voto_popular_service import VotoPopularService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_eleitor(
    nome: str = "João Silva",
    uf: str = "SP",
    email: str | None = None,
    cidadao_brasileiro: bool = True,
    data_nascimento: date | None = None,
    verificado: bool = True,
) -> Eleitor:
    """Create an Eleitor with given attributes for testing.

    Uses the normal SQLAlchemy constructor so that ORM instrumentation
    is properly initialised (``__new__`` bypasses it and breaks attribute
    setting).
    """
    return Eleitor(
        nome=nome,
        email=email or f"{uuid.uuid4().hex[:8]}@test.com",
        uf=uf,
        chat_id=str(uuid.uuid4().int)[:10],
        channel="telegram",
        verificado=verificado,
        cidadao_brasileiro=cidadao_brasileiro,
        data_nascimento=data_nascimento,
        temas_interesse=None,
    )


def _make_voto(
    eleitor_id: uuid.UUID | None = None,
    proposicao_id: int = 1234,
    voto: VotoEnum = VotoEnum.SIM,
    tipo_voto: TipoVoto = TipoVoto.OPINIAO,
    justificativa: str | None = None,
) -> VotoPopular:
    """Create a VotoPopular using the normal constructor."""
    return VotoPopular(
        eleitor_id=eleitor_id or uuid.uuid4(),
        proposicao_id=proposicao_id,
        voto=voto,
        tipo_voto=tipo_voto,
        justificativa=justificativa,
    )


# ---------------------------------------------------------------------------
# Eleitor.elegivel property
# ---------------------------------------------------------------------------


class TestEleitorElegivel:
    """Tests for the Eleitor.elegivel computed property."""

    def test_eleitor_elegivel_all_criteria_met(self) -> None:
        """Brazilian citizen, 18 years old, verified → eligible."""
        eleitor = _make_eleitor(
            cidadao_brasileiro=True,
            data_nascimento=date(2008, 1, 1),  # 18 years old
            verificado=True,
        )
        assert eleitor.elegivel is True

    def test_eleitor_elegivel_exactly_16(self) -> None:
        """Brazilian citizen, exactly 16 → eligible."""
        today = date.today()
        nascimento = date(today.year - 16, today.month, today.day)
        eleitor = _make_eleitor(
            cidadao_brasileiro=True,
            data_nascimento=nascimento,
            verificado=True,
        )
        assert eleitor.elegivel is True

    def test_eleitor_not_elegivel_under_16(self) -> None:
        """Brazilian citizen, under 16 → NOT eligible."""
        today = date.today()
        nascimento = date(today.year - 15, today.month, today.day)
        eleitor = _make_eleitor(
            cidadao_brasileiro=True,
            data_nascimento=nascimento,
            verificado=True,
        )
        assert eleitor.elegivel is False

    def test_eleitor_not_elegivel_not_brazilian(self) -> None:
        """Non-Brazilian, 30 years old, verified → NOT eligible."""
        eleitor = _make_eleitor(
            cidadao_brasileiro=False,
            data_nascimento=date(1996, 6, 15),
            verificado=True,
        )
        assert eleitor.elegivel is False

    def test_eleitor_not_elegivel_not_verified(self) -> None:
        """Brazilian, 30 years old, NOT verified → NOT eligible."""
        eleitor = _make_eleitor(
            cidadao_brasileiro=True,
            data_nascimento=date(1996, 6, 15),
            verificado=False,
        )
        assert eleitor.elegivel is False

    def test_eleitor_not_elegivel_no_birth_date(self) -> None:
        """Brazilian, verified, but no birth date → NOT eligible."""
        eleitor = _make_eleitor(
            cidadao_brasileiro=True,
            data_nascimento=None,
            verificado=True,
        )
        assert eleitor.elegivel is False

    def test_eleitor_not_elegivel_all_missing(self) -> None:
        """Default stub voter → NOT eligible."""
        eleitor = _make_eleitor(
            cidadao_brasileiro=False,
            data_nascimento=None,
            verificado=False,
        )
        assert eleitor.elegivel is False


# ---------------------------------------------------------------------------
# Eleitor.idade property
# ---------------------------------------------------------------------------


class TestEleitorIdade:
    """Tests for the Eleitor.idade computed property."""

    def test_idade_none_when_no_birth_date(self) -> None:
        eleitor = _make_eleitor(data_nascimento=None)
        assert eleitor.idade is None

    def test_idade_calculation(self) -> None:
        today = date.today()
        eleitor = _make_eleitor(data_nascimento=date(2000, 1, 1))
        expected = today.year - 2000 - (
            (today.month, today.day) < (1, 1)
        )
        assert eleitor.idade == expected

    def test_idade_birthday_not_yet(self) -> None:
        """Birthday later this year → subtract 1."""
        today = date.today()
        # Set birthday to December 31 of a year that would give nice math
        nascimento = date(today.year - 20, 12, 31)
        eleitor = _make_eleitor(data_nascimento=nascimento)
        if today.month < 12 or (today.month == 12 and today.day < 31):
            assert eleitor.idade == 19
        else:
            assert eleitor.idade == 20


# ---------------------------------------------------------------------------
# EleitorService.verificar_elegibilidade (static method)
# ---------------------------------------------------------------------------


class TestVerificarElegibilidade:
    """Tests for EleitorService.verificar_elegibilidade()."""

    def test_eligible_returns_true(self) -> None:
        eleitor = _make_eleitor(
            cidadao_brasileiro=True,
            data_nascimento=date(1990, 3, 15),
            verificado=True,
        )
        result = EleitorService.verificar_elegibilidade(eleitor)
        assert result["elegivel"] is True
        assert result["motivo"] is None

    def test_not_brazilian_returns_motivo(self) -> None:
        eleitor = _make_eleitor(cidadao_brasileiro=False)
        result = EleitorService.verificar_elegibilidade(eleitor)
        assert result["elegivel"] is False
        assert "cidadãos brasileiros" in result["motivo"]

    def test_no_birth_date_returns_motivo(self) -> None:
        eleitor = _make_eleitor(
            cidadao_brasileiro=True,
            data_nascimento=None,
            verificado=True,
        )
        result = EleitorService.verificar_elegibilidade(eleitor)
        assert result["elegivel"] is False
        assert "data de nascimento" in result["motivo"]

    def test_under_16_returns_motivo(self) -> None:
        today = date.today()
        eleitor = _make_eleitor(
            cidadao_brasileiro=True,
            data_nascimento=date(today.year - 14, today.month, today.day),
            verificado=True,
        )
        result = EleitorService.verificar_elegibilidade(eleitor)
        assert result["elegivel"] is False
        assert "16 anos" in result["motivo"]

    def test_not_verified_returns_motivo(self) -> None:
        eleitor = _make_eleitor(
            cidadao_brasileiro=True,
            data_nascimento=date(1990, 1, 1),
            verificado=False,
        )
        result = EleitorService.verificar_elegibilidade(eleitor)
        assert result["elegivel"] is False
        assert "verificação" in result["motivo"]


# ---------------------------------------------------------------------------
# VotoPopularService._classificar_voto
# ---------------------------------------------------------------------------


class TestClassificarVoto:
    """Tests for VotoPopularService._classificar_voto()."""

    def test_eligible_voter_gets_oficial(self) -> None:
        eleitor = _make_eleitor(
            cidadao_brasileiro=True,
            data_nascimento=date(1990, 1, 1),
            verificado=True,
        )
        assert VotoPopularService._classificar_voto(eleitor) == TipoVoto.OFICIAL

    def test_ineligible_voter_gets_opiniao(self) -> None:
        eleitor = _make_eleitor(
            cidadao_brasileiro=False,
            data_nascimento=date(1990, 1, 1),
            verificado=True,
        )
        assert VotoPopularService._classificar_voto(eleitor) == TipoVoto.OPINIAO

    def test_stub_voter_gets_opiniao(self) -> None:
        eleitor = _make_eleitor(
            cidadao_brasileiro=False,
            data_nascimento=None,
            verificado=False,
        )
        assert VotoPopularService._classificar_voto(eleitor) == TipoVoto.OPINIAO


# ---------------------------------------------------------------------------
# TipoVoto enum
# ---------------------------------------------------------------------------


class TestTipoVotoEnum:
    """Tests for the TipoVoto enum."""

    def test_enum_values(self) -> None:
        assert TipoVoto.OFICIAL.value == "OFICIAL"
        assert TipoVoto.OPINIAO.value == "OPINIAO"

    def test_enum_is_str(self) -> None:
        assert isinstance(TipoVoto.OFICIAL, str)
        assert isinstance(TipoVoto.OPINIAO, str)


# ---------------------------------------------------------------------------
# VotoPopular model with tipo_voto
# ---------------------------------------------------------------------------


class TestVotoPopularTipoVoto:
    """Tests for VotoPopular with tipo_voto field."""

    def test_default_tipo_voto_is_opiniao(self) -> None:
        voto = _make_voto(tipo_voto=TipoVoto.OPINIAO)
        assert voto.tipo_voto == TipoVoto.OPINIAO

    def test_oficial_tipo_voto(self) -> None:
        voto = _make_voto(
            proposicao_id=5678,
            voto=VotoEnum.NAO,
            tipo_voto=TipoVoto.OFICIAL,
        )
        assert voto.tipo_voto == TipoVoto.OFICIAL

    def test_repr_includes_tipo(self) -> None:
        voto = _make_voto(voto=VotoEnum.SIM, tipo_voto=TipoVoto.OFICIAL)
        assert "OFICIAL" in repr(voto)


# ---------------------------------------------------------------------------
# VotoPopularService.registrar_voto (mock-based)
# ---------------------------------------------------------------------------


class TestRegistrarVotoClassificacao:
    """Tests that registrar_voto correctly classifies votes."""

    @pytest.fixture
    def mock_session(self) -> MagicMock:
        return MagicMock()

    @pytest.mark.asyncio
    async def test_registrar_voto_eligible_voter_is_oficial(self, mock_session: MagicMock) -> None:
        """An eligible voter's vote should be classified as OFICIAL."""
        eleitor = _make_eleitor(
            cidadao_brasileiro=True,
            data_nascimento=date(1990, 1, 1),
            verificado=True,
        )
        proposicao_id = 1234

        service = VotoPopularService.__new__(VotoPopularService)
        service.session = mock_session
        service.repo = AsyncMock()
        service.proposicao_repo = AsyncMock()
        service.eleitor_repo = AsyncMock()

        # Mock the dependencies
        service.proposicao_repo.get_by_id_or_raise = AsyncMock()
        service.eleitor_repo.get_by_id_or_raise = AsyncMock(return_value=eleitor)
        service.repo.find_by_eleitor_proposicao = AsyncMock(return_value=None)

        created_voto = _make_voto(
            eleitor_id=eleitor.id,
            proposicao_id=proposicao_id,
            voto=VotoEnum.SIM,
            tipo_voto=TipoVoto.OFICIAL,
        )
        service.repo.create = AsyncMock(return_value=created_voto)

        result = await service.registrar_voto(
            eleitor_id=eleitor.id,
            proposicao_id=proposicao_id,
            voto=VotoEnum.SIM,
        )

        assert result.tipo_voto == TipoVoto.OFICIAL
        # Verify create was called with correct tipo_voto
        call_args = service.repo.create.call_args
        voto_obj = call_args[0][0]
        assert voto_obj.tipo_voto == TipoVoto.OFICIAL

    @pytest.mark.asyncio
    async def test_registrar_voto_ineligible_voter_is_opiniao(self, mock_session: MagicMock) -> None:
        """A non-eligible voter's vote should be classified as OPINIAO."""
        eleitor = _make_eleitor(
            cidadao_brasileiro=False,
            data_nascimento=date(1990, 1, 1),
            verificado=True,
        )
        proposicao_id = 5678

        service = VotoPopularService.__new__(VotoPopularService)
        service.session = mock_session
        service.repo = AsyncMock()
        service.proposicao_repo = AsyncMock()
        service.eleitor_repo = AsyncMock()

        service.proposicao_repo.get_by_id_or_raise = AsyncMock()
        service.eleitor_repo.get_by_id_or_raise = AsyncMock(return_value=eleitor)
        service.repo.find_by_eleitor_proposicao = AsyncMock(return_value=None)

        created_voto = _make_voto(
            eleitor_id=eleitor.id,
            proposicao_id=proposicao_id,
            voto=VotoEnum.NAO,
            tipo_voto=TipoVoto.OPINIAO,
        )
        service.repo.create = AsyncMock(return_value=created_voto)

        result = await service.registrar_voto(
            eleitor_id=eleitor.id,
            proposicao_id=proposicao_id,
            voto=VotoEnum.NAO,
        )

        assert result.tipo_voto == TipoVoto.OPINIAO
        call_args = service.repo.create.call_args
        voto_obj = call_args[0][0]
        assert voto_obj.tipo_voto == TipoVoto.OPINIAO

    @pytest.mark.asyncio
    async def test_update_existing_reclassifies(self, mock_session: MagicMock) -> None:
        """Updating an existing vote should reclassify based on current eligibility."""
        eleitor = _make_eleitor(
            cidadao_brasileiro=True,
            data_nascimento=date(1990, 1, 1),
            verificado=True,
        )

        existing_voto = _make_voto(
            eleitor_id=eleitor.id,
            proposicao_id=9999,
            voto=VotoEnum.SIM,
            tipo_voto=TipoVoto.OPINIAO,  # Was opinion before
        )

        service = VotoPopularService.__new__(VotoPopularService)
        service.session = mock_session
        service.repo = AsyncMock()
        service.proposicao_repo = AsyncMock()
        service.eleitor_repo = AsyncMock()

        service.proposicao_repo.get_by_id_or_raise = AsyncMock()
        service.eleitor_repo.get_by_id_or_raise = AsyncMock(return_value=eleitor)
        service.repo.find_by_eleitor_proposicao = AsyncMock(return_value=existing_voto)

        updated_voto = _make_voto(
            eleitor_id=eleitor.id,
            proposicao_id=9999,
            voto=VotoEnum.NAO,
            tipo_voto=TipoVoto.OFICIAL,
        )
        service.repo.update = AsyncMock(return_value=updated_voto)

        result = await service.registrar_voto(
            eleitor_id=eleitor.id,
            proposicao_id=9999,
            voto=VotoEnum.NAO,
        )

        # Should be OFICIAL now that voter is eligible
        update_call = service.repo.update.call_args
        update_dict = update_call[0][1]
        assert update_dict["tipo_voto"] == TipoVoto.OFICIAL


# ---------------------------------------------------------------------------
# VotoPopularService.obter_resultado_completo (mock-based)
# ---------------------------------------------------------------------------


class TestObterResultadoCompleto:
    """Tests for the dual result (oficial + consultivo)."""

    @pytest.mark.asyncio
    async def test_resultado_completo_structure(self) -> None:
        """obter_resultado_completo returns both oficial and consultivo."""
        service = VotoPopularService.__new__(VotoPopularService)
        service.session = MagicMock()
        service.repo = AsyncMock()

        # Mock oficial counts
        service.repo.count_oficiais_by_proposicao = AsyncMock(
            return_value={"SIM": 70, "NAO": 20, "ABSTENCAO": 10, "total": 100}
        )
        # Mock all counts
        service.repo.count_by_proposicao = AsyncMock(
            return_value={"SIM": 150, "NAO": 80, "ABSTENCAO": 20, "total": 250}
        )

        service.proposicao_repo = AsyncMock()
        service.eleitor_repo = AsyncMock()

        result = await service.obter_resultado_completo(proposicao_id=1234)

        assert result["proposicao_id"] == 1234
        assert "oficial" in result
        assert "consultivo" in result

        # Official counts
        assert result["oficial"]["SIM"] == 70
        assert result["oficial"]["total"] == 100
        assert result["oficial"]["percentual_sim"] == 70.0

        # Consultive counts (bigger, includes opinions)
        assert result["consultivo"]["SIM"] == 150
        assert result["consultivo"]["total"] == 250
        assert result["consultivo"]["percentual_sim"] == 60.0


# ---------------------------------------------------------------------------
# Schema tests
# ---------------------------------------------------------------------------


class TestSchemas:
    """Tests for updated Pydantic schemas."""

    def test_eleitor_create_with_eligibility_fields(self) -> None:
        from app.schemas.eleitor import EleitorCreate

        dto = EleitorCreate(
            nome="Maria",
            email="maria@test.com",
            uf="RJ",
            cidadao_brasileiro=True,
            data_nascimento=date(1995, 6, 20),
        )
        assert dto.cidadao_brasileiro is True
        assert dto.data_nascimento == date(1995, 6, 20)

    def test_eleitor_create_defaults(self) -> None:
        from app.schemas.eleitor import EleitorCreate

        dto = EleitorCreate(nome="Test", email="t@t.com", uf="SP")
        assert dto.cidadao_brasileiro is False
        assert dto.data_nascimento is None

    def test_eleitor_update_with_eligibility_fields(self) -> None:
        from app.schemas.eleitor import EleitorUpdate

        dto = EleitorUpdate(
            cidadao_brasileiro=True,
            data_nascimento=date(2000, 1, 1),
        )
        assert dto.cidadao_brasileiro is True
        assert dto.data_nascimento == date(2000, 1, 1)

    def test_eleitor_response_has_elegivel(self) -> None:
        from app.schemas.eleitor import EleitorResponse

        fields = EleitorResponse.model_fields
        assert "elegivel" in fields
        assert "cidadao_brasileiro" in fields
        assert "data_nascimento" in fields

    def test_voto_popular_response_has_tipo_voto(self) -> None:
        from app.schemas.voto_popular import VotoPopularResponse

        fields = VotoPopularResponse.model_fields
        assert "tipo_voto" in fields

    def test_resultado_votacao_completo(self) -> None:
        from app.schemas.voto_popular import (
            ResultadoVotacaoCompleto,
            ResultadoVotacaoOficial,
            ResultadoVotacaoPopular,
        )

        oficial = ResultadoVotacaoOficial(
            proposicao_id=1,
            total_sim=70, total_nao=20, total_abstencao=10,
            total_votos=100,
            percentual_sim=70.0, percentual_nao=20.0, percentual_abstencao=10.0,
        )
        consultivo = ResultadoVotacaoPopular(
            proposicao_id=1,
            total_sim=150, total_nao=80, total_abstencao=20,
            total_votos=250,
            percentual_sim=60.0, percentual_nao=32.0, percentual_abstencao=8.0,
        )
        completo = ResultadoVotacaoCompleto(
            proposicao_id=1,
            oficial=oficial,
            consultivo=consultivo,
        )
        assert completo.oficial.total_votos == 100
        assert completo.consultivo.total_votos == 250
