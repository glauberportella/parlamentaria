"""Repository for ComparativoVotacao domain model."""

from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.comparativo import ComparativoVotacao
from app.repositories.base import BaseRepository


class ComparativoRepository(BaseRepository[ComparativoVotacao]):
    """Repository for comparative vote analysis CRUD operations."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(ComparativoVotacao, session)

    async def get_by_proposicao(self, proposicao_id: int) -> ComparativoVotacao | None:
        """Get the most recent comparative for a proposition.

        Args:
            proposicao_id: Proposition ID.

        Returns:
            ComparativoVotacao or None.
        """
        stmt = (
            select(ComparativoVotacao)
            .where(ComparativoVotacao.proposicao_id == proposicao_id)
            .order_by(ComparativoVotacao.data_geracao.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_recent(self, limit: int = 20) -> Sequence[ComparativoVotacao]:
        """List the most recent comparatives.

        Args:
            limit: Maximum number of records.

        Returns:
            Sequence of comparativos ordered by data_geracao descending.
        """
        stmt = (
            select(ComparativoVotacao)
            .order_by(ComparativoVotacao.data_geracao.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_by_proposicao_ids(
        self, proposicao_ids: list[int]
    ) -> Sequence[ComparativoVotacao]:
        """Get comparatives for multiple propositions.

        Args:
            proposicao_ids: List of proposition IDs.

        Returns:
            Sequence of comparativos.
        """
        if not proposicao_ids:
            return []
        stmt = (
            select(ComparativoVotacao)
            .where(ComparativoVotacao.proposicao_id.in_(proposicao_ids))
            .order_by(ComparativoVotacao.data_geracao.desc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def exists_for_votacao(self, votacao_camara_id: str) -> bool:
        """Check if a comparative already exists for a parliamentary vote.

        Args:
            votacao_camara_id: Parliamentary vote session ID.

        Returns:
            True if a comparative exists.
        """
        stmt = select(ComparativoVotacao.id).where(
            ComparativoVotacao.votacao_camara_id == votacao_camara_id
        ).limit(1)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None
