"""Repository for VotoPopular domain model."""

import uuid
from typing import Sequence

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.voto_popular import VotoPopular, VotoEnum, TipoVoto
from app.repositories.base import BaseRepository


class VotoPopularRepository(BaseRepository[VotoPopular]):
    """Repository for popular vote CRUD operations."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(VotoPopular, session)

    async def find_by_eleitor_proposicao(
        self, eleitor_id: uuid.UUID, proposicao_id: int
    ) -> VotoPopular | None:
        """Find a vote by voter and proposition IDs.

        Args:
            eleitor_id: Voter UUID.
            proposicao_id: Proposition ID.

        Returns:
            VotoPopular or None.
        """
        stmt = select(VotoPopular).where(
            VotoPopular.eleitor_id == eleitor_id,
            VotoPopular.proposicao_id == proposicao_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def count_by_proposicao(
        self,
        proposicao_id: int,
        tipo_voto: TipoVoto | None = None,
    ) -> dict[str, int]:
        """Count votes by type for a proposition.

        Args:
            proposicao_id: Proposition ID.
            tipo_voto: If provided, count only votes of this classification.
                       None means count ALL votes (OFICIAL + OPINIAO).

        Returns:
            Dict with SIM, NAO, ABSTENCAO counts and total.
        """
        stmt = (
            select(VotoPopular.voto, func.count(VotoPopular.id))
            .where(VotoPopular.proposicao_id == proposicao_id)
        )
        if tipo_voto is not None:
            stmt = stmt.where(VotoPopular.tipo_voto == tipo_voto)
        stmt = stmt.group_by(VotoPopular.voto)

        result = await self.session.execute(stmt)
        counts = {row[0].value: row[1] for row in result.all()}
        return {
            "SIM": counts.get("SIM", 0),
            "NAO": counts.get("NAO", 0),
            "ABSTENCAO": counts.get("ABSTENCAO", 0),
            "total": sum(counts.values()),
        }

    async def count_oficiais_by_proposicao(self, proposicao_id: int) -> dict[str, int]:
        """Count only OFICIAL votes for a proposition.

        Official votes are from eligible Brazilian citizens (16+, verified).
        This is the result sent to parliamentarians.

        Args:
            proposicao_id: Proposition ID.

        Returns:
            Dict with SIM, NAO, ABSTENCAO counts and total.
        """
        return await self.count_by_proposicao(proposicao_id, tipo_voto=TipoVoto.OFICIAL)

    async def list_by_eleitor(
        self, eleitor_id: uuid.UUID, offset: int = 0, limit: int = 50
    ) -> Sequence[VotoPopular]:
        """List votes by a specific voter.

        Args:
            eleitor_id: Voter UUID.
            offset: Number of records to skip.
            limit: Maximum number of records.

        Returns:
            Sequence of votes.
        """
        stmt = (
            select(VotoPopular)
            .where(VotoPopular.eleitor_id == eleitor_id)
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_by_proposicao(
        self, proposicao_id: int, offset: int = 0, limit: int = 500
    ) -> Sequence[VotoPopular]:
        """List all votes for a specific proposition.

        Args:
            proposicao_id: Proposition ID.
            offset: Number of records to skip.
            limit: Maximum number of records.

        Returns:
            Sequence of votes.
        """
        stmt = (
            select(VotoPopular)
            .where(VotoPopular.proposicao_id == proposicao_id)
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
