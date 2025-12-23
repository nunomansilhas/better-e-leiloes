"""
X-Monitor History - Persists event changes history to JSON
"""
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
import asyncio
from threading import Lock

# File path for history data
HISTORY_FILE = Path(__file__).parent / "data" / "xmonitor_history.json"

# Thread-safe lock for file operations
_file_lock = Lock()


def _ensure_data_dir():
    """Ensure data directory exists"""
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)


def _load_history() -> Dict:
    """Load history from JSON file"""
    _ensure_data_dir()

    if not HISTORY_FILE.exists():
        return {
            "events": {},
            "lastUpdated": None,
            "stats": {
                "totalUpdates": 0,
                "eventsTracked": 0
            }
        }

    try:
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {
            "events": {},
            "lastUpdated": None,
            "stats": {
                "totalUpdates": 0,
                "eventsTracked": 0
            }
        }


def _save_history(data: Dict):
    """Save history to JSON file"""
    _ensure_data_dir()

    with _file_lock:
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)


def record_event_update(
    reference: str,
    lance_atual: Optional[float],
    data_fim: Optional[datetime],
    old_lance: Optional[float] = None,
    old_data_fim: Optional[datetime] = None,
    tier: str = "unknown"
) -> bool:
    """
    Record an event update to history.
    Returns True if this is a new change, False if duplicate.
    """
    now = datetime.now()
    history = _load_history()

    # Initialize event if not exists
    if reference not in history["events"]:
        history["events"][reference] = {
            "reference": reference,
            "firstSeen": now.isoformat(),
            "history": []
        }
        history["stats"]["eventsTracked"] += 1

    event_data = history["events"][reference]

    # Create history entry
    entry = {
        "timestamp": now.isoformat(),
        "lanceAtual": lance_atual,
        "dataFim": data_fim.isoformat() if data_fim else None,
        "tier": tier
    }

    # Add change details if we have old values
    if old_lance is not None and old_lance != lance_atual:
        entry["lanceAnterior"] = old_lance
        entry["lanceVariacao"] = (lance_atual or 0) - (old_lance or 0)

    if old_data_fim and data_fim and old_data_fim != data_fim:
        entry["dataFimAnterior"] = old_data_fim.isoformat()
        entry["tempoExtendido"] = True

    # Check if this is a duplicate (same values as last entry)
    if event_data["history"]:
        last = event_data["history"][-1]
        if (last.get("lanceAtual") == lance_atual and
            last.get("dataFim") == entry.get("dataFim")):
            return False  # No change

    # Add entry
    event_data["history"].append(entry)
    event_data["lastUpdate"] = now.isoformat()
    event_data["currentLance"] = lance_atual
    event_data["currentDataFim"] = data_fim.isoformat() if data_fim else None

    # Update global stats
    history["lastUpdated"] = now.isoformat()
    history["stats"]["totalUpdates"] += 1

    _save_history(history)
    return True


def get_event_history(reference: str) -> Optional[Dict]:
    """Get history for a specific event"""
    history = _load_history()
    return history["events"].get(reference)


def get_all_history() -> Dict:
    """Get all history data"""
    return _load_history()


def get_recent_changes(limit: int = 50) -> List[Dict]:
    """Get most recent changes across all events"""
    history = _load_history()

    all_changes = []
    for ref, event_data in history["events"].items():
        for entry in event_data.get("history", []):
            change = {
                "reference": ref,
                **entry
            }
            all_changes.append(change)

    # Sort by timestamp descending
    all_changes.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

    return all_changes[:limit]


def get_active_events_summary() -> List[Dict]:
    """Get summary of all tracked events with their current values"""
    history = _load_history()

    summary = []
    for ref, event_data in history["events"].items():
        summary.append({
            "reference": ref,
            "currentLance": event_data.get("currentLance"),
            "currentDataFim": event_data.get("currentDataFim"),
            "firstSeen": event_data.get("firstSeen"),
            "lastUpdate": event_data.get("lastUpdate"),
            "changesCount": len(event_data.get("history", []))
        })

    # Sort by lastUpdate descending
    summary.sort(key=lambda x: x.get("lastUpdate") or "", reverse=True)

    return summary


def get_stats() -> Dict:
    """Get history statistics"""
    history = _load_history()

    total_changes = sum(
        len(e.get("history", []))
        for e in history["events"].values()
    )

    return {
        "eventsTracked": len(history["events"]),
        "totalChanges": total_changes,
        "lastUpdated": history.get("lastUpdated"),
        "totalUpdates": history["stats"].get("totalUpdates", 0)
    }


def cleanup_old_history(days: int = 7):
    """Remove history entries older than X days"""
    from datetime import timedelta

    history = _load_history()
    cutoff = datetime.now() - timedelta(days=days)
    cutoff_str = cutoff.isoformat()

    removed = 0
    for ref, event_data in history["events"].items():
        original_len = len(event_data.get("history", []))
        event_data["history"] = [
            entry for entry in event_data.get("history", [])
            if entry.get("timestamp", "") > cutoff_str
        ]
        removed += original_len - len(event_data["history"])

    if removed > 0:
        _save_history(history)
        print(f"🧹 Cleaned up {removed} old history entries")

    return removed


def clear_history():
    """
    Clear all history data - called on API startup.
    Deletes the JSON file to start fresh.
    """
    _ensure_data_dir()

    if HISTORY_FILE.exists():
        try:
            HISTORY_FILE.unlink()
            print("🗑️ X-Monitor history cleared (fresh start)")
            return True
        except Exception as e:
            print(f"⚠️ Error clearing X-Monitor history: {e}")
            return False

    return True  # File didn't exist, nothing to clear
