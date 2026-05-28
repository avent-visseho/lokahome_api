"""
Agent/Demarcheur schemas for validation and serialization.
"""
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import Field

from app.models.agent import CommissionStatus, MandateStatus, MandateType, VisitStatus
from app.schemas.base import BaseSchema, IDSchema, TimestampSchema
from app.schemas.user import UserPublicProfile


# --- Agent Profile Schemas ---
class AgentProfileBase(BaseSchema):
    """Base agent profile schema."""

    business_name: str = Field(min_length=2, max_length=200)
    description: str | None = None
    phone_whatsapp: str | None = Field(
        default=None, pattern=r"^\+?[0-9]{8,15}$"
    )
    service_areas: list[str] = []
    specializations: list[str] = []
    commission_rate: Decimal = Field(default=Decimal("50.00"), ge=0, le=50)
    is_available: bool = True


class AgentProfileCreate(AgentProfileBase):
    """Agent profile creation schema."""

    pass


class AgentProfileUpdate(BaseSchema):
    """Agent profile update schema."""

    business_name: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = None
    phone_whatsapp: str | None = Field(
        default=None, pattern=r"^\+?[0-9]{8,15}$"
    )
    service_areas: list[str] | None = None
    specializations: list[str] | None = None
    commission_rate: Decimal | None = Field(default=None, ge=0, le=50)
    is_available: bool | None = None
    certifications: list[str] | None = None
    portfolio_images: list[str] | None = None


class AgentProfileResponse(AgentProfileBase, IDSchema, TimestampSchema):
    """Agent profile response schema."""

    user_id: UUID
    agent_code: str
    is_verified: bool
    identity_verified: bool
    completed_deals: int
    rating: Decimal | None
    response_time_hours: int | None
    certifications: list[str] = []
    portfolio_images: list[str] = []
    user: UserPublicProfile


class AgentProfileListResponse(BaseSchema):
    """Agent profile list item."""

    id: UUID
    user_id: UUID
    business_name: str
    agent_code: str
    phone_whatsapp: str | None
    service_areas: list[str]
    specializations: list[str]
    commission_rate: Decimal
    is_available: bool
    is_verified: bool
    completed_deals: int
    rating: Decimal | None
    user: UserPublicProfile


# --- Agent Mandate Schemas ---
class AgentMandateCreate(BaseSchema):
    """Create a mandate (by landlord)."""

    agent_id: UUID
    property_id: UUID | None = None
    mandate_type: MandateType = MandateType.NON_EXCLUSIVE
    commission_rate: Decimal | None = Field(default=None, ge=0, le=50)
    expires_at: datetime | None = None
    terms: str | None = None


class AgentMandateResponse(IDSchema, TimestampSchema):
    """Agent mandate response schema."""

    agent_id: UUID
    landlord_id: UUID
    property_id: UUID | None
    mandate_type: MandateType
    status: MandateStatus
    commission_rate: Decimal | None
    started_at: datetime | None
    expires_at: datetime | None
    terms: str | None
    agent: AgentProfileListResponse
    landlord: UserPublicProfile


class AgentMandateListResponse(BaseSchema):
    """Agent mandate list item."""

    id: UUID
    agent_id: UUID
    landlord_id: UUID
    property_id: UUID | None
    mandate_type: MandateType
    status: MandateStatus
    commission_rate: Decimal | None
    expires_at: datetime | None
    created_at: datetime


# --- Property Visit Schemas ---
class PropertyVisitCreate(BaseSchema):
    """Create a property visit."""

    property_id: UUID
    visitor_id: UUID
    scheduled_at: datetime


class PropertyVisitUpdate(BaseSchema):
    """Update a property visit."""

    scheduled_at: datetime | None = None
    visitor_feedback: str | None = None
    agent_notes: str | None = None


class PropertyVisitResponse(IDSchema, TimestampSchema):
    """Property visit response schema."""

    property_id: UUID
    agent_id: UUID
    visitor_id: UUID
    scheduled_at: datetime
    status: VisitStatus
    visitor_feedback: str | None
    agent_notes: str | None
    resulted_in_booking: bool
    booking_id: UUID | None
    visitor: UserPublicProfile


class PropertyVisitListResponse(BaseSchema):
    """Property visit list item."""

    id: UUID
    property_id: UUID
    visitor_id: UUID
    scheduled_at: datetime
    status: VisitStatus
    resulted_in_booking: bool
    created_at: datetime


# --- Dashboard & Commission Schemas ---
class AgentDashboardResponse(BaseSchema):
    """Agent dashboard data."""

    total_mandates: int
    active_mandates: int
    total_properties: int
    visits_this_month: int
    completed_visits: int
    total_deals: int
    pending_commissions: Decimal
    paid_commissions: Decimal
    total_commissions: Decimal
    rating: Decimal | None
    currency: str = "XOF"


class AgentCommissionResponse(BaseSchema):
    """Commission item."""

    booking_id: UUID
    booking_reference: str
    property_title: str
    tenant_name: str
    commission_rate: Decimal
    commission_amount: Decimal
    status: str  # pending, paid, disputed
    created_at: datetime
    paid_at: datetime | None


class AgentCommissionSummary(BaseSchema):
    """Commission summary."""

    total_earned: Decimal
    pending: Decimal
    paid: Decimal
    disputed: Decimal
    deals_count: int
    currency: str = "XOF"


# --- Share Link ---
class AgentShareLinkResponse(BaseSchema):
    """Share link for WhatsApp."""

    property_id: UUID
    agent_code: str
    share_url: str
    whatsapp_url: str


# --- Search Params ---
class AgentSearchParams(BaseSchema):
    """Agent search parameters."""

    city: str | None = None
    specialization: str | None = None
    is_available: bool | None = True
    is_verified: bool | None = None
    min_rating: Decimal | None = Field(default=None, ge=0, le=5)
    sort_by: str = "rating"
    sort_order: str = "desc"
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
