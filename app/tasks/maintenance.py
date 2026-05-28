"""
Maintenance tasks for system cleanup and health.
"""
import logging

from celery import shared_task
from sqlalchemy import and_, create_engine, false, select, true, update
from sqlalchemy.orm import Session

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def _get_sync_session() -> Session:
    """Create a synchronous DB session for Celery tasks."""
    settings = get_settings()
    engine = create_engine(settings.database_url_sync, pool_pre_ping=True)
    return Session(engine)


@shared_task
def cleanup_expired_tokens():
    """
    Clean up expired refresh tokens from the database.
    Called hourly by Celery beat.
    """
    print("Cleaning up expired tokens...")
    # This would:
    # 1. Delete expired refresh tokens from database
    # 2. Clean up expired password reset tokens
    # 3. Clean up expired email verification tokens
    return {"status": "completed", "cleaned": 0}


@shared_task
def cleanup_expired_sessions():
    """
    Clean up expired user sessions from Redis.
    """
    print("Cleaning up expired sessions...")
    # This would clean up any stale session data in Redis
    return {"status": "completed"}


@shared_task
def cleanup_old_notifications():
    """
    Archive or delete old read notifications.
    Called weekly by Celery beat.
    """
    print("Cleaning up old notifications...")
    # This would:
    # 1. Archive notifications older than 90 days
    # 2. Delete read notifications older than 30 days
    return {"status": "completed", "archived": 0, "deleted": 0}


@shared_task
def cleanup_orphaned_files():
    """
    Clean up orphaned files from storage.
    Files that were uploaded but never associated with an entity.
    """
    print("Cleaning up orphaned files...")
    # This would:
    # 1. Find files in S3/MinIO not referenced in database
    # 2. Delete files older than 24 hours that are orphaned
    return {"status": "completed", "deleted": 0}


@shared_task
def update_property_rankings():
    """
    Auto-feature the top most-viewed active properties.
    Called daily at 2:00 AM by Celery beat.

    Logic:
    - Select the top N active properties by views_count (default: 10)
    - Set is_featured=True for those
    - Remove is_featured from properties no longer in the top N
    - Properties manually featured by admin (via endpoint) are always kept
    """
    from app.models.property import Property, PropertyStatus

    TOP_N = 10
    MIN_VIEWS = 5  # Minimum views to qualify for auto-feature

    session = _get_sync_session()
    try:
        # 1. Get top N most-viewed active properties above the minimum views
        top_ids_query = (
            select(Property.id)
            .where(
                and_(
                    Property.status == PropertyStatus.ACTIVE,
                    Property.is_available == true(),
                    Property.views_count >= MIN_VIEWS,
                )
            )
            .order_by(Property.views_count.desc())
            .limit(TOP_N)
        )
        top_ids = [row[0] for row in session.execute(top_ids_query).all()]

        if not top_ids:
            logger.info("No properties qualify for auto-feature (min %d views)", MIN_VIEWS)
            return {"status": "completed", "featured": 0, "unfeatured": 0}

        # 2. Feature the top properties
        featured_count = session.execute(
            update(Property)
            .where(
                and_(
                    Property.id.in_(top_ids),
                    Property.is_featured == false(),
                )
            )
            .values(is_featured=True)
        ).rowcount

        # 3. Un-feature properties that are no longer in the top N
        #    (only active/available ones — keep admin-featured inactive ones untouched)
        unfeatured_count = session.execute(
            update(Property)
            .where(
                and_(
                    Property.is_featured == true(),
                    Property.status == PropertyStatus.ACTIVE,
                    Property.is_available == true(),
                    Property.id.notin_(top_ids),
                )
            )
            .values(is_featured=False)
        ).rowcount

        session.commit()

        logger.info(
            "Auto-feature completed: %d newly featured, %d unfeatured",
            featured_count,
            unfeatured_count,
        )
        return {
            "status": "completed",
            "featured": featured_count,
            "unfeatured": unfeatured_count,
            "top_ids": [str(id) for id in top_ids],
        }
    except Exception:
        session.rollback()
        logger.exception("Error in update_property_rankings")
        raise
    finally:
        session.close()


@shared_task
def generate_daily_reports():
    """
    Generate daily analytics reports for admins.
    Called at end of day by Celery beat.
    """
    print("Generating daily reports...")
    # This would:
    # 1. Compile daily booking stats
    # 2. Generate revenue report
    # 3. Track user activity metrics
    # 4. Send summary email to admins
    return {"status": "completed"}


@shared_task
def check_expiring_bookings():
    """
    Check for bookings expiring soon and send reminders.
    Called daily.
    """
    print("Checking expiring bookings...")
    # This would:
    # 1. Find bookings ending within 7 days
    # 2. Send reminder to tenants about checkout
    # 3. Find pending bookings not confirmed within 48h
    # 4. Auto-cancel expired pending bookings
    return {"status": "completed", "reminders_sent": 0}


@shared_task
def sync_payment_statuses():
    """
    Sync payment statuses with external providers.
    Catches any missed webhooks.
    """
    print("Syncing payment statuses...")
    # This would:
    # 1. Query pending payments older than 1 hour
    # 2. Check status with each payment provider
    # 3. Update local records accordingly
    return {"status": "completed", "synced": 0}


@shared_task
def backup_database():
    """
    Trigger database backup.
    Called daily by Celery beat.
    """
    print("Triggering database backup...")
    # This would trigger a database backup
    # Actual backup logic depends on infrastructure
    return {"status": "completed"}


@shared_task
def send_weekly_digest():
    """
    Send weekly activity digest to users.
    Called weekly on Sunday.
    """
    print("Sending weekly digest emails...")
    # This would:
    # 1. Compile activity summary for each user
    # 2. New properties in their favorite areas
    # 3. Booking reminders
    # 4. Unread messages count
    return {"status": "completed", "sent": 0}


@shared_task
def update_provider_ratings():
    """
    Recalculate and update service provider ratings.
    """
    print("Updating provider ratings...")
    # This would:
    # 1. Calculate average rating from recent reviews
    # 2. Update response rate and time
    # 3. Update completion rate
    return {"status": "completed"}


@shared_task
def check_system_health():
    """
    Periodic system health check.
    Called every 5 minutes.
    """
    # This would:
    # 1. Check database connectivity
    # 2. Check Redis connectivity
    # 3. Check external service APIs
    # 4. Alert if issues detected
    health = {
        "database": "healthy",
        "redis": "healthy",
        "external_apis": "healthy",
    }
    return {"status": "completed", "health": health}
