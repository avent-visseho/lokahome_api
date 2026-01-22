"""
Notification tasks for push notifications and SMS.
"""

from celery import shared_task

from app.core.config import settings

# === Firebase Push Notifications ===

def get_firebase_app():
    """Get Firebase Admin app instance."""
    try:
        import firebase_admin
        from firebase_admin import credentials

        if not firebase_admin._apps:
            if settings.FIREBASE_CREDENTIALS_PATH:
                cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
                firebase_admin.initialize_app(cred)
            else:
                return None
        return firebase_admin.get_app()
    except Exception as e:
        print(f"Firebase init error: {e}")
        return None


def send_fcm_notification(
    fcm_token: str,
    title: str,
    body: str,
    data: dict | None = None,
) -> bool:
    """Send FCM push notification."""
    try:
        from firebase_admin import messaging

        app = get_firebase_app()
        if not app:
            print("Firebase not configured")
            return False

        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            data={k: str(v) for k, v in (data or {}).items()},
            token=fcm_token,
            android=messaging.AndroidConfig(
                priority="high",
                notification=messaging.AndroidNotification(
                    icon="notification_icon",
                    color="#2563eb",
                ),
            ),
            apns=messaging.APNSConfig(
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(
                        badge=1,
                        sound="default",
                    ),
                ),
            ),
        )

        response = messaging.send(message)
        print(f"FCM sent: {response}")
        return True

    except Exception as e:
        print(f"FCM error: {e}")
        return False


def send_fcm_to_topic(
    topic: str,
    title: str,
    body: str,
    data: dict | None = None,
) -> bool:
    """Send FCM notification to a topic."""
    try:
        from firebase_admin import messaging

        app = get_firebase_app()
        if not app:
            return False

        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            data={k: str(v) for k, v in (data or {}).items()},
            topic=topic,
        )

        response = messaging.send(message)
        print(f"FCM topic sent: {response}")
        return True

    except Exception as e:
        print(f"FCM topic error: {e}")
        return False


# === Twilio SMS ===

def send_twilio_sms(to_phone: str, message: str) -> bool:
    """Send SMS via Twilio."""
    try:
        from twilio.rest import Client

        if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
            print("Twilio not configured")
            return False

        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

        # Format phone number
        if not to_phone.startswith("+"):
            to_phone = f"+229{to_phone}"  # Benin country code

        sms = client.messages.create(
            body=message,
            from_=settings.TWILIO_PHONE_NUMBER,
            to=to_phone,
        )

        print(f"SMS sent: {sms.sid}")
        return True

    except Exception as e:
        print(f"Twilio error: {e}")
        return False


# === Celery Tasks ===

@shared_task(bind=True, max_retries=3)
def send_push_notification(
    self,
    fcm_token: str,
    title: str,
    body: str,
    data: dict | None = None,
):
    """Send push notification to a single device."""
    try:
        success = send_fcm_notification(fcm_token, title, body, data)
        if not success:
            raise Exception("Push notification failed")
        return {"status": "sent", "token": fcm_token[:20] + "..."}
    except Exception as e:
        self.retry(exc=e, countdown=30 * (self.request.retries + 1))


@shared_task(bind=True, max_retries=3)
def send_push_to_topic(
    self,
    topic: str,
    title: str,
    body: str,
    data: dict | None = None,
):
    """Send push notification to a topic."""
    try:
        success = send_fcm_to_topic(topic, title, body, data)
        if not success:
            raise Exception("Topic notification failed")
        return {"status": "sent", "topic": topic}
    except Exception as e:
        self.retry(exc=e, countdown=30 * (self.request.retries + 1))


@shared_task(bind=True, max_retries=3)
def send_sms(self, to_phone: str, message: str):
    """Send SMS message."""
    try:
        success = send_twilio_sms(to_phone, message)
        if not success:
            raise Exception("SMS send failed")
        return {"status": "sent", "to": to_phone}
    except Exception as e:
        self.retry(exc=e, countdown=60 * (self.request.retries + 1))


@shared_task
def send_booking_reminders():
    """
    Send reminders for upcoming bookings.
    Called daily by Celery beat.
    """
    # This would query upcoming bookings and send reminders
    # Implementation requires database access in task
    print("Sending booking reminders...")
    return {"status": "completed"}


@shared_task
def notify_new_booking(
    landlord_fcm_token: str | None,
    landlord_email: str,
    landlord_name: str,
    property_title: str,
    tenant_name: str,
    check_in: str,
    check_out: str,
    booking_reference: str,
):
    """Notify landlord of new booking request."""
    # Push notification
    if landlord_fcm_token:
        send_push_notification.delay(
            fcm_token=landlord_fcm_token,
            title="Nouvelle demande de réservation",
            body=f"{tenant_name} souhaite réserver {property_title}",
            data={
                "type": "new_booking",
                "reference": booking_reference,
            },
        )

    # Email notification
    from app.tasks.email import send_generic_email

    html = f"""
    <h2>Nouvelle demande de réservation</h2>
    <p>Bonjour {landlord_name},</p>
    <p>{tenant_name} souhaite réserver votre bien <strong>{property_title}</strong>.</p>
    <p>Dates: {check_in} au {check_out}</p>
    <p>Référence: {booking_reference}</p>
    <p>Connectez-vous pour approuver ou refuser cette demande.</p>
    """

    send_generic_email.delay(
        to_email=landlord_email,
        subject=f"Nouvelle réservation - {property_title}",
        html_content=html,
    )

    return {"status": "notified"}


@shared_task
def notify_booking_status_change(
    user_fcm_token: str | None,
    user_email: str,
    user_name: str,
    property_title: str,
    booking_reference: str,
    new_status: str,
    message: str,
):
    """Notify user of booking status change."""
    status_messages = {
        "approved": "Votre réservation a été approuvée!",
        "rejected": "Votre demande de réservation a été refusée.",
        "confirmed": "Votre réservation est confirmée!",
        "cancelled": "Votre réservation a été annulée.",
    }

    title = status_messages.get(new_status, "Mise à jour de réservation")

    # Push notification
    if user_fcm_token:
        send_push_notification.delay(
            fcm_token=user_fcm_token,
            title=title,
            body=f"{property_title} - {booking_reference}",
            data={
                "type": "booking_update",
                "status": new_status,
                "reference": booking_reference,
            },
        )

    # Email notification
    from app.tasks.email import send_generic_email

    html = f"""
    <h2>{title}</h2>
    <p>Bonjour {user_name},</p>
    <p>{message}</p>
    <p>Bien: {property_title}</p>
    <p>Référence: {booking_reference}</p>
    """

    send_generic_email.delay(
        to_email=user_email,
        subject=f"{title} - {booking_reference}",
        html_content=html,
    )

    return {"status": "notified"}


@shared_task
def notify_new_message(
    recipient_fcm_token: str | None,
    sender_name: str,
    message_preview: str,
    conversation_id: str,
):
    """Notify user of new message."""
    if recipient_fcm_token:
        send_push_notification.delay(
            fcm_token=recipient_fcm_token,
            title=f"Message de {sender_name}",
            body=message_preview[:100],
            data={
                "type": "new_message",
                "conversation_id": conversation_id,
            },
        )

    return {"status": "notified"}


@shared_task
def notify_payment_received(
    receiver_fcm_token: str | None,
    receiver_email: str,
    receiver_name: str,
    amount: str,
    payment_type: str,
    reference: str,
):
    """Notify user of payment received."""
    if receiver_fcm_token:
        send_push_notification.delay(
            fcm_token=receiver_fcm_token,
            title="Paiement reçu",
            body=f"Vous avez reçu {amount}",
            data={
                "type": "payment_received",
                "reference": reference,
            },
        )

    # Email notification
    from app.tasks.email import send_generic_email

    html = f"""
    <h2>Paiement reçu</h2>
    <p>Bonjour {receiver_name},</p>
    <p>Vous avez reçu un paiement de <strong>{amount}</strong>.</p>
    <p>Type: {payment_type}</p>
    <p>Référence: {reference}</p>
    """

    send_generic_email.delay(
        to_email=receiver_email,
        subject=f"Paiement reçu - {reference}",
        html_content=html,
    )

    return {"status": "notified"}
