"""Service for Evento business logic and orchestration."""

from datetime import datetime
from typing import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.evento import Evento
from app.exceptions import NotFoundException
from app.logging import get_logger
from app.repositories.evento import EventoRepository

logger = get_logger(__name__)


class EventoService:
    """Orchestrates plenary event operations.

    Handles CRUD and upsert logic for events synced from the Câmara API.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = EventoRepository(session)

    async def get_by_id(self, evento_id: int) -> Evento:
        """Get an event by ID, raising if not found.

        Args:
            evento_id: Event ID.

        Returns:
            Evento instance.

        Raises:
            NotFoundException: If not found.
        """
        return await self.repo.get_by_id_or_raise(evento_id)

    async def list_recent(self, limit: int = 20) -> Sequence[Evento]:
        """List most recent events.

        Args:
            limit: Maximum number of records.

        Returns:
            Sequence of events.
        """
        return await self.repo.list_recent(limit)

    async def list_by_data_range(
        self,
        data_inicio: datetime,
        data_fim: datetime,
        offset: int = 0,
        limit: int = 50,
    ) -> Sequence[Evento]:
        """List events within a date range.

        Args:
            data_inicio: Start datetime.
            data_fim: End datetime.
            offset: Records to skip.
            limit: Maximum records.

        Returns:
            Sequence of events.
        """
        return await self.repo.find_by_data_range(data_inicio, data_fim, offset, limit)

    async def count(self) -> int:
        """Return total number of events."""
        return await self.repo.count()

    async def upsert_from_api(self, api_data: dict) -> Evento:
        """Create or update an event from Câmara API data.

        Used by the sync service to persist data from the external API.

        Args:
            api_data: Dictionary with event fields from API.

        Returns:
            Created or updated Evento.
        """
        existing = await self.repo.get_by_id(api_data["id"])
        if existing:
            update_fields = {
                k: v for k, v in api_data.items()
                if k != "id" and v is not None
            }
            result = await self.repo.update(existing, update_fields)
            logger.info("evento.upsert.updated", id=result.id)
            return result
        else:
            evento = Evento(**api_data)
            result = await self.repo.create(evento)
            logger.info("evento.upsert.created", id=result.id)
            return result
