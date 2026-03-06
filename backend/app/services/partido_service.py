"""Service for Partido business logic and orchestration."""

from typing import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.partido import Partido
from app.exceptions import NotFoundException
from app.logging import get_logger
from app.repositories.partido import PartidoRepository

logger = get_logger(__name__)


class PartidoService:
    """Orchestrates political party operations.

    Handles CRUD and upsert logic for parties synced from the Câmara API.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = PartidoRepository(session)

    async def get_by_id(self, partido_id: int) -> Partido:
        """Get a party by ID, raising if not found.

        Args:
            partido_id: Party ID.

        Returns:
            Partido instance.

        Raises:
            NotFoundException: If not found.
        """
        return await self.repo.get_by_id_or_raise(partido_id)

    async def get_by_sigla(self, sigla: str) -> Partido | None:
        """Get a party by abbreviation.

        Args:
            sigla: Party abbreviation (e.g., PT, PL).

        Returns:
            Partido or None.
        """
        return await self.repo.find_by_sigla(sigla)

    async def list_partidos(
        self, offset: int = 0, limit: int = 100
    ) -> Sequence[Partido]:
        """List all parties ordered by abbreviation.

        Args:
            offset: Records to skip.
            limit: Maximum records.

        Returns:
            Sequence of parties.
        """
        return await self.repo.list_all_ordered(offset, limit)

    async def count(self) -> int:
        """Return total number of parties."""
        return await self.repo.count()

    async def upsert_from_api(self, api_data: dict) -> Partido:
        """Create or update a party from Câmara API data.

        Used by the sync service to persist data from the external API.

        Args:
            api_data: Dictionary with party fields from API.

        Returns:
            Created or updated Partido.
        """
        existing = await self.repo.get_by_id(api_data["id"])
        if existing:
            update_fields = {
                k: v for k, v in api_data.items()
                if k != "id" and v is not None
            }
            result = await self.repo.update(existing, update_fields)
            logger.info("partido.upsert.updated", id=result.id, sigla=result.sigla)
            return result
        else:
            partido = Partido(**api_data)
            result = await self.repo.create(partido)
            logger.info("partido.upsert.created", id=result.id, sigla=result.sigla)
            return result
