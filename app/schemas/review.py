"""
Review schemas for validation and serialization.
"""
from uuid import UUID

from pydantic import Field

from app.models.review import ReviewType
from app.schemas.base import BaseSchema, IDSchema, TimestampSchema
from app.schemas.user import UserPublicProfile


class ReviewBase(BaseSchema):
    """Base review schema."""

    rating: int = Field(ge=1, le=5)
    title: str | None = Field(default=None, max_length=200)
    comment: str | None = None
    detailed_ratings: dict | None = None  # {"cleanliness": 5, "communication": 4}
    images: list[str] = []


class ReviewCreate(ReviewBase):
    """Review creation schema."""

    review_type: ReviewType

    # Target (one of these based on review_type)
    property_id: UUID | None = None
    reviewed_user_id: UUID | None = None
    service_provider_id: UUID | None = None

    # Optional references
    booking_id: UUID | None = None
    service_request_id: UUID | None = None


class ReviewResponse(ReviewBase, IDSchema, TimestampSchema):
    """Review response schema."""

    reviewer_id: UUID
    review_type: ReviewType
    property_id: UUID | None
    reviewed_user_id: UUID | None
    service_provider_id: UUID | None
    booking_id: UUID | None
    service_request_id: UUID | None
    response: str | None
    response_at: str | None
    is_visible: bool
    reviewer: UserPublicProfile


class ReviewListResponse(BaseSchema):
    """Review list item."""

    id: UUID
    rating: int
    title: str | None
    comment: str | None
    review_type: ReviewType
    reviewer: UserPublicProfile
    response: str | None
    created_at: str


class ReviewResponseCreate(BaseSchema):
    """Response to a review from the reviewed party."""

    response: str = Field(min_length=10)


class ReviewSummary(BaseSchema):
    """Review summary statistics."""

    average_rating: float
    total_reviews: int
    rating_distribution: dict  # {"5": 10, "4": 5, "3": 2, "2": 1, "1": 0}
    detailed_averages: dict | None = None  # {"cleanliness": 4.5, "communication": 4.8}


class ReviewFilter(BaseSchema):
    """Review filter parameters."""

    review_type: ReviewType | None = None
    min_rating: int | None = Field(default=None, ge=1, le=5)
    max_rating: int | None = Field(default=None, ge=1, le=5)
    has_comment: bool | None = None
    sort_by: str = "created_at"
    sort_order: str = "desc"
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
