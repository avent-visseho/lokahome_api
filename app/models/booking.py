"""
Booking model for property reservations.
"""
import enum
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.agent import AgentProfile
    from app.models.contract import Contract
    from app.models.payment import Payment
    from app.models.property import Property
    from app.models.user import User


class BookingStatus(str, enum.Enum):
    """Booking status workflow."""

    PENDING = "pending"  # Awaiting landlord approval
    APPROVED = "approved"  # Landlord approved, awaiting payment
    CONFIRMED = "confirmed"  # Payment received
    ACTIVE = "active"  # Tenant has moved in
    COMPLETED = "completed"  # Rental period ended
    CANCELLED = "cancelled"  # Cancelled by tenant or landlord
    REJECTED = "rejected"  # Rejected by landlord


class Booking(BaseModel):
    """Booking/Reservation model."""

    __tablename__ = "bookings"

    # References
    property_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("properties.id", ondelete="CASCADE"),
        nullable=False,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # Booking reference (human-readable)
    reference: Mapped[str] = mapped_column(
        String(20), unique=True, index=True, nullable=False
    )

    # Dates
    check_in: Mapped[date] = mapped_column(Date, nullable=False)
    check_out: Mapped[date] = mapped_column(Date, nullable=False)

    # Status
    status: Mapped[BookingStatus] = mapped_column(
        Enum(BookingStatus), default=BookingStatus.PENDING, nullable=False
    )

    # Pricing
    base_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    service_fee: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), nullable=False
    )
    deposit_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="XOF", nullable=False)

    # Occupants
    guests_count: Mapped[int] = mapped_column(default=1, nullable=False)

    # Notes
    tenant_notes: Mapped[str | None] = mapped_column(Text)
    landlord_notes: Mapped[str | None] = mapped_column(Text)

    # Cancellation
    cancelled_at: Mapped[date | None] = mapped_column(Date)
    cancelled_by: Mapped[str | None] = mapped_column(String(50))  # tenant/landlord
    cancellation_reason: Mapped[str | None] = mapped_column(Text)

    # Contract details
    contract_signed_at: Mapped[date | None] = mapped_column(Date)
    contract_url: Mapped[str | None] = mapped_column(String(500))

    # Agent/Demarcheur (if booking was facilitated by an agent)
    agent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_profiles.id", ondelete="SET NULL")
    )
    agent_commission_rate: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    agent_commission_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    agent_commission_status: Mapped[str | None] = mapped_column(
        String(20)
    )  # pending, paid, disputed
    agent_commission_paid_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )

    # Additional metadata
    extra_data: Mapped[dict | None] = mapped_column(JSONB, default={})

    # Relationships
    booked_property: Mapped["Property"] = relationship(
        "Property", back_populates="bookings"
    )
    tenant: Mapped["User"] = relationship(
        "User", back_populates="bookings", foreign_keys=[tenant_id]
    )
    payments: Mapped[list["Payment"]] = relationship(
        "Payment", back_populates="booking", cascade="all, delete-orphan"
    )
    contract: Mapped["Contract | None"] = relationship(
        "Contract", back_populates="booking", uselist=False, cascade="all, delete-orphan"
    )
    agent: Mapped["AgentProfile | None"] = relationship(
        "AgentProfile", foreign_keys=[agent_id]
    )

    @property
    def duration_days(self) -> int:
        """Calculate booking duration in days."""
        return (self.check_out - self.check_in).days

    def __repr__(self) -> str:
        return f"<Booking {self.reference}>"
