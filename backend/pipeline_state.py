"""
Pipeline State Management System
Persists scraping progress to JSON file for real-time frontend feedback
"""

import json
import os
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path
import asyncio
from contextlib import asynccontextmanager


class PipelineState:
    """Manages pipeline state with file persistence"""

    STATE_FILE = Path(__file__).parent / "pipeline_state.json"

    def __init__(self):
        self._state: Dict[str, Any] = {
            "active": False,
            "stage": None,
            "stage_name": None,
            "current": 0,
            "total": 0,
            "message": "",
            "started_at": None,
            "updated_at": None,
            "errors": [],
            "details": {}
        }
        self._lock = asyncio.Lock()
        self._load_from_file()

    def _load_from_file(self):
        """Load state from file if exists"""
        if self.STATE_FILE.exists():
            try:
                with open(self.STATE_FILE, 'r', encoding='utf-8') as f:
                    saved_state = json.load(f)
                    self._state.update(saved_state)
                    print(f"📂 Pipeline state loaded from file")
            except Exception as e:
                print(f"⚠️ Error loading pipeline state: {e}")

    def _save_to_file(self):
        """Save state to file"""
        try:
            with open(self.STATE_FILE, 'w', encoding='utf-8') as f:
                json.dump(self._state, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️ Error saving pipeline state: {e}")

    async def start(self, stage: int, stage_name: str, total: int = 0, details: Dict = None):
        """Start a new pipeline stage"""
        async with self._lock:
            now = datetime.now().isoformat()
            self._state.update({
                "active": True,
                "stage": stage,
                "stage_name": stage_name,
                "current": 0,
                "total": total,
                "message": f"Iniciando {stage_name}...",
                "started_at": now,
                "updated_at": now,
                "errors": [],
                "details": details or {}
            })
            self._save_to_file()
            print(f"🚀 Pipeline Stage {stage} ({stage_name}) iniciada: {total} itens")

    async def update(self, current: int = None, total: int = None, message: str = None, details: Dict = None):
        """Update pipeline progress"""
        async with self._lock:
            if current is not None:
                self._state["current"] = current
            if total is not None:
                self._state["total"] = total
            if message is not None:
                self._state["message"] = message
            if details is not None:
                self._state["details"].update(details)

            self._state["updated_at"] = datetime.now().isoformat()
            self._save_to_file()

    async def increment(self, message: str = None, details: Dict = None):
        """Increment current counter by 1"""
        async with self._lock:
            self._state["current"] += 1
            if message:
                self._state["message"] = message
            if details:
                self._state["details"].update(details)

            self._state["updated_at"] = datetime.now().isoformat()
            self._save_to_file()

    async def add_error(self, error: str):
        """Add an error to the error list"""
        async with self._lock:
            self._state["errors"].append({
                "timestamp": datetime.now().isoformat(),
                "error": error
            })
            self._save_to_file()

    async def complete(self, message: str = None):
        """Mark pipeline stage as complete"""
        async with self._lock:
            if message:
                self._state["message"] = message
            else:
                self._state["message"] = f"✅ {self._state['stage_name']} concluído"

            self._state["updated_at"] = datetime.now().isoformat()
            self._save_to_file()
            print(f"✅ Pipeline Stage {self._state['stage']} concluída: {self._state['current']}/{self._state['total']}")

    async def stop(self):
        """Stop pipeline and clear state"""
        async with self._lock:
            self._state = {
                "active": False,
                "stage": None,
                "stage_name": None,
                "current": 0,
                "total": 0,
                "message": "",
                "started_at": None,
                "updated_at": None,
                "errors": [],
                "details": {}
            }
            self._save_to_file()

            # Delete state file
            if self.STATE_FILE.exists():
                try:
                    self.STATE_FILE.unlink()
                    print(f"🗑️ Pipeline state file deleted")
                except Exception as e:
                    print(f"⚠️ Error deleting state file: {e}")

    async def get_state(self) -> Dict[str, Any]:
        """Get current state (async for consistency)"""
        async with self._lock:
            return self._state.copy()

    def get_state_sync(self) -> Dict[str, Any]:
        """Get current state synchronously"""
        return self._state.copy()

    @property
    def is_active(self) -> bool:
        """Check if pipeline is currently active"""
        return self._state.get("active", False)

    @asynccontextmanager
    async def stage_context(self, stage: int, stage_name: str, total: int = 0, details: Dict = None):
        """Context manager for pipeline stages"""
        await self.start(stage, stage_name, total, details)
        try:
            yield self
        except Exception as e:
            await self.add_error(str(e))
            raise
        finally:
            await self.complete()


# Global singleton instance
_pipeline_state_instance = None


def get_pipeline_state() -> PipelineState:
    """Get or create global pipeline state instance"""
    global _pipeline_state_instance
    if _pipeline_state_instance is None:
        _pipeline_state_instance = PipelineState()
    return _pipeline_state_instance
