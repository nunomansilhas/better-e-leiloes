"""
Price History Manager - Stores all price changes in the database
Uses the PriceHistoryDB model for persistent storage across all users.
"""
from datetime import datetime
from typing import Dict, List, Optional

from database import get_db


async def record_price_change(
    reference: str,
    new_price: float,
    old_price: Optional[float] = None,
    source: Optional[str] = None
) -> Optional[int]:
    """
    Record a price change for an event.
    If it's the first record for this event, just stores the price.
    If price changed from last record, adds a new entry.

    Args:
        reference: Event reference
        new_price: Current price
        old_price: Previous price (optional - will be fetched if not provided)
        source: Source of the update ('xmonitor', 'ysync', 'zwatch', 'manual')

    Returns:
        ID of created record, or None if no change
    """
    async with get_db() as db:
        return await db.record_price_change(reference, new_price, old_price, source)


async def get_event_history(reference: str) -> List[dict]:
    """
    Get complete price history for a specific event.
    Returns list of price records ordered from oldest to newest.
    """
    async with get_db() as db:
        return await db.get_event_price_history(reference)


async def get_recent_changes(limit: int = 30, hours: int = 24) -> List[dict]:
    """
    Get recent price changes across all events.
    Returns only the LATEST change per event (no duplicates).
    Filters to only show changes from the last X hours.

    Returns list with keys:
        - reference
        - preco_anterior
        - preco_atual
        - variacao
        - variacao_percent
        - timestamp
        - source
    """
    async with get_db() as db:
        return await db.get_recent_price_changes(limit, hours)


async def get_all_history() -> Dict[str, List[dict]]:
    """
    Get the complete price history for all events.
    Returns dict with reference as key and list of price records as value.
    """
    async with get_db() as db:
        references = await db.get_all_price_history_references()
        result = {}
        for ref in references:
            history = await db.get_event_price_history(ref)
            # Convert to old format for compatibility
            result[ref] = [{
                "preco": h["new_price"],
                "timestamp": h["recorded_at"]
            } for h in history]
        return result


async def get_stats() -> dict:
    """
    Get statistics about the price history.
    Returns:
        - total_events_tracked: Number of unique events
        - total_price_changes: Number of actual price changes
        - events_with_changes: Events that had at least one price change
        - total_records: Total number of records in DB
        - by_source: Breakdown by source
    """
    async with get_db() as db:
        stats = await db.get_price_history_stats()
        return {
            "total_events_tracked": stats["unique_events"],
            "total_price_changes": stats["real_changes"],
            "events_with_changes": stats["events_with_changes"],
            "total_records": stats["total_records"],
            "by_source": stats["by_source"]
        }


async def migrate_from_json(json_data: dict) -> int:
    """
    Migrate price history from JSON file to database.

    Args:
        json_data: Dict with reference as key and list of {preco, timestamp} as value

    Returns:
        Number of records imported
    """
    async with get_db() as db:
        return await db.bulk_import_price_history(json_data)
