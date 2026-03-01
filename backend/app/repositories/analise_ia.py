"""Repository for AnaliseIA domain model."""

from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.analise_ia import AnaliseIA
from app.repositories.base import BaseRepository


class AnaliseIARepository(BaseRepository[AnaliseIA]):
    """Repository for AI analysis CRUD operations."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(AnaliseIA, session)

    async def find_latest_by_proposicao(self, proposicao_id: int) -> AnaliseIA | None:
        """Find the latest analysis for a proposition.

        Args:
            proposicao_id: Proposition ID.

        Returns:
            Latest AnaliseIA or None.
        """
        stmt = (
            select(AnaliseIA)
            .where(AnaliseIA.proposicao_id == proposicao_id)
            .order_by(AnaliseIA.versao.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_proposicao(
        self, proposicao_id: int
    ) -> Sequence[AnaliseIA]:
        """List all analyses for a proposition.

        Args:
            proposicao_id: Proposition ID.

        Returns:
            Sequence of analyses ordered by version descending.
        """
        stmt = (
            select(AnaliseIA)
            .where(AnaliseIA.proposicao_id == proposicao_id)
            .order_by(AnaliseIA.versao.desc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
