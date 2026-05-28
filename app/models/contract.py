"""
Contract model for rental agreements.
"""
import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.booking import Booking


class ContractStatus(str, enum.Enum):
    """Contract signature workflow status."""

    DRAFT = "draft"
    PENDING_LANDLORD = "pending_landlord"
    PENDING_TENANT = "pending_tenant"
    FULLY_SIGNED = "fully_signed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class ContractType(str, enum.Enum):
    """Type of rental contract."""

    SHORT_TERM = "short_term"
    LONG_TERM = "long_term"
    FURNISHED = "furnished"
    UNFURNISHED = "unfurnished"
    SEASONAL = "seasonal"


class Contract(BaseModel):
    """Rental contract with digital signature support."""

    __tablename__ = "contracts"

    # References
    booking_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("bookings.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    reference: Mapped[str] = mapped_column(
        String(20), unique=True, index=True, nullable=False
    )

    # Type & status
    contract_type: Mapped[ContractType] = mapped_column(
        Enum(ContractType), nullable=False
    )
    status: Mapped[ContractStatus] = mapped_column(
        Enum(ContractStatus), default=ContractStatus.DRAFT, nullable=False
    )

    # PDF URLs
    draft_url: Mapped[str | None] = mapped_column(String(500))
    signed_url: Mapped[str | None] = mapped_column(String(500))

    # Landlord signature
    landlord_signature_data: Mapped[str | None] = mapped_column(Text)
    landlord_signed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    landlord_ip_address: Mapped[str | None] = mapped_column(String(45))
    landlord_user_agent: Mapped[str | None] = mapped_column(String(500))
    landlord_verification_code: Mapped[str | None] = mapped_column(String(10))
    landlord_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )

    # Tenant signature
    tenant_signature_data: Mapped[str | None] = mapped_column(Text)
    tenant_signed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    tenant_ip_address: Mapped[str | None] = mapped_column(String(45))
    tenant_user_agent: Mapped[str | None] = mapped_column(String(500))
    tenant_verification_code: Mapped[str | None] = mapped_column(String(10))
    tenant_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )

    # Security
    document_hash: Mapped[str | None] = mapped_column(String(64))
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Expiration
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Special conditions
    special_conditions: Mapped[str | None] = mapped_column(Text)

    # Audit log
    audit_log: Mapped[list | None] = mapped_column(JSONB, default=[])

    # Relationships
    booking: Mapped["Booking"] = relationship(
        "Booking", back_populates="contract", uselist=False
    )

    def __repr__(self) -> str:
        return f"<Contract {self.reference}>"
