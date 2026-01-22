"""
Celery application configuration.
"""
from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "lokahome",
    broker=str(settings.REDIS_URL),
    backend=str(settings.REDIS_URL),
    include=[
        "app.tasks.email",
        "app.tasks.notifications",
        "app.tasks.payments",
        "app.tasks.maintenance",
    ],
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Africa/Porto-Novo",  # Benin timezone
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes
    task_soft_time_limit=240,  # 4 minutes
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    # Rate limits
    task_default_rate_limit="100/m",
    # Retry settings
    task_default_retry_delay=60,
    task_max_retries=3,
)

# Beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    # Every 5 minutes
    "check-pending-payments": {
        "task": "app.tasks.payments.check_pending_payments",
        "schedule": 300.0,
    },
    "check-system-health": {
        "task": "app.tasks.maintenance.check_system_health",
        "schedule": 300.0,
    },
    # Every hour
    "cleanup-expired-tokens": {
        "task": "app.tasks.maintenance.cleanup_expired_tokens",
        "schedule": 3600.0,
    },
    "sync-payment-statuses": {
        "task": "app.tasks.maintenance.sync_payment_statuses",
        "schedule": 3600.0,
    },
    # Daily at 6:00 AM (Benin time)
    "send-booking-reminders": {
        "task": "app.tasks.notifications.send_booking_reminders",
        "schedule": crontab(hour=6, minute=0),
    },
    "check-expiring-bookings": {
        "task": "app.tasks.maintenance.check_expiring_bookings",
        "schedule": crontab(hour=7, minute=0),
    },
    "update-property-rankings": {
        "task": "app.tasks.maintenance.update_property_rankings",
        "schedule": crontab(hour=2, minute=0),
    },
    # Daily at midnight
    "reconcile-daily-payments": {
        "task": "app.tasks.payments.reconcile_daily_payments",
        "schedule": crontab(hour=0, minute=0),
    },
    "generate-daily-reports": {
        "task": "app.tasks.maintenance.generate_daily_reports",
        "schedule": crontab(hour=23, minute=30),
    },
    "backup-database": {
        "task": "app.tasks.maintenance.backup_database",
        "schedule": crontab(hour=3, minute=0),
    },
    # Weekly on Sunday at 10:00 AM
    "send-weekly-digest": {
        "task": "app.tasks.maintenance.send_weekly_digest",
        "schedule": crontab(hour=10, minute=0, day_of_week=0),
    },
    "cleanup-old-notifications": {
        "task": "app.tasks.maintenance.cleanup_old_notifications",
        "schedule": crontab(hour=4, minute=0, day_of_week=0),
    },
    "update-provider-ratings": {
        "task": "app.tasks.maintenance.update_provider_ratings",
        "schedule": crontab(hour=5, minute=0, day_of_week=0),
    },
}
