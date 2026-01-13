"""
WebSocket Connection Manager for Real-time Notifications
Manages WebSocket connections and broadcasts notifications to all connected clients
"""

from fastapi import WebSocket
from typing import List, Dict, Any
import asyncio
import json
from datetime import datetime


class NotificationWebSocketManager:
    """
    Manages WebSocket connections for real-time notifications.
    Supports multiple concurrent connections and broadcasts to all.
    """

    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        """Accept and register a new WebSocket connection"""
        await websocket.accept()
        async with self._lock:
            self.active_connections.append(websocket)
        print(f"🔌 WebSocket connected. Total connections: {len(self.active_connections)}")

    async def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection"""
        async with self._lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
        print(f"🔌 WebSocket disconnected. Total connections: {len(self.active_connections)}")

    async def broadcast_notification(self, notification: Dict[str, Any]):
        """
        Broadcast a notification to all connected clients.
        Automatically removes dead connections.
        """
        if not self.active_connections:
            return

        message = json.dumps({
            "type": "notification",
            "data": notification,
            "timestamp": datetime.now().isoformat()
        })

        dead_connections = []

        async with self._lock:
            for connection in self.active_connections:
                try:
                    await connection.send_text(message)
                except Exception as e:
                    print(f"❌ WebSocket send error: {e}")
                    dead_connections.append(connection)

            # Clean up dead connections
            for dead in dead_connections:
                if dead in self.active_connections:
                    self.active_connections.remove(dead)

        if dead_connections:
            print(f"🧹 Cleaned {len(dead_connections)} dead WebSocket connections")

    async def broadcast_price_change(
        self,
        event_reference: str,
        event_titulo: str,
        old_price: float,
        new_price: float,
        event_tipo: str = None,
        event_distrito: str = None
    ):
        """Convenience method to broadcast a price change notification"""
        await self.broadcast_notification({
            "notification_type": "price_change",
            "event_reference": event_reference,
            "event_titulo": event_titulo,
            "preco_anterior": old_price,
            "preco_atual": new_price,
            "preco_variacao": new_price - old_price,
            "event_tipo": event_tipo,
            "event_distrito": event_distrito
        })

    async def broadcast_new_event(
        self,
        event_reference: str,
        event_titulo: str,
        event_tipo: str = None,
        event_distrito: str = None,
        valor_base: float = None
    ):
        """Convenience method to broadcast a new event notification"""
        await self.broadcast_notification({
            "notification_type": "new_event",
            "event_reference": event_reference,
            "event_titulo": event_titulo,
            "event_tipo": event_tipo,
            "event_distrito": event_distrito,
            "valor_base": valor_base
        })

    async def broadcast_ending_soon(
        self,
        event_reference: str,
        event_titulo: str,
        minutes_remaining: int,
        preco_atual: float = None
    ):
        """Convenience method to broadcast an ending soon notification"""
        await self.broadcast_notification({
            "notification_type": "ending_soon",
            "event_reference": event_reference,
            "event_titulo": event_titulo,
            "minutes_remaining": minutes_remaining,
            "preco_atual": preco_atual
        })

    @property
    def connection_count(self) -> int:
        """Get the number of active connections"""
        return len(self.active_connections)


# Global instance
notification_ws_manager = NotificationWebSocketManager()
