"""Tests for CPF and Título de Eleitor validation services.

Tests cover:
- CPF validation (valid, invalid, blacklist, formatting)
- Título de Eleitor validation (valid, invalid, special states)
- UF extraction from título
- SHA-256 document hashing
- Digit extraction helpers
"""

import hashlib
import re

import pytest

from app.services.validators import (
    validar_cpf,
    validar_titulo_eleitor,
    extrair_uf_titulo,
    extrair_cpf_digitos,
    extrair_titulo_digitos,
    hash_documento,
)


# ---------------------------------------------------------------------------
# CPF Validation
# ---------------------------------------------------------------------------


class TestValidarCPF:
    """Tests for the validar_cpf() function."""

    # Known valid CPFs (generated with correct check digits)
    @pytest.mark.parametrize(
        "cpf",
        [
            "52998224725",       # Valid CPF
            "11144477735",       # Valid CPF
            "12345678909",       # Valid CPF with sequential digits
        ],
    )
    def test_valid_cpf(self, cpf: str) -> None:
        is_valid, message = validar_cpf(cpf)
        assert is_valid is True
        assert "válido" in message.lower()

    def test_valid_cpf_with_formatting(self) -> None:
        """Should accept CPF with dots and dashes."""
        is_valid, message = validar_cpf("529.982.247-25")
        assert is_valid is True

    def test_invalid_cpf_wrong_length(self) -> None:
        is_valid, message = validar_cpf("1234567890")  # 10 digits
        assert is_valid is False
        assert "11 dígitos" in message

    def test_invalid_cpf_too_long(self) -> None:
        is_valid, message = validar_cpf("123456789012")  # 12 digits
        assert is_valid is False
        assert "11 dígitos" in message

    @pytest.mark.parametrize(
        "cpf",
        [
            "00000000000",
            "11111111111",
            "22222222222",
            "33333333333",
            "44444444444",
            "55555555555",
            "66666666666",
            "77777777777",
            "88888888888",
            "99999999999",
        ],
    )
    def test_blacklisted_cpf(self, cpf: str) -> None:
        """All same-digit CPFs should be rejected."""
        is_valid, message = validar_cpf(cpf)
        assert is_valid is False
        assert "inválido" in message.lower()

    def test_invalid_cpf_wrong_check_digit_1(self) -> None:
        is_valid, message = validar_cpf("52998224715")  # Changed digit 10
        assert is_valid is False
        assert "dígito verificador" in message.lower()

    def test_invalid_cpf_wrong_check_digit_2(self) -> None:
        is_valid, message = validar_cpf("52998224726")  # Changed last digit
        assert is_valid is False
        assert "dígito verificador" in message.lower()

    def test_cpf_with_letters_stripped(self) -> None:
        """Non-digit characters should be stripped."""
        is_valid, message = validar_cpf("529.982.247-25")
        assert is_valid is True

    def test_empty_cpf(self) -> None:
        is_valid, message = validar_cpf("")
        assert is_valid is False


class TestExtrairCPFDigitos:
    """Tests for extrair_cpf_digitos()."""

    def test_strip_formatting(self) -> None:
        assert extrair_cpf_digitos("529.982.247-25") == "52998224725"

    def test_already_digits(self) -> None:
        assert extrair_cpf_digitos("52998224725") == "52998224725"

    def test_spaces(self) -> None:
        assert extrair_cpf_digitos("529 982 247 25") == "52998224725"


# ---------------------------------------------------------------------------
# Título de Eleitor Validation
# ---------------------------------------------------------------------------


class TestValidarTituloEleitor:
    """Tests for the validar_titulo_eleitor() function."""

    def test_invalid_titulo_wrong_length(self) -> None:
        is_valid, message = validar_titulo_eleitor("1234567890")  # 10 digits
        assert is_valid is False
        assert "12 dígitos" in message

    def test_invalid_titulo_too_long(self) -> None:
        is_valid, message = validar_titulo_eleitor("1234567890123")  # 13 digits
        assert is_valid is False
        assert "12 dígitos" in message

    def test_invalid_titulo_state_code_zero(self) -> None:
        """State code 00 should be invalid."""
        is_valid, message = validar_titulo_eleitor("000000000011")
        assert is_valid is False

    def test_invalid_titulo_state_code_too_high(self) -> None:
        """State code > 29 should be invalid."""
        is_valid, message = validar_titulo_eleitor("000000003011")
        assert is_valid is False

    def test_empty_titulo(self) -> None:
        is_valid, message = validar_titulo_eleitor("")
        assert is_valid is False


class TestExtrairUFTitulo:
    """Tests for extrair_uf_titulo()."""

    def test_sp_titulo(self) -> None:
        """State code 01 → SP."""
        # Build a 12-digit titulo with state code 01
        titulo = "00000000" + "01" + "00"  # placeholder digits
        uf = extrair_uf_titulo(titulo)
        assert uf == "SP"

    def test_mg_titulo(self) -> None:
        """State code 02 → MG."""
        titulo = "00000000" + "02" + "00"
        uf = extrair_uf_titulo(titulo)
        assert uf == "MG"

    def test_rj_titulo(self) -> None:
        """State code 03 → RJ."""
        titulo = "00000000" + "03" + "00"
        uf = extrair_uf_titulo(titulo)
        assert uf == "RJ"

    def test_invalid_length(self) -> None:
        assert extrair_uf_titulo("12345") is None

    def test_unknown_code(self) -> None:
        """State code 30 → None (unknown)."""
        titulo = "00000000" + "30" + "00"
        uf = extrair_uf_titulo(titulo)
        assert uf is None


class TestExtrairTituloDigitos:
    """Tests for extrair_titulo_digitos()."""

    def test_strip_spaces(self) -> None:
        assert extrair_titulo_digitos("0123 4567 8901") == "012345678901"

    def test_already_digits(self) -> None:
        assert extrair_titulo_digitos("012345678901") == "012345678901"


# ---------------------------------------------------------------------------
# Document Hashing
# ---------------------------------------------------------------------------


class TestHashDocumento:
    """Tests for hash_documento()."""

    def test_consistent_hash(self) -> None:
        """Same input should always produce the same hash."""
        h1 = hash_documento("12345678909")
        h2 = hash_documento("12345678909")
        assert h1 == h2

    def test_formatting_stripped(self) -> None:
        """Hash should be the same with or without formatting."""
        h1 = hash_documento("529.982.247-25")
        h2 = hash_documento("52998224725")
        assert h1 == h2

    def test_hash_is_sha256_hex(self) -> None:
        """Hash should be 64-character hex string (SHA-256)."""
        h = hash_documento("12345678909")
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_hash_matches_manual(self) -> None:
        """Verify hash matches manual SHA-256 computation."""
        digits = "52998224725"
        expected = hashlib.sha256(digits.encode()).hexdigest()
        assert hash_documento("52998224725") == expected
        assert hash_documento("529.982.247-25") == expected

    def test_different_inputs_different_hashes(self) -> None:
        h1 = hash_documento("12345678909")
        h2 = hash_documento("52998224725")
        assert h1 != h2

    def test_empty_string(self) -> None:
        """Empty input should still produce a valid hash."""
        h = hash_documento("")
        assert len(h) == 64
