"""
Cleanup Management Router
Endpoints for data cleanup operations
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/api/cleanup", tags=["Cleanup"])


@router.get("/stats")
async def get_cleanup_stats():
    """
    Get statistics about data that can be cleaned up.

    Returns:
    - old_notifications: Count of notifications older than retention period
    - old_price_history: Count of price history older than retention period
    - old_refresh_logs: Count of refresh logs older than retention period
    - old_terminated_events: Count of terminated events that can be marked inactive
    - config: Current cleanup configuration
    """
    from cleanup import get_cleanup_stats
    return await get_cleanup_stats()


@router.post("/run")
async def run_cleanup():
    """
    Manually trigger a full cleanup.
    This will delete old data according to retention settings.

    Returns:
    - notifications: Number of deleted notifications
    - price_history: Number of deleted price history records
    - refresh_logs: Number of deleted refresh logs
    - inactive_events: Number of events marked as inactive
    """
    from cleanup import run_full_cleanup
    return await run_full_cleanup()


@router.post("/notifications")
async def cleanup_notifications(days: int = None):
    """
    Clean up old notifications.

    Args:
        days: Optional - Override default retention days
    """
    from cleanup import cleanup_old_notifications
    deleted = await cleanup_old_notifications(days)
    return {"success": True, "deleted": deleted, "type": "notifications"}


@router.post("/price-history")
async def cleanup_price_history(days: int = None):
    """
    Clean up old price history.

    Args:
        days: Optional - Override default retention days
    """
    from cleanup import cleanup_old_price_history
    deleted = await cleanup_old_price_history(days)
    return {"success": True, "deleted": deleted, "type": "price_history"}


@router.post("/refresh-logs")
async def cleanup_refresh_logs(days: int = None):
    """
    Clean up old refresh logs.

    Args:
        days: Optional - Override default retention days
    """
    from cleanup import cleanup_old_refresh_logs
    deleted = await cleanup_old_refresh_logs(days)
    return {"success": True, "deleted": deleted, "type": "refresh_logs"}


@router.post("/inactive-events")
async def mark_events_inactive(days: int = None):
    """
    Mark old terminated events as inactive.

    Args:
        days: Optional - Override default retention days
    """
    from cleanup import mark_old_events_inactive
    updated = await mark_old_events_inactive(days)
    return {"success": True, "updated": updated, "type": "events"}


@router.get("/config")
async def get_cleanup_config():
    """
    Get current cleanup configuration.
    """
    from cleanup import CLEANUP_CONFIG
    return {
        "config": CLEANUP_CONFIG,
        "description": {
            "notifications_max_age": "Days to keep notifications",
            "price_history_max_age": "Days to keep price history",
            "refresh_logs_max_age": "Days to keep refresh logs",
            "terminated_events_max_age": "Days after termination to mark inactive",
            "cache_cleanup_interval": "Seconds between cache cleanups"
        }
    }
