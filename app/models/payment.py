"""
Payment model for transaction tracking.
"""
import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.booking import Booking
    from app.models.service import ServiceRequest


class PaymentStatus(str, enum.Enum):
    """Payment status."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"


class PaymentMethod(str, enum.Enum):
    """Available payment methods."""

    FEDAPAY = "fedapay"
    MTN_MOMO = "mtn_momo"
    MOOV_MONEY = "moov_money"
    STRIPE = "stripe"
    BANK_TRANSFER = "bank_transfer"
    CASH = "cash"


class PaymentType(str, enum.Enum):
    """Type of payment."""

    BOOKING = "booking"
    DEPOSIT = "deposit"
    SERVICE = "service"
    SUBSCRIPTION = "subscription"
    REFUND = "refund"


class Payment(BaseModel):
    """Payment transaction model."""

    __tablename__ = "payments"

    # References
    booking_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bookings.id", ondelete="SET NULL")
    )
    service_request_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("service_requests.id", ondelete="SET NULL")
    )
    payer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    receiver_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # Transaction reference
    reference: Mapped[str] = mapped_column(
        String(50), unique=True, index=True, nullable=False
    )

    # Payment details
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    fee: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), nullable=False
    )
    net_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="XOF", nullable=False)

    # Payment method
    payment_method: Mapped[PaymentMethod] = mapped_column(
        Enum(PaymentMethod), nullable=False
    )
    payment_type: Mapped[PaymentType] = mapped_column(Enum(PaymentType), nullable=False)

    # Status
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False
    )

    # Provider information
    provider_reference: Mapped[str | None] = mapped_column(String(100))
    provider_status: Mapped[str | None] = mapped_column(String(50))
    provider_response: Mapped[dict | None] = mapped_column(JSONB)

    # Timestamps
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Error handling
    error_message: Mapped[str | None] = mapped_column(Text)
    error_code: Mapped[str | None] = mapped_column(String(50))

    # Refund information
    refund_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    refund_reason: Mapped[str | None] = mapped_column(Text)
    refunded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Phone number for mobile money
    phone_number: Mapped[str | None] = mapped_column(String(20))

    # Additional metadata
    extra_data: Mapped[dict | None] = mapped_column(JSONB, default={})

    # Relationships
    booking: Mapped["Booking | None"] = relationship(
        "Booking", back_populates="payments"
    )
    service_request: Mapped["ServiceRequest | None"] = relationship(
        "ServiceRequest", back_populates="payments"
    )

    def __repr__(self) -> str:
        return f"<Payment {self.reference}>"
