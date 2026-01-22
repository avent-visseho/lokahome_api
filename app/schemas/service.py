"""
Service marketplace schemas for validation and serialization.
"""
from decimal import Decimal
from uuid import UUID

from pydantic import Field

from app.models.service import (
    QuoteStatus,
    ServiceCategory,
    ServiceRequestStatus,
)
from app.schemas.base import BaseSchema, IDSchema, TimestampSchema
from app.schemas.user import UserPublicProfile


# --- Service Provider Schemas ---
class ServiceProviderBase(BaseSchema):
    """Base service provider schema."""

    business_name: str = Field(min_length=2, max_length=200)
    description: str | None = None
    categories: list[ServiceCategory]
    service_areas: list[str] = []
    hourly_rate: Decimal | None = Field(default=None, ge=0)
    minimum_charge: Decimal | None = Field(default=None, ge=0)
    currency: str = "XOF"
    is_available: bool = True
    availability_schedule: dict | None = None


class ServiceProviderCreate(ServiceProviderBase):
    """Service provider creation schema."""

    pass


class ServiceProviderUpdate(BaseSchema):
    """Service provider update schema."""

    business_name: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = None
    categories: list[ServiceCategory] | None = None
    service_areas: list[str] | None = None
    hourly_rate: Decimal | None = Field(default=None, ge=0)
    minimum_charge: Decimal | None = Field(default=None, ge=0)
    is_available: bool | None = None
    availability_schedule: dict | None = None
    certifications: list[str] | None = None
    portfolio_images: list[str] | None = None


class ServiceProviderResponse(ServiceProviderBase, IDSchema, TimestampSchema):
    """Service provider response schema."""

    user_id: UUID
    is_verified: bool
    completed_jobs: int
    rating: Decimal | None
    response_time_hours: int | None
    certifications: list[str] = []
    portfolio_images: list[str] = []
    user: UserPublicProfile


class ServiceProviderListResponse(BaseSchema):
    """Service provider list item."""

    id: UUID
    user_id: UUID
    business_name: str
    categories: list[ServiceCategory]
    service_areas: list[str]
    hourly_rate: Decimal | None
    currency: str
    is_available: bool
    is_verified: bool
    completed_jobs: int
    rating: Decimal | None
    user: UserPublicProfile


# --- Service Request Schemas ---
class ServiceRequestBase(BaseSchema):
    """Base service request schema."""

    category: ServiceCategory
    title: str = Field(min_length=5, max_length=200)
    description: str = Field(min_length=20)
    address: str = Field(min_length=5, max_length=500)
    city: str = Field(min_length=2, max_length=100)
    preferred_date: str | None = None
    preferred_time: str | None = None
    is_urgent: bool = False
    budget_min: Decimal | None = Field(default=None, ge=0)
    budget_max: Decimal | None = Field(default=None, ge=0)
    currency: str = "XOF"


class ServiceRequestCreate(ServiceRequestBase):
    """Service request creation schema."""

    property_id: UUID | None = None
    images: list[str] = []


class ServiceRequestUpdate(BaseSchema):
    """Service request update schema."""

    title: str | None = Field(default=None, min_length=5, max_length=200)
    description: str | None = Field(default=None, min_length=20)
    preferred_date: str | None = None
    preferred_time: str | None = None
    is_urgent: bool | None = None
    budget_min: Decimal | None = Field(default=None, ge=0)
    budget_max: Decimal | None = Field(default=None, ge=0)
    images: list[str] | None = None


class ServiceRequestResponse(ServiceRequestBase, IDSchema, TimestampSchema):
    """Service request response schema."""

    reference: str
    requester_id: UUID
    property_id: UUID | None
    status: ServiceRequestStatus
    accepted_quote_id: UUID | None
    images: list[str]
    requester: UserPublicProfile


class ServiceRequestListResponse(BaseSchema):
    """Service request list item."""

    id: UUID
    reference: str
    category: ServiceCategory
    title: str
    city: str
    is_urgent: bool
    status: ServiceRequestStatus
    budget_min: Decimal | None
    budget_max: Decimal | None
    currency: str
    created_at: str


# --- Service Quote Schemas ---
class ServiceQuoteBase(BaseSchema):
    """Base service quote schema."""

    amount: Decimal = Field(gt=0)
    currency: str = "XOF"
    description: str = Field(min_length=10)
    estimated_duration: str | None = None
    available_date: str | None = None
    includes: list[str] = []
    excludes: list[str] = []


class ServiceQuoteCreate(ServiceQuoteBase):
    """Service quote creation schema."""

    request_id: UUID


class ServiceQuoteResponse(ServiceQuoteBase, IDSchema, TimestampSchema):
    """Service quote response schema."""

    request_id: UUID
    provider_id: UUID
    status: QuoteStatus
    expires_at: str | None
    provider: ServiceProviderListResponse


class ServiceQuoteListResponse(BaseSchema):
    """Service quote list item."""

    id: UUID
    amount: Decimal
    currency: str
    estimated_duration: str | None
    status: QuoteStatus
    provider: ServiceProviderListResponse
    created_at: str


# --- Search and Filter Schemas ---
class ServiceProviderSearchParams(BaseSchema):
    """Service provider search parameters."""

    category: ServiceCategory | None = None
    city: str | None = None
    is_available: bool | None = True
    is_verified: bool | None = None
    min_rating: Decimal | None = Field(default=None, ge=0, le=5)
    max_hourly_rate: Decimal | None = Field(default=None, ge=0)
    sort_by: str = "rating"
    sort_order: str = "desc"
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class ServiceRequestSearchParams(BaseSchema):
    """Service request search parameters (for providers)."""

    category: ServiceCategory | None = None
    city: str | None = None
    is_urgent: bool | None = None
    status: ServiceRequestStatus | None = ServiceRequestStatus.PENDING
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
