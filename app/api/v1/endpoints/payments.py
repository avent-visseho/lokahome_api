"""
Payment endpoints for transaction management and webhooks.
"""
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Header, Query, Request, status

from app.api.deps import ActiveUser, DbSession
from app.models.payment import PaymentStatus, PaymentType
from app.schemas.payment import (
    PaymentCreate,
    PaymentInitResponse,
    PaymentListResponse,
    PaymentResponse,
    RefundRequest,
    RefundResponse,
    TransactionSummary,
)
from app.services.payment import PaymentService

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.post(
    "/booking/{booking_id}",
    response_model=PaymentInitResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Initier un paiement de réservation",
)
async def initiate_booking_payment(
    booking_id: UUID,
    data: PaymentCreate,
    current_user: ActiveUser,
    session: DbSession,
):
    """
    Initier le paiement pour une réservation approuvée.

    - **payment_method**: fedapay, mtn_momo, moov_money
    - **phone_number**: Requis pour Mobile Money
    - **return_url**: URL de redirection après paiement (optionnel)
    """
    payment_service = PaymentService(session)
    result = await payment_service.initiate_booking_payment(
        booking_id=booking_id,
        payer=current_user,
        payment_method=data.payment_method,
        phone_number=data.phone_number,
        return_url=data.return_url,
    )
    return result


@router.post(
    "/service/{service_request_id}",
    response_model=PaymentInitResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Initier un paiement de service",
)
async def initiate_service_payment(
    service_request_id: UUID,
    data: PaymentCreate,
    current_user: ActiveUser,
    session: DbSession,
):
    """
    Initier le paiement pour une demande de service avec devis accepté.
    """
    payment_service = PaymentService(session)
    result = await payment_service.initiate_service_payment(
        service_request_id=service_request_id,
        payer=current_user,
        payment_method=data.payment_method,
        phone_number=data.phone_number,
        return_url=data.return_url,
    )
    return result


@router.get(
    "/my-payments",
    response_model=list[PaymentListResponse],
    summary="Mes paiements",
)
async def get_my_payments(
    current_user: ActiveUser,
    session: DbSession,
    payment_type: PaymentType | None = None,
    status: PaymentStatus | None = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
):
    """Récupérer l'historique de mes paiements."""
    payment_service = PaymentService(session)
    return await payment_service.get_user_payments(
        user_id=current_user.id,
        payment_type=payment_type,
        status=status,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/summary",
    response_model=TransactionSummary,
    summary="Résumé des transactions",
)
async def get_transaction_summary(
    current_user: ActiveUser,
    session: DbSession,
    start_date: datetime,
    end_date: datetime,
):
    """Obtenir un résumé des transactions pour une période."""
    payment_service = PaymentService(session)
    return await payment_service.get_transaction_summary(
        user_id=current_user.id,
        start_date=start_date,
        end_date=end_date,
    )


@router.get(
    "/{payment_id}",
    response_model=PaymentResponse,
    summary="Détails d'un paiement",
)
async def get_payment(
    payment_id: UUID,
    current_user: ActiveUser,
    session: DbSession,
):
    """Récupérer les détails d'un paiement."""
    payment_service = PaymentService(session)
    payment = await payment_service.get_payment(payment_id)

    # Verify access
    if payment.payer_id != current_user.id and payment.receiver_id != current_user.id:
        from app.core.exceptions import InsufficientPermissionsException
        raise InsufficientPermissionsException()

    return payment


@router.get(
    "/reference/{reference}",
    response_model=PaymentResponse,
    summary="Paiement par référence",
)
async def get_payment_by_reference(
    reference: str,
    current_user: ActiveUser,
    session: DbSession,
):
    """Récupérer un paiement par sa référence."""
    payment_service = PaymentService(session)
    payment = await payment_service.get_payment_by_reference(reference)

    # Verify access
    if payment.payer_id != current_user.id and payment.receiver_id != current_user.id:
        from app.core.exceptions import InsufficientPermissionsException
        raise InsufficientPermissionsException()

    return payment


@router.post(
    "/{payment_id}/refund",
    response_model=RefundResponse,
    summary="Demander un remboursement",
)
async def request_refund(
    payment_id: UUID,
    data: RefundRequest,
    current_user: ActiveUser,
    session: DbSession,
):
    """
    Demander un remboursement pour un paiement complété.

    Note: Les remboursements sont soumis à validation.
    """
    payment_service = PaymentService(session)

    # Verify ownership
    payment = await payment_service.get_payment(payment_id)
    if payment.payer_id != current_user.id:
        from app.core.exceptions import InsufficientPermissionsException
        raise InsufficientPermissionsException(
            "Seul le payeur peut demander un remboursement"
        )

    refunded_payment = await payment_service.process_refund(
        payment_id=payment_id,
        amount=data.amount,
        reason=data.reason,
    )

    return RefundResponse(
        payment_id=refunded_payment.id,
        refund_amount=refunded_payment.refund_amount,
        original_amount=refunded_payment.amount,
        status="refunded",
        refunded_at=refunded_payment.refunded_at,
    )


# Webhooks
@router.post(
    "/webhook/fedapay",
    include_in_schema=False,
    summary="Webhook FedaPay",
)
async def fedapay_webhook(
    request: Request,
    session: DbSession,
    x_fedapay_signature: str | None = Header(default=None),
):
    """
    Webhook endpoint for FedaPay callbacks.

    This endpoint receives payment status updates from FedaPay.
    """
    body = await request.json()
    event = body.get("name", "")
    data = body.get("object", {})

    payment_service = PaymentService(session)

    try:
        await payment_service.handle_fedapay_webhook(
            event=event,
            data=data,
            signature=x_fedapay_signature,
        )
        return {"status": "ok"}
    except Exception as e:
        # Log error but return 200 to prevent retries
        print(f"FedaPay webhook error: {e}")
        return {"status": "error", "message": str(e)}


@router.post(
    "/webhook/mtn-momo",
    include_in_schema=False,
    summary="Webhook MTN MoMo",
)
async def mtn_momo_webhook(
    request: Request,
    session: DbSession,
):
    """
    Webhook endpoint for MTN Mobile Money callbacks.
    """
    body = await request.json()

    payment_service = PaymentService(session)

    try:
        await payment_service.handle_mobile_money_webhook(
            transaction_id=body.get("financialTransactionId", ""),
            status=body.get("status", ""),
            amount=body.get("amount", 0),
            phone_number=body.get("payer", {}).get("partyId", ""),
            metadata=body.get("metadata"),
        )
        return {"status": "ok"}
    except Exception as e:
        print(f"MTN MoMo webhook error: {e}")
        return {"status": "error", "message": str(e)}


@router.post(
    "/webhook/moov",
    include_in_schema=False,
    summary="Webhook Moov Money",
)
async def moov_webhook(
    request: Request,
    session: DbSession,
):
    """
    Webhook endpoint for Moov Money callbacks.
    """
    body = await request.json()

    payment_service = PaymentService(session)

    try:
        await payment_service.handle_mobile_money_webhook(
            transaction_id=body.get("transactionId", ""),
            status=body.get("status", ""),
            amount=body.get("amount", 0),
            phone_number=body.get("phoneNumber", ""),
            metadata=body.get("metadata"),
        )
        return {"status": "ok"}
    except Exception as e:
        print(f"Moov webhook error: {e}")
        return {"status": "error", "message": str(e)}
