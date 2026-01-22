"""
User model for authentication and profile management.
"""
import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.booking import Booking
    from app.models.message import Message
    from app.models.property import Property
    from app.models.review import Review
    from app.models.service import ServiceProvider, ServiceRequest


class UserRole(str, enum.Enum):
    """User roles for access control."""

    TENANT = "tenant"
    LANDLORD = "landlord"
    PROVIDER = "provider"
    ADMIN = "admin"


class User(BaseModel):
    """User model with authentication and profile data."""

    __tablename__ = "users"

    # Authentication
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    phone: Mapped[str | None] = mapped_column(String(20), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    # Profile
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(500))
    bio: Mapped[str | None] = mapped_column(Text)

    # Role and status
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole), default=UserRole.TENANT, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Verification
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    phone_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    identity_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )

    # Identity documents
    identity_document_type: Mapped[str | None] = mapped_column(String(50))
    identity_document_number: Mapped[str | None] = mapped_column(String(100))
    identity_document_url: Mapped[str | None] = mapped_column(String(500))

    # Notifications preferences
    notification_preferences: Mapped[dict | None] = mapped_column(
        JSONB,
        default={
            "email": True,
            "push": True,
            "sms": False,
        },
    )

    # FCM token for push notifications
    fcm_token: Mapped[str | None] = mapped_column(String(500))

    # Last activity
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Relationships
    properties: Mapped[list["Property"]] = relationship(
        "Property", back_populates="owner", cascade="all, delete-orphan"
    )
    bookings: Mapped[list["Booking"]] = relationship(
        "Booking", back_populates="tenant", foreign_keys="Booking.tenant_id"
    )
    sent_messages: Mapped[list["Message"]] = relationship(
        "Message", back_populates="sender", foreign_keys="Message.sender_id"
    )
    received_messages: Mapped[list["Message"]] = relationship(
        "Message", back_populates="receiver", foreign_keys="Message.receiver_id"
    )
    reviews_given: Mapped[list["Review"]] = relationship(
        "Review", back_populates="reviewer", foreign_keys="Review.reviewer_id"
    )
    reviews_received: Mapped[list["Review"]] = relationship(
        "Review", back_populates="reviewed_user", foreign_keys="Review.reviewed_user_id"
    )
    service_provider: Mapped["ServiceProvider | None"] = relationship(
        "ServiceProvider", back_populates="user", uselist=False
    )
    service_requests: Mapped[list["ServiceRequest"]] = relationship(
        "ServiceRequest", back_populates="requester"
    )

    @property
    def full_name(self) -> str:
        """Return user's full name."""
        return f"{self.first_name} {self.last_name}"

    def __repr__(self) -> str:
        return f"<User {self.email}>"
