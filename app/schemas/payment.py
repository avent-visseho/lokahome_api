"""
Payment schemas for validation and serialization.
"""
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import Field

from app.models.payment import PaymentMethod, PaymentStatus, PaymentType
from app.schemas.base import BaseSchema, IDSchema, TimestampSchema


class PaymentCreate(BaseSchema):
    """Payment creation schema."""

    booking_id: UUID | None = None
    service_request_id: UUID | None = None
    payment_method: PaymentMethod
    phone_number: str | None = Field(
        default=None, pattern=r"^\+?[0-9]{8,15}$"
    )  # For mobile money

    # Return URL for payment providers
    return_url: str | None = None
    cancel_url: str | None = None


class PaymentInitResponse(BaseSchema):
    """Payment initialization response."""

    payment_id: UUID
    reference: str
    amount: Decimal
    currency: str
    payment_method: PaymentMethod
    payment_url: str | None = None  # URL for redirect-based payments
    instructions: str | None = None  # Instructions for mobile money
    expires_at: datetime | None = None


class PaymentResponse(IDSchema, TimestampSchema):
    """Payment response schema."""

    reference: str
    booking_id: UUID | None
    service_request_id: UUID | None
    payer_id: UUID
    receiver_id: UUID
    amount: Decimal
    fee: Decimal
    net_amount: Decimal
    currency: str
    payment_method: PaymentMethod
    payment_type: PaymentType
    status: PaymentStatus
    provider_reference: str | None
    paid_at: datetime | None
    error_message: str | None


class PaymentListResponse(BaseSchema):
    """Payment list item response."""

    id: UUID
    reference: str
    amount: Decimal
    currency: str
    payment_method: PaymentMethod
    payment_type: PaymentType
    status: PaymentStatus
    paid_at: datetime | None
    created_at: datetime


# --- Webhook Schemas ---
class FedaPayWebhook(BaseSchema):
    """FedaPay webhook payload."""

    event: str
    data: dict


class MobileMoneyWebhook(BaseSchema):
    """Mobile Money webhook payload."""

    transaction_id: str
    status: str
    amount: Decimal
    currency: str
    phone_number: str
    metadata: dict | None = None


# --- Refund Schemas ---
class RefundRequest(BaseSchema):
    """Refund request schema."""

    payment_id: UUID
    amount: Decimal | None = None  # Partial or full refund
    reason: str = Field(min_length=10)


class RefundResponse(BaseSchema):
    """Refund response schema."""

    payment_id: UUID
    refund_amount: Decimal
    original_amount: Decimal
    status: str
    refunded_at: datetime | None


# --- Transaction History ---
class TransactionFilter(BaseSchema):
    """Transaction filter parameters."""

    payment_type: PaymentType | None = None
    payment_method: PaymentMethod | None = None
    status: PaymentStatus | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class TransactionSummary(BaseSchema):
    """Transaction summary for a period."""

    total_received: Decimal
    total_paid: Decimal
    total_fees: Decimal
    net_balance: Decimal
    currency: str
    transaction_count: int
    period_start: datetime
    period_end: datetime
