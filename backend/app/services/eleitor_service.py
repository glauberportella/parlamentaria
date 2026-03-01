"""Service for Eleitor (voter) business logic."""

import uuid
from typing import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.eleitor import Eleitor
from app.exceptions import NotFoundException, ValidationException
from app.logging import get_logger
from app.repositories.eleitor import EleitorRepository
from app.schemas.eleitor import EleitorCreate, EleitorUpdate

logger = get_logger(__name__)


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

        eleitor = Eleitor(**data.model_dump())
        result = await self.repo.create(eleitor)
        logger.info("eleitor.registered", id=str(result.id), nome=result.nome)
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
