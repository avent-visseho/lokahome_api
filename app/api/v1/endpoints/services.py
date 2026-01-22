"""
Service marketplace endpoints for providers, requests, and quotes.
"""
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Query, status

from app.api.deps import ActiveUser, DbSession
from app.core.exceptions import InsufficientPermissionsException, NotFoundException
from app.models.service import QuoteStatus, ServiceCategory, ServiceRequestStatus
from app.models.user import UserRole
from app.schemas.service import (
    ServiceProviderCreate,
    ServiceProviderListResponse,
    ServiceProviderResponse,
    ServiceProviderUpdate,
    ServiceQuoteCreate,
    ServiceQuoteListResponse,
    ServiceQuoteResponse,
    ServiceRequestCreate,
    ServiceRequestListResponse,
    ServiceRequestResponse,
    ServiceRequestUpdate,
)
from app.services.service_marketplace import ServiceMarketplaceService

router = APIRouter(prefix="/services", tags=["Services"])


# === Service Providers ===

@router.get(
    "/providers",
    response_model=list[ServiceProviderListResponse],
    summary="Rechercher des prestataires",
)
async def search_providers(
    session: DbSession,
    category: ServiceCategory | None = None,
    city: str | None = None,
    is_available: bool = True,
    is_verified: bool | None = None,
    min_rating: Decimal | None = Query(default=None, ge=0, le=5),
    sort_by: str = "rating",
    sort_order: str = "desc",
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
):
    """
    Rechercher des prestataires de services.

    - **category**: Catégorie de service (plumbing, electrical, etc.)
    - **city**: Ville de service
    - **min_rating**: Note minimale (0-5)
    """
    service = ServiceMarketplaceService(session)
    return await service.search_providers(
        category=category,
        city=city,
        is_available=is_available,
        is_verified=is_verified,
        min_rating=min_rating,
        skip=skip,
        limit=limit,
        sort_by=sort_by,
        sort_desc=sort_order == "desc",
    )


@router.get(
    "/providers/me",
    response_model=ServiceProviderResponse,
    summary="Mon profil prestataire",
)
async def get_my_provider_profile(
    current_user: ActiveUser,
    session: DbSession,
):
    """Récupérer mon profil de prestataire."""
    service = ServiceMarketplaceService(session)
    provider = await service.get_provider_by_user(current_user.id)

    if not provider:
        raise NotFoundException("Profil prestataire")

    return provider


@router.post(
    "/providers",
    response_model=ServiceProviderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Créer un profil prestataire",
)
async def create_provider_profile(
    data: ServiceProviderCreate,
    current_user: ActiveUser,
    session: DbSession,
):
    """
    Créer un profil de prestataire de services.

    Permet à l'utilisateur de proposer ses services sur la marketplace.
    """
    service = ServiceMarketplaceService(session)
    return await service.create_provider_profile(
        user=current_user,
        data=data.model_dump(),
    )


@router.patch(
    "/providers/{provider_id}",
    response_model=ServiceProviderResponse,
    summary="Modifier mon profil prestataire",
)
async def update_provider_profile(
    provider_id: UUID,
    data: ServiceProviderUpdate,
    current_user: ActiveUser,
    session: DbSession,
):
    """Modifier mon profil de prestataire."""
    service = ServiceMarketplaceService(session)
    return await service.update_provider_profile(
        provider_id=provider_id,
        user=current_user,
        data=data.model_dump(exclude_unset=True),
    )


@router.get(
    "/providers/{provider_id}",
    response_model=ServiceProviderResponse,
    summary="Détails d'un prestataire",
)
async def get_provider(
    provider_id: UUID,
    session: DbSession,
):
    """Récupérer les détails d'un prestataire."""
    service = ServiceMarketplaceService(session)
    return await service.get_provider(provider_id)


# === Service Requests ===

@router.get(
    "/requests",
    response_model=list[ServiceRequestListResponse],
    summary="Demandes de services disponibles (Prestataires)",
)
async def search_requests_for_providers(
    current_user: ActiveUser,
    session: DbSession,
    category: ServiceCategory | None = None,
    city: str | None = None,
    is_urgent: bool | None = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
):
    """
    Rechercher des demandes de services disponibles.

    Pour les prestataires cherchant des missions.
    """
    service = ServiceMarketplaceService(session)

    # Get provider profile
    provider = await service.get_provider_by_user(current_user.id)
    if not provider:
        raise InsufficientPermissionsException(
            "Vous devez avoir un profil prestataire"
        )

    return await service.search_requests_for_providers(
        provider=provider,
        category=category,
        city=city,
        is_urgent=is_urgent,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/requests/my-requests",
    response_model=list[ServiceRequestListResponse],
    summary="Mes demandes de services",
)
async def get_my_requests(
    current_user: ActiveUser,
    session: DbSession,
    status: ServiceRequestStatus | None = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
):
    """Récupérer mes demandes de services."""
    service = ServiceMarketplaceService(session)
    return await service.get_user_requests(
        user_id=current_user.id,
        status=status,
        skip=skip,
        limit=limit,
    )


@router.post(
    "/requests",
    response_model=ServiceRequestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Créer une demande de service",
)
async def create_request(
    data: ServiceRequestCreate,
    current_user: ActiveUser,
    session: DbSession,
):
    """
    Créer une nouvelle demande de service.

    Les prestataires pourront soumettre des devis.
    """
    service = ServiceMarketplaceService(session)
    return await service.create_request(
        requester=current_user,
        data=data.model_dump(),
    )


@router.get(
    "/requests/{request_id}",
    response_model=ServiceRequestResponse,
    summary="Détails d'une demande",
)
async def get_request(
    request_id: UUID,
    current_user: ActiveUser,
    session: DbSession,
):
    """Récupérer les détails d'une demande de service."""
    service = ServiceMarketplaceService(session)
    request = await service.get_request(request_id)

    # Check access (requester or provider with accepted quote)
    is_requester = request.requester_id == current_user.id
    is_admin = current_user.role == UserRole.ADMIN

    if not is_requester and not is_admin:
        # Check if user is a provider who submitted a quote
        provider = await service.get_provider_by_user(current_user.id)
        if not provider:
            raise InsufficientPermissionsException()

    return request


@router.patch(
    "/requests/{request_id}",
    response_model=ServiceRequestResponse,
    summary="Modifier une demande",
)
async def update_request(
    request_id: UUID,
    data: ServiceRequestUpdate,
    current_user: ActiveUser,
    session: DbSession,
):
    """Modifier une demande de service en attente."""
    service = ServiceMarketplaceService(session)
    return await service.update_request(
        request_id=request_id,
        user=current_user,
        data=data.model_dump(exclude_unset=True),
    )


@router.post(
    "/requests/{request_id}/cancel",
    response_model=ServiceRequestResponse,
    summary="Annuler une demande",
)
async def cancel_request(
    request_id: UUID,
    current_user: ActiveUser,
    session: DbSession,
):
    """Annuler une demande de service."""
    service = ServiceMarketplaceService(session)
    return await service.cancel_request(request_id, current_user)


# === Quotes ===

@router.get(
    "/requests/{request_id}/quotes",
    response_model=list[ServiceQuoteListResponse],
    summary="Devis pour une demande",
)
async def get_request_quotes(
    request_id: UUID,
    current_user: ActiveUser,
    session: DbSession,
):
    """Récupérer tous les devis pour une demande."""
    service = ServiceMarketplaceService(session)

    # Verify access
    request = await service.get_request(request_id)
    if request.requester_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise InsufficientPermissionsException()

    return await service.get_request_quotes(request_id)


@router.post(
    "/requests/{request_id}/quotes",
    response_model=ServiceQuoteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Soumettre un devis (Prestataire)",
)
async def create_quote(
    request_id: UUID,
    data: ServiceQuoteCreate,
    current_user: ActiveUser,
    session: DbSession,
):
    """
    Soumettre un devis pour une demande de service.

    Requiert un profil prestataire.
    """
    service = ServiceMarketplaceService(session)

    # Get provider profile
    provider = await service.get_provider_by_user(current_user.id)
    if not provider:
        raise InsufficientPermissionsException(
            "Vous devez avoir un profil prestataire"
        )

    return await service.create_quote(
        provider=provider,
        request_id=request_id,
        data=data.model_dump(exclude={"request_id"}),
    )


@router.get(
    "/quotes/my-quotes",
    response_model=list[ServiceQuoteListResponse],
    summary="Mes devis soumis (Prestataire)",
)
async def get_my_quotes(
    current_user: ActiveUser,
    session: DbSession,
    status: QuoteStatus | None = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
):
    """Récupérer mes devis soumis."""
    service = ServiceMarketplaceService(session)

    provider = await service.get_provider_by_user(current_user.id)
    if not provider:
        raise InsufficientPermissionsException(
            "Vous devez avoir un profil prestataire"
        )

    return await service.get_provider_quotes(
        provider_id=provider.id,
        status=status,
        skip=skip,
        limit=limit,
    )


@router.post(
    "/quotes/{quote_id}/accept",
    response_model=ServiceQuoteResponse,
    summary="Accepter un devis",
)
async def accept_quote(
    quote_id: UUID,
    current_user: ActiveUser,
    session: DbSession,
):
    """Accepter un devis pour une demande de service."""
    service = ServiceMarketplaceService(session)
    return await service.accept_quote(quote_id, current_user)


@router.post(
    "/quotes/{quote_id}/reject",
    response_model=ServiceQuoteResponse,
    summary="Refuser un devis",
)
async def reject_quote(
    quote_id: UUID,
    current_user: ActiveUser,
    session: DbSession,
):
    """Refuser un devis."""
    service = ServiceMarketplaceService(session)
    return await service.reject_quote(quote_id, current_user)


# === Service Workflow ===

@router.post(
    "/requests/{request_id}/start",
    response_model=ServiceRequestResponse,
    summary="Démarrer le service (Prestataire)",
)
async def start_service(
    request_id: UUID,
    current_user: ActiveUser,
    session: DbSession,
):
    """Marquer le service comme en cours."""
    service = ServiceMarketplaceService(session)

    provider = await service.get_provider_by_user(current_user.id)
    if not provider:
        raise InsufficientPermissionsException()

    return await service.start_service(request_id, provider)


@router.post(
    "/requests/{request_id}/complete",
    response_model=ServiceRequestResponse,
    summary="Terminer le service (Prestataire)",
)
async def complete_service(
    request_id: UUID,
    current_user: ActiveUser,
    session: DbSession,
):
    """Marquer le service comme terminé."""
    service = ServiceMarketplaceService(session)

    provider = await service.get_provider_by_user(current_user.id)
    if not provider:
        raise InsufficientPermissionsException()

    return await service.complete_service(request_id, provider)
