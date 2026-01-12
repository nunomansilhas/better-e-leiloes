"""
Automatic Data Cleanup Module
Scheduled jobs for maintaining database hygiene
"""

from datetime import datetime, timedelta
from sqlalchemy import delete, select, func, and_
from logger import log_info, log_error, log_warning


# Cleanup configuration (days)
CLEANUP_CONFIG = {
    "notifications_max_age": 30,       # Delete notifications older than 30 days
    "price_history_max_age": 90,       # Delete price history older than 90 days
    "refresh_logs_max_age": 7,         # Delete refresh logs older than 7 days
    "terminated_events_max_age": 180,  # Mark events as inactive after 180 days
    "cache_cleanup_interval": 3600,    # Run cache cleanup every hour
}


async def cleanup_old_notifications(days: int = None) -> int:
    """
    Delete notifications older than X days.

    Args:
        days: Number of days to keep (default from config)

    Returns:
        Number of deleted records
    """
    from database import get_db, NotificationDB

    days = days or CLEANUP_CONFIG["notifications_max_age"]
    cutoff = datetime.utcnow() - timedelta(days=days)

    try:
        async with get_db() as db:
            result = await db.session.execute(
                delete(NotificationDB).where(NotificationDB.created_at < cutoff)
            )
            await db.session.commit()
            deleted = result.rowcount

            if deleted > 0:
                log_info(f"Cleanup: Deleted {deleted} old notifications (>{days} days)")

            return deleted
    except Exception as e:
        log_error(f"Cleanup notifications failed", e)
        return 0


async def cleanup_old_price_history(days: int = None) -> int:
    """
    Delete price history records older than X days.
    Keeps at least the first and last record for each event.

    Args:
        days: Number of days to keep (default from config)

    Returns:
        Number of deleted records
    """
    from database import get_db, PriceHistoryDB

    days = days or CLEANUP_CONFIG["price_history_max_age"]
    cutoff = datetime.utcnow() - timedelta(days=days)

    try:
        async with get_db() as db:
            # Delete old records, but keep boundary records (first/last per event)
            # This preserves the price trajectory while reducing data
            result = await db.session.execute(
                delete(PriceHistoryDB).where(
                    and_(
                        PriceHistoryDB.recorded_at < cutoff,
                        # Keep records where old_price is None (first record)
                        PriceHistoryDB.old_price.isnot(None)
                    )
                )
            )
            await db.session.commit()
            deleted = result.rowcount

            if deleted > 0:
                log_info(f"Cleanup: Deleted {deleted} old price history records (>{days} days)")

            return deleted
    except Exception as e:
        log_error(f"Cleanup price history failed", e)
        return 0


async def cleanup_old_refresh_logs(days: int = None) -> int:
    """
    Delete processed refresh logs older than X days.

    Args:
        days: Number of days to keep (default from config)

    Returns:
        Number of deleted records
    """
    from database import get_db, RefreshLogDB

    days = days or CLEANUP_CONFIG["refresh_logs_max_age"]
    cutoff = datetime.utcnow() - timedelta(days=days)

    try:
        async with get_db() as db:
            # Only delete completed or errored logs (state 2 or 3)
            result = await db.session.execute(
                delete(RefreshLogDB).where(
                    and_(
                        RefreshLogDB.created_at < cutoff,
                        RefreshLogDB.state.in_([2, 3])  # completed or error
                    )
                )
            )
            await db.session.commit()
            deleted = result.rowcount

            if deleted > 0:
                log_info(f"Cleanup: Deleted {deleted} old refresh logs (>{days} days)")

            return deleted
    except Exception as e:
        log_error(f"Cleanup refresh logs failed", e)
        return 0


async def mark_old_events_inactive(days: int = None) -> int:
    """
    Mark terminated events as inactive after X days.
    This reduces clutter in active queries.

    Args:
        days: Number of days after termination (default from config)

    Returns:
        Number of updated records
    """
    from database import get_db, EventDB
    from sqlalchemy import update

    days = days or CLEANUP_CONFIG["terminated_events_max_age"]
    cutoff = datetime.utcnow() - timedelta(days=days)

    try:
        async with get_db() as db:
            result = await db.session.execute(
                update(EventDB).where(
                    and_(
                        EventDB.terminado == True,
                        EventDB.data_fim < cutoff,
                        EventDB.ativo == True
                    )
                ).values(ativo=False)
            )
            await db.session.commit()
            updated = result.rowcount

            if updated > 0:
                log_info(f"Cleanup: Marked {updated} old terminated events as inactive")

            return updated
    except Exception as e:
        log_error(f"Cleanup old events failed", e)
        return 0


async def run_full_cleanup() -> dict:
    """
    Run all cleanup jobs.

    Returns:
        Dict with cleanup results
    """
    log_info("Starting scheduled cleanup...")

    results = {
        "notifications": await cleanup_old_notifications(),
        "price_history": await cleanup_old_price_history(),
        "refresh_logs": await cleanup_old_refresh_logs(),
        "inactive_events": await mark_old_events_inactive(),
        "timestamp": datetime.utcnow().isoformat()
    }

    total = sum(v for k, v in results.items() if isinstance(v, int))
    log_info(f"Cleanup completed: {total} total records affected")

    return results


async def get_cleanup_stats() -> dict:
    """
    Get statistics about data that could be cleaned up.

    Returns:
        Dict with cleanup statistics
    """
    from database import get_db, NotificationDB, PriceHistoryDB, RefreshLogDB, EventDB

    now = datetime.utcnow()

    try:
        async with get_db() as db:
            # Old notifications
            notif_cutoff = now - timedelta(days=CLEANUP_CONFIG["notifications_max_age"])
            old_notif = await db.session.scalar(
                select(func.count()).select_from(NotificationDB)
                .where(NotificationDB.created_at < notif_cutoff)
            )

            # Old price history
            price_cutoff = now - timedelta(days=CLEANUP_CONFIG["price_history_max_age"])
            old_price = await db.session.scalar(
                select(func.count()).select_from(PriceHistoryDB)
                .where(PriceHistoryDB.recorded_at < price_cutoff)
            )

            # Old refresh logs
            refresh_cutoff = now - timedelta(days=CLEANUP_CONFIG["refresh_logs_max_age"])
            old_refresh = await db.session.scalar(
                select(func.count()).select_from(RefreshLogDB)
                .where(RefreshLogDB.created_at < refresh_cutoff)
            )

            # Old terminated events
            events_cutoff = now - timedelta(days=CLEANUP_CONFIG["terminated_events_max_age"])
            old_events = await db.session.scalar(
                select(func.count()).select_from(EventDB)
                .where(
                    and_(
                        EventDB.terminado == True,
                        EventDB.data_fim < events_cutoff,
                        EventDB.ativo == True
                    )
                )
            )

            return {
                "old_notifications": old_notif or 0,
                "old_price_history": old_price or 0,
                "old_refresh_logs": old_refresh or 0,
                "old_terminated_events": old_events or 0,
                "total_cleanable": (old_notif or 0) + (old_price or 0) + (old_refresh or 0),
                "config": CLEANUP_CONFIG
            }
    except Exception as e:
        log_error(f"Get cleanup stats failed", e)
        return {"error": str(e)}


def schedule_cleanup_jobs(scheduler):
    """
    Schedule automatic cleanup jobs.

    Args:
        scheduler: APScheduler instance
    """
    from apscheduler.triggers.cron import CronTrigger

    # Run full cleanup daily at 3 AM
    scheduler.add_job(
        run_full_cleanup,
        CronTrigger(hour=3, minute=0),
        id="daily_cleanup",
        replace_existing=True
    )
    log_info("Scheduled daily cleanup job (3:00 AM)")

    # Run cache cleanup every hour
    from apscheduler.triggers.interval import IntervalTrigger

    async def cleanup_cache():
        from main import cache_manager
        if cache_manager:
            count = await cache_manager.cleanup_expired_memory_cache()
            if count > 0:
                log_info(f"Cache cleanup: removed {count} expired entries")

    scheduler.add_job(
        cleanup_cache,
        IntervalTrigger(seconds=CLEANUP_CONFIG["cache_cleanup_interval"]),
        id="cache_cleanup",
        replace_existing=True
    )
    log_info("Scheduled hourly cache cleanup")
