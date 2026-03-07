"""Repository for Evento domain model."""

from datetime import datetime
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.evento import Evento
from app.repositories.base import BaseRepository


class EventoRepository(BaseRepository[Evento]):
    """Repository for plenary event CRUD operations."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Evento, session)

    async def find_by_data_range(
        self,
        data_inicio: datetime,
        data_fim: datetime,
        offset: int = 0,
        limit: int = 50,
    ) -> Sequence[Evento]:
        """Find events within a date range.

        Args:
            data_inicio: Start datetime.
            data_fim: End datetime.
            offset: Number of records to skip.
            limit: Maximum number of records.

        Returns:
            Sequence of events.
        """
        stmt = (
            select(Evento)
            .where(Evento.data_inicio >= data_inicio, Evento.data_inicio <= data_fim)
            .order_by(Evento.data_inicio.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def find_by_situacao(
        self, situacao: str, offset: int = 0, limit: int = 50
    ) -> Sequence[Evento]:
        """Find events by situation/status.

        Args:
            situacao: Event situation (e.g., 'Encerrada', 'Em Andamento').
            offset: Number of records to skip.
            limit: Maximum number of records.

        Returns:
            Sequence of events.
        """
        stmt = (
            select(Evento)
            .where(Evento.situacao == situacao)
            .order_by(Evento.data_inicio.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_recent(self, limit: int = 20) -> Sequence[Evento]:
        """List most recent events.

        Args:
            limit: Maximum number of records.

        Returns:
            Sequence of events ordered by start date descending.
        """
        stmt = (
            select(Evento)
            .order_by(Evento.data_inicio.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
