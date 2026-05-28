"""
Contract service for digital rental agreement management.
"""
import os
import random
from datetime import datetime, timedelta, timezone
from uuid import UUID

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import (
    BusinessLogicException,
    InsufficientPermissionsException,
    NotFoundException,
)
from app.models.booking import Booking, BookingStatus
from app.models.contract import Contract, ContractStatus, ContractType
from app.models.property import PropertyType
from app.models.user import User, UserRole
from app.repositories.booking import BookingRepository
from app.repositories.contract import ContractRepository
from app.utils.contract_pdf import compute_pdf_hash, generate_contract_pdf


class ContractService:
    """Service for contract operations."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.contract_repo = ContractRepository(session)
        self.booking_repo = BookingRepository(session)

    def _determine_contract_type(self, booking: Booking) -> ContractType:
        """Determine contract type based on booking duration and property type."""
        duration = (booking.check_out - booking.check_in).days

        prop = booking.booked_property
        if prop and prop.property_type in (PropertyType.ROOM, PropertyType.STUDIO):
            if duration < 30:
                return ContractType.SHORT_TERM
            return ContractType.FURNISHED

        if duration < 30:
            return ContractType.SHORT_TERM
        return ContractType.LONG_TERM

    def _get_upload_dir(self) -> str:
        """Get contract upload directory, creating it if needed."""
        upload_dir = getattr(settings, "CONTRACT_UPLOAD_DIR", "static/uploads/contracts")
        os.makedirs(upload_dir, exist_ok=True)
        return upload_dir

    async def generate_contract(self, booking_id: UUID) -> Contract:
        """Generate a contract for a confirmed booking."""
        # Check if contract already exists
        existing = await self.contract_repo.get_by_booking(booking_id)
        if existing:
            logger.info(f"Contract already exists for booking {booking_id}")
            return existing

        # Load booking with details
        booking = await self.booking_repo.get_with_details(booking_id)
        if not booking:
            raise NotFoundException("Réservation")

        if booking.status not in (
            BookingStatus.APPROVED,
            BookingStatus.CONFIRMED,
            BookingStatus.ACTIVE,
        ):
            raise BusinessLogicException(
                "La réservation doit être approuvée pour générer un contrat"
            )

        prop = booking.booked_property
        owner = prop.owner
        tenant = booking.tenant

        contract_type = self._determine_contract_type(booking)
        upload_dir = self._get_upload_dir()

        # Generate draft PDF
        pdf_bytes = generate_contract_pdf(
            reference="DRAFT",  # Will be updated after contract creation
            contract_type=contract_type.value,
            landlord_name=f"{owner.first_name} {owner.last_name}",
            landlord_email=owner.email,
            landlord_phone=owner.phone,
            tenant_name=f"{tenant.first_name} {tenant.last_name}",
            tenant_email=tenant.email,
            tenant_phone=tenant.phone,
            property_title=prop.title,
            property_type=prop.property_type.value,
            property_address=prop.address or "",
            property_city=prop.city or "",
            property_description=prop.description,
            surface_area=float(prop.surface_area) if prop.surface_area else None,
            bedrooms=prop.bedrooms,
            bathrooms=prop.bathrooms,
            check_in=booking.check_in,
            check_out=booking.check_out,
            duration_days=booking.duration_days,
            base_price=booking.base_price,
            service_fee=booking.service_fee,
            deposit_amount=booking.deposit_amount,
            total_amount=booking.total_amount,
            currency=booking.currency,
        )

        # Create contract record first to get the reference
        expiry_hours = getattr(settings, "CONTRACT_EXPIRY_HOURS", 72)
        contract_data = {
            "booking_id": booking_id,
            "contract_type": contract_type,
            "status": ContractStatus.PENDING_LANDLORD,
            "expires_at": datetime.now(timezone.utc) + timedelta(hours=expiry_hours),
            "audit_log": [
                {
                    "action": "contract_generated",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "details": f"Contract generated for booking {booking.reference}",
                }
            ],
        }
        contract = await self.contract_repo.create(contract_data)

        # Now regenerate PDF with actual reference
        pdf_bytes = generate_contract_pdf(
            reference=contract.reference,
            contract_type=contract_type.value,
            landlord_name=f"{owner.first_name} {owner.last_name}",
            landlord_email=owner.email,
            landlord_phone=owner.phone,
            tenant_name=f"{tenant.first_name} {tenant.last_name}",
            tenant_email=tenant.email,
            tenant_phone=tenant.phone,
            property_title=prop.title,
            property_type=prop.property_type.value,
            property_address=prop.address or "",
            property_city=prop.city or "",
            property_description=prop.description,
            surface_area=float(prop.surface_area) if prop.surface_area else None,
            bedrooms=prop.bedrooms,
            bathrooms=prop.bathrooms,
            check_in=booking.check_in,
            check_out=booking.check_out,
            duration_days=booking.duration_days,
            base_price=booking.base_price,
            service_fee=booking.service_fee,
            deposit_amount=booking.deposit_amount,
            total_amount=booking.total_amount,
            currency=booking.currency,
        )

        # Save draft PDF
        draft_filename = f"{contract.reference}_draft.pdf"
        draft_path = os.path.join(upload_dir, draft_filename)
        with open(draft_path, "wb") as f:
            f.write(pdf_bytes)

        draft_url = f"/static/uploads/contracts/{draft_filename}"
        await self.contract_repo.update(contract, {"draft_url": draft_url})

        # Reload with details
        contract = await self.contract_repo.get_with_details(contract.id)
        logger.info(f"Contract {contract.reference} generated for booking {booking.reference}")
        return contract

    async def get_contract(self, contract_id: UUID, user: User) -> Contract:
        """Get a contract by ID, checking access."""
        contract = await self.contract_repo.get_with_details(contract_id)
        if not contract:
            raise NotFoundException("Contrat")
        self._check_access(contract, user)
        return contract

    async def get_contract_by_booking(self, booking_id: UUID, user: User) -> Contract:
        """Get contract for a booking."""
        contract = await self.contract_repo.get_by_booking(booking_id)
        if not contract:
            raise NotFoundException("Contrat")
        self._check_access(contract, user)
        return contract

    async def get_user_contracts(
        self, user: User, status: ContractStatus | None = None
    ) -> list[Contract]:
        """Get all contracts for a user."""
        return await self.contract_repo.get_user_contracts(
            user.id, status=status
        )

    async def get_pending_contracts(self, user: User) -> list[Contract]:
        """Get contracts pending user's signature."""
        return await self.contract_repo.get_pending_for_user(user.id)

    async def request_verification_code(
        self, contract_id: UUID, user: User, ip: str
    ) -> dict:
        """Generate and send verification code for signing."""
        contract = await self.contract_repo.get_with_details(contract_id)
        if not contract:
            raise NotFoundException("Contrat")

        self._check_can_sign(contract, user)

        # Generate 6-digit code
        code = "".join([str(random.randint(0, 9)) for _ in range(6)])

        booking = contract.booking
        prop = booking.booked_property
        is_landlord = prop.owner_id == user.id

        # Store code
        if is_landlord:
            await self.contract_repo.update(contract, {
                "landlord_verification_code": code,
            })
        else:
            await self.contract_repo.update(contract, {
                "tenant_verification_code": code,
            })

        # Send code by email directly (synchronous SMTP, no Celery dependency)
        method = "email"
        try:
            from app.tasks.email import send_email_sync
            success = send_email_sync(
                to_email=user.email,
                subject="Code de vérification - Signature de contrat",
                html_content=(
                    f"<h2>Code de vérification</h2>"
                    f"<p>Bonjour {user.first_name or ''},</p>"
                    f"<p>Votre code pour signer le contrat <strong>{contract.reference}</strong> est :</p>"
                    f"<h1 style='text-align:center;color:#1E40AF;letter-spacing:8px;'>{code}</h1>"
                    f"<p>Ce code est valable pendant 10 minutes.</p>"
                    f"<p>Si vous n'avez pas demandé ce code, ignorez ce message.</p>"
                ),
            )
            if not success:
                raise BusinessLogicException(
                    "Impossible d'envoyer le code par email. Vérifiez votre adresse email."
                )
        except BusinessLogicException:
            raise
        except Exception as e:
            logger.error(f"Email sending failed for verification code: {e}")
            raise BusinessLogicException(
                "Impossible d'envoyer le code de vérification. Réessayez plus tard."
            )

        # Audit
        audit_entry = {
            "action": "verification_code_sent",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": str(user.id),
            "method": method,
            "ip": ip,
        }
        audit_log = contract.audit_log or []
        audit_log.append(audit_entry)
        await self.contract_repo.update(contract, {"audit_log": audit_log})

        return {
            "method": method,
            "message": f"Code envoyé par {method} à {'votre téléphone' if method == 'sms' else 'votre email'}",
        }

    async def verify_code(
        self, contract_id: UUID, user: User, code: str
    ) -> bool:
        """Verify the OTP code for signing."""
        contract = await self.contract_repo.get_with_details(contract_id)
        if not contract:
            raise NotFoundException("Contrat")

        self._check_can_sign(contract, user)

        booking = contract.booking
        prop = booking.booked_property
        is_landlord = prop.owner_id == user.id

        stored_code = (
            contract.landlord_verification_code
            if is_landlord
            else contract.tenant_verification_code
        )

        if not stored_code or stored_code != code:
            raise BusinessLogicException("Code de vérification invalide")

        now = datetime.now(timezone.utc)
        if is_landlord:
            await self.contract_repo.update(contract, {
                "landlord_verified_at": now,
            })
        else:
            await self.contract_repo.update(contract, {
                "tenant_verified_at": now,
            })

        return True

    async def sign_contract(
        self,
        contract_id: UUID,
        user: User,
        signature_data: str,
        ip: str,
        user_agent: str,
    ) -> Contract:
        """Sign the contract with a digital signature."""
        contract = await self.contract_repo.get_with_details(contract_id)
        if not contract:
            raise NotFoundException("Contrat")

        self._check_can_sign(contract, user)

        booking = contract.booking
        prop = booking.booked_property
        owner = prop.owner
        tenant = booking.tenant
        is_landlord = prop.owner_id == user.id

        # Check code was verified
        if is_landlord and not contract.landlord_verified_at:
            raise BusinessLogicException(
                "Vous devez vérifier votre code avant de signer"
            )
        if not is_landlord and not contract.tenant_verified_at:
            raise BusinessLogicException(
                "Vous devez vérifier votre code avant de signer"
            )

        now = datetime.now(timezone.utc)
        audit_log = contract.audit_log or []

        if is_landlord:
            # Landlord signs first
            update_data = {
                "landlord_signature_data": signature_data,
                "landlord_signed_at": now,
                "landlord_ip_address": ip,
                "landlord_user_agent": user_agent[:500],
                "status": ContractStatus.PENDING_TENANT,
            }
            audit_log.append({
                "action": "landlord_signed",
                "timestamp": now.isoformat(),
                "user_id": str(user.id),
                "ip": ip,
            })
            update_data["audit_log"] = audit_log
            await self.contract_repo.update(contract, update_data)

            # Notify tenant
            try:
                from app.tasks.notifications import send_push_notification
                send_push_notification.delay(
                    str(tenant.id),
                    "Contrat à signer",
                    f"Le bailleur a signé le contrat {contract.reference}. "
                    "C'est à votre tour de le signer.",
                    {"type": "signature_needed", "contract_id": str(contract.id)},
                )
            except Exception:
                logger.warning("Failed to send signature notification to tenant")

        else:
            # Tenant signs second → contract fully signed
            update_data = {
                "tenant_signature_data": signature_data,
                "tenant_signed_at": now,
                "tenant_ip_address": ip,
                "tenant_user_agent": user_agent[:500],
                "status": ContractStatus.FULLY_SIGNED,
                "is_locked": True,
            }

            # Generate final PDF with both signatures
            upload_dir = self._get_upload_dir()
            pdf_bytes = generate_contract_pdf(
                reference=contract.reference,
                contract_type=contract.contract_type.value,
                landlord_name=f"{owner.first_name} {owner.last_name}",
                landlord_email=owner.email,
                landlord_phone=owner.phone,
                tenant_name=f"{tenant.first_name} {tenant.last_name}",
                tenant_email=tenant.email,
                tenant_phone=tenant.phone,
                property_title=prop.title,
                property_type=prop.property_type.value,
                property_address=prop.address or "",
                property_city=prop.city or "",
                property_description=prop.description,
                surface_area=float(prop.surface_area) if prop.surface_area else None,
                bedrooms=prop.bedrooms,
                bathrooms=prop.bathrooms,
                check_in=booking.check_in,
                check_out=booking.check_out,
                duration_days=booking.duration_days,
                base_price=booking.base_price,
                service_fee=booking.service_fee,
                deposit_amount=booking.deposit_amount,
                total_amount=booking.total_amount,
                currency=booking.currency,
                landlord_signature=contract.landlord_signature_data,
                landlord_signed_at=contract.landlord_signed_at,
                tenant_signature=signature_data,
                tenant_signed_at=now,
            )

            # Compute hash
            doc_hash = compute_pdf_hash(pdf_bytes)
            update_data["document_hash"] = doc_hash

            # Save signed PDF
            signed_filename = f"{contract.reference}_signed.pdf"
            signed_path = os.path.join(upload_dir, signed_filename)
            with open(signed_path, "wb") as f:
                f.write(pdf_bytes)

            signed_url = f"/static/uploads/contracts/{signed_filename}"
            update_data["signed_url"] = signed_url

            audit_log.append({
                "action": "tenant_signed",
                "timestamp": now.isoformat(),
                "user_id": str(user.id),
                "ip": ip,
            })
            audit_log.append({
                "action": "contract_fully_signed",
                "timestamp": now.isoformat(),
                "document_hash": doc_hash,
            })
            update_data["audit_log"] = audit_log

            await self.contract_repo.update(contract, update_data)

            # Update booking with contract info
            await self.booking_repo.update(booking, {
                "contract_url": signed_url,
                "contract_signed_at": now.date(),
            })

            # Send signed PDF by email to both parties
            try:
                from app.tasks.contracts import send_signed_contract_to_both
                send_signed_contract_to_both.delay(
                    owner.email,
                    f"{owner.first_name} {owner.last_name}",
                    tenant.email,
                    f"{tenant.first_name} {tenant.last_name}",
                    contract.reference,
                    prop.title,
                    signed_path,
                )
            except Exception:
                logger.error("Failed to queue signed contract emails")

            # Notify both parties
            try:
                from app.tasks.notifications import send_push_notification
                for uid in [str(owner.id), str(tenant.id)]:
                    send_push_notification.delay(
                        uid,
                        "Contrat signé",
                        f"Le contrat {contract.reference} est maintenant "
                        "entièrement signé par les deux parties.",
                        {"type": "contract_signed", "contract_id": str(contract.id)},
                    )
            except Exception:
                logger.warning("Failed to send contract signed notifications")

        # Reload contract
        contract = await self.contract_repo.get_with_details(contract.id)
        return contract

    def _check_access(self, contract: Contract, user: User):
        """Check that user has access to this contract."""
        if user.role == UserRole.ADMIN:
            return

        booking = contract.booking
        prop = booking.booked_property
        if booking.tenant_id != user.id and prop.owner_id != user.id:
            raise InsufficientPermissionsException()

    def _check_can_sign(self, contract: Contract, user: User):
        """Check that user can sign this contract."""
        if contract.is_locked:
            raise BusinessLogicException("Ce contrat est déjà verrouillé")

        if contract.status == ContractStatus.FULLY_SIGNED:
            raise BusinessLogicException("Ce contrat est déjà entièrement signé")

        if contract.status in (ContractStatus.EXPIRED, ContractStatus.CANCELLED):
            raise BusinessLogicException("Ce contrat n'est plus valide")

        # Check expiry
        if contract.expires_at and datetime.now(timezone.utc) > contract.expires_at:
            raise BusinessLogicException("Ce contrat a expiré")

        booking = contract.booking
        prop = booking.booked_property
        is_landlord = prop.owner_id == user.id
        is_tenant = booking.tenant_id == user.id

        if not is_landlord and not is_tenant:
            raise InsufficientPermissionsException()

        if contract.status == ContractStatus.PENDING_LANDLORD and not is_landlord:
            raise BusinessLogicException(
                "C'est au bailleur de signer en premier"
            )

        if contract.status == ContractStatus.PENDING_TENANT and not is_tenant:
            raise BusinessLogicException(
                "C'est au locataire de signer maintenant"
            )
