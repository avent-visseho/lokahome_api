"""
Booking endpoints for reservation management.
"""
from uuid import UUID

from fastapi import APIRouter, Query, status

from app.api.deps import ActiveUser, DbSession, RequireLandlord
from app.models.booking import BookingStatus
from app.models.user import UserRole
from app.schemas.booking import (
    AvailabilityCheck,
    AvailabilityResponse,
    BookingCancellation,
    BookingCreate,
    BookingDetailResponse,
    BookingListResponse,
    BookingResponse,
    BookingStatusUpdate,
    BookingUpdate,
)
from app.services.booking import BookingService

router = APIRouter(prefix="/bookings", tags=["Bookings"])


@router.post(
    "/check-availability",
    response_model=AvailabilityResponse,
    summary="Vérifier la disponibilité",
)
async def check_availability(
    data: AvailabilityCheck,
    session: DbSession,
):
    """
    Vérifier la disponibilité d'une propriété pour des dates données.

    Retourne également le calcul des prix.
    """
    booking_service = BookingService(session)
    return await booking_service.check_availability(
        property_id=data.property_id,
        check_in=data.check_in,
        check_out=data.check_out,
    )


@router.post(
    "",
    response_model=BookingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Créer une réservation",
)
async def create_booking(
    data: BookingCreate,
    current_user: ActiveUser,
    session: DbSession,
):
    """
    Créer une nouvelle réservation.

    La réservation sera en statut "pending" jusqu'à approbation par le propriétaire.
    """
    booking_service = BookingService(session)
    return await booking_service.create_booking(current_user, data)


@router.get(
    "/my-bookings",
    response_model=list[BookingListResponse],
    summary="Mes réservations (Locataire)",
)
async def get_my_bookings(
    current_user: ActiveUser,
    session: DbSession,
    status: BookingStatus | None = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
):
    """Récupérer mes réservations en tant que locataire."""
    booking_service = BookingService(session)
    return await booking_service.get_tenant_bookings(
        tenant_id=current_user.id,
        status=status,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/landlord",
    response_model=list[BookingListResponse],
    summary="Réservations de mes biens (Propriétaire)",
    dependencies=[RequireLandlord],
)
async def get_landlord_bookings(
    current_user: ActiveUser,
    session: DbSession,
    status: BookingStatus | None = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
):
    """Récupérer les réservations pour tous mes biens immobiliers."""
    booking_service = BookingService(session)
    return await booking_service.get_landlord_bookings(
        owner_id=current_user.id,
        status=status,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/property/{property_id}",
    response_model=list[BookingListResponse],
    summary="Réservations d'une propriété",
)
async def get_property_bookings(
    property_id: UUID,
    current_user: ActiveUser,
    session: DbSession,
    status: BookingStatus | None = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
):
    """Récupérer les réservations d'une propriété spécifique."""
    booking_service = BookingService(session)
    # TODO: Verify user has access to this property
    return await booking_service.get_property_bookings(
        property_id=property_id,
        status=status,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/reference/{reference}",
    response_model=BookingDetailResponse,
    summary="Détails par référence",
)
async def get_booking_by_reference(
    reference: str,
    current_user: ActiveUser,
    session: DbSession,
):
    """Récupérer une réservation par son code de référence."""
    booking_service = BookingService(session)
    booking = await booking_service.get_booking_by_reference(reference)

    # Verify access
    if (
        booking.tenant_id != current_user.id
        and booking.booked_property.owner_id != current_user.id
        and current_user.role != UserRole.ADMIN
    ):
        from app.core.exceptions import InsufficientPermissionsException

        raise InsufficientPermissionsException()

    return booking


@router.get(
    "/{booking_id}",
    response_model=BookingDetailResponse,
    summary="Détails d'une réservation",
)
async def get_booking(
    booking_id: UUID,
    current_user: ActiveUser,
    session: DbSession,
):
    """Récupérer les détails d'une réservation."""
    booking_service = BookingService(session)
    booking = await booking_service.get_booking(booking_id)

    # Verify access
    if (
        booking.tenant_id != current_user.id
        and booking.booked_property.owner_id != current_user.id
        and current_user.role != UserRole.ADMIN
    ):
        from app.core.exceptions import InsufficientPermissionsException

        raise InsufficientPermissionsException()

    return booking


@router.patch(
    "/{booking_id}",
    response_model=BookingResponse,
    summary="Modifier une réservation",
)
async def update_booking(
    booking_id: UUID,
    data: BookingUpdate,
    current_user: ActiveUser,
    session: DbSession,
):
    """
    Modifier une réservation en attente.

    Seules les réservations en statut "pending" peuvent être modifiées.
    """
    booking_service = BookingService(session)
    return await booking_service.update_booking(booking_id, current_user, data)


@router.post(
    "/{booking_id}/approve",
    response_model=BookingResponse,
    summary="Approuver une réservation (Propriétaire)",
    dependencies=[RequireLandlord],
)
async def approve_booking(
    booking_id: UUID,
    current_user: ActiveUser,
    session: DbSession,
    data: BookingStatusUpdate | None = None,
):
    """
    Approuver une réservation.

    Le locataire pourra ensuite procéder au paiement.
    """
    booking_service = BookingService(session)
    notes = data.landlord_notes if data else None
    return await booking_service.approve_booking(booking_id, current_user, notes)


@router.post(
    "/{booking_id}/reject",
    response_model=BookingResponse,
    summary="Rejeter une réservation (Propriétaire)",
    dependencies=[RequireLandlord],
)
async def reject_booking(
    booking_id: UUID,
    current_user: ActiveUser,
    session: DbSession,
    data: BookingStatusUpdate | None = None,
):
    """Rejeter une demande de réservation."""
    booking_service = BookingService(session)
    reason = data.landlord_notes if data else None
    return await booking_service.reject_booking(booking_id, current_user, reason)


@router.post(
    "/{booking_id}/cancel",
    response_model=BookingResponse,
    summary="Annuler une réservation",
)
async def cancel_booking(
    booking_id: UUID,
    data: BookingCancellation,
    current_user: ActiveUser,
    session: DbSession,
):
    """
    Annuler une réservation.

    Peut être effectué par le locataire ou le propriétaire.
    """
    booking_service = BookingService(session)
    return await booking_service.cancel_booking(
        booking_id, current_user, data.reason
    )


@router.post(
    "/{booking_id}/confirm",
    response_model=BookingResponse,
    summary="Confirmer une réservation après paiement",
)
async def confirm_booking(
    booking_id: UUID,
    session: DbSession,
):
    """
    Confirmer une réservation après réception du paiement.

    Note: Cette route est généralement appelée par le webhook de paiement.
    """
    booking_service = BookingService(session)
    return await booking_service.confirm_booking(booking_id)
