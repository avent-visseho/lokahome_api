"""
Service marketplace service for service providers, requests, and quotes.
"""
import random
import string
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
from app.models.service import (
    QuoteStatus,
    ServiceCategory,
    ServiceProvider,
    ServiceQuote,
    ServiceRequest,
    ServiceRequestStatus,
)
from app.models.user import User, UserRole
from app.repositories.base import BaseRepository


class ServiceProviderRepository(BaseRepository[ServiceProvider]):
    """Repository for ServiceProvider operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(ServiceProvider, session)

    async def get_by_user(self, user_id: UUID) -> ServiceProvider | None:
        """Get provider profile by user ID."""
        result = await self.session.execute(
            select(ServiceProvider)
            .options(selectinload(ServiceProvider.user))
            .where(ServiceProvider.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def search(
        self,
        *,
        category: ServiceCategory | None = None,
        city: str | None = None,
        is_available: bool | None = True,
        is_verified: bool | None = None,
        min_rating: Decimal | None = None,
        skip: int = 0,
        limit: int = 20,
        sort_by: str = "rating",
        sort_desc: bool = True,
    ) -> list[ServiceProvider]:
        """Search service providers."""
        query = select(ServiceProvider).options(selectinload(ServiceProvider.user))

        if category:
            query = query.where(ServiceProvider.categories.contains([category.value]))

        if city:
            query = query.where(ServiceProvider.service_areas.contains([city]))

        if is_available is not None:
            query = query.where(ServiceProvider.is_available == is_available)

        if is_verified is not None:
            query = query.where(ServiceProvider.is_verified == is_verified)

        if min_rating is not None:
            query = query.where(ServiceProvider.rating >= min_rating)

        # Sorting
        if sort_by == "rating" and hasattr(ServiceProvider, "rating"):
            column = ServiceProvider.rating
            query = query.order_by(
                column.desc().nullslast() if sort_desc else column.asc().nullsfirst()
            )
        elif sort_by == "completed_jobs":
            query = query.order_by(
                ServiceProvider.completed_jobs.desc()
                if sort_desc
                else ServiceProvider.completed_jobs.asc()
            )

        query = query.offset(skip).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())


class ServiceRequestRepository(BaseRepository[ServiceRequest]):
    """Repository for ServiceRequest operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(ServiceRequest, session)

    def _generate_reference(self) -> str:
        """Generate unique service request reference."""
        chars = string.ascii_uppercase + string.digits
        return "SR" + "".join(random.choices(chars, k=8))

    async def create(self, data: dict) -> ServiceRequest:
        """Create with generated reference."""
        while True:
            reference = self._generate_reference()
            exists = await self.session.execute(
                select(func.count())
                .select_from(ServiceRequest)
                .where(ServiceRequest.reference == reference)
            )
            if exists.scalar_one() == 0:
                break

        data["reference"] = reference
        return await super().create(data)

    async def get_with_details(self, request_id: UUID) -> ServiceRequest | None:
        """Get request with quotes and requester."""
        result = await self.session.execute(
            select(ServiceRequest)
            .options(
                selectinload(ServiceRequest.requester),
                selectinload(ServiceRequest.quotes).selectinload(ServiceQuote.provider),
            )
            .where(ServiceRequest.id == request_id)
        )
        return result.scalar_one_or_none()

    async def get_by_requester(
        self,
        requester_id: UUID,
        *,
        status: ServiceRequestStatus | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[ServiceRequest]:
        """Get requests by requester."""
        query = select(ServiceRequest).where(
            ServiceRequest.requester_id == requester_id
        )

        if status:
            query = query.where(ServiceRequest.status == status)

        query = query.order_by(ServiceRequest.created_at.desc()).offset(skip).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def search_for_providers(
        self,
        *,
        category: ServiceCategory | None = None,
        city: str | None = None,
        is_urgent: bool | None = None,
        status: ServiceRequestStatus | None = ServiceRequestStatus.PENDING,
        skip: int = 0,
        limit: int = 20,
    ) -> list[ServiceRequest]:
        """Search requests available for providers to quote."""
        query = select(ServiceRequest).options(selectinload(ServiceRequest.requester))

        if category:
            query = query.where(ServiceRequest.category == category)

        if city:
            query = query.where(func.lower(ServiceRequest.city) == city.lower())

        if is_urgent is not None:
            query = query.where(ServiceRequest.is_urgent == is_urgent)

        if status:
            query = query.where(ServiceRequest.status == status)

        query = query.order_by(
            ServiceRequest.is_urgent.desc(),
            ServiceRequest.created_at.desc(),
        ).offset(skip).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())


class ServiceQuoteRepository(BaseRepository[ServiceQuote]):
    """Repository for ServiceQuote operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(ServiceQuote, session)

    async def get_by_request(self, request_id: UUID) -> list[ServiceQuote]:
        """Get all quotes for a request."""
        result = await self.session.execute(
            select(ServiceQuote)
            .options(selectinload(ServiceQuote.provider).selectinload(ServiceProvider.user))
            .where(ServiceQuote.request_id == request_id)
            .order_by(ServiceQuote.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_provider(
        self,
        provider_id: UUID,
        *,
        status: QuoteStatus | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[ServiceQuote]:
        """Get quotes by provider."""
        query = (
            select(ServiceQuote)
            .options(selectinload(ServiceQuote.request))
            .where(ServiceQuote.provider_id == provider_id)
        )

        if status:
            query = query.where(ServiceQuote.status == status)

        query = query.order_by(ServiceQuote.created_at.desc()).offset(skip).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def provider_has_quoted(
        self, provider_id: UUID, request_id: UUID
    ) -> bool:
        """Check if provider already quoted on request."""
        result = await self.session.execute(
            select(func.count())
            .select_from(ServiceQuote)
            .where(
                and_(
                    ServiceQuote.provider_id == provider_id,
                    ServiceQuote.request_id == request_id,
                )
            )
        )
        return result.scalar_one() > 0


class ServiceMarketplaceService:
    """Service for marketplace operations."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.provider_repo = ServiceProviderRepository(session)
        self.request_repo = ServiceRequestRepository(session)
        self.quote_repo = ServiceQuoteRepository(session)

    # Provider Management
    async def get_provider(self, provider_id: UUID) -> ServiceProvider:
        """Get provider by ID."""
        provider = await self.provider_repo.get(provider_id)
        if not provider:
            raise NotFoundException("Prestataire")
        return provider

    async def get_provider_by_user(self, user_id: UUID) -> ServiceProvider | None:
        """Get provider profile by user ID."""
        return await self.provider_repo.get_by_user(user_id)

    async def create_provider_profile(
        self, user: User, data: dict
    ) -> ServiceProvider:
        """Create a service provider profile."""
        # Check if user already has a provider profile
        existing = await self.provider_repo.get_by_user(user.id)
        if existing:
            raise AlreadyExistsException("Profil prestataire")

        # Update user role if needed
        if user.role == UserRole.TENANT:
            user.role = UserRole.PROVIDER
            await self.session.flush()

        provider_data = {
            **data,
            "user_id": user.id,
        }

        return await self.provider_repo.create(provider_data)

    async def update_provider_profile(
        self, provider_id: UUID, user: User, data: dict
    ) -> ServiceProvider:
        """Update provider profile."""
        provider = await self.get_provider(provider_id)

        if provider.user_id != user.id and user.role != UserRole.ADMIN:
            raise InsufficientPermissionsException()

        return await self.provider_repo.update(provider, data)

    async def search_providers(
        self,
        *,
        category: ServiceCategory | None = None,
        city: str | None = None,
        is_available: bool | None = True,
        is_verified: bool | None = None,
        min_rating: Decimal | None = None,
        skip: int = 0,
        limit: int = 20,
        sort_by: str = "rating",
        sort_desc: bool = True,
    ) -> list[ServiceProvider]:
        """Search service providers."""
        return await self.provider_repo.search(
            category=category,
            city=city,
            is_available=is_available,
            is_verified=is_verified,
            min_rating=min_rating,
            skip=skip,
            limit=limit,
            sort_by=sort_by,
            sort_desc=sort_desc,
        )

    # Service Requests
    async def get_request(self, request_id: UUID) -> ServiceRequest:
        """Get service request by ID."""
        request = await self.request_repo.get_with_details(request_id)
        if not request:
            raise NotFoundException("Demande de service")
        return request

    async def create_request(
        self, requester: User, data: dict
    ) -> ServiceRequest:
        """Create a new service request."""
        request_data = {
            **data,
            "requester_id": requester.id,
            "status": ServiceRequestStatus.PENDING,
        }

        return await self.request_repo.create(request_data)

    async def update_request(
        self, request_id: UUID, user: User, data: dict
    ) -> ServiceRequest:
        """Update a service request."""
        request = await self.get_request(request_id)

        if request.requester_id != user.id:
            raise InsufficientPermissionsException()

        if request.status not in [
            ServiceRequestStatus.PENDING,
            ServiceRequestStatus.QUOTED,
        ]:
            raise BusinessLogicException(
                "Vous ne pouvez modifier qu'une demande en attente"
            )

        return await self.request_repo.update(request, data)

    async def cancel_request(
        self, request_id: UUID, user: User
    ) -> ServiceRequest:
        """Cancel a service request."""
        request = await self.get_request(request_id)

        if request.requester_id != user.id and user.role != UserRole.ADMIN:
            raise InsufficientPermissionsException()

        if request.status in [
            ServiceRequestStatus.IN_PROGRESS,
            ServiceRequestStatus.COMPLETED,
        ]:
            raise BusinessLogicException(
                "Vous ne pouvez pas annuler une demande en cours ou terminée"
            )

        return await self.request_repo.update(
            request, {"status": ServiceRequestStatus.CANCELLED}
        )

    async def get_user_requests(
        self,
        user_id: UUID,
        *,
        status: ServiceRequestStatus | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[ServiceRequest]:
        """Get requests created by a user."""
        return await self.request_repo.get_by_requester(
            user_id, status=status, skip=skip, limit=limit
        )

    async def search_requests_for_providers(
        self,
        provider: ServiceProvider,
        *,
        category: ServiceCategory | None = None,
        city: str | None = None,
        is_urgent: bool | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> list[ServiceRequest]:
        """Search available requests for a provider to quote."""
        # Filter by provider's categories if not specified
        if category is None and provider.categories:
            # Return requests matching any of provider's categories
            pass  # Will return all categories for now

        return await self.request_repo.search_for_providers(
            category=category,
            city=city,
            is_urgent=is_urgent,
            skip=skip,
            limit=limit,
        )

    # Quotes
    async def get_quote(self, quote_id: UUID) -> ServiceQuote:
        """Get quote by ID."""
        quote = await self.quote_repo.get(quote_id)
        if not quote:
            raise NotFoundException("Devis")
        return quote

    async def create_quote(
        self, provider: ServiceProvider, request_id: UUID, data: dict
    ) -> ServiceQuote:
        """Create a quote for a service request."""
        request = await self.get_request(request_id)

        # Verify request is open for quotes
        if request.status not in [
            ServiceRequestStatus.PENDING,
            ServiceRequestStatus.QUOTED,
        ]:
            raise BusinessLogicException(
                "Cette demande n'accepte plus de devis"
            )

        # Check if provider already quoted
        if await self.quote_repo.provider_has_quoted(provider.id, request_id):
            raise AlreadyExistsException("Devis")

        quote_data = {
            **data,
            "request_id": request_id,
            "provider_id": provider.id,
            "status": QuoteStatus.PENDING,
        }

        quote = await self.quote_repo.create(quote_data)

        # Update request status to quoted
        if request.status == ServiceRequestStatus.PENDING:
            await self.request_repo.update(
                request, {"status": ServiceRequestStatus.QUOTED}
            )

        return quote

    async def accept_quote(
        self, quote_id: UUID, user: User
    ) -> ServiceQuote:
        """Accept a quote (by requester)."""
        quote = await self.get_quote(quote_id)
        request = await self.get_request(quote.request_id)

        if request.requester_id != user.id:
            raise InsufficientPermissionsException()

        if quote.status != QuoteStatus.PENDING:
            raise BusinessLogicException("Ce devis n'est plus disponible")

        # Update quote status
        quote = await self.quote_repo.update(quote, {"status": QuoteStatus.ACCEPTED})

        # Update request with accepted quote
        await self.request_repo.update(
            request,
            {
                "status": ServiceRequestStatus.ACCEPTED,
                "accepted_quote_id": quote.id,
            },
        )

        # Reject other quotes
        other_quotes = await self.quote_repo.get_by_request(quote.request_id)
        for other_quote in other_quotes:
            if other_quote.id != quote.id and other_quote.status == QuoteStatus.PENDING:
                await self.quote_repo.update(
                    other_quote, {"status": QuoteStatus.REJECTED}
                )

        return quote

    async def reject_quote(
        self, quote_id: UUID, user: User
    ) -> ServiceQuote:
        """Reject a quote (by requester)."""
        quote = await self.get_quote(quote_id)
        request = await self.get_request(quote.request_id)

        if request.requester_id != user.id:
            raise InsufficientPermissionsException()

        if quote.status != QuoteStatus.PENDING:
            raise BusinessLogicException("Ce devis n'est plus en attente")

        return await self.quote_repo.update(quote, {"status": QuoteStatus.REJECTED})

    async def get_request_quotes(self, request_id: UUID) -> list[ServiceQuote]:
        """Get all quotes for a request."""
        return await self.quote_repo.get_by_request(request_id)

    async def get_provider_quotes(
        self,
        provider_id: UUID,
        *,
        status: QuoteStatus | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[ServiceQuote]:
        """Get quotes submitted by a provider."""
        return await self.quote_repo.get_by_provider(
            provider_id, status=status, skip=skip, limit=limit
        )

    # Status Updates
    async def start_service(
        self, request_id: UUID, provider: ServiceProvider
    ) -> ServiceRequest:
        """Mark service as in progress."""
        request = await self.get_request(request_id)

        # Verify provider is the accepted one
        if request.accepted_quote_id:
            quote = await self.get_quote(request.accepted_quote_id)
            if quote.provider_id != provider.id:
                raise InsufficientPermissionsException()

        if request.status != ServiceRequestStatus.ACCEPTED:
            raise BusinessLogicException(
                "Le service doit être accepté et payé avant de commencer"
            )

        return await self.request_repo.update(
            request, {"status": ServiceRequestStatus.IN_PROGRESS}
        )

    async def complete_service(
        self, request_id: UUID, provider: ServiceProvider
    ) -> ServiceRequest:
        """Mark service as completed."""
        request = await self.get_request(request_id)

        # Verify provider
        if request.accepted_quote_id:
            quote = await self.get_quote(request.accepted_quote_id)
            if quote.provider_id != provider.id:
                raise InsufficientPermissionsException()

        if request.status != ServiceRequestStatus.IN_PROGRESS:
            raise BusinessLogicException("Le service doit être en cours")

        # Update provider stats
        provider.completed_jobs += 1
        await self.session.flush()

        return await self.request_repo.update(
            request, {"status": ServiceRequestStatus.COMPLETED}
        )
