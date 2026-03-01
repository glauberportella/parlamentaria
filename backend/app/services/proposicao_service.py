"""Service for Proposição business logic and orchestration."""

from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.proposicao import Proposicao
from app.exceptions import NotFoundException, ValidationException
from app.logging import get_logger
from app.repositories.proposicao import ProposicaoRepository
from app.schemas.proposicao import ProposicaoCreate, ProposicaoUpdate

logger = get_logger(__name__)


class ProposicaoService:
    """Orchestrates proposition operations.

    Handles CRUD, search, and upsert logic for legislative propositions
    synced from the Câmara API.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = ProposicaoRepository(session)

    async def get_by_id(self, proposicao_id: int) -> Proposicao:
        """Get a proposition by ID, raising if not found.

        Args:
            proposicao_id: Proposition ID.

        Returns:
            Proposicao instance.

        Raises:
            NotFoundException: If the proposition doesn't exist.
        """
        return await self.repo.get_by_id_or_raise(proposicao_id)

    async def list_proposicoes(
        self,
        tipo: str | None = None,
        ano: int | None = None,
        tema: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> Sequence[Proposicao]:
        """List propositions with optional filters.

        Args:
            tipo: Proposition type (PL, PEC, etc.).
            ano: Year filter.
            tema: Theme filter.
            offset: Records to skip.
            limit: Maximum records.

        Returns:
            Sequence of propositions.
        """
        if tema:
            return await self.repo.find_by_tema(tema, offset, limit)
        if ano:
            return await self.repo.find_by_ano(ano, offset, limit)
        return await self.repo.list_all(offset, limit)

    async def count(self) -> int:
        """Return total number of propositions."""
        return await self.repo.count()

    async def create(self, data: ProposicaoCreate) -> Proposicao:
        """Create a new proposition.

        Args:
            data: Validated proposition data.

        Returns:
            Created Proposicao instance.
        """
        proposicao = Proposicao(**data.model_dump())
        result = await self.repo.create(proposicao)
        logger.info("proposicao.created", id=result.id, tipo=result.tipo, numero=result.numero)
        return result

    async def update(self, proposicao_id: int, data: ProposicaoUpdate) -> Proposicao:
        """Update an existing proposition.

        Args:
            proposicao_id: ID of the proposition to update.
            data: Fields to update (partial).

        Returns:
            Updated Proposicao.

        Raises:
            NotFoundException: If proposition doesn't exist.
        """
        proposicao = await self.repo.get_by_id_or_raise(proposicao_id)
        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            return proposicao
        result = await self.repo.update(proposicao, update_data)
        logger.info("proposicao.updated", id=result.id)
        return result

    async def upsert_from_api(self, api_data: dict) -> Proposicao:
        """Create or update a proposition from Câmara API data.

        Used by the sync service to persist data from the external API.
        Avoids duplicates by checking existence first.

        Args:
            api_data: Dictionary with proposition fields from API.

        Returns:
            Created or updated Proposicao.
        """
        existing = await self.repo.get_by_id(api_data["id"])
        if existing:
            update_fields = {
                k: v for k, v in api_data.items()
                if k != "id" and v is not None
            }
            update_fields["ultima_sincronizacao"] = datetime.now(timezone.utc)
            result = await self.repo.update(existing, update_fields)
            logger.info("proposicao.upsert.updated", id=result.id)
            return result
        else:
            api_data["ultima_sincronizacao"] = datetime.now(timezone.utc)
            proposicao = Proposicao(**api_data)
            result = await self.repo.create(proposicao)
            logger.info("proposicao.upsert.created", id=result.id)
            return result

    async def delete(self, proposicao_id: int) -> None:
        """Delete a proposition.

        Args:
            proposicao_id: Proposition ID.

        Raises:
            NotFoundException: If proposition doesn't exist.
        """
        proposicao = await self.repo.get_by_id_or_raise(proposicao_id)
        await self.repo.delete(proposicao)
        logger.info("proposicao.deleted", id=proposicao_id)
