"""
Review models for ratings and feedback.
"""
import enum
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.property import Property
    from app.models.service import ServiceProvider
    from app.models.user import User


class ReviewType(str, enum.Enum):
    """Type of review."""

    PROPERTY = "property"  # Tenant reviews property/landlord
    TENANT = "tenant"  # Landlord reviews tenant
    SERVICE_PROVIDER = "service_provider"  # User reviews service provider


class Review(BaseModel):
    """Review/Rating model."""

    __tablename__ = "reviews"

    # Reviewer
    reviewer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # Review type
    review_type: Mapped[ReviewType] = mapped_column(Enum(ReviewType), nullable=False)

    # Target references (one of these will be set based on review_type)
    property_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("properties.id", ondelete="CASCADE")
    )
    reviewed_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    service_provider_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("service_providers.id", ondelete="CASCADE")
    )

    # Booking reference (for property/tenant reviews)
    booking_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bookings.id", ondelete="SET NULL")
    )

    # Service request reference (for service provider reviews)
    service_request_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("service_requests.id", ondelete="SET NULL")
    )

    # Rating (1-5)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)

    # Detailed ratings (optional)
    detailed_ratings: Mapped[dict | None] = mapped_column(
        JSONB
    )  # {"cleanliness": 5, "communication": 4, "location": 5}

    # Content
    title: Mapped[str | None] = mapped_column(String(200))
    comment: Mapped[str | None] = mapped_column(Text)

    # Images
    images: Mapped[list | None] = mapped_column(JSONB, default=[])

    # Response from reviewed party
    response: Mapped[str | None] = mapped_column(Text)
    response_at: Mapped[str | None] = mapped_column(String(50))

    # Moderation
    is_visible: Mapped[bool] = mapped_column(default=True, nullable=False)
    moderation_note: Mapped[str | None] = mapped_column(Text)

    # Relationships
    reviewer: Mapped["User"] = relationship(
        "User", back_populates="reviews_given", foreign_keys=[reviewer_id]
    )
    reviewed_user: Mapped["User | None"] = relationship(
        "User", back_populates="reviews_received", foreign_keys=[reviewed_user_id]
    )
    property: Mapped["Property | None"] = relationship(
        "Property", back_populates="reviews"
    )
    service_provider: Mapped["ServiceProvider | None"] = relationship(
        "ServiceProvider", back_populates="reviews"
    )

    def __repr__(self) -> str:
        return f"<Review {self.id} rating={self.rating}>"
