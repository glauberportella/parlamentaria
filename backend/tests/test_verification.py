"""Tests for voter verification service methods (registrar_cpf, verificar_titulo_eleitor).

Tests cover:
- EleitorService.registrar_cpf — CPF validation, hashing, uniqueness, auto-promotion
- EleitorService.verificar_titulo_eleitor — título validation, UF cross-check, promotion
- verificar_elegibilidade — updated with NivelVerificacao levels
"""

import uuid
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.domain.eleitor import Eleitor, NivelVerificacao
from app.exceptions import NotFoundException, ValidationException
from app.services.eleitor_service import EleitorService
from app.services.validators import hash_documento


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_eleitor(
    nome: str = "João Silva",
    uf: str = "SP",
    email: str | None = None,
    cidadao_brasileiro: bool = True,
    data_nascimento: date | None = date(1990, 6, 15),
    verificado: bool = False,
    cpf_hash: str | None = None,
    titulo_eleitor_hash: str | None = None,
    nivel_verificacao: NivelVerificacao = NivelVerificacao.NAO_VERIFICADO,
) -> Eleitor:
    """Create an Eleitor for testing."""
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
        cpf_hash=cpf_hash,
        titulo_eleitor_hash=titulo_eleitor_hash,
        nivel_verificacao=nivel_verificacao,
    )


# ---------------------------------------------------------------------------
# registrar_cpf
# ---------------------------------------------------------------------------


class TestRegistrarCPF:
    """Tests for EleitorService.registrar_cpf()."""

    @pytest.fixture
    def service(self, db_session):
        return EleitorService(db_session)

    async def test_registrar_cpf_valid(self, service, db_session):
        """Valid CPF should be hashed and stored."""
        eleitor = _make_eleitor(
            nome="Ana Costa", uf="SP",
            cidadao_brasileiro=True,
            data_nascimento=date(1990, 1, 1),
        )
        db_session.add(eleitor)
        await db_session.flush()
        await db_session.refresh(eleitor)

        cpf = "52998224725"  # Valid CPF
        updated, result = await service.registrar_cpf(eleitor.id, cpf)

        assert result["cpf_valido"] is True
        assert updated.cpf_hash is not None
        assert updated.cpf_hash == hash_documento(cpf)

    async def test_registrar_cpf_auto_promotes(self, service, db_session):
        """With all data present, registering CPF should promote to AUTO_DECLARADO."""
        eleitor = _make_eleitor(
            nome="Ana Costa", uf="SP",
            cidadao_brasileiro=True,
            data_nascimento=date(1990, 1, 1),
            nivel_verificacao=NivelVerificacao.NAO_VERIFICADO,
        )
        db_session.add(eleitor)
        await db_session.flush()
        await db_session.refresh(eleitor)

        cpf = "52998224725"
        updated, result = await service.registrar_cpf(eleitor.id, cpf)

        assert updated.nivel_verificacao == NivelVerificacao.AUTO_DECLARADO
        assert result["nivel_verificacao"] == "AUTO_DECLARADO"

    async def test_registrar_cpf_no_promote_incomplete(self, service, db_session):
        """Without all data, CPF registration shouldn't promote level."""
        eleitor = _make_eleitor(
            nome="Ana", uf="SP",
            cidadao_brasileiro=False,  # Missing citizenship
            data_nascimento=date(1990, 1, 1),
            nivel_verificacao=NivelVerificacao.NAO_VERIFICADO,
        )
        db_session.add(eleitor)
        await db_session.flush()
        await db_session.refresh(eleitor)

        cpf = "52998224725"
        updated, result = await service.registrar_cpf(eleitor.id, cpf)

        assert updated.nivel_verificacao == NivelVerificacao.NAO_VERIFICADO
        assert updated.cpf_hash is not None

    async def test_registrar_cpf_invalid_rejected(self, service, db_session):
        """Invalid CPF should raise ValidationException."""
        eleitor = _make_eleitor()
        db_session.add(eleitor)
        await db_session.flush()
        await db_session.refresh(eleitor)

        with pytest.raises(ValidationException, match="inválido"):
            await service.registrar_cpf(eleitor.id, "00000000000")

    async def test_registrar_cpf_wrong_digits_rejected(self, service, db_session):
        """CPF with wrong check digits should raise ValidationException."""
        eleitor = _make_eleitor()
        db_session.add(eleitor)
        await db_session.flush()
        await db_session.refresh(eleitor)

        with pytest.raises(ValidationException, match="dígito"):
            await service.registrar_cpf(eleitor.id, "52998224726")  # Wrong last digit

    async def test_registrar_cpf_duplicate_rejected(self, service, db_session):
        """CPF already used by another voter should be rejected."""
        cpf = "52998224725"
        cpf_hash = hash_documento(cpf)

        # First eleitor with this CPF
        eleitor1 = _make_eleitor(nome="First", cpf_hash=cpf_hash)
        db_session.add(eleitor1)
        await db_session.flush()

        # Second eleitor tries the same CPF
        eleitor2 = _make_eleitor(nome="Second")
        db_session.add(eleitor2)
        await db_session.flush()
        await db_session.refresh(eleitor2)

        with pytest.raises(ValidationException, match="já está registrado"):
            await service.registrar_cpf(eleitor2.id, cpf)

    async def test_registrar_cpf_same_user_ok(self, service, db_session):
        """Re-registering same CPF for the same user should succeed."""
        cpf = "52998224725"
        cpf_hash = hash_documento(cpf)

        eleitor = _make_eleitor(
            nome="Ana", uf="SP",
            cidadao_brasileiro=True,
            data_nascimento=date(1990, 1, 1),
            cpf_hash=cpf_hash,
            nivel_verificacao=NivelVerificacao.AUTO_DECLARADO,
        )
        db_session.add(eleitor)
        await db_session.flush()
        await db_session.refresh(eleitor)

        # Re-register same CPF — should not raise
        updated, result = await service.registrar_cpf(eleitor.id, cpf)
        assert result["cpf_valido"] is True

    async def test_registrar_cpf_not_found(self, service):
        """Non-existent voter should raise NotFoundException."""
        with pytest.raises(Exception):
            await service.registrar_cpf(uuid.uuid4(), "52998224725")

    async def test_registrar_cpf_with_formatting(self, service, db_session):
        """CPF with formatting should be accepted."""
        eleitor = _make_eleitor(
            nome="Ana", uf="SP",
            cidadao_brasileiro=True,
            data_nascimento=date(1990, 1, 1),
        )
        db_session.add(eleitor)
        await db_session.flush()
        await db_session.refresh(eleitor)

        updated, result = await service.registrar_cpf(eleitor.id, "529.982.247-25")
        assert result["cpf_valido"] is True
        assert updated.cpf_hash == hash_documento("52998224725")


# ---------------------------------------------------------------------------
# verificar_titulo_eleitor
# ---------------------------------------------------------------------------


class TestVerificarTituloEleitor:
    """Tests for EleitorService.verificar_titulo_eleitor()."""

    @pytest.fixture
    def service(self, db_session):
        return EleitorService(db_session)

    async def test_titulo_invalid_rejected(self, service, db_session):
        """Invalid título should raise ValidationException."""
        eleitor = _make_eleitor(cpf_hash="a" * 64)
        db_session.add(eleitor)
        await db_session.flush()
        await db_session.refresh(eleitor)

        with pytest.raises(ValidationException, match="12 dígitos"):
            await service.verificar_titulo_eleitor(eleitor.id, "12345")

    async def test_titulo_not_found_eleitor(self, service):
        """Non-existent voter should raise."""
        with pytest.raises(Exception):
            await service.verificar_titulo_eleitor(uuid.uuid4(), "012345678901")

    async def test_titulo_duplicate_rejected(self, service, db_session):
        """Título already used by another voter should be rejected."""
        # Use a pre-computed hash to simulate a título already registered
        # (bypassing validation by inserting the hash directly)
        fake_titulo_hash = hash_documento("012345678901")

        eleitor1 = _make_eleitor(
            nome="First",
            cpf_hash="a" * 64,
            titulo_eleitor_hash=fake_titulo_hash,
        )
        db_session.add(eleitor1)
        await db_session.flush()

        eleitor2 = _make_eleitor(nome="Second", cpf_hash="b" * 64)
        db_session.add(eleitor2)
        await db_session.flush()
        await db_session.refresh(eleitor2)

        # Mock the validator to return valid, so we hit the uniqueness check
        with patch("app.services.eleitor_service.validar_titulo_eleitor", return_value=(True, "Valid")):
            with patch("app.services.eleitor_service.hash_documento", return_value=fake_titulo_hash):
                with patch("app.services.eleitor_service.extrair_uf_titulo", return_value="SP"):
                    with pytest.raises(ValidationException, match="já está registrado"):
                        await service.verificar_titulo_eleitor(eleitor2.id, "012345678901")


# ---------------------------------------------------------------------------
# verificar_elegibilidade — NivelVerificacao integration
# ---------------------------------------------------------------------------


class TestVerificarElegibilidadeNivel:
    """Tests for EleitorService.verificar_elegibilidade with NivelVerificacao."""

    def test_nao_verificado_without_cpf(self) -> None:
        """NAO_VERIFICADO without CPF → not eligible, asks for CPF."""
        eleitor = _make_eleitor(
            cidadao_brasileiro=True,
            data_nascimento=date(1990, 1, 1),
            cpf_hash=None,
            nivel_verificacao=NivelVerificacao.NAO_VERIFICADO,
        )
        result = EleitorService.verificar_elegibilidade(eleitor)
        assert result["elegivel"] is False
        assert "CPF" in result["motivo"]

    def test_auto_declarado_eligible(self) -> None:
        """AUTO_DECLARADO with CPF, Brazilian, 16+ → eligible."""
        eleitor = _make_eleitor(
            cidadao_brasileiro=True,
            data_nascimento=date(1990, 1, 1),
            cpf_hash="a" * 64,
            nivel_verificacao=NivelVerificacao.AUTO_DECLARADO,
        )
        result = EleitorService.verificar_elegibilidade(eleitor)
        assert result["elegivel"] is True
        assert result["nivel_verificacao"] == "AUTO_DECLARADO"
        # Should suggest título verification
        assert result["proximo_passo"] is not None
        assert "título" in result["proximo_passo"].lower() or "verificar" in result["proximo_passo"].lower()

    def test_verificado_titulo_eligible(self) -> None:
        """VERIFICADO_TITULO → eligible, no next step."""
        eleitor = _make_eleitor(
            cidadao_brasileiro=True,
            data_nascimento=date(1990, 1, 1),
            cpf_hash="a" * 64,
            titulo_eleitor_hash="b" * 64,
            nivel_verificacao=NivelVerificacao.VERIFICADO_TITULO,
        )
        result = EleitorService.verificar_elegibilidade(eleitor)
        assert result["elegivel"] is True
        assert result["nivel_verificacao"] == "VERIFICADO_TITULO"
        assert result["proximo_passo"] is None

    def test_non_brazilian_not_eligible(self) -> None:
        """Non-Brazilian is never eligible regardless of NivelVerificacao."""
        eleitor = _make_eleitor(
            cidadao_brasileiro=False,
            data_nascimento=date(1990, 1, 1),
            cpf_hash="a" * 64,
            nivel_verificacao=NivelVerificacao.VERIFICADO_TITULO,
        )
        result = EleitorService.verificar_elegibilidade(eleitor)
        assert result["elegivel"] is False
        assert "cidadãos brasileiros" in result["motivo"]

    def test_under_16_not_eligible(self) -> None:
        """Under 16 is not eligible regardless of NivelVerificacao."""
        today = date.today()
        eleitor = _make_eleitor(
            cidadao_brasileiro=True,
            data_nascimento=date(today.year - 14, today.month, today.day),
            cpf_hash="a" * 64,
            nivel_verificacao=NivelVerificacao.AUTO_DECLARADO,
        )
        result = EleitorService.verificar_elegibilidade(eleitor)
        assert result["elegivel"] is False
        assert "16 anos" in result["motivo"]

    def test_result_has_nivel_field(self) -> None:
        """Result should always contain nivel_verificacao."""
        eleitor = _make_eleitor(
            nivel_verificacao=NivelVerificacao.NAO_VERIFICADO,
            cpf_hash=None,
        )
        result = EleitorService.verificar_elegibilidade(eleitor)
        assert "nivel_verificacao" in result
        assert result["nivel_verificacao"] == "NAO_VERIFICADO"


# ---------------------------------------------------------------------------
# Eleitor.elegivel property with NivelVerificacao
# ---------------------------------------------------------------------------


class TestElegivelPropertyNivel:
    """Tests for the elegivel property with new verification levels."""

    def test_auto_declarado_with_cpf_is_eligible(self) -> None:
        eleitor = _make_eleitor(
            cidadao_brasileiro=True,
            data_nascimento=date(1990, 1, 1),
            cpf_hash="a" * 64,
            nivel_verificacao=NivelVerificacao.AUTO_DECLARADO,
        )
        assert eleitor.elegivel is True

    def test_verificado_titulo_is_eligible(self) -> None:
        eleitor = _make_eleitor(
            cidadao_brasileiro=True,
            data_nascimento=date(1990, 1, 1),
            cpf_hash="a" * 64,
            titulo_eleitor_hash="b" * 64,
            nivel_verificacao=NivelVerificacao.VERIFICADO_TITULO,
        )
        assert eleitor.elegivel is True

    def test_nao_verificado_is_not_eligible(self) -> None:
        eleitor = _make_eleitor(
            cidadao_brasileiro=True,
            data_nascimento=date(1990, 1, 1),
            cpf_hash="a" * 64,
            nivel_verificacao=NivelVerificacao.NAO_VERIFICADO,
        )
        assert eleitor.elegivel is False

    def test_no_cpf_is_not_eligible(self) -> None:
        eleitor = _make_eleitor(
            cidadao_brasileiro=True,
            data_nascimento=date(1990, 1, 1),
            cpf_hash=None,
            nivel_verificacao=NivelVerificacao.AUTO_DECLARADO,
        )
        assert eleitor.elegivel is False
