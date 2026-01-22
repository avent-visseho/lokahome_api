"""
Admin endpoints for platform management and moderation.
"""
from datetime import date, datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Query
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.api.deps import DbSession, RequireAdmin
from app.models.booking import Booking
from app.models.payment import Payment, PaymentStatus
from app.models.property import Property, PropertyStatus
from app.models.review import Review
from app.models.service import ServiceProvider
from app.models.user import User, UserRole
from app.schemas.base import MessageResponse

router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
    dependencies=[RequireAdmin],
)


# === Dashboard & Analytics ===

@router.get(
    "/dashboard",
    summary="Tableau de bord admin",
)
async def get_admin_dashboard(
    session: DbSession,
) -> dict[str, Any]:
    """
    Obtenir les statistiques générales de la plateforme.

    - Nombre d'utilisateurs par rôle
    - Nombre de biens par statut
    - Statistiques de réservation
    - Volume de paiements
    """
    # Users stats
    users_query = select(
        User.role,
        func.count(User.id).label("count"),
    ).group_by(User.role)
    users_result = await session.execute(users_query)
    users_by_role = {row.role.value: row.count for row in users_result}

    # Properties stats
    props_query = select(
        Property.status,
        func.count(Property.id).label("count"),
    ).group_by(Property.status)
    props_result = await session.execute(props_query)
    properties_by_status = {row.status.value: row.count for row in props_result}

    # Bookings stats
    bookings_query = select(
        Booking.status,
        func.count(Booking.id).label("count"),
    ).group_by(Booking.status)
    bookings_result = await session.execute(bookings_query)
    bookings_by_status = {row.status.value: row.count for row in bookings_result}

    # Payments stats
    payments_query = select(
        func.sum(Payment.amount).label("total"),
        func.count(Payment.id).label("count"),
    ).where(Payment.status == PaymentStatus.COMPLETED)
    payments_result = await session.execute(payments_query)
    payments_row = payments_result.first()

    # Recent activity counts (last 30 days)
    thirty_days_ago = datetime.utcnow().replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    new_users = await session.scalar(
        select(func.count(User.id)).where(User.created_at >= thirty_days_ago)
    )
    new_bookings = await session.scalar(
        select(func.count(Booking.id)).where(Booking.created_at >= thirty_days_ago)
    )

    return {
        "users": {
            "total": sum(users_by_role.values()),
            "by_role": users_by_role,
            "new_last_30_days": new_users or 0,
        },
        "properties": {
            "total": sum(properties_by_status.values()),
            "by_status": properties_by_status,
        },
        "bookings": {
            "total": sum(bookings_by_status.values()),
            "by_status": bookings_by_status,
            "new_last_30_days": new_bookings or 0,
        },
        "payments": {
            "total_amount": float(payments_row.total or 0) if payments_row else 0,
            "total_count": payments_row.count if payments_row else 0,
        },
    }


@router.get(
    "/analytics/revenue",
    summary="Analyse des revenus",
)
async def get_revenue_analytics(
    session: DbSession,
    start_date: date | None = None,
    end_date: date | None = None,
    group_by: str = Query(default="day", regex="^(day|week|month)$"),
) -> dict[str, Any]:
    """
    Obtenir les statistiques de revenus par période.
    """
    # Build date filter
    filters = [Payment.status == PaymentStatus.COMPLETED]
    if start_date:
        filters.append(Payment.created_at >= datetime.combine(start_date, datetime.min.time()))
    if end_date:
        filters.append(Payment.created_at <= datetime.combine(end_date, datetime.max.time()))

    # Group by time period
    if group_by == "day":
        date_trunc = func.date_trunc("day", Payment.created_at)
    elif group_by == "week":
        date_trunc = func.date_trunc("week", Payment.created_at)
    else:
        date_trunc = func.date_trunc("month", Payment.created_at)

    query = (
        select(
            date_trunc.label("period"),
            func.sum(Payment.amount).label("revenue"),
            func.count(Payment.id).label("transactions"),
        )
        .where(*filters)
        .group_by(date_trunc)
        .order_by(date_trunc)
    )

    result = await session.execute(query)

    return {
        "group_by": group_by,
        "data": [
            {
                "period": row.period.isoformat() if row.period else None,
                "revenue": float(row.revenue or 0),
                "transactions": row.transactions,
            }
            for row in result
        ],
    }


# === User Management ===

@router.get(
    "/users",
    summary="Liste des utilisateurs",
)
async def list_users(
    session: DbSession,
    role: UserRole | None = None,
    is_active: bool | None = None,
    is_verified: bool | None = None,
    search: str | None = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
) -> dict[str, Any]:
    """Lister les utilisateurs avec filtres."""
    query = select(User)

    if role:
        query = query.where(User.role == role)
    if is_active is not None:
        query = query.where(User.is_active == is_active)
    if is_verified is not None:
        query = query.where(User.is_verified == is_verified)
    if search:
        search_filter = f"%{search}%"
        query = query.where(
            (User.email.ilike(search_filter))
            | (User.first_name.ilike(search_filter))
            | (User.last_name.ilike(search_filter))
            | (User.phone.ilike(search_filter))
        )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = await session.scalar(count_query)

    # Get paginated results
    query = query.offset(skip).limit(limit).order_by(User.created_at.desc())
    result = await session.execute(query)
    users = result.scalars().all()

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": [
            {
                "id": str(user.id),
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "phone": user.phone,
                "role": user.role.value,
                "is_active": user.is_active,
                "is_verified": user.is_verified,
                "created_at": user.created_at.isoformat(),
            }
            for user in users
        ],
    }


@router.post(
    "/users/{user_id}/activate",
    response_model=MessageResponse,
    summary="Activer un utilisateur",
)
async def activate_user(
    user_id: UUID,
    session: DbSession,
):
    """Activer un compte utilisateur."""
    user = await session.get(User, user_id)
    if not user:
        from app.core.exceptions import NotFoundError
        raise NotFoundError("Utilisateur non trouvé")

    user.is_active = True
    await session.commit()

    return MessageResponse(message="Utilisateur activé")


@router.post(
    "/users/{user_id}/deactivate",
    response_model=MessageResponse,
    summary="Désactiver un utilisateur",
)
async def deactivate_user(
    user_id: UUID,
    session: DbSession,
):
    """Désactiver un compte utilisateur."""
    user = await session.get(User, user_id)
    if not user:
        from app.core.exceptions import NotFoundError
        raise NotFoundError("Utilisateur non trouvé")

    user.is_active = False
    await session.commit()

    return MessageResponse(message="Utilisateur désactivé")


@router.post(
    "/users/{user_id}/verify",
    response_model=MessageResponse,
    summary="Vérifier un utilisateur",
)
async def verify_user(
    user_id: UUID,
    session: DbSession,
):
    """Marquer un utilisateur comme vérifié."""
    user = await session.get(User, user_id)
    if not user:
        from app.core.exceptions import NotFoundError
        raise NotFoundError("Utilisateur non trouvé")

    user.is_verified = True
    await session.commit()

    return MessageResponse(message="Utilisateur vérifié")


@router.patch(
    "/users/{user_id}/role",
    response_model=MessageResponse,
    summary="Changer le rôle d'un utilisateur",
)
async def change_user_role(
    user_id: UUID,
    new_role: UserRole,
    session: DbSession,
):
    """Changer le rôle d'un utilisateur."""
    user = await session.get(User, user_id)
    if not user:
        from app.core.exceptions import NotFoundError
        raise NotFoundError("Utilisateur non trouvé")

    user.role = new_role
    await session.commit()

    return MessageResponse(message=f"Rôle changé en {new_role.value}")


# === Property Management ===

@router.get(
    "/properties",
    summary="Liste des biens (Admin)",
)
async def list_all_properties(
    session: DbSession,
    status: PropertyStatus | None = None,
    owner_id: UUID | None = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
) -> dict[str, Any]:
    """Lister tous les biens avec filtres admin."""
    query = select(Property).options(selectinload(Property.owner))

    if status:
        query = query.where(Property.status == status)
    if owner_id:
        query = query.where(Property.owner_id == owner_id)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = await session.scalar(count_query)

    # Get paginated results
    query = query.offset(skip).limit(limit).order_by(Property.created_at.desc())
    result = await session.execute(query)
    properties = result.scalars().all()

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": [
            {
                "id": str(prop.id),
                "title": prop.title,
                "status": prop.status.value,
                "owner": {
                    "id": str(prop.owner.id),
                    "email": prop.owner.email,
                    "name": f"{prop.owner.first_name} {prop.owner.last_name}",
                },
                "city": prop.city,
                "price_per_night": float(prop.price_per_night) if prop.price_per_night else None,
                "price_per_month": float(prop.price_per_month) if prop.price_per_month else None,
                "created_at": prop.created_at.isoformat(),
            }
            for prop in properties
        ],
    }


@router.post(
    "/properties/{property_id}/approve",
    response_model=MessageResponse,
    summary="Approuver un bien",
)
async def approve_property(
    property_id: UUID,
    session: DbSession,
):
    """Approuver un bien en attente de validation."""
    prop = await session.get(Property, property_id)
    if not prop:
        from app.core.exceptions import NotFoundError
        raise NotFoundError("Bien non trouvé")

    prop.status = PropertyStatus.PUBLISHED
    await session.commit()

    return MessageResponse(message="Bien approuvé et publié")


@router.post(
    "/properties/{property_id}/reject",
    response_model=MessageResponse,
    summary="Rejeter un bien",
)
async def reject_property(
    property_id: UUID,
    session: DbSession,
    reason: str | None = None,
):
    """Rejeter un bien avec raison optionnelle."""
    prop = await session.get(Property, property_id)
    if not prop:
        from app.core.exceptions import NotFoundError
        raise NotFoundError("Bien non trouvé")

    prop.status = PropertyStatus.REJECTED
    if reason:
        prop.admin_notes = reason
    await session.commit()

    return MessageResponse(message="Bien rejeté")


@router.post(
    "/properties/{property_id}/suspend",
    response_model=MessageResponse,
    summary="Suspendre un bien",
)
async def suspend_property(
    property_id: UUID,
    session: DbSession,
    reason: str | None = None,
):
    """Suspendre temporairement un bien publié."""
    prop = await session.get(Property, property_id)
    if not prop:
        from app.core.exceptions import NotFoundError
        raise NotFoundError("Bien non trouvé")

    prop.status = PropertyStatus.SUSPENDED
    if reason:
        prop.admin_notes = reason
    await session.commit()

    return MessageResponse(message="Bien suspendu")


# === Service Provider Management ===

@router.get(
    "/providers",
    summary="Liste des prestataires",
)
async def list_providers(
    session: DbSession,
    is_verified: bool | None = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
) -> dict[str, Any]:
    """Lister les prestataires de services."""
    query = select(ServiceProvider).options(selectinload(ServiceProvider.user))

    if is_verified is not None:
        query = query.where(ServiceProvider.is_verified == is_verified)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = await session.scalar(count_query)

    # Get paginated results
    query = query.offset(skip).limit(limit).order_by(ServiceProvider.created_at.desc())
    result = await session.execute(query)
    providers = result.scalars().all()

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": [
            {
                "id": str(provider.id),
                "user": {
                    "id": str(provider.user.id),
                    "email": provider.user.email,
                    "name": f"{provider.user.first_name} {provider.user.last_name}",
                },
                "business_name": provider.business_name,
                "service_types": provider.service_types,
                "is_verified": provider.is_verified,
                "rating": float(provider.rating) if provider.rating else None,
                "created_at": provider.created_at.isoformat(),
            }
            for provider in providers
        ],
    }


@router.post(
    "/providers/{provider_id}/verify",
    response_model=MessageResponse,
    summary="Vérifier un prestataire",
)
async def verify_provider(
    provider_id: UUID,
    session: DbSession,
):
    """Vérifier un profil de prestataire."""
    provider = await session.get(ServiceProvider, provider_id)
    if not provider:
        from app.core.exceptions import NotFoundError
        raise NotFoundError("Prestataire non trouvé")

    provider.is_verified = True
    await session.commit()

    return MessageResponse(message="Prestataire vérifié")


@router.post(
    "/providers/{provider_id}/unverify",
    response_model=MessageResponse,
    summary="Retirer la vérification d'un prestataire",
)
async def unverify_provider(
    provider_id: UUID,
    session: DbSession,
):
    """Retirer la vérification d'un prestataire."""
    provider = await session.get(ServiceProvider, provider_id)
    if not provider:
        from app.core.exceptions import NotFoundError
        raise NotFoundError("Prestataire non trouvé")

    provider.is_verified = False
    await session.commit()

    return MessageResponse(message="Vérification retirée")


# === Moderation ===

@router.get(
    "/moderation/pending-reviews",
    summary="Avis en attente de modération",
)
async def get_pending_reviews(
    session: DbSession,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
) -> dict[str, Any]:
    """Récupérer les avis signalés ou en attente de modération."""
    query = (
        select(Review)
        .where(Review.is_hidden)
        .options(
            selectinload(Review.reviewer),
        )
    )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = await session.scalar(count_query)

    # Get paginated results
    query = query.offset(skip).limit(limit).order_by(Review.created_at.desc())
    result = await session.execute(query)
    reviews = result.scalars().all()

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": [
            {
                "id": str(review.id),
                "reviewer": {
                    "id": str(review.reviewer.id),
                    "name": f"{review.reviewer.first_name} {review.reviewer.last_name}",
                },
                "rating": review.rating,
                "comment": review.comment,
                "admin_notes": review.admin_notes,
                "created_at": review.created_at.isoformat(),
            }
            for review in reviews
        ],
    }


# === Payments ===

@router.get(
    "/payments",
    summary="Liste des paiements (Admin)",
)
async def list_all_payments(
    session: DbSession,
    status: PaymentStatus | None = None,
    provider: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
) -> dict[str, Any]:
    """Lister tous les paiements avec filtres."""
    query = select(Payment).options(selectinload(Payment.user))

    if status:
        query = query.where(Payment.status == status)
    if provider:
        query = query.where(Payment.provider == provider)
    if start_date:
        query = query.where(
            Payment.created_at >= datetime.combine(start_date, datetime.min.time())
        )
    if end_date:
        query = query.where(
            Payment.created_at <= datetime.combine(end_date, datetime.max.time())
        )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = await session.scalar(count_query)

    # Get paginated results
    query = query.offset(skip).limit(limit).order_by(Payment.created_at.desc())
    result = await session.execute(query)
    payments = result.scalars().all()

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": [
            {
                "id": str(payment.id),
                "reference": payment.reference,
                "user": {
                    "id": str(payment.user.id),
                    "email": payment.user.email,
                },
                "amount": float(payment.amount),
                "currency": payment.currency,
                "provider": payment.provider,
                "status": payment.status.value,
                "created_at": payment.created_at.isoformat(),
            }
            for payment in payments
        ],
    }


@router.post(
    "/payments/{payment_id}/refund",
    response_model=MessageResponse,
    summary="Initier un remboursement",
)
async def initiate_refund(
    payment_id: UUID,
    session: DbSession,
    amount: float | None = None,
    reason: str | None = None,
):
    """Initier un remboursement pour un paiement."""
    payment = await session.get(Payment, payment_id)
    if not payment:
        from app.core.exceptions import NotFoundError
        raise NotFoundError("Paiement non trouvé")

    if payment.status != PaymentStatus.COMPLETED:
        from app.core.exceptions import BusinessLogicError
        raise BusinessLogicError("Seuls les paiements complétés peuvent être remboursés")

    refund_amount = amount or float(payment.amount)

    # Queue refund task
    from app.tasks import process_refund
    process_refund.delay(
        payment_id=str(payment.id),
        refund_amount=refund_amount,
        reason=reason or "Admin initiated refund",
    )

    return MessageResponse(
        message=f"Remboursement de {refund_amount} {payment.currency} initié"
    )


# === System ===

@router.get(
    "/system/health",
    summary="État du système",
)
async def system_health(
    session: DbSession,
) -> dict[str, Any]:
    """Vérifier l'état de santé du système."""
    from app.core.redis import redis_manager

    # Check database
    try:
        await session.execute(select(1))
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    # Check Redis
    try:
        await redis_manager.ping()
        redis_status = "healthy"
    except Exception as e:
        redis_status = f"unhealthy: {str(e)}"

    return {
        "status": "healthy" if db_status == "healthy" and redis_status == "healthy" else "degraded",
        "services": {
            "database": db_status,
            "redis": redis_status,
        },
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.post(
    "/system/clear-cache",
    response_model=MessageResponse,
    summary="Vider le cache",
)
async def clear_cache():
    """Vider le cache Redis."""
    from app.core.redis import redis_manager

    await redis_manager.clear_all()

    return MessageResponse(message="Cache vidé")
