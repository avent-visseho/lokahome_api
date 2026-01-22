"""
Base repository with common CRUD operations.
"""
from typing import Any, Generic, TypeVar
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """
    Base repository class with common CRUD operations.
    All repositories should inherit from this class.
    """

    def __init__(self, model: type[ModelType], session: AsyncSession):
        self.model = model
        self.session = session

    async def get(self, id: UUID) -> ModelType | None:
        """Get a single record by ID."""
        result = await self.session.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalar_one_or_none()

    async def get_by_field(self, field: str, value: Any) -> ModelType | None:
        """Get a single record by field value."""
        column = getattr(self.model, field)
        result = await self.session.execute(select(self.model).where(column == value))
        return result.scalar_one_or_none()

    async def get_multi(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        filters: dict[str, Any] | None = None,
        order_by: str | None = None,
        order_desc: bool = True,
    ) -> list[ModelType]:
        """Get multiple records with optional filtering and pagination."""
        query = select(self.model)

        # Apply filters
        if filters:
            for field, value in filters.items():
                if value is not None and hasattr(self.model, field):
                    column = getattr(self.model, field)
                    query = query.where(column == value)

        # Apply ordering
        if order_by and hasattr(self.model, order_by):
            column = getattr(self.model, order_by)
            query = query.order_by(column.desc() if order_desc else column.asc())

        # Apply pagination
        query = query.offset(skip).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count(self, filters: dict[str, Any] | None = None) -> int:
        """Count records with optional filtering."""
        query = select(func.count()).select_from(self.model)

        if filters:
            for field, value in filters.items():
                if value is not None and hasattr(self.model, field):
                    column = getattr(self.model, field)
                    query = query.where(column == value)

        result = await self.session.execute(query)
        return result.scalar_one()

    async def create(self, data: dict[str, Any]) -> ModelType:
        """Create a new record."""
        instance = self.model(**data)
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def update(
        self, instance: ModelType, data: dict[str, Any]
    ) -> ModelType:
        """Update an existing record."""
        for field, value in data.items():
            if hasattr(instance, field) and value is not None:
                setattr(instance, field, value)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def delete(self, instance: ModelType) -> None:
        """Delete a record."""
        await self.session.delete(instance)
        await self.session.flush()

    async def exists(self, id: UUID) -> bool:
        """Check if a record exists by ID."""
        query = select(func.count()).select_from(self.model).where(self.model.id == id)
        result = await self.session.execute(query)
        return result.scalar_one() > 0

    async def exists_by_field(self, field: str, value: Any) -> bool:
        """Check if a record exists by field value."""
        column = getattr(self.model, field)
        query = select(func.count()).select_from(self.model).where(column == value)
        result = await self.session.execute(query)
        return result.scalar_one() > 0
