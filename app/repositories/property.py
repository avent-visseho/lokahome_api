"""
Property repository for data access operations.
"""
from decimal import Decimal
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.property import (
    Property,
    PropertyFavorite,
    PropertyImage,
    PropertyStatus,
    PropertyType,
)
from app.repositories.base import BaseRepository


class PropertyRepository(BaseRepository[Property]):
    """Repository for Property model operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(Property, session)

    async def get_with_details(self, property_id: UUID) -> Property | None:
        """Get property with owner and images loaded."""
        result = await self.session.execute(
            select(Property)
            .options(
                selectinload(Property.owner),
                selectinload(Property.images),
            )
            .where(Property.id == property_id)
        )
        return result.scalar_one_or_none()

    async def get_by_owner(
        self,
        owner_id: UUID,
        *,
        skip: int = 0,
        limit: int = 100,
        status: PropertyStatus | None = None,
    ) -> list[Property]:
        """Get properties by owner."""
        query = (
            select(Property)
            .options(selectinload(Property.images))
            .where(Property.owner_id == owner_id)
        )

        if status:
            query = query.where(Property.status == status)

        query = query.order_by(Property.created_at.desc()).offset(skip).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def search(
        self,
        *,
        query_str: str | None = None,
        city: str | None = None,
        neighborhood: str | None = None,
        property_type: PropertyType | None = None,
        min_price: Decimal | None = None,
        max_price: Decimal | None = None,
        min_bedrooms: int | None = None,
        max_bedrooms: int | None = None,
        amenities: list[str] | None = None,
        pets_allowed: bool | None = None,
        is_available: bool | None = True,
        skip: int = 0,
        limit: int = 20,
        sort_by: str = "created_at",
        sort_desc: bool = True,
    ) -> list[Property]:
        """Search properties with multiple filters."""
        query = (
            select(Property)
            .options(
                selectinload(Property.owner),
                selectinload(Property.images),
            )
            .where(Property.status == PropertyStatus.ACTIVE)
        )

        # Text search
        if query_str:
            search_pattern = f"%{query_str}%"
            query = query.where(
                or_(
                    Property.title.ilike(search_pattern),
                    Property.description.ilike(search_pattern),
                    Property.address.ilike(search_pattern),
                )
            )

        # Location filters
        if city:
            query = query.where(func.lower(Property.city) == city.lower())
        if neighborhood:
            query = query.where(
                func.lower(Property.neighborhood) == neighborhood.lower()
            )

        # Type filter
        if property_type:
            query = query.where(Property.property_type == property_type)

        # Price filters
        if min_price is not None:
            query = query.where(Property.price >= min_price)
        if max_price is not None:
            query = query.where(Property.price <= max_price)

        # Bedrooms filter
        if min_bedrooms is not None:
            query = query.where(Property.bedrooms >= min_bedrooms)
        if max_bedrooms is not None:
            query = query.where(Property.bedrooms <= max_bedrooms)

        # Amenities filter (JSONB contains)
        if amenities:
            for amenity in amenities:
                query = query.where(Property.amenities.contains([amenity]))

        # Boolean filters
        if pets_allowed is not None:
            query = query.where(Property.pets_allowed == pets_allowed)
        if is_available is not None:
            query = query.where(Property.is_available == is_available)

        # Sorting
        if hasattr(Property, sort_by):
            column = getattr(Property, sort_by)
            query = query.order_by(column.desc() if sort_desc else column.asc())

        # Pagination
        query = query.offset(skip).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count_search(
        self,
        *,
        city: str | None = None,
        property_type: PropertyType | None = None,
        min_price: Decimal | None = None,
        max_price: Decimal | None = None,
        is_available: bool | None = True,
    ) -> int:
        """Count properties matching search criteria."""
        query = (
            select(func.count())
            .select_from(Property)
            .where(Property.status == PropertyStatus.ACTIVE)
        )

        if city:
            query = query.where(func.lower(Property.city) == city.lower())
        if property_type:
            query = query.where(Property.property_type == property_type)
        if min_price is not None:
            query = query.where(Property.price >= min_price)
        if max_price is not None:
            query = query.where(Property.price <= max_price)
        if is_available is not None:
            query = query.where(Property.is_available == is_available)

        result = await self.session.execute(query)
        return result.scalar_one()

    async def get_nearby(
        self,
        latitude: Decimal,
        longitude: Decimal,
        radius_km: float,
        *,
        limit: int = 10,
    ) -> list[Property]:
        """
        Get nearby properties using Haversine formula.
        For production, consider using PostGIS ST_DWithin.
        """
        # Haversine formula for distance calculation
        # This is a simplified version - use PostGIS for production
        earth_radius_km = 6371

        lat_diff = func.radians(Property.latitude - latitude)
        lon_diff = func.radians(Property.longitude - longitude)

        a = (
            func.sin(lat_diff / 2) * func.sin(lat_diff / 2)
            + func.cos(func.radians(latitude))
            * func.cos(func.radians(Property.latitude))
            * func.sin(lon_diff / 2)
            * func.sin(lon_diff / 2)
        )

        c = 2 * func.atan2(func.sqrt(a), func.sqrt(1 - a))
        distance = earth_radius_km * c

        query = (
            select(Property)
            .options(
                selectinload(Property.owner),
                selectinload(Property.images),
            )
            .where(
                and_(
                    Property.status == PropertyStatus.ACTIVE,
                    Property.is_available == True,  # noqa: E712
                    Property.latitude.isnot(None),
                    Property.longitude.isnot(None),
                    distance <= radius_km,
                )
            )
            .order_by(distance)
            .limit(limit)
        )

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def increment_views(self, property_id: UUID) -> None:
        """Increment property view count."""
        property_obj = await self.get(property_id)
        if property_obj:
            property_obj.views_count += 1
            await self.session.flush()

    async def get_featured(self, *, limit: int = 10) -> list[Property]:
        """Get featured properties."""
        result = await self.session.execute(
            select(Property)
            .options(
                selectinload(Property.owner),
                selectinload(Property.images),
            )
            .where(
                and_(
                    Property.status == PropertyStatus.ACTIVE,
                    Property.is_featured == True,  # noqa: E712
                    Property.is_available == True,  # noqa: E712
                )
            )
            .order_by(Property.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())


class PropertyImageRepository(BaseRepository[PropertyImage]):
    """Repository for PropertyImage model operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(PropertyImage, session)

    async def get_by_property(self, property_id: UUID) -> list[PropertyImage]:
        """Get all images for a property."""
        result = await self.session.execute(
            select(PropertyImage)
            .where(PropertyImage.property_id == property_id)
            .order_by(PropertyImage.order)
        )
        return list(result.scalars().all())

    async def set_primary(self, image_id: UUID, property_id: UUID) -> None:
        """Set an image as primary, unsetting others."""
        # Unset current primary
        await self.session.execute(
            select(PropertyImage).where(
                and_(
                    PropertyImage.property_id == property_id,
                    PropertyImage.is_primary == True,  # noqa: E712
                )
            )
        )
        # Set new primary
        image = await self.get(image_id)
        if image:
            image.is_primary = True
            await self.session.flush()


class PropertyFavoriteRepository(BaseRepository[PropertyFavorite]):
    """Repository for PropertyFavorite model operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(PropertyFavorite, session)

    async def get_user_favorites(
        self, user_id: UUID, *, skip: int = 0, limit: int = 100
    ) -> list[Property]:
        """Get user's favorite properties."""
        result = await self.session.execute(
            select(Property)
            .join(PropertyFavorite)
            .where(PropertyFavorite.user_id == user_id)
            .options(
                selectinload(Property.owner),
                selectinload(Property.images),
            )
            .order_by(PropertyFavorite.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def is_favorited(self, user_id: UUID, property_id: UUID) -> bool:
        """Check if property is favorited by user."""
        result = await self.session.execute(
            select(func.count())
            .select_from(PropertyFavorite)
            .where(
                and_(
                    PropertyFavorite.user_id == user_id,
                    PropertyFavorite.property_id == property_id,
                )
            )
        )
        return result.scalar_one() > 0

    async def toggle_favorite(
        self, user_id: UUID, property_id: UUID
    ) -> bool:
        """Toggle favorite status. Returns True if added, False if removed."""
        existing = await self.session.execute(
            select(PropertyFavorite).where(
                and_(
                    PropertyFavorite.user_id == user_id,
                    PropertyFavorite.property_id == property_id,
                )
            )
        )
        favorite = existing.scalar_one_or_none()

        if favorite:
            await self.session.delete(favorite)
            await self.session.flush()
            return False
        else:
            new_favorite = PropertyFavorite(user_id=user_id, property_id=property_id)
            self.session.add(new_favorite)
            await self.session.flush()
            return True
