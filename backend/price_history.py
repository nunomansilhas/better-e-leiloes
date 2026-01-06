"""
Price History Manager - Stores all price changes in a JSON file
"""
import json
import os
from datetime import datetime
from typing import Dict, List, Optional
import asyncio
from pathlib import Path

# Path to the price history file
DATA_DIR = Path(__file__).parent / "data"
PRICE_HISTORY_FILE = DATA_DIR / "price_history.json"

# Lock for thread-safe file operations
_file_lock = asyncio.Lock()


def _ensure_file_exists():
    """Ensure the data directory and file exist"""
    DATA_DIR.mkdir(exist_ok=True)
    if not PRICE_HISTORY_FILE.exists():
        with open(PRICE_HISTORY_FILE, 'w') as f:
            json.dump({}, f)


def _load_history() -> Dict[str, List[dict]]:
    """Load price history from JSON file"""
    _ensure_file_exists()
    try:
        with open(PRICE_HISTORY_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}


def _save_history(history: Dict[str, List[dict]]):
    """Save price history to JSON file"""
    _ensure_file_exists()
    with open(PRICE_HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=2, default=str)


async def record_price_change(reference: str, new_price: float, old_price: Optional[float] = None):
    """
    Record a price change for an event.
    If it's the first record for this event, just stores the price.
    If price changed from last record, adds a new entry.
    """
    async with _file_lock:
        history = _load_history()

        now = datetime.utcnow().isoformat()

        if reference not in history:
            # First time seeing this event
            history[reference] = [{
                "preco": new_price,
                "timestamp": now
            }]
        else:
            # Check if price actually changed
            last_entry = history[reference][-1]
            last_price = last_entry.get("preco")

            if last_price != new_price:
                # Price changed, add new entry
                history[reference].append({
                    "preco": new_price,
                    "timestamp": now
                })

        _save_history(history)


async def get_event_history(reference: str) -> List[dict]:
    """Get complete price history for a specific event"""
    async with _file_lock:
        history = _load_history()
        return history.get(reference, [])


async def get_recent_changes(limit: int = 30, hours: int = 24) -> List[dict]:
    """
    Get recent price changes across all events.
    Returns only the LATEST change per event (no duplicates).
    Filters to only show changes from the last X hours.
    """
    from datetime import timedelta

    async with _file_lock:
        history = _load_history()

        changes = []
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)

        for reference, prices in history.items():
            if len(prices) >= 2:
                # Only get the LAST change for this event
                i = len(prices) - 1
                timestamp_str = prices[i]["timestamp"]

                # Parse timestamp
                try:
                    timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                except:
                    timestamp = datetime.utcnow()

                # Only include if within the time window
                if timestamp >= cutoff_time:
                    changes.append({
                        "reference": reference,
                        "preco_anterior": prices[i-1]["preco"],
                        "preco_atual": prices[i]["preco"],
                        "variacao": prices[i]["preco"] - prices[i-1]["preco"],
                        "timestamp": prices[i]["timestamp"]
                    })

        # Sort by timestamp (most recent first)
        changes.sort(key=lambda x: x["timestamp"], reverse=True)

        return changes[:limit]


async def get_all_history() -> Dict[str, List[dict]]:
    """Get the complete price history for all events"""
    async with _file_lock:
        return _load_history()


async def get_stats() -> dict:
    """Get statistics about the price history"""
    async with _file_lock:
        history = _load_history()

        total_events = len(history)
        total_changes = sum(len(prices) - 1 for prices in history.values() if len(prices) > 1)
        events_with_changes = sum(1 for prices in history.values() if len(prices) > 1)

        return {
            "total_events_tracked": total_events,
            "total_price_changes": total_changes,
            "events_with_changes": events_with_changes
        }
