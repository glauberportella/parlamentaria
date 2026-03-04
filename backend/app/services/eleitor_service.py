"""Service for Eleitor (voter) business logic."""

import uuid
from datetime import date
from typing import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.eleitor import Eleitor, NivelVerificacao
from app.exceptions import NotFoundException, ValidationException
from app.logging import get_logger
from app.repositories.eleitor import EleitorRepository
from app.schemas.eleitor import EleitorCreate, EleitorUpdate
from app.services.validators import (
    validar_cpf,
    validar_titulo_eleitor,
    extrair_uf_titulo,
    hash_documento,
    extrair_cpf_digitos,
    extrair_titulo_digitos,
)

logger = get_logger(__name__)

# Valid Brazilian UF codes
UFS_VALIDAS = frozenset([
    "AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA",
    "MG", "MS", "MT", "PA", "PB", "PE", "PI", "PR", "RJ", "RN",
    "RO", "RR", "RS", "SC", "SE", "SP", "TO",
])


class EleitorService:
    """Orchestrates voter registration and management."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = EleitorRepository(session)

    async def get_by_id(self, eleitor_id: uuid.UUID) -> Eleitor:
        """Get a voter by UUID.

        Args:
            eleitor_id: Voter UUID.

        Returns:
            Eleitor instance.

        Raises:
            NotFoundException: If not found.
        """
        return await self.repo.get_by_id_or_raise(eleitor_id)

    async def get_by_chat_id(self, chat_id: str) -> Eleitor | None:
        """Find a voter by their messaging platform chat ID.

        Args:
            chat_id: Chat ID (e.g., Telegram user ID).

        Returns:
            Eleitor or None.
        """
        return await self.repo.find_by_chat_id(chat_id)

    async def get_or_create_by_chat_id(
        self, chat_id: str, channel: str = "telegram"
    ) -> tuple[Eleitor, bool]:
        """Get existing voter by chat_id or create a minimal stub.

        Used when a user first interacts via a messaging channel.

        Args:
            chat_id: Chat ID from the messaging platform.
            channel: Channel name (telegram, whatsapp).

        Returns:
            Tuple of (Eleitor, created: bool).
        """
        existing = await self.repo.find_by_chat_id(chat_id)
        if existing:
            return existing, False

        eleitor = Eleitor(
            chat_id=chat_id,
            channel=channel,
            nome="",
            email=f"{chat_id}@placeholder.parlamentaria.app",
            uf="XX",
        )
        result = await self.repo.create(eleitor)
        logger.info("eleitor.created_stub", chat_id=chat_id, channel=channel)
        return result, True

    async def register(self, data: EleitorCreate) -> Eleitor:
        """Register a new voter with full profile.

        Args:
            data: Validated voter data.

        Returns:
            Created Eleitor.

        Raises:
            ValidationException: If email or chat_id already exists.
        """
        if data.email:
            existing = await self.repo.find_by_email(data.email)
            if existing:
                raise ValidationException(detail=f"E-mail {data.email} já cadastrado")

        if data.chat_id:
            existing = await self.repo.find_by_chat_id(data.chat_id)
            if existing:
                raise ValidationException(detail=f"chat_id {data.chat_id} já cadastrado")

        eleitor = Eleitor(**data.model_dump(exclude={"cpf", "titulo_eleitor"}))
        result = await self.repo.create(eleitor)
        logger.info("eleitor.registered", id=str(result.id), nome=result.nome)

        # Register CPF if provided in the creation data
        if data.cpf:
            result, _ = await self.registrar_cpf(result.id, data.cpf)

        # Register título if provided in the creation data
        if data.titulo_eleitor:
            result, _ = await self.verificar_titulo_eleitor(result.id, data.titulo_eleitor)

        return result

    async def update_profile(self, eleitor_id: uuid.UUID, data: EleitorUpdate) -> Eleitor:
        """Update a voter's profile.

        Args:
            eleitor_id: Voter UUID.
            data: Fields to update.

        Returns:
            Updated Eleitor.

        Raises:
            NotFoundException: If voter not found.
        """
        eleitor = await self.repo.get_by_id_or_raise(eleitor_id)
        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            return eleitor
        result = await self.repo.update(eleitor, update_data)
        logger.info("eleitor.updated", id=str(result.id))
        return result

    async def list_eleitores(
        self, uf: str | None = None, offset: int = 0, limit: int = 50
    ) -> Sequence[Eleitor]:
        """List voters with optional UF filter.

        Args:
            uf: State abbreviation filter.
            offset: Records to skip.
            limit: Maximum records.

        Returns:
            Sequence of Eleitor.
        """
        if uf:
            return await self.repo.find_by_uf(uf, offset, limit)
        return await self.repo.list_all(offset, limit)

    async def find_by_tema(
        self, tema: str, offset: int = 0, limit: int = 50
    ) -> Sequence[Eleitor]:
        """Find voters interested in a given theme.

        Args:
            tema: Theme name.
            offset: Records to skip.
            limit: Maximum records.

        Returns:
            Sequence of voters.
        """
        return await self.repo.find_by_tema_interesse(tema, offset, limit)

    async def count(self) -> int:
        """Return total number of registered voters."""
        return await self.repo.count()

    # ------------------------------------------------------------------
    # Eligibility & Verification — Sistema de Verificação Progressiva
    # ------------------------------------------------------------------

    @staticmethod
    def verificar_elegibilidade(eleitor: Eleitor) -> dict[str, bool | str | None]:
        """Check if a voter meets eligibility criteria for official votes.

        Criteria (CF/88, Art. 14):
        - Brazilian citizen (self-declared).
        - 16 years of age or older.
        - At least AUTO_DECLARADO verification level with CPF.

        Args:
            eleitor: Eleitor instance to check.

        Returns:
            Dict with ``elegivel`` bool, ``motivo`` explanation,
            ``nivel_verificacao`` and ``proximo_passo``.
        """
        nivel = getattr(eleitor, "nivel_verificacao", NivelVerificacao.NAO_VERIFICADO)
        if isinstance(nivel, str):
            try:
                nivel = NivelVerificacao(nivel)
            except ValueError:
                nivel = NivelVerificacao.NAO_VERIFICADO

        base = {
            "elegivel": False,
            "motivo": None,
            "nivel_verificacao": nivel.value if isinstance(nivel, NivelVerificacao) else str(nivel),
        }

        if not eleitor.cidadao_brasileiro:
            return {
                **base,
                "motivo": "Apenas cidadãos brasileiros podem emitir voto oficial. "
                          "Sua opinião será registrada como voto consultivo.",
                "proximo_passo": "Informe que é cidadão brasileiro durante o cadastro.",
            }

        if eleitor.data_nascimento is None:
            return {
                **base,
                "motivo": "Informe sua data de nascimento para verificar elegibilidade.",
                "proximo_passo": "Forneça sua data de nascimento (DD/MM/AAAA).",
            }

        idade = eleitor.idade
        if idade is not None and idade < 16:
            return {
                **base,
                "motivo": f"Você tem {idade} anos. O voto é permitido a partir de 16 anos (CF/88 Art. 14). "
                          "Sua opinião será registrada como voto consultivo.",
                "proximo_passo": None,
            }

        cpf_hash = getattr(eleitor, "cpf_hash", None)
        if cpf_hash is None:
            return {
                **base,
                "motivo": "Informe seu CPF para completar a verificação.",
                "proximo_passo": "Forneça seu CPF (somente números).",
            }

        if nivel == NivelVerificacao.NAO_VERIFICADO:
            return {
                **base,
                "motivo": "Complete seu cadastro para votar oficialmente.",
                "proximo_passo": "Forneça nome, UF, CPF e data de nascimento.",
            }

        return {
            "elegivel": True,
            "motivo": None,
            "nivel_verificacao": nivel.value if isinstance(nivel, NivelVerificacao) else str(nivel),
            "proximo_passo": (
                "Para aumentar a confiança do seu voto, valide seu título de eleitor com /verificar."
                if nivel == NivelVerificacao.AUTO_DECLARADO
                else None
            ),
        }

    async def atualizar_cidadania(
        self,
        eleitor_id: uuid.UUID,
        cidadao_brasileiro: bool,
        data_nascimento: date | None = None,
    ) -> Eleitor:
        """Update citizenship and birth date of a voter.

        After updating, re-evaluates eligibility.

        Args:
            eleitor_id: Voter UUID.
            cidadao_brasileiro: Self-declaration of Brazilian citizenship.
            data_nascimento: Date of birth (YYYY-MM-DD).

        Returns:
            Updated Eleitor.

        Raises:
            NotFoundException: If voter not found.
        """
        eleitor = await self.repo.get_by_id_or_raise(eleitor_id)

        update_data: dict = {"cidadao_brasileiro": cidadao_brasileiro}
        if data_nascimento is not None:
            update_data["data_nascimento"] = data_nascimento

        result = await self.repo.update(eleitor, update_data)
        logger.info(
            "eleitor.cidadania_atualizada",
            id=str(result.id),
            cidadao_brasileiro=cidadao_brasileiro,
            elegivel=result.elegivel,
        )
        return result

    async def registrar_cpf(
        self,
        eleitor_id: uuid.UUID,
        cpf: str,
    ) -> tuple[Eleitor, dict]:
        """Validate and register a CPF for a voter.

        The CPF is validated mathematically, then stored as a SHA-256 hash.
        If the CPF is already registered to another voter, the operation fails
        (one person, one vote).

        If the voter has name, UF, birth date, citizenship, and now CPF,
        their verification level is promoted to AUTO_DECLARADO.

        Args:
            eleitor_id: Voter UUID.
            cpf: CPF string (with or without formatting).

        Returns:
            Tuple of (updated Eleitor, validation result dict).

        Raises:
            NotFoundException: If voter not found.
            ValidationException: If CPF is invalid or already registered.
        """
        # Validate CPF digits
        is_valid, message = validar_cpf(cpf)
        if not is_valid:
            raise ValidationException(detail=message)

        cpf_hashed = hash_documento(cpf)

        # Check uniqueness
        existing = await self.repo.find_by_cpf_hash(cpf_hashed)
        if existing and existing.id != eleitor_id:
            raise ValidationException(
                detail="Este CPF já está registrado em outra conta. "
                       "Cada pessoa pode ter apenas uma conta na plataforma."
            )

        eleitor = await self.repo.get_by_id_or_raise(eleitor_id)

        update_data: dict = {"cpf_hash": cpf_hashed}

        # Auto-promote to AUTO_DECLARADO if all basic data is present
        nivel = getattr(eleitor, "nivel_verificacao", NivelVerificacao.NAO_VERIFICADO)
        if isinstance(nivel, str):
            try:
                nivel = NivelVerificacao(nivel)
            except ValueError:
                nivel = NivelVerificacao.NAO_VERIFICADO

        if (
            nivel == NivelVerificacao.NAO_VERIFICADO
            and eleitor.nome
            and eleitor.uf
            and eleitor.uf != "XX"
            and eleitor.cidadao_brasileiro
            and eleitor.data_nascimento is not None
        ):
            update_data["nivel_verificacao"] = NivelVerificacao.AUTO_DECLARADO
            update_data["verificado"] = True

        result = await self.repo.update(eleitor, update_data)
        logger.info(
            "eleitor.cpf_registrado",
            id=str(result.id),
            nivel=str(result.nivel_verificacao),
            elegivel=result.elegivel,
        )

        return result, {
            "cpf_valido": True,
            "nivel_verificacao": result.nivel_verificacao.value
            if isinstance(result.nivel_verificacao, NivelVerificacao)
            else str(result.nivel_verificacao),
            "elegivel": result.elegivel,
        }

    async def verificar_titulo_eleitor(
        self,
        eleitor_id: uuid.UUID,
        titulo: str,
    ) -> tuple[Eleitor, dict]:
        """Validate and register a título de eleitor for a voter.

        The título is validated mathematically. The UF encoded in the título
        is cross-checked against the declared UF.  Stored as SHA-256 hash.

        Promotes verification level to VERIFICADO_TITULO on success.

        Args:
            eleitor_id: Voter UUID.
            titulo: Título de eleitor string (12 digits).

        Returns:
            Tuple of (updated Eleitor, validation result dict).

        Raises:
            NotFoundException: If voter not found.
            ValidationException: If título is invalid, UF mismatch, or already registered.
        """
        is_valid, message = validar_titulo_eleitor(titulo)
        if not is_valid:
            raise ValidationException(detail=message)

        titulo_hashed = hash_documento(titulo)

        # Check uniqueness
        existing = await self.repo.find_by_titulo_hash(titulo_hashed)
        if existing and existing.id != eleitor_id:
            raise ValidationException(
                detail="Este título de eleitor já está registrado em outra conta."
            )

        eleitor = await self.repo.get_by_id_or_raise(eleitor_id)

        # Cross-check UF
        uf_titulo = extrair_uf_titulo(titulo)
        if uf_titulo and eleitor.uf and eleitor.uf != "XX":
            if uf_titulo not in ("ZZ", "EX") and uf_titulo != eleitor.uf:
                raise ValidationException(
                    detail=f"O título pertence a {uf_titulo}, mas seu cadastro indica {eleitor.uf}. "
                           "Atualize sua UF ou verifique o número do título."
                )

        update_data: dict = {
            "titulo_eleitor_hash": titulo_hashed,
            "nivel_verificacao": NivelVerificacao.VERIFICADO_TITULO,
            "verificado": True,
        }

        result = await self.repo.update(eleitor, update_data)
        logger.info(
            "eleitor.titulo_verificado",
            id=str(result.id),
            nivel=NivelVerificacao.VERIFICADO_TITULO.value,
            elegivel=result.elegivel,
        )

        return result, {
            "titulo_valido": True,
            "uf_titulo": uf_titulo,
            "nivel_verificacao": NivelVerificacao.VERIFICADO_TITULO.value,
            "elegivel": result.elegivel,
        }
