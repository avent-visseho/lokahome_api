"""
Property model for real estate listings.
"""
import enum
import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.booking import Booking
    from app.models.review import Review
    from app.models.user import User


class PropertyType(str, enum.Enum):
    """Types of properties."""

    APARTMENT = "apartment"
    HOUSE = "house"
    STUDIO = "studio"
    VILLA = "villa"
    DUPLEX = "duplex"
    ROOM = "room"
    OFFICE = "office"
    COMMERCIAL = "commercial"


class PropertyStatus(str, enum.Enum):
    """Property listing status."""

    DRAFT = "draft"
    PENDING = "pending"
    ACTIVE = "active"
    RENTED = "rented"
    INACTIVE = "inactive"
    REJECTED = "rejected"


class RentalPeriod(str, enum.Enum):
    """Rental period types."""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"


class Property(BaseModel):
    """Property listing model."""

    __tablename__ = "properties"

    # Owner relationship
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # Basic info
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    property_type: Mapped[PropertyType] = mapped_column(
        Enum(PropertyType), nullable=False
    )
    status: Mapped[PropertyStatus] = mapped_column(
        Enum(PropertyStatus), default=PropertyStatus.DRAFT, nullable=False
    )

    # Location
    address: Mapped[str] = mapped_column(String(500), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    neighborhood: Mapped[str | None] = mapped_column(String(100), index=True)
    postal_code: Mapped[str | None] = mapped_column(String(20))
    country: Mapped[str] = mapped_column(String(100), default="Bénin", nullable=False)

    # Geolocation (for PostGIS queries)
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 8))
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(11, 8))

    # Pricing
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="XOF", nullable=False)
    rental_period: Mapped[RentalPeriod] = mapped_column(
        Enum(RentalPeriod), default=RentalPeriod.MONTHLY, nullable=False
    )
    deposit: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    agency_fees: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))

    # Characteristics
    bedrooms: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    bathrooms: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    surface_area: Mapped[int | None] = mapped_column(Integer)  # in m²
    floor: Mapped[int | None] = mapped_column(Integer)
    total_floors: Mapped[int | None] = mapped_column(Integer)
    year_built: Mapped[int | None] = mapped_column(Integer)

    # Amenities (stored as JSONB for flexibility)
    amenities: Mapped[list | None] = mapped_column(
        JSONB,
        default=[],
    )  # ["wifi", "parking", "pool", "garden", "security", etc.]

    # Rules
    pets_allowed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    smoking_allowed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    max_occupants: Mapped[int | None] = mapped_column(Integer)

    # Availability
    is_available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    available_from: Mapped[str | None] = mapped_column(String(50))
    minimum_stay: Mapped[int | None] = mapped_column(Integer)  # in days

    # Stats
    views_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    favorites_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Verification
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Featured listing
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    owner: Mapped["User"] = relationship("User", back_populates="properties")
    images: Mapped[list["PropertyImage"]] = relationship(
        "PropertyImage", back_populates="property", cascade="all, delete-orphan"
    )
    bookings: Mapped[list["Booking"]] = relationship(
        "Booking", back_populates="booked_property", cascade="all, delete-orphan"
    )
    reviews: Mapped[list["Review"]] = relationship(
        "Review", back_populates="property", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Property {self.title}>"


class PropertyImage(BaseModel):
    """Property images model."""

    __tablename__ = "property_images"

    property_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("properties.id", ondelete="CASCADE"),
        nullable=False,
    )
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    thumbnail_url: Mapped[str | None] = mapped_column(String(500))
    caption: Mapped[str | None] = mapped_column(String(200))
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationship
    property: Mapped["Property"] = relationship("Property", back_populates="images")

    def __repr__(self) -> str:
        return f"<PropertyImage {self.id}>"


class PropertyFavorite(BaseModel):
    """User favorites for properties."""

    __tablename__ = "property_favorites"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    property_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("properties.id", ondelete="CASCADE"),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<PropertyFavorite user={self.user_id} property={self.property_id}>"
