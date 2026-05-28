"""
Contract schemas for validation and serialization.
"""
from datetime import datetime
from uuid import UUID

from pydantic import Field, field_validator

from app.models.contract import ContractStatus, ContractType
from app.schemas.base import BaseSchema, IDSchema, TimestampSchema
from app.schemas.booking import BookingDetailResponse


class ContractResponse(IDSchema, TimestampSchema):
    """Contract response schema."""

    reference: str
    booking_id: UUID
    contract_type: ContractType
    status: ContractStatus
    draft_url: str | None
    signed_url: str | None
    landlord_signed_at: datetime | None
    tenant_signed_at: datetime | None
    document_hash: str | None
    is_locked: bool
    expires_at: datetime | None
    special_conditions: str | None


class ContractDetailResponse(ContractResponse):
    """Detailed contract response with booking info."""

    booking: BookingDetailResponse
    audit_log: list[dict] | None = None


class ContractSignRequest(BaseSchema):
    """Request to sign a contract."""

    signature_data: str = Field(
        ..., min_length=100, description="Base64-encoded PNG signature image"
    )
    accept_terms: bool = Field(..., description="Must accept contract terms")

    @field_validator("accept_terms")
    @classmethod
    def must_accept_terms(cls, v: bool) -> bool:
        if not v:
            raise ValueError("Vous devez accepter les termes du contrat")
        return v


class ContractVerifyCodeRequest(BaseSchema):
    """Request to verify OTP code."""

    code: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$")


class ContractListResponse(BaseSchema):
    """Contract list item."""

    id: UUID
    reference: str
    booking_id: UUID
    contract_type: ContractType
    status: ContractStatus
    landlord_signed_at: datetime | None
    tenant_signed_at: datetime | None
    is_locked: bool
    expires_at: datetime | None
    created_at: datetime
