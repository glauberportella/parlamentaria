"""Validation services for Brazilian identity documents.

Provides stateless validators for CPF and Título de Eleitor numbers.
These are pure functions — no database or network access required.

Security: the platform stores only SHA-256 hashes of these documents,
never the raw numbers. Hashing is also provided by this module.
"""

from __future__ import annotations

import hashlib
import re

# ---------------------------------------------------------------------------
# CPF Validation
# ---------------------------------------------------------------------------

# Known-invalid CPFs (all digits equal)
_CPF_BLACKLIST: frozenset[str] = frozenset(
    f"{d}" * 11 for d in range(10)
)

# Mapping UF → código(s) do estado no título de eleitor (dígitos 9-10)
_TITULO_UF_MAP: dict[str, list[str]] = {
    "SP": ["01"],
    "MG": ["02"],
    "RJ": ["03"],
    "RS": ["04"],
    "BA": ["05"],
    "PR": ["06"],
    "CE": ["07"],
    "PE": ["08"],
    "SC": ["09"],
    "GO": ["10"],
    "MA": ["11"],
    "PB": ["12"],
    "PA": ["13"],
    "ES": ["14"],
    "PI": ["15"],
    "RN": ["16"],
    "AL": ["17"],
    "MT": ["18"],
    "MS": ["19"],
    "DF": ["20"],
    "SE": ["21"],
    "AM": ["22"],
    "RO": ["23"],
    "AC": ["24"],
    "AP": ["25"],
    "RR": ["26"],
    "TO": ["27"],
    "ZZ": ["28"],  # Exterior
    "EX": ["29"],  # Exterior (variante)
}


def validar_cpf(cpf: str) -> tuple[bool, str]:
    """Validate a Brazilian CPF number using check-digit algorithm.

    The CPF (Cadastro de Pessoas Físicas) has 11 digits where the last
    two are check digits computed via modulo-11 arithmetic.

    Args:
        cpf: CPF string (may contain dots and dashes, e.g. '123.456.789-09').

    Returns:
        Tuple of (is_valid, message).
    """
    # Strip formatting
    digits = re.sub(r"\D", "", cpf)

    if len(digits) != 11:
        return False, "CPF deve ter exatamente 11 dígitos."

    if digits in _CPF_BLACKLIST:
        return False, "CPF inválido (todos os dígitos iguais)."

    # --- First check digit ---
    weights1 = [10, 9, 8, 7, 6, 5, 4, 3, 2]
    soma1 = sum(int(digits[i]) * weights1[i] for i in range(9))
    resto1 = soma1 % 11
    dv1 = 0 if resto1 < 2 else 11 - resto1

    if int(digits[9]) != dv1:
        return False, "CPF inválido (dígito verificador 1 não confere)."

    # --- Second check digit ---
    weights2 = [11, 10, 9, 8, 7, 6, 5, 4, 3, 2]
    soma2 = sum(int(digits[i]) * weights2[i] for i in range(10))
    resto2 = soma2 % 11
    dv2 = 0 if resto2 < 2 else 11 - resto2

    if int(digits[10]) != dv2:
        return False, "CPF inválido (dígito verificador 2 não confere)."

    return True, "CPF válido."


def extrair_cpf_digitos(cpf: str) -> str:
    """Strip formatting from a CPF string and return only digits.

    Args:
        cpf: CPF string with optional formatting.

    Returns:
        11-digit string.
    """
    return re.sub(r"\D", "", cpf)


# ---------------------------------------------------------------------------
# Título de Eleitor Validation
# ---------------------------------------------------------------------------

def validar_titulo_eleitor(titulo: str) -> tuple[bool, str]:
    """Validate a Brazilian voter registration number (título de eleitor).

    The título has 12 digits:
    - Digits 1-8: sequential number.
    - Digits 9-10: state code (01-28 + 29 for exterior).
    - Digit 11: first check digit (computed over digits 1-8).
    - Digit 12: second check digit (computed over state + dv1).

    Args:
        titulo: Título de eleitor string (digits only or with spaces).

    Returns:
        Tuple of (is_valid, message).
    """
    digits = re.sub(r"\D", "", titulo)

    if len(digits) != 12:
        return False, "Título de eleitor deve ter exatamente 12 dígitos."

    sequencial = digits[:8]
    estado = digits[8:10]
    estado_int = int(estado)

    # State codes: 01 to 28 (+ 29 for exterior in some systems)
    if not (1 <= estado_int <= 29):
        return False, f"Código de estado inválido no título: {estado}."

    # --- First check digit (over the 8 sequential digits) ---
    pesos1 = [2, 3, 4, 5, 6, 7, 8, 9]
    soma1 = sum(int(sequencial[i]) * pesos1[i] for i in range(8))
    resto1 = soma1 % 11

    # Special handling for states SP (01) and MG (02) where resto == 1
    if resto1 == 0:
        dv1 = 0
    elif resto1 == 1:
        dv1 = 1 if estado_int in (1, 2) else 0
    else:
        dv1 = 11 - resto1

    if int(digits[10]) != dv1:
        return False, "Título de eleitor inválido (dígito verificador 1 não confere)."

    # --- Second check digit (over state code + dv1) ---
    pesos2 = [7, 8, 9]
    valores2 = [int(estado[0]), int(estado[1]), dv1]
    soma2 = sum(v * p for v, p in zip(valores2, pesos2))
    resto2 = soma2 % 11

    if resto2 == 0:
        dv2 = 0
    elif resto2 == 1:
        dv2 = 1 if estado_int in (1, 2) else 0
    else:
        dv2 = 11 - resto2

    if int(digits[11]) != dv2:
        return False, "Título de eleitor inválido (dígito verificador 2 não confere)."

    return True, "Título de eleitor válido."


def extrair_uf_titulo(titulo: str) -> str | None:
    """Extract the UF (state) from a título de eleitor number.

    Args:
        titulo: Título de eleitor (12 digits).

    Returns:
        UF abbreviation (e.g. 'SP', 'RJ') or None if invalid code.
    """
    digits = re.sub(r"\D", "", titulo)
    if len(digits) != 12:
        return None

    codigo = digits[8:10]
    for uf, codigos in _TITULO_UF_MAP.items():
        if codigo in codigos:
            return uf
    return None


def extrair_titulo_digitos(titulo: str) -> str:
    """Strip formatting from a título de eleitor string.

    Args:
        titulo: Título string with optional spaces/formatting.

    Returns:
        12-digit string.
    """
    return re.sub(r"\D", "", titulo)


# ---------------------------------------------------------------------------
# Hashing (for secure storage)
# ---------------------------------------------------------------------------

def hash_documento(valor: str) -> str:
    """Compute a SHA-256 hex digest from a document number.

    Only digits are hashed (formatting is stripped first) so that
    ``hash_documento("123.456.789-09") == hash_documento("12345678909")``.

    Args:
        valor: Raw document string (CPF, título, etc.).

    Returns:
        64-character lowercase hex SHA-256 hash.
    """
    digits = re.sub(r"\D", "", valor)
    return hashlib.sha256(digits.encode("utf-8")).hexdigest()
