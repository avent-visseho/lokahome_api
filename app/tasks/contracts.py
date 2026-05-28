"""
Celery tasks for contract generation and email delivery.
"""
import logging

from celery import shared_task

from app.core.config import settings
from app.tasks.email import send_email_with_attachment_sync

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def generate_contract_task(self, booking_id: str):
    """Generate contract asynchronously after booking confirmation."""
    import asyncio

    from app.core.database import async_session_factory
    from app.services.contract import ContractService

    async def _generate():
        async with async_session_factory() as session:
            service = ContractService(session)
            contract = await service.generate_contract(booking_id)
            await session.commit()
            return str(contract.reference)

    try:
        ref = asyncio.run(_generate())
        logger.info(f"Contract {ref} generated for booking {booking_id}")
        return {"status": "generated", "reference": ref}
    except Exception as e:
        logger.error(f"Contract generation failed for booking {booking_id}: {e}")
        self.retry(exc=e, countdown=60 * (self.request.retries + 1))


@shared_task(bind=True, max_retries=3)
def send_contract_email(
    self,
    to_email: str,
    user_name: str,
    contract_ref: str,
    property_title: str,
    pdf_path: str,
):
    """Send contract PDF to a party via email."""
    subject = f"Contrat de location {contract_ref} - {settings.APP_NAME}"

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background-color: #1E40AF; color: white; padding: 20px; text-align: center; }}
            .content {{ padding: 20px; background-color: #f9fafb; }}
            .footer {{ padding: 20px; text-align: center; font-size: 12px; color: #666; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Contrat de Location</h1>
            </div>
            <div class="content">
                <p>Bonjour {user_name},</p>
                <p>Veuillez trouver ci-joint le contrat de location signé pour le bien :</p>
                <p><strong>{property_title}</strong></p>
                <p>Référence du contrat : <strong>{contract_ref}</strong></p>
                <p>Ce document est archivé et accessible à tout moment depuis votre espace FIFALOGE.</p>
            </div>
            <div class="footer">
                <p>&copy; {settings.APP_NAME} - Tous droits réservés</p>
            </div>
        </div>
    </body>
    </html>
    """

    try:
        success = send_email_with_attachment_sync(
            to_email=to_email,
            subject=subject,
            html_content=html,
            attachment_path=pdf_path,
            attachment_filename=f"{contract_ref}_signed.pdf",
        )
        if not success:
            raise Exception("Email send failed")
        return {"status": "sent", "to": to_email}
    except Exception as e:
        self.retry(exc=e, countdown=60 * (self.request.retries + 1))


@shared_task(bind=True, max_retries=3)
def send_signed_contract_to_both(
    self,
    landlord_email: str,
    landlord_name: str,
    tenant_email: str,
    tenant_name: str,
    contract_ref: str,
    property_title: str,
    pdf_path: str,
):
    """Send the signed contract PDF to both landlord and tenant."""
    try:
        # Send to landlord
        send_contract_email.delay(
            landlord_email, landlord_name, contract_ref, property_title, pdf_path
        )
        # Send to tenant
        send_contract_email.delay(
            tenant_email, tenant_name, contract_ref, property_title, pdf_path
        )
        return {"status": "queued", "recipients": [landlord_email, tenant_email]}
    except Exception as e:
        self.retry(exc=e, countdown=60 * (self.request.retries + 1))


@shared_task
def expire_pending_contracts():
    """Mark expired contracts. Run periodically via Celery Beat."""
    import asyncio

    from app.core.database import async_session_factory
    from app.models.contract import ContractStatus
    from app.repositories.contract import ContractRepository

    async def _expire():
        async with async_session_factory() as session:
            repo = ContractRepository(session)
            expired = await repo.get_expired_contracts()
            count = 0
            for contract in expired:
                await repo.update(contract, {"status": ContractStatus.EXPIRED})
                count += 1
            await session.commit()
            return count

    count = asyncio.run(_expire())
    logger.info(f"Expired {count} pending contracts")
    return {"expired_count": count}
