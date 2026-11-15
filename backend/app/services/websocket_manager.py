"""
Real-Time WebSocket Connection Manager
Coordinates client lifecycles, broadcasting of live AI detection events,
camera status changes, and heartbeat telemetry.
"""

import time
import asyncio
import json
from typing import List, Dict, Any, Optional
from fastapi import WebSocket, WebSocketDisconnect

from app.core.logging import logger
from app.services.camera_stream import camera_manager
from app.services.dual_detector import dual_engine
from app.services.video_pipeline import video_pipeline


class WebSocketManager:
    """Manages active WebSocket client connections and broadcasts live vision telemetry."""

    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self._lock = asyncio.Lock()
        self._broadcast_task: Optional[asyncio.Task] = None
        self._is_broadcasting = False

    async def connect(self, websocket: WebSocket):
        """Accepts and registers a new WebSocket client connection."""
        await websocket.accept()
        async with self._lock:
            self.active_connections.append(websocket)
        logger.info(f"WebSocket client connected. Total active clients: {len(self.active_connections)}")

        # Send initial handshake payload
        await websocket.send_json({
            "event": "HANDSHAKE_ACK",
            "timestamp": time.time(),
            "camera_status": camera_manager.stream_info,
            "engine_status": dual_engine.status,
            "message": "Connected to Road Damage & Object Detection Stream"
        })

    async def disconnect(self, websocket: WebSocket):
        """Removes a disconnected client."""
        async with self._lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
        logger.info(f"WebSocket client disconnected. Total active clients: {len(self.active_connections)}")

    async def broadcast(self, message: Dict[str, Any]):
        """Dispatches JSON payload to all connected clients."""
        if not self.active_connections:
            return

        dead_connections = []
        async with self._lock:
            for connection in self.active_connections:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.warning(f"Failed to send to client: {e}")
                    dead_connections.append(connection)

            for dead in dead_connections:
                if dead in self.active_connections:
                    self.active_connections.remove(dead)

    def start_broadcasting(self):
        """Starts background broadcasting loop if not already running."""
        if self._is_broadcasting:
            return
        self._is_broadcasting = True

    def stop_broadcasting(self):
        """Halts background broadcasting."""
        self._is_broadcasting = False


ws_manager = WebSocketManager()
