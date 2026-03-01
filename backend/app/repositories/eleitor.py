"""Repository for Eleitor domain model."""

import uuid
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.eleitor import Eleitor
from app.repositories.base import BaseRepository


class EleitorRepository(BaseRepository[Eleitor]):
    """Repository for voter CRUD operations."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Eleitor, session)

    async def find_by_email(self, email: str) -> Eleitor | None:
        """Find a voter by email.

        Args:
            email: Email address.

        Returns:
            Eleitor or None.
        """
        stmt = select(Eleitor).where(Eleitor.email == email)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_by_chat_id(self, chat_id: str) -> Eleitor | None:
        """Find a voter by messaging platform chat ID.

        Args:
            chat_id: Chat ID from the messaging platform.

        Returns:
            Eleitor or None.
        """
        stmt = select(Eleitor).where(Eleitor.chat_id == chat_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_by_uf(self, uf: str, offset: int = 0, limit: int = 50) -> Sequence[Eleitor]:
        """Find voters by state.

        Args:
            uf: State abbreviation.
            offset: Number of records to skip.
            limit: Maximum number of records.

        Returns:
            Sequence of voters.
        """
        stmt = (
            select(Eleitor)
            .where(Eleitor.uf == uf)
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def find_by_tema_interesse(
        self, tema: str, offset: int = 0, limit: int = 50
    ) -> Sequence[Eleitor]:
        """Find voters interested in a specific theme.

        Args:
            tema: Theme to filter by.
            offset: Number of records to skip.
            limit: Maximum number of records.

        Returns:
            Sequence of voters interested in the theme.
        """
        stmt = (
            select(Eleitor)
            .where(Eleitor.temas_interesse.any(tema))
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
