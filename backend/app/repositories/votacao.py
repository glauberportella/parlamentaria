"""Repository for Votação domain model."""

from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.votacao import Votacao
from app.repositories.base import BaseRepository


class VotacaoRepository(BaseRepository[Votacao]):
    """Repository for vote session CRUD operations."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Votacao, session)

    async def find_by_proposicao(
        self, proposicao_id: int, offset: int = 0, limit: int = 50
    ) -> Sequence[Votacao]:
        """Find vote sessions for a proposition.

        Args:
            proposicao_id: Proposition ID.
            offset: Number of records to skip.
            limit: Maximum number of records.

        Returns:
            Sequence of vote sessions.
        """
        stmt = (
            select(Votacao)
            .where(Votacao.proposicao_id == proposicao_id)
            .order_by(Votacao.data.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
