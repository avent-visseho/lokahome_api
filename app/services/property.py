"""
Property service for listing management operations.
"""
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    InsufficientPermissionsException,
    NotFoundException,
)
from app.models.property import Property, PropertyImage, PropertyStatus
from app.models.user import User, UserRole
from app.repositories.property import (
    PropertyFavoriteRepository,
    PropertyImageRepository,
    PropertyRepository,
)
from app.schemas.property import PropertyCreate, PropertySearchParams, PropertyUpdate


class PropertyService:
    """Service for property operations."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.property_repo = PropertyRepository(session)
        self.image_repo = PropertyImageRepository(session)
        self.favorite_repo = PropertyFavoriteRepository(session)

    async def get_property(self, property_id: UUID) -> Property:
        """
        Get property by ID.

        Args:
            property_id: Property UUID

        Returns:
            Property instance

        Raises:
            NotFoundException: If property not found
        """
        property_obj = await self.property_repo.get_with_details(property_id)
        if not property_obj:
            raise NotFoundException("Bien immobilier")
        return property_obj

    async def create_property(
        self, owner: User, data: PropertyCreate
    ) -> Property:
        """
        Create a new property listing.

        Args:
            owner: Property owner
            data: Property creation data

        Returns:
            Created property
        """
        # Only landlords and admins can create properties
        if owner.role not in [UserRole.LANDLORD, UserRole.ADMIN]:
            raise InsufficientPermissionsException(
                "Seuls les propriétaires peuvent créer des annonces"
            )

        property_data = data.model_dump()
        property_data["owner_id"] = owner.id
        property_data["status"] = PropertyStatus.PENDING  # Requires approval

        property_obj = await self.property_repo.create(property_data)
        # Reload with images eagerly loaded for response serialization
        return await self.property_repo.get_with_details(property_obj.id)  # type: ignore[return-value]

    async def update_property(
        self,
        property_id: UUID,
        user: User,
        data: PropertyUpdate,
    ) -> Property:
        """
        Update a property listing.

        Args:
            property_id: Property UUID
            user: User making the update
            data: Update data

        Returns:
            Updated property

        Raises:
            NotFoundException: If property not found
            InsufficientPermissionsException: If user not owner or admin
        """
        property_obj = await self.get_property(property_id)

        # Check ownership
        if property_obj.owner_id != user.id and user.role != UserRole.ADMIN:
            raise InsufficientPermissionsException(
                "Vous n'êtes pas autorisé à modifier ce bien"
            )

        update_data = data.model_dump(exclude_unset=True)
        return await self.property_repo.update(property_obj, update_data)

    async def delete_property(
        self, property_id: UUID, user: User
    ) -> None:
        """
        Delete a property listing.

        Args:
            property_id: Property UUID
            user: User making the deletion
        """
        property_obj = await self.get_property(property_id)

        # Check ownership
        if property_obj.owner_id != user.id and user.role != UserRole.ADMIN:
            raise InsufficientPermissionsException(
                "Vous n'êtes pas autorisé à supprimer ce bien"
            )

        await self.property_repo.delete(property_obj)

    async def search_properties(
        self, params: PropertySearchParams
    ) -> tuple[list[Property], int]:
        """
        Search properties with filters.

        Returns:
            Tuple of (properties list, total count)
        """
        properties = await self.property_repo.search(
            query_str=params.query,
            city=params.city,
            neighborhood=params.neighborhood,
            property_type=params.property_type,
            min_price=params.min_price,
            max_price=params.max_price,
            min_bedrooms=params.min_bedrooms,
            max_bedrooms=params.max_bedrooms,
            amenities=params.amenities,
            pets_allowed=params.pets_allowed,
            is_available=params.is_available,
            skip=(params.page - 1) * params.page_size,
            limit=params.page_size,
            sort_by=params.sort_by,
            sort_desc=params.sort_order == "desc",
        )

        total = await self.property_repo.count_search(
            city=params.city,
            property_type=params.property_type,
            min_price=params.min_price,
            max_price=params.max_price,
            is_available=params.is_available,
        )

        return properties, total

    async def get_nearby_properties(
        self,
        latitude: Decimal,
        longitude: Decimal,
        radius_km: float = 5,
        limit: int = 10,
    ) -> list[Property]:
        """Get properties near a location."""
        return await self.property_repo.get_nearby(
            latitude=latitude,
            longitude=longitude,
            radius_km=radius_km,
            limit=limit,
        )

    async def get_user_properties(
        self,
        owner_id: UUID,
        *,
        status: PropertyStatus | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Property]:
        """Get properties owned by a user."""
        return await self.property_repo.get_by_owner(
            owner_id=owner_id,
            status=status,
            skip=skip,
            limit=limit,
        )

    async def get_featured_properties(
        self, limit: int = 10
    ) -> list[Property]:
        """Get featured properties."""
        return await self.property_repo.get_featured(limit=limit)

    async def increment_views(self, property_id: UUID) -> None:
        """Increment property view count."""
        await self.property_repo.increment_views(property_id)

    # Image management
    async def add_image(
        self,
        property_id: UUID,
        user: User,
        url: str,
        is_primary: bool = False,
        caption: str | None = None,
    ) -> PropertyImage:
        """Add image to property."""
        property_obj = await self.get_property(property_id)

        if property_obj.owner_id != user.id and user.role != UserRole.ADMIN:
            raise InsufficientPermissionsException()

        # Get current image count for ordering
        images = await self.image_repo.get_by_property(property_id)
        order = len(images)

        data: dict = {
            "property_id": property_id,
            "url": url,
            "is_primary": is_primary or order == 0,  # First image is always primary
            "order": order,
        }
        if caption:
            data["caption"] = caption

        return await self.image_repo.create(data)

    async def delete_image(
        self,
        image_id: UUID,
        user: User,
    ) -> None:
        """Delete property image."""
        image = await self.image_repo.get(image_id)
        if not image:
            raise NotFoundException("Image")

        property_obj = await self.get_property(image.property_id)

        if property_obj.owner_id != user.id and user.role != UserRole.ADMIN:
            raise InsufficientPermissionsException()

        await self.image_repo.delete(image)

    # Favorites
    async def toggle_favorite(
        self, user_id: UUID, property_id: UUID
    ) -> bool:
        """Toggle property favorite status."""
        # Verify property exists
        await self.get_property(property_id)
        return await self.favorite_repo.toggle_favorite(user_id, property_id)

    async def get_user_favorites(
        self,
        user_id: UUID,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Property]:
        """Get user's favorite properties."""
        return await self.favorite_repo.get_user_favorites(
            user_id, skip=skip, limit=limit
        )

    async def is_favorited(
        self, user_id: UUID, property_id: UUID
    ) -> bool:
        """Check if property is favorited by user."""
        return await self.favorite_repo.is_favorited(user_id, property_id)

    # Admin operations
    async def approve_property(self, property_id: UUID) -> Property:
        """Approve a property listing (admin)."""
        property_obj = await self.get_property(property_id)
        return await self.property_repo.update(
            property_obj,
            {
                "status": PropertyStatus.ACTIVE,
                "is_verified": True,
            },
        )

    async def reject_property(
        self, property_id: UUID, reason: str | None = None
    ) -> Property:
        """Reject a property listing (admin)."""
        property_obj = await self.get_property(property_id)
        return await self.property_repo.update(
            property_obj,
            {"status": PropertyStatus.REJECTED},
        )

    async def feature_property(
        self, property_id: UUID, featured: bool = True
    ) -> Property:
        """Set property as featured (admin)."""
        property_obj = await self.get_property(property_id)
        return await self.property_repo.update(
            property_obj, {"is_featured": featured}
        )
