"""
Review endpoints for ratings and feedback.
"""
from uuid import UUID

from fastapi import APIRouter, Query, status

from app.api.deps import ActiveUser, DbSession, RequireAdmin
from app.schemas.review import (
    ReviewCreate,
    ReviewListResponse,
    ReviewResponse,
    ReviewResponseCreate,
    ReviewSummary,
)
from app.services.review import ReviewService

router = APIRouter(prefix="/reviews", tags=["Reviews"])


# === Property Reviews ===

@router.get(
    "/property/{property_id}",
    response_model=list[ReviewListResponse],
    summary="Avis sur un bien",
)
async def get_property_reviews(
    property_id: UUID,
    session: DbSession,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
):
    """Récupérer les avis sur un bien immobilier."""
    service = ReviewService(session)
    return await service.get_property_reviews(
        property_id, skip=skip, limit=limit
    )


@router.get(
    "/property/{property_id}/summary",
    response_model=ReviewSummary,
    summary="Résumé des avis d'un bien",
)
async def get_property_review_summary(
    property_id: UUID,
    session: DbSession,
):
    """Obtenir le résumé des avis (moyenne, distribution) pour un bien."""
    service = ReviewService(session)
    return await service.get_review_summary(property_id=property_id)


@router.post(
    "/property/{property_id}",
    response_model=ReviewResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Évaluer un bien",
)
async def create_property_review(
    property_id: UUID,
    data: ReviewCreate,
    current_user: ActiveUser,
    session: DbSession,
):
    """
    Créer un avis sur un bien après une réservation terminée.

    - **booking_id**: ID de la réservation (obligatoire)
    - **rating**: Note de 1 à 5
    - **detailed_ratings**: Notes détaillées (propreté, communication, etc.)
    """
    service = ReviewService(session)
    return await service.create_property_review(
        reviewer=current_user,
        property_id=property_id,
        booking_id=data.booking_id,
        rating=data.rating,
        title=data.title,
        comment=data.comment,
        detailed_ratings=data.detailed_ratings,
        images=data.images,
    )


# === Tenant Reviews ===

@router.get(
    "/user/{user_id}",
    response_model=list[ReviewListResponse],
    summary="Avis sur un utilisateur",
)
async def get_user_reviews(
    user_id: UUID,
    session: DbSession,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
):
    """Récupérer les avis sur un utilisateur (locataire ou propriétaire)."""
    service = ReviewService(session)
    return await service.get_user_reviews(
        user_id, as_reviewer=False, skip=skip, limit=limit
    )


@router.get(
    "/user/{user_id}/summary",
    response_model=ReviewSummary,
    summary="Résumé des avis d'un utilisateur",
)
async def get_user_review_summary(
    user_id: UUID,
    session: DbSession,
):
    """Obtenir le résumé des avis pour un utilisateur."""
    service = ReviewService(session)
    return await service.get_review_summary(user_id=user_id)


@router.post(
    "/tenant/{tenant_id}",
    response_model=ReviewResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Évaluer un locataire (Propriétaire)",
)
async def create_tenant_review(
    tenant_id: UUID,
    data: ReviewCreate,
    current_user: ActiveUser,
    session: DbSession,
):
    """
    Créer un avis sur un locataire après une réservation terminée.

    Seul le propriétaire du bien peut évaluer le locataire.
    """
    service = ReviewService(session)
    return await service.create_tenant_review(
        reviewer=current_user,
        tenant_id=tenant_id,
        booking_id=data.booking_id,
        rating=data.rating,
        comment=data.comment,
    )


# === Service Provider Reviews ===

@router.get(
    "/provider/{provider_id}",
    response_model=list[ReviewListResponse],
    summary="Avis sur un prestataire",
)
async def get_provider_reviews(
    provider_id: UUID,
    session: DbSession,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
):
    """Récupérer les avis sur un prestataire de services."""
    service = ReviewService(session)
    return await service.get_provider_reviews(
        provider_id, skip=skip, limit=limit
    )


@router.get(
    "/provider/{provider_id}/summary",
    response_model=ReviewSummary,
    summary="Résumé des avis d'un prestataire",
)
async def get_provider_review_summary(
    provider_id: UUID,
    session: DbSession,
):
    """Obtenir le résumé des avis pour un prestataire."""
    service = ReviewService(session)
    return await service.get_review_summary(provider_id=provider_id)


@router.post(
    "/provider/{provider_id}",
    response_model=ReviewResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Évaluer un prestataire",
)
async def create_provider_review(
    provider_id: UUID,
    data: ReviewCreate,
    current_user: ActiveUser,
    session: DbSession,
):
    """
    Créer un avis sur un prestataire après un service terminé.

    - **service_request_id**: ID de la demande de service (obligatoire)
    """
    service = ReviewService(session)
    return await service.create_provider_review(
        reviewer=current_user,
        provider_id=provider_id,
        service_request_id=data.service_request_id,
        rating=data.rating,
        title=data.title,
        comment=data.comment,
        images=data.images,
    )


# === My Reviews ===

@router.get(
    "/my-reviews",
    response_model=list[ReviewListResponse],
    summary="Mes avis donnés",
)
async def get_my_reviews(
    current_user: ActiveUser,
    session: DbSession,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
):
    """Récupérer les avis que j'ai donnés."""
    service = ReviewService(session)
    return await service.get_user_reviews(
        current_user.id, as_reviewer=True, skip=skip, limit=limit
    )


@router.get(
    "/reviews-about-me",
    response_model=list[ReviewListResponse],
    summary="Avis me concernant",
)
async def get_reviews_about_me(
    current_user: ActiveUser,
    session: DbSession,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
):
    """Récupérer les avis me concernant."""
    service = ReviewService(session)
    return await service.get_user_reviews(
        current_user.id, as_reviewer=False, skip=skip, limit=limit
    )


# === Review Response ===

@router.post(
    "/{review_id}/respond",
    response_model=ReviewResponse,
    summary="Répondre à un avis",
)
async def respond_to_review(
    review_id: UUID,
    data: ReviewResponseCreate,
    current_user: ActiveUser,
    session: DbSession,
):
    """
    Répondre à un avis (par la partie évaluée).

    Une seule réponse est autorisée par avis.
    """
    service = ReviewService(session)
    return await service.respond_to_review(
        review_id=review_id,
        responder=current_user,
        response=data.response,
    )


@router.get(
    "/{review_id}",
    response_model=ReviewResponse,
    summary="Détails d'un avis",
)
async def get_review(
    review_id: UUID,
    session: DbSession,
):
    """Récupérer les détails d'un avis."""
    service = ReviewService(session)
    return await service.get_review(review_id)


# === Admin ===

@router.post(
    "/{review_id}/hide",
    response_model=ReviewResponse,
    summary="Masquer un avis (Admin)",
    dependencies=[RequireAdmin],
)
async def hide_review(
    review_id: UUID,
    session: DbSession,
    note: str | None = None,
):
    """Masquer un avis (modération)."""
    service = ReviewService(session)
    return await service.hide_review(review_id, note)


@router.post(
    "/{review_id}/show",
    response_model=ReviewResponse,
    summary="Afficher un avis masqué (Admin)",
    dependencies=[RequireAdmin],
)
async def show_review(
    review_id: UUID,
    session: DbSession,
):
    """Rétablir un avis masqué."""
    service = ReviewService(session)
    return await service.show_review(review_id)
