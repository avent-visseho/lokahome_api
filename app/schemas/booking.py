"""
Booking schemas for validation and serialization.
"""
from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import AliasChoices, Field, model_validator

from app.models.booking import BookingStatus
from app.schemas.base import BaseSchema, IDSchema, TimestampSchema
from app.schemas.property import PropertyListResponse
from app.schemas.user import UserPublicProfile


class BookingBase(BaseSchema):
    """Base booking schema."""

    property_id: UUID
    check_in: date
    check_out: date
    guests_count: int = Field(default=1, ge=1)
    tenant_notes: str | None = None

    @model_validator(mode="after")
    def validate_dates(self):
        if self.check_out <= self.check_in:
            raise ValueError("La date de départ doit être après la date d'arrivée")
        return self


class BookingCreate(BookingBase):
    """Booking creation schema."""

    pass


class BookingUpdate(BaseSchema):
    """Booking update schema."""

    check_in: date | None = None
    check_out: date | None = None
    guests_count: int | None = Field(default=None, ge=1)
    tenant_notes: str | None = None


class BookingStatusUpdate(BaseSchema):
    """Booking status update (landlord/admin)."""

    status: BookingStatus
    landlord_notes: str | None = None


class BookingCancellation(BaseSchema):
    """Booking cancellation request."""

    reason: str = Field(min_length=10)


class BookingResponse(IDSchema, TimestampSchema):
    """Booking response schema."""

    reference: str
    property_id: UUID
    tenant_id: UUID
    check_in: date
    check_out: date
    status: BookingStatus
    base_price: Decimal
    service_fee: Decimal
    deposit_amount: Decimal | None
    total_amount: Decimal
    currency: str
    guests_count: int
    tenant_notes: str | None
    landlord_notes: str | None
    cancelled_at: date | None
    cancelled_by: str | None
    cancellation_reason: str | None

    @property
    def duration_days(self) -> int:
        return (self.check_out - self.check_in).days


class BookingDetailResponse(BookingResponse):
    """Detailed booking response with property and tenant info."""

    property: PropertyListResponse = Field(validation_alias=AliasChoices("property", "booked_property"))
    tenant: UserPublicProfile


class BookingListResponse(BaseSchema):
    """Booking list item response."""

    id: UUID
    reference: str
    check_in: date
    check_out: date
    status: BookingStatus
    total_amount: Decimal
    currency: str
    property: PropertyListResponse = Field(validation_alias=AliasChoices("property", "booked_property"))
    tenant: UserPublicProfile


# --- Availability Schemas ---
class AvailabilityCheck(BaseSchema):
    """Check property availability."""

    property_id: UUID
    check_in: date
    check_out: date

    @model_validator(mode="after")
    def validate_dates(self):
        if self.check_out <= self.check_in:
            raise ValueError("La date de départ doit être après la date d'arrivée")
        if self.check_in < date.today():
            raise ValueError("La date d'arrivée ne peut pas être dans le passé")
        return self


class AvailabilityResponse(BaseSchema):
    """Availability check response."""

    is_available: bool
    property_id: UUID
    check_in: date
    check_out: date
    price_per_period: Decimal
    total_price: Decimal
    service_fee: Decimal
    deposit: Decimal | None
    total_amount: Decimal
    currency: str


class BookingPriceCalculation(BaseSchema):
    """Booking price breakdown."""

    nights: int
    price_per_night: Decimal
    base_price: Decimal
    service_fee: Decimal
    deposit: Decimal | None
    total_amount: Decimal
    currency: str
