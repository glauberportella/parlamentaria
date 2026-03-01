"""Generic async repository base class using SQLAlchemy 2.0."""

from typing import Any, Generic, TypeVar, Sequence
from uuid import UUID

from sqlalchemy import select, func, delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base
from app.exceptions import NotFoundException

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Generic async CRUD repository.

    Provides standard operations for any SQLAlchemy model.

    Args:
        model: SQLAlchemy model class.
        session: Async database session.
    """

    def __init__(self, model: type[ModelType], session: AsyncSession) -> None:
        self.model = model
        self.session = session

    async def get_by_id(self, id: int | UUID) -> ModelType | None:
        """Get a single record by primary key.

        Args:
            id: Primary key value.

        Returns:
            Model instance or None if not found.
        """
        return await self.session.get(self.model, id)

    async def get_by_id_or_raise(self, id: int | UUID) -> ModelType:
        """Get a single record by primary key, raising if not found.

        Args:
            id: Primary key value.

        Returns:
            Model instance.

        Raises:
            NotFoundException: If record doesn't exist.
        """
        instance = await self.get_by_id(id)
        if instance is None:
            raise NotFoundException(
                detail=f"{self.model.__name__} com id={id} não encontrado"
            )
        return instance

    async def list_all(
        self,
        offset: int = 0,
        limit: int = 50,
    ) -> Sequence[ModelType]:
        """List records with pagination.

        Args:
            offset: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            Sequence of model instances.
        """
        stmt = select(self.model).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count(self) -> int:
        """Count total records.

        Returns:
            Total number of records.
        """
        stmt = select(func.count()).select_from(self.model)
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def create(self, instance: ModelType) -> ModelType:
        """Insert a new record.

        Args:
            instance: Model instance to persist.

        Returns:
            The persisted model instance.
        """
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def create_many(self, instances: list[ModelType]) -> list[ModelType]:
        """Insert multiple records.

        Args:
            instances: List of model instances to persist.

        Returns:
            List of persisted model instances.
        """
        self.session.add_all(instances)
        await self.session.flush()
        for instance in instances:
            await self.session.refresh(instance)
        return instances

    async def update(self, instance: ModelType, data: dict[str, Any]) -> ModelType:
        """Update a record with given data.

        Args:
            instance: Existing model instance.
            data: Dict of field -> value to update.

        Returns:
            Updated model instance.
        """
        for key, value in data.items():
            if hasattr(instance, key):
                setattr(instance, key, value)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def delete(self, instance: ModelType) -> None:
        """Delete a record.

        Args:
            instance: Model instance to delete.
        """
        await self.session.delete(instance)
        await self.session.flush()

    async def exists(self, id: int | UUID) -> bool:
        """Check if a record exists by primary key.

        Args:
            id: Primary key value.

        Returns:
            True if exists.
        """
        instance = await self.get_by_id(id)
        return instance is not None
