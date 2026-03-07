"""Repository for Partido domain model."""

from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.partido import Partido
from app.repositories.base import BaseRepository


class PartidoRepository(BaseRepository[Partido]):
    """Repository for political party CRUD operations."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Partido, session)

    async def find_by_sigla(self, sigla: str) -> Partido | None:
        """Find a party by abbreviation.

        Args:
            sigla: Party abbreviation (e.g., PT, PL, PSOL).

        Returns:
            Partido or None.
        """
        stmt = select(Partido).where(Partido.sigla == sigla)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_all_ordered(
        self, offset: int = 0, limit: int = 100
    ) -> Sequence[Partido]:
        """List all parties ordered by abbreviation.

        Args:
            offset: Number of records to skip.
            limit: Maximum number of records.

        Returns:
            Sequence of parties.
        """
        stmt = (
            select(Partido)
            .order_by(Partido.sigla)
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
