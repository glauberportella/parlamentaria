"""Repository for Proposição domain model."""

from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.proposicao import Proposicao
from app.repositories.base import BaseRepository


class ProposicaoRepository(BaseRepository[Proposicao]):
    """Repository for legislative proposition CRUD operations."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Proposicao, session)

    async def find_by_tipo_numero_ano(
        self, tipo: str, numero: int, ano: int
    ) -> Proposicao | None:
        """Find a proposition by type, number and year.

        Args:
            tipo: Proposition type (PL, PEC, etc.).
            numero: Proposition number.
            ano: Year.

        Returns:
            Proposicao or None.
        """
        stmt = select(Proposicao).where(
            Proposicao.tipo == tipo,
            Proposicao.numero == numero,
            Proposicao.ano == ano,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_by_tema(self, tema: str, offset: int = 0, limit: int = 50) -> Sequence[Proposicao]:
        """Find propositions by theme.

        Args:
            tema: Theme to filter by.
            offset: Number of records to skip.
            limit: Maximum number of records.

        Returns:
            Sequence of propositions.
        """
        stmt = (
            select(Proposicao)
            .where(Proposicao.temas.any(tema))
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def find_by_ano(self, ano: int, offset: int = 0, limit: int = 50) -> Sequence[Proposicao]:
        """Find propositions by year.

        Args:
            ano: Year to filter by.
            offset: Number of records to skip.
            limit: Maximum number of records.

        Returns:
            Sequence of propositions.
        """
        stmt = (
            select(Proposicao)
            .where(Proposicao.ano == ano)
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
