"""
Email tasks for asynchronous email sending.
"""
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from celery import shared_task

from app.core.config import settings


def get_smtp_connection():
    """Create SMTP connection."""
    if settings.MAIL_SSL_TLS:
        server = smtplib.SMTP_SSL(settings.MAIL_SERVER, settings.MAIL_PORT)
    else:
        server = smtplib.SMTP(settings.MAIL_SERVER, settings.MAIL_PORT)
        if settings.MAIL_STARTTLS:
            server.starttls()

    if settings.MAIL_USERNAME and settings.MAIL_PASSWORD:
        server.login(settings.MAIL_USERNAME, settings.MAIL_PASSWORD)

    return server


def send_email_sync(
    to_email: str,
    subject: str,
    html_content: str,
    text_content: str | None = None,
) -> bool:
    """Send email synchronously."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{settings.MAIL_FROM_NAME} <{settings.MAIL_FROM}>"
    msg["To"] = to_email

    # Add text version
    if text_content:
        msg.attach(MIMEText(text_content, "plain"))

    # Add HTML version
    msg.attach(MIMEText(html_content, "html"))

    try:
        server = get_smtp_connection()
        server.sendmail(settings.MAIL_FROM, to_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"Email send error: {e}")
        return False


# === Email Templates ===

def get_welcome_email(user_name: str, verification_url: str) -> tuple[str, str]:
    """Get welcome email content."""
    subject = f"Bienvenue sur {settings.APP_NAME}!"

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background-color: #2563eb; color: white; padding: 20px; text-align: center; }}
            .content {{ padding: 20px; background-color: #f9fafb; }}
            .button {{ display: inline-block; padding: 12px 24px; background-color: #2563eb; color: white; text-decoration: none; border-radius: 6px; }}
            .footer {{ padding: 20px; text-align: center; font-size: 12px; color: #666; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>{settings.APP_NAME}</h1>
            </div>
            <div class="content">
                <h2>Bienvenue {user_name}!</h2>
                <p>Merci de vous être inscrit sur {settings.APP_NAME}, la plateforme de location immobilière au Bénin.</p>
                <p>Pour activer votre compte, veuillez cliquer sur le bouton ci-dessous :</p>
                <p style="text-align: center;">
                    <a href="{verification_url}" class="button">Vérifier mon email</a>
                </p>
                <p>Ce lien expire dans 24 heures.</p>
                <p>Si vous n'avez pas créé de compte, ignorez cet email.</p>
            </div>
            <div class="footer">
                <p>&copy; {settings.APP_NAME} - Tous droits réservés</p>
            </div>
        </div>
    </body>
    </html>
    """

    text = f"""
    Bienvenue sur {settings.APP_NAME}!

    Bonjour {user_name},

    Merci de vous être inscrit sur {settings.APP_NAME}.

    Pour activer votre compte, cliquez sur ce lien : {verification_url}

    Ce lien expire dans 24 heures.

    Si vous n'avez pas créé de compte, ignorez cet email.

    {settings.APP_NAME}
    """

    return subject, html, text


def get_password_reset_email(user_name: str, reset_url: str) -> tuple[str, str, str]:
    """Get password reset email content."""
    subject = f"Réinitialisation de mot de passe - {settings.APP_NAME}"

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background-color: #2563eb; color: white; padding: 20px; text-align: center; }}
            .content {{ padding: 20px; background-color: #f9fafb; }}
            .button {{ display: inline-block; padding: 12px 24px; background-color: #dc2626; color: white; text-decoration: none; border-radius: 6px; }}
            .footer {{ padding: 20px; text-align: center; font-size: 12px; color: #666; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>{settings.APP_NAME}</h1>
            </div>
            <div class="content">
                <h2>Réinitialisation de mot de passe</h2>
                <p>Bonjour {user_name},</p>
                <p>Vous avez demandé la réinitialisation de votre mot de passe.</p>
                <p>Cliquez sur le bouton ci-dessous pour créer un nouveau mot de passe :</p>
                <p style="text-align: center;">
                    <a href="{reset_url}" class="button">Réinitialiser mon mot de passe</a>
                </p>
                <p>Ce lien expire dans 1 heure.</p>
                <p>Si vous n'avez pas fait cette demande, ignorez cet email.</p>
            </div>
            <div class="footer">
                <p>&copy; {settings.APP_NAME} - Tous droits réservés</p>
            </div>
        </div>
    </body>
    </html>
    """

    text = f"""
    Réinitialisation de mot de passe

    Bonjour {user_name},

    Vous avez demandé la réinitialisation de votre mot de passe.

    Cliquez sur ce lien : {reset_url}

    Ce lien expire dans 1 heure.

    Si vous n'avez pas fait cette demande, ignorez cet email.

    {settings.APP_NAME}
    """

    return subject, html, text


def get_booking_confirmation_email(
    user_name: str,
    property_title: str,
    check_in: str,
    check_out: str,
    total_amount: str,
    reference: str,
) -> tuple[str, str, str]:
    """Get booking confirmation email content."""
    subject = f"Confirmation de réservation #{reference} - {settings.APP_NAME}"

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background-color: #16a34a; color: white; padding: 20px; text-align: center; }}
            .content {{ padding: 20px; background-color: #f9fafb; }}
            .details {{ background-color: white; padding: 15px; border-radius: 8px; margin: 15px 0; }}
            .footer {{ padding: 20px; text-align: center; font-size: 12px; color: #666; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Réservation Confirmée!</h1>
            </div>
            <div class="content">
                <p>Bonjour {user_name},</p>
                <p>Votre réservation a été confirmée avec succès!</p>
                <div class="details">
                    <h3>{property_title}</h3>
                    <p><strong>Référence:</strong> {reference}</p>
                    <p><strong>Arrivée:</strong> {check_in}</p>
                    <p><strong>Départ:</strong> {check_out}</p>
                    <p><strong>Montant total:</strong> {total_amount}</p>
                </div>
                <p>Vous recevrez les détails de contact du propriétaire par message.</p>
            </div>
            <div class="footer">
                <p>&copy; {settings.APP_NAME} - Tous droits réservés</p>
            </div>
        </div>
    </body>
    </html>
    """

    text = f"""
    Réservation Confirmée!

    Bonjour {user_name},

    Votre réservation a été confirmée!

    Détails:
    - Bien: {property_title}
    - Référence: {reference}
    - Arrivée: {check_in}
    - Départ: {check_out}
    - Montant: {total_amount}

    {settings.APP_NAME}
    """

    return subject, html, text


# === Celery Tasks ===

@shared_task(bind=True, max_retries=3)
def send_welcome_email(self, to_email: str, user_name: str, verification_url: str):
    """Send welcome email to new user."""
    try:
        subject, html, text = get_welcome_email(user_name, verification_url)
        success = send_email_sync(to_email, subject, html, text)
        if not success:
            raise Exception("Email send failed")
        return {"status": "sent", "to": to_email}
    except Exception as e:
        self.retry(exc=e, countdown=60 * (self.request.retries + 1))


@shared_task(bind=True, max_retries=3)
def send_password_reset_email(self, to_email: str, user_name: str, reset_url: str):
    """Send password reset email."""
    try:
        subject, html, text = get_password_reset_email(user_name, reset_url)
        success = send_email_sync(to_email, subject, html, text)
        if not success:
            raise Exception("Email send failed")
        return {"status": "sent", "to": to_email}
    except Exception as e:
        self.retry(exc=e, countdown=60 * (self.request.retries + 1))


@shared_task(bind=True, max_retries=3)
def send_booking_confirmation_email(
    self,
    to_email: str,
    user_name: str,
    property_title: str,
    check_in: str,
    check_out: str,
    total_amount: str,
    reference: str,
):
    """Send booking confirmation email."""
    try:
        subject, html, text = get_booking_confirmation_email(
            user_name, property_title, check_in, check_out, total_amount, reference
        )
        success = send_email_sync(to_email, subject, html, text)
        if not success:
            raise Exception("Email send failed")
        return {"status": "sent", "to": to_email}
    except Exception as e:
        self.retry(exc=e, countdown=60 * (self.request.retries + 1))


@shared_task(bind=True, max_retries=3)
def send_generic_email(
    self,
    to_email: str,
    subject: str,
    html_content: str,
    text_content: str | None = None,
):
    """Send a generic email."""
    try:
        success = send_email_sync(to_email, subject, html_content, text_content)
        if not success:
            raise Exception("Email send failed")
        return {"status": "sent", "to": to_email}
    except Exception as e:
        self.retry(exc=e, countdown=60 * (self.request.retries + 1))
