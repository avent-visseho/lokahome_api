"""
Service models for the service marketplace.
"""
import enum
import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.payment import Payment
    from app.models.review import Review
    from app.models.user import User


class ServiceCategory(str, enum.Enum):
    """Service categories."""

    PLUMBING = "plumbing"  # Plomberie
    ELECTRICAL = "electrical"  # Électricité
    CLEANING = "cleaning"  # Nettoyage
    CARPENTRY = "carpentry"  # Menuiserie
    PAINTING = "painting"  # Peinture
    GARDENING = "gardening"  # Jardinage
    MOVING = "moving"  # Déménagement
    AIR_CONDITIONING = "air_conditioning"  # Climatisation
    SECURITY = "security"  # Sécurité
    OTHER = "other"


class ServiceRequestStatus(str, enum.Enum):
    """Service request status."""

    PENDING = "pending"  # Waiting for quotes
    QUOTED = "quoted"  # Quotes received
    ACCEPTED = "accepted"  # Quote accepted
    IN_PROGRESS = "in_progress"  # Work in progress
    COMPLETED = "completed"  # Work completed
    CANCELLED = "cancelled"


class QuoteStatus(str, enum.Enum):
    """Quote status."""

    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"


class ServiceProvider(BaseModel):
    """Service provider profile."""

    __tablename__ = "service_providers"

    # Reference to user
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    # Business info
    business_name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    # Categories (multiple possible)
    categories: Mapped[list] = mapped_column(JSONB, default=[], nullable=False)

    # Location coverage
    service_areas: Mapped[list] = mapped_column(
        JSONB, default=[]
    )  # List of cities/neighborhoods

    # Pricing
    hourly_rate: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    minimum_charge: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    currency: Mapped[str] = mapped_column(String(3), default="XOF", nullable=False)

    # Availability
    is_available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    availability_schedule: Mapped[dict | None] = mapped_column(
        JSONB
    )  # {"monday": ["09:00-18:00"], ...}

    # Verification
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    certifications: Mapped[list | None] = mapped_column(JSONB, default=[])

    # Stats
    completed_jobs: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rating: Mapped[Decimal | None] = mapped_column(Numeric(3, 2))
    response_time_hours: Mapped[int | None] = mapped_column(Integer)

    # Portfolio
    portfolio_images: Mapped[list | None] = mapped_column(JSONB, default=[])

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="service_provider")
    quotes: Mapped[list["ServiceQuote"]] = relationship(
        "ServiceQuote", back_populates="provider", cascade="all, delete-orphan"
    )
    reviews: Mapped[list["Review"]] = relationship(
        "Review", back_populates="service_provider"
    )

    def __repr__(self) -> str:
        return f"<ServiceProvider {self.business_name}>"


class ServiceRequest(BaseModel):
    """Service request from a user."""

    __tablename__ = "service_requests"

    # Reference
    reference: Mapped[str] = mapped_column(
        String(20), unique=True, index=True, nullable=False
    )

    # Requester
    requester_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # Property (optional)
    property_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("properties.id", ondelete="SET NULL")
    )

    # Service details
    category: Mapped[ServiceCategory] = mapped_column(
        Enum(ServiceCategory), nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # Location
    address: Mapped[str] = mapped_column(String(500), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)

    # Timing
    preferred_date: Mapped[str | None] = mapped_column(String(50))
    preferred_time: Mapped[str | None] = mapped_column(String(50))
    is_urgent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Budget
    budget_min: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    budget_max: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    currency: Mapped[str] = mapped_column(String(3), default="XOF", nullable=False)

    # Status
    status: Mapped[ServiceRequestStatus] = mapped_column(
        Enum(ServiceRequestStatus), default=ServiceRequestStatus.PENDING, nullable=False
    )

    # Accepted quote
    accepted_quote_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("service_quotes.id", ondelete="SET NULL")
    )

    # Images
    images: Mapped[list | None] = mapped_column(JSONB, default=[])

    # Additional info
    extra_data: Mapped[dict | None] = mapped_column(JSONB, default={})

    # Relationships
    requester: Mapped["User"] = relationship(
        "User", back_populates="service_requests", foreign_keys=[requester_id]
    )
    quotes: Mapped[list["ServiceQuote"]] = relationship(
        "ServiceQuote",
        back_populates="request",
        cascade="all, delete-orphan",
        foreign_keys="ServiceQuote.request_id",
    )
    payments: Mapped[list["Payment"]] = relationship(
        "Payment", back_populates="service_request"
    )

    def __repr__(self) -> str:
        return f"<ServiceRequest {self.reference}>"


class ServiceQuote(BaseModel):
    """Quote from a service provider."""

    __tablename__ = "service_quotes"

    # References
    request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("service_requests.id", ondelete="CASCADE"),
        nullable=False,
    )
    provider_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("service_providers.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Quote details
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="XOF", nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # Timeline
    estimated_duration: Mapped[str | None] = mapped_column(
        String(100)
    )  # "2 heures", "3 jours"
    available_date: Mapped[str | None] = mapped_column(String(50))

    # Status
    status: Mapped[QuoteStatus] = mapped_column(
        Enum(QuoteStatus), default=QuoteStatus.PENDING, nullable=False
    )

    # Expiration
    expires_at: Mapped[str | None] = mapped_column(String(50))

    # Additional details
    includes: Mapped[list | None] = mapped_column(JSONB, default=[])
    excludes: Mapped[list | None] = mapped_column(JSONB, default=[])

    # Relationships
    request: Mapped["ServiceRequest"] = relationship(
        "ServiceRequest", back_populates="quotes", foreign_keys=[request_id]
    )
    provider: Mapped["ServiceProvider"] = relationship(
        "ServiceProvider", back_populates="quotes"
    )

    def __repr__(self) -> str:
        return f"<ServiceQuote {self.id}>"
