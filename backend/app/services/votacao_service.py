"""Service for Votação business logic."""

from typing import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.votacao import Votacao
from app.logging import get_logger
from app.repositories.votacao import VotacaoRepository
from app.schemas.votacao import VotacaoCreate, VotacaoUpdate

logger = get_logger(__name__)


class VotacaoService:
    """Orchestrates parliamentary vote session operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = VotacaoRepository(session)

    async def get_by_id(self, votacao_id: str) -> Votacao:
        """Get a vote session by ID.

        Args:
            votacao_id: Vote session ID.

        Returns:
            Votacao instance.

        Raises:
            NotFoundException: If not found.
        """
        return await self.repo.get_by_id_or_raise(votacao_id)

    async def list_by_proposicao(
        self, proposicao_id: int, offset: int = 0, limit: int = 50
    ) -> Sequence[Votacao]:
        """List vote sessions for a proposition.

        Args:
            proposicao_id: Proposition ID.
            offset: Records to skip.
            limit: Maximum records.

        Returns:
            Sequence of Votacao.
        """
        return await self.repo.find_by_proposicao(proposicao_id, offset, limit)

    async def list_votacoes(self, offset: int = 0, limit: int = 50) -> Sequence[Votacao]:
        """List all vote sessions.

        Args:
            offset: Records to skip.
            limit: Maximum records.

        Returns:
            Sequence of Votacao.
        """
        return await self.repo.list_all(offset, limit)

    async def create(self, data: VotacaoCreate) -> Votacao:
        """Create a new vote session record.

        Args:
            data: Validated vote session data.

        Returns:
            Created Votacao.
        """
        votacao = Votacao(**data.model_dump())
        result = await self.repo.create(votacao)
        logger.info("votacao.created", id=result.id)
        return result

    async def upsert_from_api(self, api_data: dict) -> Votacao:
        """Create or update a vote session from Câmara API data.

        Args:
            api_data: Dictionary with vote session fields.

        Returns:
            Created or updated Votacao.
        """
        existing = await self.repo.get_by_id(api_data["id"])
        if existing:
            update_fields = {k: v for k, v in api_data.items() if k != "id" and v is not None}
            result = await self.repo.update(existing, update_fields)
            logger.info("votacao.upsert.updated", id=result.id)
            return result
        else:
            votacao = Votacao(**api_data)
            result = await self.repo.create(votacao)
            logger.info("votacao.upsert.created", id=result.id)
            return result
