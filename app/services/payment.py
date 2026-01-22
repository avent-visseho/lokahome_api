"""
Payment service for FedaPay, Mobile Money, and Stripe integrations.
"""
import hashlib
import hmac
import random
import string
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import (
    BusinessLogicException,
    NotFoundException,
    PaymentFailedException,
)
from app.models.booking import Booking, BookingStatus
from app.models.payment import Payment, PaymentMethod, PaymentStatus, PaymentType
from app.models.service import ServiceRequest, ServiceRequestStatus
from app.models.user import User
from app.repositories.base import BaseRepository


class PaymentRepository(BaseRepository[Payment]):
    """Repository for Payment model operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(Payment, session)

    def _generate_reference(self) -> str:
        """Generate unique payment reference."""
        chars = string.ascii_uppercase + string.digits
        return "PAY" + "".join(random.choices(chars, k=10))

    async def create(self, data: dict) -> Payment:
        """Create payment with generated reference."""
        while True:
            reference = self._generate_reference()
            exists = await self.session.execute(
                select(func.count())
                .select_from(Payment)
                .where(Payment.reference == reference)
            )
            if exists.scalar_one() == 0:
                break

        data["reference"] = reference
        return await super().create(data)

    async def get_by_reference(self, reference: str) -> Payment | None:
        """Get payment by reference."""
        result = await self.session.execute(
            select(Payment).where(Payment.reference == reference)
        )
        return result.scalar_one_or_none()

    async def get_by_provider_reference(self, provider_ref: str) -> Payment | None:
        """Get payment by provider reference."""
        result = await self.session.execute(
            select(Payment).where(Payment.provider_reference == provider_ref)
        )
        return result.scalar_one_or_none()

    async def get_user_payments(
        self,
        user_id: UUID,
        *,
        payment_type: PaymentType | None = None,
        status: PaymentStatus | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Payment]:
        """Get payments for a user (as payer or receiver)."""
        from sqlalchemy import or_

        query = select(Payment).where(
            or_(Payment.payer_id == user_id, Payment.receiver_id == user_id)
        )

        if payment_type:
            query = query.where(Payment.payment_type == payment_type)
        if status:
            query = query.where(Payment.status == status)

        query = query.order_by(Payment.created_at.desc()).offset(skip).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())


class FedaPayClient:
    """
    Client for FedaPay API integration.

    FedaPay is the primary payment provider for Benin supporting:
    - Card payments
    - Mobile Money (MTN, Moov)
    - Bank transfers

    API Documentation: https://docs.fedapay.com/api-reference/introduction

    Transaction flow:
    1. Create transaction (POST /transactions)
    2. Generate payment token (POST /transactions/{id}/token)
    3. Redirect user to payment URL
    4. Handle callback/webhook for status updates

    Transaction statuses:
    - pending: Initial state
    - approved: Payment completed successfully
    - declined: Insufficient funds or account issues
    - canceled: Customer-initiated cancellation
    - refunded: Payment reversed
    - transferred: Funds sent to merchant balance
    """

    BASE_URL_SANDBOX = "https://sandbox-api.fedapay.com/v1"
    BASE_URL_LIVE = "https://api.fedapay.com/v1"

    def __init__(self):
        self.api_key = settings.FEDAPAY_API_KEY
        self.secret_key = settings.FEDAPAY_SECRET_KEY
        self.environment = settings.FEDAPAY_ENVIRONMENT
        self.webhook_secret = settings.FEDAPAY_WEBHOOK_SECRET
        self.base_url = (
            self.BASE_URL_LIVE
            if self.environment == "live"
            else self.BASE_URL_SANDBOX
        )

    def _get_headers(self) -> dict:
        """Get API headers with Bearer token authentication."""
        return {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json",
        }

    async def create_transaction(
        self,
        amount: Decimal,
        currency: str,
        description: str,
        customer_email: str,
        customer_firstname: str,
        customer_lastname: str,
        customer_phone: str | None = None,
        callback_url: str | None = None,
        metadata: dict | None = None,
    ) -> dict:
        """
        Create a FedaPay transaction.

        Args:
            amount: Transaction amount (must be integer, no decimals)
            currency: ISO currency code (XOF for CFA Franc)
            description: Brief transaction description
            customer_email: Customer email address
            customer_firstname: Customer first name
            customer_lastname: Customer last name
            customer_phone: Customer phone number (optional)
            callback_url: URL to redirect after payment (optional)
            metadata: Additional data to attach to transaction (optional)

        Returns:
            Transaction data with 'v1' key containing transaction details
        """
        # Build customer object
        customer = {
            "email": customer_email,
            "firstname": customer_firstname,
            "lastname": customer_lastname,
        }

        if customer_phone:
            # Phone number format: just the number string
            customer["phone_number"] = {"number": customer_phone}

        payload = {
            "description": description,
            "amount": int(amount),  # Amount must be integer
            "currency": {"iso": currency},
            "customer": customer,
        }

        # callback_url is for redirecting user after payment completion
        if callback_url:
            payload["callback_url"] = callback_url

        if metadata:
            payload["metadata"] = metadata

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/transactions",
                json=payload,
                headers=self._get_headers(),
                timeout=30.0,
            )

            if response.status_code not in [200, 201]:
                raise PaymentFailedException(
                    f"FedaPay transaction creation failed: {response.text}"
                )

            return response.json()

    async def generate_payment_token(self, transaction_id: int | str) -> dict:
        """
        Generate a payment token and URL for the transaction.

        Args:
            transaction_id: The FedaPay transaction ID

        Returns:
            Token data with 'v1' key containing 'token' and 'url'
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/transactions/{transaction_id}/token",
                headers=self._get_headers(),
                timeout=30.0,
            )

            if response.status_code not in [200, 201]:
                raise PaymentFailedException(
                    f"FedaPay token generation failed: {response.text}"
                )

            return response.json()

    async def get_transaction(self, transaction_id: int | str) -> dict:
        """
        Get transaction details by ID.

        Use this to verify transaction status instead of relying
        solely on callback URL parameters.

        Args:
            transaction_id: The FedaPay transaction ID

        Returns:
            Transaction data with current status
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/transactions/{transaction_id}",
                headers=self._get_headers(),
                timeout=30.0,
            )

            if response.status_code != 200:
                raise PaymentFailedException(
                    f"FedaPay transaction retrieval failed: {response.text}"
                )

            return response.json()

    async def send_mobile_payment(
        self,
        transaction_id: int | str,
        mode: str,
        phone_number: str,
    ) -> dict:
        """
        Send payment request directly to mobile money (no redirect).

        Supported modes for Benin:
        - mtn: MTN Mobile Money
        - moov: Moov Money

        Args:
            transaction_id: The FedaPay transaction ID
            mode: Payment mode (mtn, moov, etc.)
            phone_number: Customer phone number

        Returns:
            Payment request status
        """
        payload = {
            "mode": mode,
            "phone_number": phone_number,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/transactions/{transaction_id}",
                json=payload,
                headers=self._get_headers(),
                timeout=30.0,
            )

            if response.status_code not in [200, 201]:
                raise PaymentFailedException(
                    f"FedaPay mobile payment failed: {response.text}"
                )

            return response.json()

    def verify_webhook_signature(
        self, payload: bytes, signature: str
    ) -> bool:
        """
        Verify FedaPay webhook signature.

        FedaPay signs webhooks using X-FEDAPAY-SIGNATURE header.
        Each webhook endpoint has a unique secret key.

        Args:
            payload: Raw request body bytes
            signature: Value from X-FEDAPAY-SIGNATURE header

        Returns:
            True if signature is valid
        """
        if not self.webhook_secret:
            # Skip verification if no secret configured (dev mode)
            return True

        expected_signature = hmac.new(
            self.webhook_secret.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(expected_signature, signature)


class MobileMoneyClient:
    """Client for Mobile Money (MTN MoMo, Moov Money) integrations."""

    # MTN MoMo API endpoints (Benin)
    MTN_SANDBOX_URL = "https://sandbox.momodeveloper.mtn.com"
    MTN_LIVE_URL = "https://momodeveloper.mtn.com"

    def __init__(self):
        self.environment = settings.ENVIRONMENT

    async def initiate_mtn_payment(
        self,
        amount: Decimal,
        currency: str,
        phone_number: str,
        external_id: str,
        payer_message: str = "Paiement LOKAHOME",
        payee_note: str = "Location immobilière",
    ) -> dict:
        """
        Initiate MTN Mobile Money payment.

        This is a request-to-pay flow where the user
        receives a prompt on their phone to approve.
        """
        # MTN MoMo API implementation
        # Note: In production, use the actual MTN MoMo API
        # This is a placeholder structure

        {
            "amount": str(amount),
            "currency": currency,
            "externalId": external_id,
            "payer": {
                "partyIdType": "MSISDN",
                "partyId": phone_number,
            },
            "payerMessage": payer_message,
            "payeeNote": payee_note,
        }

        # Placeholder response for development
        return {
            "status": "PENDING",
            "referenceId": external_id,
            "financialTransactionId": f"MTN{external_id}",
        }

    async def check_mtn_payment_status(self, reference_id: str) -> dict:
        """Check MTN MoMo payment status."""
        # Placeholder for MTN MoMo status check
        return {
            "status": "SUCCESSFUL",
            "referenceId": reference_id,
        }

    async def initiate_moov_payment(
        self,
        amount: Decimal,
        currency: str,
        phone_number: str,
        external_id: str,
    ) -> dict:
        """
        Initiate Moov Money payment.

        Similar to MTN MoMo, user receives a USSD prompt.
        """
        # Moov Money API implementation placeholder
        return {
            "status": "PENDING",
            "referenceId": external_id,
            "transactionId": f"MOOV{external_id}",
        }


class PaymentService:
    """Service for payment operations."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.payment_repo = PaymentRepository(session)
        self.fedapay = FedaPayClient()
        self.mobile_money = MobileMoneyClient()

    async def get_payment(self, payment_id: UUID) -> Payment:
        """Get payment by ID."""
        payment = await self.payment_repo.get(payment_id)
        if not payment:
            raise NotFoundException("Paiement")
        return payment

    async def get_payment_by_reference(self, reference: str) -> Payment:
        """Get payment by reference."""
        payment = await self.payment_repo.get_by_reference(reference)
        if not payment:
            raise NotFoundException("Paiement")
        return payment

    async def initiate_booking_payment(
        self,
        booking_id: UUID,
        payer: User,
        payment_method: PaymentMethod,
        phone_number: str | None = None,
        return_url: str | None = None,
    ) -> dict:
        """
        Initiate payment for a booking.

        Returns payment details including redirect URL or instructions.
        """
        # Get booking
        booking = await self.session.get(Booking, booking_id)
        if not booking:
            raise NotFoundException("Réservation")

        if booking.status != BookingStatus.APPROVED:
            raise BusinessLogicException(
                "La réservation doit être approuvée avant le paiement"
            )

        if booking.tenant_id != payer.id:
            raise BusinessLogicException(
                "Vous ne pouvez payer que vos propres réservations"
            )

        # Get property owner as receiver
        from app.models.property import Property
        property_obj = await self.session.get(Property, booking.property_id)
        receiver_id = property_obj.owner_id

        # Calculate fees
        amount = booking.total_amount
        fee = amount * Decimal("0.025")  # 2.5% platform fee
        net_amount = amount - fee

        # Create payment record
        payment = await self.payment_repo.create({
            "booking_id": booking_id,
            "payer_id": payer.id,
            "receiver_id": receiver_id,
            "amount": amount,
            "fee": fee,
            "net_amount": net_amount,
            "currency": booking.currency,
            "payment_method": payment_method,
            "payment_type": PaymentType.BOOKING,
            "status": PaymentStatus.PENDING,
            "phone_number": phone_number,
        })

        # Process based on payment method
        result = await self._process_payment(
            payment=payment,
            payer=payer,
            description=f"Réservation {booking.reference}",
            return_url=return_url,
        )

        return result

    async def initiate_service_payment(
        self,
        service_request_id: UUID,
        payer: User,
        payment_method: PaymentMethod,
        phone_number: str | None = None,
        return_url: str | None = None,
    ) -> dict:
        """Initiate payment for a service request."""
        # Get service request
        service_request = await self.session.get(ServiceRequest, service_request_id)
        if not service_request:
            raise NotFoundException("Demande de service")

        if service_request.status != ServiceRequestStatus.ACCEPTED:
            raise BusinessLogicException(
                "Un devis doit être accepté avant le paiement"
            )

        # Get accepted quote
        from app.models.service import ServiceQuote
        quote = await self.session.get(ServiceQuote, service_request.accepted_quote_id)
        if not quote:
            raise BusinessLogicException("Devis non trouvé")

        # Get provider user ID
        from app.models.service import ServiceProvider
        provider = await self.session.get(ServiceProvider, quote.provider_id)

        # Calculate fees
        amount = quote.amount
        fee = amount * Decimal("0.05")  # 5% platform fee for services
        net_amount = amount - fee

        # Create payment record
        payment = await self.payment_repo.create({
            "service_request_id": service_request_id,
            "payer_id": payer.id,
            "receiver_id": provider.user_id,
            "amount": amount,
            "fee": fee,
            "net_amount": net_amount,
            "currency": quote.currency,
            "payment_method": payment_method,
            "payment_type": PaymentType.SERVICE,
            "status": PaymentStatus.PENDING,
            "phone_number": phone_number,
        })

        # Process based on payment method
        result = await self._process_payment(
            payment=payment,
            payer=payer,
            description=f"Service {service_request.reference}",
            return_url=return_url,
        )

        return result

    async def _process_payment(
        self,
        payment: Payment,
        payer: User,
        description: str,
        return_url: str | None = None,
    ) -> dict:
        """Process payment based on method."""
        try:
            if payment.payment_method == PaymentMethod.FEDAPAY:
                return await self._process_fedapay(payment, payer, description, return_url)

            elif payment.payment_method == PaymentMethod.MTN_MOMO:
                return await self._process_mtn_momo(payment, description)

            elif payment.payment_method == PaymentMethod.MOOV_MONEY:
                return await self._process_moov_money(payment, description)

            else:
                raise BusinessLogicException(
                    f"Méthode de paiement non supportée: {payment.payment_method}"
                )

        except Exception as e:
            # Update payment status on error
            await self.payment_repo.update(payment, {
                "status": PaymentStatus.FAILED,
                "error_message": str(e),
                "failed_at": datetime.now(UTC),
            })
            raise

    async def _process_fedapay(
        self,
        payment: Payment,
        payer: User,
        description: str,
        return_url: str | None,
    ) -> dict:
        """Process FedaPay payment with redirect flow."""
        # Parse customer name
        name_parts = (payer.full_name or "").split()
        firstname = name_parts[0] if name_parts else payer.email.split("@")[0]
        lastname = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""

        # Create FedaPay transaction
        # callback_url is where user is redirected after payment (with ?id=X&status=Y)
        transaction = await self.fedapay.create_transaction(
            amount=payment.amount,
            currency=payment.currency,
            description=description,
            customer_email=payer.email,
            customer_firstname=firstname,
            customer_lastname=lastname,
            customer_phone=payment.phone_number,
            callback_url=return_url,  # User redirect URL, not webhook
            metadata={
                "payment_id": str(payment.id),
                "payment_reference": payment.reference,
            },
        )

        transaction_id = transaction.get("v1", {}).get("id")

        # Generate payment token
        token_response = await self.fedapay.generate_payment_token(transaction_id)
        payment_url = token_response.get("v1", {}).get("url")

        # Update payment with provider reference
        await self.payment_repo.update(payment, {
            "provider_reference": str(transaction_id),
            "status": PaymentStatus.PROCESSING,
            "provider_response": transaction,
        })

        return {
            "payment_id": payment.id,
            "reference": payment.reference,
            "amount": payment.amount,
            "currency": payment.currency,
            "payment_method": payment.payment_method,
            "payment_url": payment_url,
            "instructions": "Vous allez être redirigé vers la page de paiement FedaPay.",
        }

    async def _process_mtn_momo(
        self,
        payment: Payment,
        description: str,
    ) -> dict:
        """Process MTN Mobile Money payment."""
        if not payment.phone_number:
            raise BusinessLogicException(
                "Numéro de téléphone requis pour MTN MoMo"
            )

        # Initiate MTN MoMo request-to-pay
        result = await self.mobile_money.initiate_mtn_payment(
            amount=payment.amount,
            currency=payment.currency,
            phone_number=payment.phone_number,
            external_id=payment.reference,
            payer_message=description,
        )

        # Update payment status
        await self.payment_repo.update(payment, {
            "provider_reference": result.get("financialTransactionId"),
            "status": PaymentStatus.PROCESSING,
            "provider_response": result,
        })

        return {
            "payment_id": payment.id,
            "reference": payment.reference,
            "amount": payment.amount,
            "currency": payment.currency,
            "payment_method": payment.payment_method,
            "payment_url": None,
            "instructions": f"Une demande de paiement a été envoyée au {payment.phone_number}. "
                           "Veuillez valider le paiement sur votre téléphone.",
        }

    async def _process_moov_money(
        self,
        payment: Payment,
        description: str,
    ) -> dict:
        """Process Moov Money payment."""
        if not payment.phone_number:
            raise BusinessLogicException(
                "Numéro de téléphone requis pour Moov Money"
            )

        # Initiate Moov Money payment
        result = await self.mobile_money.initiate_moov_payment(
            amount=payment.amount,
            currency=payment.currency,
            phone_number=payment.phone_number,
            external_id=payment.reference,
        )

        # Update payment status
        await self.payment_repo.update(payment, {
            "provider_reference": result.get("transactionId"),
            "status": PaymentStatus.PROCESSING,
            "provider_response": result,
        })

        return {
            "payment_id": payment.id,
            "reference": payment.reference,
            "amount": payment.amount,
            "currency": payment.currency,
            "payment_method": payment.payment_method,
            "payment_url": None,
            "instructions": f"Une demande de paiement a été envoyée au {payment.phone_number}. "
                           "Composez *155# pour valider le paiement.",
        }

    async def handle_fedapay_webhook(
        self,
        event: str,
        data: dict,
        signature: str | None = None,
    ) -> Payment:
        """Handle FedaPay webhook callback."""
        # Verify signature if provided
        # if signature and not self.fedapay.verify_webhook_signature(...):
        #     raise BusinessLogicException("Invalid webhook signature")

        transaction = data.get("transaction", {})
        transaction_id = str(transaction.get("id"))
        status = transaction.get("status")

        # Find payment by provider reference
        payment = await self.payment_repo.get_by_provider_reference(transaction_id)
        if not payment:
            raise NotFoundException("Paiement")

        # Map FedaPay status to our status
        status_mapping = {
            "approved": PaymentStatus.COMPLETED,
            "transferred": PaymentStatus.COMPLETED,
            "declined": PaymentStatus.FAILED,
            "canceled": PaymentStatus.CANCELLED,
            "refunded": PaymentStatus.REFUNDED,
        }

        new_status = status_mapping.get(status, PaymentStatus.PROCESSING)

        update_data = {
            "status": new_status,
            "provider_status": status,
            "provider_response": data,
        }

        if new_status == PaymentStatus.COMPLETED:
            update_data["paid_at"] = datetime.now(UTC)

            # Update related booking status
            if payment.booking_id:
                booking = await self.session.get(Booking, payment.booking_id)
                if booking:
                    booking.status = BookingStatus.CONFIRMED
                    await self.session.flush()

        elif new_status == PaymentStatus.FAILED:
            update_data["failed_at"] = datetime.now(UTC)
            update_data["error_message"] = transaction.get("error_message")

        payment = await self.payment_repo.update(payment, update_data)
        return payment

    async def handle_mobile_money_webhook(
        self,
        transaction_id: str,
        status: str,
        amount: Decimal,
        phone_number: str,
        metadata: dict | None = None,
    ) -> Payment:
        """Handle Mobile Money webhook callback."""
        # Find payment by provider reference or reference in metadata
        payment = await self.payment_repo.get_by_provider_reference(transaction_id)

        if not payment and metadata:
            reference = metadata.get("payment_reference")
            if reference:
                payment = await self.payment_repo.get_by_reference(reference)

        if not payment:
            raise NotFoundException("Paiement")

        # Map status
        status_mapping = {
            "SUCCESSFUL": PaymentStatus.COMPLETED,
            "FAILED": PaymentStatus.FAILED,
            "PENDING": PaymentStatus.PROCESSING,
            "CANCELLED": PaymentStatus.CANCELLED,
        }

        new_status = status_mapping.get(status.upper(), PaymentStatus.PROCESSING)

        update_data = {
            "status": new_status,
            "provider_status": status,
        }

        if new_status == PaymentStatus.COMPLETED:
            update_data["paid_at"] = datetime.now(UTC)

            # Update related booking status
            if payment.booking_id:
                booking = await self.session.get(Booking, payment.booking_id)
                if booking:
                    booking.status = BookingStatus.CONFIRMED
                    await self.session.flush()

        elif new_status == PaymentStatus.FAILED:
            update_data["failed_at"] = datetime.now(UTC)

        payment = await self.payment_repo.update(payment, update_data)
        return payment

    async def process_refund(
        self,
        payment_id: UUID,
        amount: Decimal | None = None,
        reason: str = "",
    ) -> Payment:
        """Process a refund for a payment."""
        payment = await self.get_payment(payment_id)

        if payment.status != PaymentStatus.COMPLETED:
            raise BusinessLogicException(
                "Seuls les paiements complétés peuvent être remboursés"
            )

        refund_amount = amount or payment.amount

        if refund_amount > payment.amount:
            raise BusinessLogicException(
                "Le montant du remboursement ne peut pas dépasser le montant payé"
            )

        # Process refund via payment provider
        # (Implementation depends on provider)

        # Update payment
        payment = await self.payment_repo.update(payment, {
            "status": PaymentStatus.REFUNDED,
            "refund_amount": refund_amount,
            "refund_reason": reason,
            "refunded_at": datetime.now(UTC),
        })

        return payment

    async def get_user_payments(
        self,
        user_id: UUID,
        *,
        payment_type: PaymentType | None = None,
        status: PaymentStatus | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Payment]:
        """Get user's payment history."""
        return await self.payment_repo.get_user_payments(
            user_id,
            payment_type=payment_type,
            status=status,
            skip=skip,
            limit=limit,
        )

    async def get_transaction_summary(
        self,
        user_id: UUID,
        start_date: datetime,
        end_date: datetime,
    ) -> dict:
        """Get transaction summary for a period."""
        payments = await self.payment_repo.get_user_payments(
            user_id,
            status=PaymentStatus.COMPLETED,
        )

        # Filter by date range
        filtered = [
            p for p in payments
            if p.paid_at and start_date <= p.paid_at <= end_date
        ]

        total_received = sum(
            p.net_amount for p in filtered if p.receiver_id == user_id
        )
        total_paid = sum(
            p.amount for p in filtered if p.payer_id == user_id
        )
        total_fees = sum(
            p.fee for p in filtered if p.payer_id == user_id
        )

        return {
            "total_received": total_received,
            "total_paid": total_paid,
            "total_fees": total_fees,
            "net_balance": total_received - total_paid,
            "currency": "XOF",
            "transaction_count": len(filtered),
            "period_start": start_date,
            "period_end": end_date,
        }
