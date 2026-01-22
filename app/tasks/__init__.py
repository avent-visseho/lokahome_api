"""
Celery tasks for LOKAHOME API asynchronous processing.
"""
from app.tasks.celery_app import celery_app
from app.tasks.email import (
    send_booking_confirmation_email,
    send_generic_email,
    send_password_reset_email,
    send_welcome_email,
)
from app.tasks.maintenance import (
    backup_database,
    check_expiring_bookings,
    check_system_health,
    cleanup_expired_sessions,
    cleanup_expired_tokens,
    cleanup_old_notifications,
    cleanup_orphaned_files,
    generate_daily_reports,
    send_weekly_digest,
    sync_payment_statuses,
    update_property_rankings,
    update_provider_ratings,
)
from app.tasks.notifications import (
    notify_booking_status_change,
    notify_new_booking,
    notify_new_message,
    notify_payment_received,
    send_booking_reminders,
    send_push_notification,
    send_push_to_topic,
    send_sms,
)
from app.tasks.payments import (
    check_pending_payments,
    generate_payment_report,
    process_refund,
    reconcile_daily_payments,
    verify_payment_status,
)

__all__ = [
    "celery_app",
    # Email tasks
    "send_welcome_email",
    "send_password_reset_email",
    "send_booking_confirmation_email",
    "send_generic_email",
    # Notification tasks
    "send_push_notification",
    "send_push_to_topic",
    "send_sms",
    "send_booking_reminders",
    "notify_new_booking",
    "notify_booking_status_change",
    "notify_new_message",
    "notify_payment_received",
    # Payment tasks
    "check_pending_payments",
    "verify_payment_status",
    "process_refund",
    "generate_payment_report",
    "reconcile_daily_payments",
    # Maintenance tasks
    "cleanup_expired_tokens",
    "cleanup_expired_sessions",
    "cleanup_old_notifications",
    "cleanup_orphaned_files",
    "update_property_rankings",
    "generate_daily_reports",
    "check_expiring_bookings",
    "sync_payment_statuses",
    "backup_database",
    "send_weekly_digest",
    "update_provider_ratings",
    "check_system_health",
]
