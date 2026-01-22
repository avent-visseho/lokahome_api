"""
Review service for ratings and feedback management.
"""
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import (
    AlreadyExistsException,
    BusinessLogicException,
    InsufficientPermissionsException,
    NotFoundException,
)
from app.models.booking import Booking, BookingStatus
from app.models.property import Property
from app.models.review import Review, ReviewType
from app.models.service import ServiceProvider, ServiceRequest, ServiceRequestStatus
from app.models.user import User, UserRole
from app.repositories.base import BaseRepository


class ReviewRepository(BaseRepository[Review]):
    """Repository for Review operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(Review, session)

    async def get_with_details(self, review_id: UUID) -> Review | None:
        """Get review with reviewer info."""
        result = await self.session.execute(
            select(Review)
            .options(selectinload(Review.reviewer))
            .where(Review.id == review_id)
        )
        return result.scalar_one_or_none()

    async def get_property_reviews(
        self,
        property_id: UUID,
        *,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Review]:
        """Get reviews for a property."""
        result = await self.session.execute(
            select(Review)
            .options(selectinload(Review.reviewer))
            .where(
                and_(
                    Review.property_id == property_id,
                    Review.is_visible == True,  # noqa: E712
                )
            )
            .order_by(Review.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_user_reviews(
        self,
        user_id: UUID,
        *,
        as_reviewer: bool = True,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Review]:
        """Get reviews by or about a user."""
        if as_reviewer:
            query = select(Review).where(Review.reviewer_id == user_id)
        else:
            query = select(Review).where(
                and_(
                    Review.reviewed_user_id == user_id,
                    Review.is_visible == True,  # noqa: E712
                )
            )

        query = (
            query.options(selectinload(Review.reviewer))
            .order_by(Review.created_at.desc())
            .offset(skip)
            .limit(limit)
        )

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_provider_reviews(
        self,
        provider_id: UUID,
        *,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Review]:
        """Get reviews for a service provider."""
        result = await self.session.execute(
            select(Review)
            .options(selectinload(Review.reviewer))
            .where(
                and_(
                    Review.service_provider_id == provider_id,
                    Review.is_visible == True,  # noqa: E712
                )
            )
            .order_by(Review.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def exists_for_booking(
        self,
        reviewer_id: UUID,
        booking_id: UUID,
        review_type: ReviewType,
    ) -> bool:
        """Check if review already exists for a booking."""
        result = await self.session.execute(
            select(func.count())
            .select_from(Review)
            .where(
                and_(
                    Review.reviewer_id == reviewer_id,
                    Review.booking_id == booking_id,
                    Review.review_type == review_type,
                )
            )
        )
        return result.scalar_one() > 0

    async def exists_for_service(
        self,
        reviewer_id: UUID,
        service_request_id: UUID,
    ) -> bool:
        """Check if review already exists for a service request."""
        result = await self.session.execute(
            select(func.count())
            .select_from(Review)
            .where(
                and_(
                    Review.reviewer_id == reviewer_id,
                    Review.service_request_id == service_request_id,
                )
            )
        )
        return result.scalar_one() > 0

    async def calculate_average_rating(
        self,
        *,
        property_id: UUID | None = None,
        user_id: UUID | None = None,
        provider_id: UUID | None = None,
    ) -> dict:
        """Calculate average rating and distribution."""
        query = select(Review.rating).where(Review.is_visible == True)  # noqa: E712

        if property_id:
            query = query.where(Review.property_id == property_id)
        elif user_id:
            query = query.where(Review.reviewed_user_id == user_id)
        elif provider_id:
            query = query.where(Review.service_provider_id == provider_id)
        else:
            return {}

        result = await self.session.execute(query)
        ratings = [r[0] for r in result.fetchall()]

        if not ratings:
            return {
                "average_rating": 0,
                "total_reviews": 0,
                "rating_distribution": {str(i): 0 for i in range(1, 6)},
            }

        distribution = {str(i): ratings.count(i) for i in range(1, 6)}

        return {
            "average_rating": round(sum(ratings) / len(ratings), 2),
            "total_reviews": len(ratings),
            "rating_distribution": distribution,
        }


class ReviewService:
    """Service for review operations."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.review_repo = ReviewRepository(session)

    async def get_review(self, review_id: UUID) -> Review:
        """Get review by ID."""
        review = await self.review_repo.get_with_details(review_id)
        if not review:
            raise NotFoundException("Avis")
        return review

    async def create_property_review(
        self,
        reviewer: User,
        property_id: UUID,
        booking_id: UUID,
        rating: int,
        title: str | None = None,
        comment: str | None = None,
        detailed_ratings: dict | None = None,
        images: list[str] | None = None,
    ) -> Review:
        """Create a review for a property after a completed booking."""
        # Verify booking exists and is completed
        booking = await self.session.get(Booking, booking_id)
        if not booking:
            raise NotFoundException("Réservation")

        if booking.tenant_id != reviewer.id:
            raise InsufficientPermissionsException(
                "Vous ne pouvez évaluer que vos propres réservations"
            )

        if booking.status != BookingStatus.COMPLETED:
            raise BusinessLogicException(
                "Vous ne pouvez évaluer qu'une réservation terminée"
            )

        if booking.property_id != property_id:
            raise BusinessLogicException("La réservation ne correspond pas au bien")

        # Check for existing review
        if await self.review_repo.exists_for_booking(
            reviewer.id, booking_id, ReviewType.PROPERTY
        ):
            raise AlreadyExistsException("Avis")

        # Get property owner
        property_obj = await self.session.get(Property, property_id)

        # Create review
        review = await self.review_repo.create({
            "reviewer_id": reviewer.id,
            "review_type": ReviewType.PROPERTY,
            "property_id": property_id,
            "reviewed_user_id": property_obj.owner_id,
            "booking_id": booking_id,
            "rating": rating,
            "title": title,
            "comment": comment,
            "detailed_ratings": detailed_ratings,
            "images": images or [],
        })

        # Update property average rating (could be done async)
        await self._update_property_rating(property_id)

        return review

    async def create_tenant_review(
        self,
        reviewer: User,
        tenant_id: UUID,
        booking_id: UUID,
        rating: int,
        comment: str | None = None,
    ) -> Review:
        """Create a review for a tenant (by landlord) after a completed booking."""
        # Verify booking exists and is completed
        booking = await self.session.get(Booking, booking_id)
        if not booking:
            raise NotFoundException("Réservation")

        # Verify reviewer is the property owner
        property_obj = await self.session.get(Property, booking.property_id)
        if property_obj.owner_id != reviewer.id:
            raise InsufficientPermissionsException(
                "Seul le propriétaire peut évaluer le locataire"
            )

        if booking.status != BookingStatus.COMPLETED:
            raise BusinessLogicException(
                "Vous ne pouvez évaluer qu'une réservation terminée"
            )

        if booking.tenant_id != tenant_id:
            raise BusinessLogicException("Le locataire ne correspond pas à la réservation")

        # Check for existing review
        if await self.review_repo.exists_for_booking(
            reviewer.id, booking_id, ReviewType.TENANT
        ):
            raise AlreadyExistsException("Avis")

        # Create review
        return await self.review_repo.create({
            "reviewer_id": reviewer.id,
            "review_type": ReviewType.TENANT,
            "reviewed_user_id": tenant_id,
            "booking_id": booking_id,
            "rating": rating,
            "comment": comment,
        })

    async def create_provider_review(
        self,
        reviewer: User,
        provider_id: UUID,
        service_request_id: UUID,
        rating: int,
        title: str | None = None,
        comment: str | None = None,
        images: list[str] | None = None,
    ) -> Review:
        """Create a review for a service provider after a completed service."""
        # Verify service request exists and is completed
        service_request = await self.session.get(ServiceRequest, service_request_id)
        if not service_request:
            raise NotFoundException("Demande de service")

        if service_request.requester_id != reviewer.id:
            raise InsufficientPermissionsException(
                "Vous ne pouvez évaluer que vos propres demandes de service"
            )

        if service_request.status != ServiceRequestStatus.COMPLETED:
            raise BusinessLogicException(
                "Vous ne pouvez évaluer qu'un service terminé"
            )

        # Check for existing review
        if await self.review_repo.exists_for_service(reviewer.id, service_request_id):
            raise AlreadyExistsException("Avis")

        # Create review
        review = await self.review_repo.create({
            "reviewer_id": reviewer.id,
            "review_type": ReviewType.SERVICE_PROVIDER,
            "service_provider_id": provider_id,
            "service_request_id": service_request_id,
            "rating": rating,
            "title": title,
            "comment": comment,
            "images": images or [],
        })

        # Update provider rating
        await self._update_provider_rating(provider_id)

        return review

    async def respond_to_review(
        self,
        review_id: UUID,
        responder: User,
        response: str,
    ) -> Review:
        """Add a response to a review (by reviewed party)."""
        review = await self.get_review(review_id)

        # Verify responder is the reviewed party
        can_respond = False

        if review.review_type == ReviewType.PROPERTY:
            property_obj = await self.session.get(Property, review.property_id)
            can_respond = property_obj and property_obj.owner_id == responder.id

        elif review.review_type == ReviewType.TENANT:
            can_respond = review.reviewed_user_id == responder.id

        elif review.review_type == ReviewType.SERVICE_PROVIDER:
            provider = await self.session.get(ServiceProvider, review.service_provider_id)
            can_respond = provider and provider.user_id == responder.id

        if not can_respond and responder.role != UserRole.ADMIN:
            raise InsufficientPermissionsException(
                "Vous ne pouvez répondre qu'aux avis vous concernant"
            )

        if review.response:
            raise BusinessLogicException("Cet avis a déjà une réponse")

        return await self.review_repo.update(review, {
            "response": response,
            "response_at": datetime.now(UTC).isoformat(),
        })

    async def get_property_reviews(
        self,
        property_id: UUID,
        *,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Review]:
        """Get reviews for a property."""
        return await self.review_repo.get_property_reviews(
            property_id, skip=skip, limit=limit
        )

    async def get_user_reviews(
        self,
        user_id: UUID,
        *,
        as_reviewer: bool = False,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Review]:
        """Get reviews by or about a user."""
        return await self.review_repo.get_user_reviews(
            user_id, as_reviewer=as_reviewer, skip=skip, limit=limit
        )

    async def get_provider_reviews(
        self,
        provider_id: UUID,
        *,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Review]:
        """Get reviews for a service provider."""
        return await self.review_repo.get_provider_reviews(
            provider_id, skip=skip, limit=limit
        )

    async def get_review_summary(
        self,
        *,
        property_id: UUID | None = None,
        user_id: UUID | None = None,
        provider_id: UUID | None = None,
    ) -> dict:
        """Get review summary (average, count, distribution)."""
        return await self.review_repo.calculate_average_rating(
            property_id=property_id,
            user_id=user_id,
            provider_id=provider_id,
        )

    async def _update_property_rating(self, property_id: UUID) -> None:
        """Update property's average rating."""
        await self.get_review_summary(property_id=property_id)
        # Could update a cached rating field on the property
        pass

    async def _update_provider_rating(self, provider_id: UUID) -> None:
        """Update provider's average rating."""
        summary = await self.get_review_summary(provider_id=provider_id)
        provider = await self.session.get(ServiceProvider, provider_id)
        if provider:
            provider.rating = Decimal(str(summary.get("average_rating", 0)))
            await self.session.flush()

    # Admin operations
    async def hide_review(self, review_id: UUID, note: str | None = None) -> Review:
        """Hide a review (admin moderation)."""
        review = await self.get_review(review_id)
        return await self.review_repo.update(review, {
            "is_visible": False,
            "moderation_note": note,
        })

    async def show_review(self, review_id: UUID) -> Review:
        """Show a hidden review (admin)."""
        review = await self.get_review(review_id)
        return await self.review_repo.update(review, {"is_visible": True})
