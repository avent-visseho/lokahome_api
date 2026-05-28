"""
Agent/Demarcheur models for property intermediation.
"""
import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.booking import Booking
    from app.models.property import Property
    from app.models.review import Review
    from app.models.user import User


class MandateType(str, enum.Enum):
    """Type of agent mandate."""

    EXCLUSIVE = "exclusive"  # Seul ce demarcheur peut proposer cette propriete
    NON_EXCLUSIVE = "non_exclusive"  # Plusieurs demarcheurs possibles
    GLOBAL = "global"  # Represente le proprietaire pour toutes ses proprietes


class MandateStatus(str, enum.Enum):
    """Status of an agent mandate."""

    PENDING = "pending"
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"


class VisitStatus(str, enum.Enum):
    """Status of a property visit."""

    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


class CommissionStatus(str, enum.Enum):
    """Status of an agent commission on a booking."""

    PENDING = "pending"
    PAID = "paid"
    DISPUTED = "disputed"


class AgentProfile(BaseModel):
    """Agent/Demarcheur profile."""

    __tablename__ = "agent_profiles"

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

    # Contact WhatsApp (crucial au Benin)
    phone_whatsapp: Mapped[str | None] = mapped_column(String(20))

    # Agent code unique (ex: AGT-COTONOU-001)
    agent_code: Mapped[str] = mapped_column(
        String(30), unique=True, index=True, nullable=False
    )

    # Zones et specialisations
    service_areas: Mapped[list] = mapped_column(JSONB, default=[], nullable=False)
    specializations: Mapped[list] = mapped_column(JSONB, default=[], nullable=False)

    # Taux de commission par defaut (max 50% d'un mois de loyer)
    commission_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), default=Decimal("50.00"), nullable=False
    )

    # Verification
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    identity_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Stats
    completed_deals: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rating: Mapped[Decimal | None] = mapped_column(Numeric(3, 2))
    response_time_hours: Mapped[int | None] = mapped_column(Integer)

    # Certifications et portfolio
    certifications: Mapped[list | None] = mapped_column(JSONB, default=[])
    portfolio_images: Mapped[list | None] = mapped_column(JSONB, default=[])

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="agent_profile")
    mandates: Mapped[list["AgentMandate"]] = relationship(
        "AgentMandate", back_populates="agent", foreign_keys="AgentMandate.agent_id",
        cascade="all, delete-orphan",
    )
    visits: Mapped[list["PropertyVisit"]] = relationship(
        "PropertyVisit", back_populates="agent", cascade="all, delete-orphan",
    )
    reviews: Mapped[list["Review"]] = relationship(
        "Review", back_populates="agent_profile",
    )

    def __repr__(self) -> str:
        return f"<AgentProfile {self.agent_code} - {self.business_name}>"


class AgentMandate(BaseModel):
    """Mandate linking an agent to a landlord for a property."""

    __tablename__ = "agent_mandates"

    # References
    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    landlord_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    property_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("properties.id", ondelete="CASCADE"),
    )

    # Type et statut
    mandate_type: Mapped[MandateType] = mapped_column(
        Enum(MandateType), default=MandateType.NON_EXCLUSIVE, nullable=False
    )
    status: Mapped[MandateStatus] = mapped_column(
        Enum(MandateStatus), default=MandateStatus.PENDING, nullable=False
    )

    # Commission override (surcharge le taux par defaut de l'agent)
    commission_rate: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))

    # Duree
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Conditions
    terms: Mapped[str | None] = mapped_column(Text)

    # Relationships
    agent: Mapped["AgentProfile"] = relationship(
        "AgentProfile", back_populates="mandates", foreign_keys=[agent_id]
    )
    landlord: Mapped["User"] = relationship("User", foreign_keys=[landlord_id])
    mandate_property: Mapped["Property | None"] = relationship(
        "Property", foreign_keys=[property_id]
    )

    def __repr__(self) -> str:
        return f"<AgentMandate {self.id} type={self.mandate_type.value}>"


class PropertyVisit(BaseModel):
    """Property visit organized by an agent."""

    __tablename__ = "property_visits"

    # References
    property_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("properties.id", ondelete="CASCADE"),
        nullable=False,
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    visitor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Planning
    scheduled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    status: Mapped[VisitStatus] = mapped_column(
        Enum(VisitStatus), default=VisitStatus.SCHEDULED, nullable=False
    )

    # Feedback
    visitor_feedback: Mapped[str | None] = mapped_column(Text)
    agent_notes: Mapped[str | None] = mapped_column(Text)

    # Resultat
    resulted_in_booking: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    booking_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bookings.id", ondelete="SET NULL")
    )

    # Relationships
    visit_property: Mapped["Property"] = relationship("Property", foreign_keys=[property_id])
    agent: Mapped["AgentProfile"] = relationship(
        "AgentProfile", back_populates="visits", foreign_keys=[agent_id]
    )
    visitor: Mapped["User"] = relationship("User", foreign_keys=[visitor_id])
    booking: Mapped["Booking | None"] = relationship("Booking", foreign_keys=[booking_id])

    def __repr__(self) -> str:
        return f"<PropertyVisit {self.id} status={self.status.value}>"
