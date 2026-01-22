"""
Property schemas for validation and serialization.
"""
from decimal import Decimal
from uuid import UUID

from pydantic import Field, field_validator

from app.models.property import PropertyStatus, PropertyType, RentalPeriod
from app.schemas.base import BaseSchema, IDSchema, TimestampSchema
from app.schemas.user import UserPublicProfile


# --- Property Image Schemas ---
class PropertyImageBase(BaseSchema):
    """Base property image schema."""

    url: str
    thumbnail_url: str | None = None
    caption: str | None = None
    is_primary: bool = False
    order: int = 0


class PropertyImageCreate(PropertyImageBase):
    """Property image creation schema."""

    pass


class PropertyImageResponse(PropertyImageBase, IDSchema):
    """Property image response schema."""

    pass


# --- Property Schemas ---
class PropertyBase(BaseSchema):
    """Base property schema."""

    title: str = Field(min_length=5, max_length=200)
    description: str = Field(min_length=20)
    property_type: PropertyType

    # Location
    address: str = Field(min_length=5, max_length=500)
    city: str = Field(min_length=2, max_length=100)
    neighborhood: str | None = None
    postal_code: str | None = None
    country: str = "Bénin"
    latitude: Decimal | None = Field(default=None, ge=-90, le=90)
    longitude: Decimal | None = Field(default=None, ge=-180, le=180)

    # Pricing
    price: Decimal = Field(gt=0)
    currency: str = "XOF"
    rental_period: RentalPeriod = RentalPeriod.MONTHLY
    deposit: Decimal | None = Field(default=None, ge=0)
    agency_fees: Decimal | None = Field(default=None, ge=0)

    # Characteristics
    bedrooms: int = Field(ge=0, le=50, default=1)
    bathrooms: int = Field(ge=0, le=20, default=1)
    surface_area: int | None = Field(default=None, ge=1)
    floor: int | None = None
    total_floors: int | None = None
    year_built: int | None = Field(default=None, ge=1800, le=2100)

    # Amenities
    amenities: list[str] = []

    # Rules
    pets_allowed: bool = False
    smoking_allowed: bool = False
    max_occupants: int | None = Field(default=None, ge=1)

    # Availability
    is_available: bool = True
    available_from: str | None = None
    minimum_stay: int | None = Field(default=None, ge=1)


class PropertyCreate(PropertyBase):
    """Property creation schema."""

    @field_validator("amenities", mode="before")
    @classmethod
    def validate_amenities(cls, v):
        if v is None:
            return []
        return v


class PropertyUpdate(BaseSchema):
    """Property update schema."""

    title: str | None = Field(default=None, min_length=5, max_length=200)
    description: str | None = Field(default=None, min_length=20)
    property_type: PropertyType | None = None

    # Location
    address: str | None = Field(default=None, min_length=5, max_length=500)
    city: str | None = Field(default=None, min_length=2, max_length=100)
    neighborhood: str | None = None
    latitude: Decimal | None = Field(default=None, ge=-90, le=90)
    longitude: Decimal | None = Field(default=None, ge=-180, le=180)

    # Pricing
    price: Decimal | None = Field(default=None, gt=0)
    rental_period: RentalPeriod | None = None
    deposit: Decimal | None = Field(default=None, ge=0)
    agency_fees: Decimal | None = Field(default=None, ge=0)

    # Characteristics
    bedrooms: int | None = Field(default=None, ge=0, le=50)
    bathrooms: int | None = Field(default=None, ge=0, le=20)
    surface_area: int | None = Field(default=None, ge=1)

    # Amenities
    amenities: list[str] | None = None

    # Rules
    pets_allowed: bool | None = None
    smoking_allowed: bool | None = None
    max_occupants: int | None = Field(default=None, ge=1)

    # Availability
    is_available: bool | None = None
    available_from: str | None = None
    minimum_stay: int | None = Field(default=None, ge=1)

    # Status
    status: PropertyStatus | None = None


class PropertyResponse(PropertyBase, IDSchema, TimestampSchema):
    """Property response schema."""

    owner_id: UUID
    status: PropertyStatus
    is_verified: bool
    is_featured: bool
    views_count: int
    favorites_count: int
    images: list[PropertyImageResponse] = []


class PropertyDetailResponse(PropertyResponse):
    """Detailed property response with owner info."""

    owner: UserPublicProfile


class PropertyListResponse(BaseSchema):
    """Property list item response."""

    id: UUID
    title: str
    property_type: PropertyType
    city: str
    neighborhood: str | None
    price: Decimal
    currency: str
    rental_period: RentalPeriod
    bedrooms: int
    bathrooms: int
    surface_area: int | None
    is_available: bool
    is_verified: bool
    is_featured: bool
    primary_image_url: str | None = None
    owner: UserPublicProfile


# --- Search and Filter Schemas ---
class PropertySearchParams(BaseSchema):
    """Property search parameters."""

    query: str | None = None
    city: str | None = None
    neighborhood: str | None = None
    property_type: PropertyType | None = None
    min_price: Decimal | None = Field(default=None, ge=0)
    max_price: Decimal | None = Field(default=None, ge=0)
    min_bedrooms: int | None = Field(default=None, ge=0)
    max_bedrooms: int | None = Field(default=None, ge=0)
    min_bathrooms: int | None = Field(default=None, ge=0)
    amenities: list[str] | None = None
    pets_allowed: bool | None = None
    is_available: bool | None = True

    # Geolocation
    latitude: Decimal | None = Field(default=None, ge=-90, le=90)
    longitude: Decimal | None = Field(default=None, ge=-180, le=180)
    radius_km: float | None = Field(default=None, gt=0, le=100)

    # Sorting
    sort_by: str = "created_at"
    sort_order: str = "desc"

    # Pagination
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class NearbyPropertiesRequest(BaseSchema):
    """Request for nearby properties."""

    latitude: Decimal = Field(ge=-90, le=90)
    longitude: Decimal = Field(ge=-180, le=180)
    radius_km: float = Field(default=5, gt=0, le=50)
    limit: int = Field(default=10, ge=1, le=50)
