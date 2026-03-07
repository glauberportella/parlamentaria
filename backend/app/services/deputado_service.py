"""Service for Deputado business logic and orchestration."""

from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.deputado import Deputado
from app.exceptions import NotFoundException
from app.logging import get_logger
from app.repositories.deputado import DeputadoRepository

logger = get_logger(__name__)


class DeputadoService:
    """Orchestrates deputy operations.

    Handles CRUD and upsert logic for federal deputies
    synced from the Câmara API.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = DeputadoRepository(session)

    async def get_by_id(self, deputado_id: int) -> Deputado:
        """Get a deputy by ID, raising if not found.

        Args:
            deputado_id: Deputy ID.

        Returns:
            Deputado instance.

        Raises:
            NotFoundException: If not found.
        """
        return await self.repo.get_by_id_or_raise(deputado_id)

    async def list_deputados(
        self,
        sigla_partido: str | None = None,
        sigla_uf: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> Sequence[Deputado]:
        """List deputies with optional filters.

        Args:
            sigla_partido: Party abbreviation filter.
            sigla_uf: State abbreviation filter.
            offset: Records to skip.
            limit: Maximum records.

        Returns:
            Sequence of deputies.
        """
        if sigla_partido:
            return await self.repo.find_by_partido(sigla_partido, offset, limit)
        if sigla_uf:
            return await self.repo.find_by_uf(sigla_uf, offset, limit)
        return await self.repo.list_all(offset, limit)

    async def search_by_nome(self, nome: str) -> Sequence[Deputado]:
        """Search deputies by name.

        Args:
            nome: Name to search (partial, case-insensitive).

        Returns:
            Sequence of matching deputies.
        """
        return await self.repo.find_by_nome(nome)

    async def count(self) -> int:
        """Return total number of deputies."""
        return await self.repo.count()

    async def upsert_from_api(self, api_data: dict) -> Deputado:
        """Create or update a deputy from Câmara API data.

        Used by the sync service to persist data from the external API.

        Args:
            api_data: Dictionary with deputy fields from API.

        Returns:
            Created or updated Deputado.
        """
        existing = await self.repo.get_by_id(api_data["id"])
        if existing:
            update_fields = {
                k: v for k, v in api_data.items()
                if k != "id" and v is not None
            }
            update_fields["updated_at"] = datetime.now(timezone.utc)
            result = await self.repo.update(existing, update_fields)
            logger.info("deputado.upsert.updated", id=result.id, nome=result.nome)
            return result
        else:
            deputado = Deputado(**api_data)
            result = await self.repo.create(deputado)
            logger.info("deputado.upsert.created", id=result.id, nome=result.nome)
            return result
