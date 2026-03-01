"""Repository for Deputado domain model."""

from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.deputado import Deputado
from app.repositories.base import BaseRepository


class DeputadoRepository(BaseRepository[Deputado]):
    """Repository for deputy CRUD operations."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Deputado, session)

    async def find_by_nome(self, nome: str) -> Sequence[Deputado]:
        """Find deputies by name (case-insensitive, partial match).

        Args:
            nome: Name to search.

        Returns:
            Sequence of matching deputies.
        """
        stmt = select(Deputado).where(Deputado.nome.ilike(f"%{nome}%"))
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def find_by_partido(
        self, sigla_partido: str, offset: int = 0, limit: int = 50
    ) -> Sequence[Deputado]:
        """Find deputies by party.

        Args:
            sigla_partido: Party abbreviation.
            offset: Number of records to skip.
            limit: Maximum number of records.

        Returns:
            Sequence of deputies.
        """
        stmt = (
            select(Deputado)
            .where(Deputado.sigla_partido == sigla_partido)
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def find_by_uf(
        self, sigla_uf: str, offset: int = 0, limit: int = 50
    ) -> Sequence[Deputado]:
        """Find deputies by state.

        Args:
            sigla_uf: State abbreviation.
            offset: Number of records to skip.
            limit: Maximum number of records.

        Returns:
            Sequence of deputies.
        """
        stmt = (
            select(Deputado)
            .where(Deputado.sigla_uf == sigla_uf)
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
