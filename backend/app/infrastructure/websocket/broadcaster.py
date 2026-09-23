"""Thread-safe WebSocket broadcast manager with per-client bounded queues and backpressure."""

import asyncio
import time
from dataclasses import dataclass
from typing import Any

from fastapi import WebSocket

from app.infrastructure.logging.logger import get_logger
from app.infrastructure.websocket.protocol import (
    ErrorMessage,
    HeartbeatMessage,
    StatusMessage,
    TelemetryMessage,
)

logger = get_logger("aerotwin.websocket.broadcaster")


@dataclass
class ClientSession:
    """State tracking for an active WebSocket client session."""

    client_id: str
    websocket: WebSocket
    queue: asyncio.Queue[str]
    connected_at: float
    frames_sent: int = 0
    frames_dropped: int = 0


class WebSocketBroadcastManager:
    """Manages active WebSocket connections, enforces client limits,

    and delivers messages via bounded queues with a latest-value drop strategy.
    """

    def __init__(self, max_clients: int = 50, queue_size: int = 100):
        self.max_clients = max_clients
        self.queue_size = queue_size
        self._clients: dict[str, ClientSession] = {}
        self._lock = asyncio.Lock()
        self._total_broadcast_frames: int = 0
        self._total_dropped_frames: int = 0

    @property
    def active_client_count(self) -> int:
        """Return the current number of connected clients."""
        return len(self._clients)

    async def register(self, client_id: str, websocket: WebSocket) -> ClientSession | None:
        """Register a new client connection if below max_clients limit."""
        async with self._lock:
            if len(self._clients) >= self.max_clients:
                logger.warning(
                    f"Connection rejected for client {client_id}: limit of {self.max_clients} reached"
                )
                return None

            queue: asyncio.Queue[str] = asyncio.Queue(maxsize=self.queue_size)
            session = ClientSession(
                client_id=client_id,
                websocket=websocket,
                queue=queue,
                connected_at=time.time(),
            )
            self._clients[client_id] = session
            logger.info(
                f"Client {client_id} connected. Active clients: {len(self._clients)}/{self.max_clients}"
            )
            return session

    async def unregister(self, client_id: str) -> None:
        """Unregister a client connection and clean up its resources."""
        async with self._lock:
            session = self._clients.pop(client_id, None)
            if session:
                duration = time.time() - session.connected_at
                logger.info(
                    f"Client {client_id} disconnected after {duration:.1f}s. "
                    f"Sent: {session.frames_sent}, Dropped: {session.frames_dropped}. "
                    f"Remaining clients: {len(self._clients)}"
                )

    async def broadcast_telemetry(self, message: TelemetryMessage) -> None:
        """Serialize once and broadcast telemetry message to all registered clients.

        Enforces latest-value backpressure: if a client queue is full, the oldest
        frame is discarded to prevent lag and buffer bloat.
        """
        payload = message.model_dump_json()
        self._total_broadcast_frames += 1

        async with self._lock:
            for session in list(self._clients.values()):
                if session.queue.full():
                    try:
                        # Drop oldest unconsumed frame (latest-value policy)
                        session.queue.get_nowait()
                        session.frames_dropped += 1
                        self._total_dropped_frames += 1
                    except asyncio.QueueEmpty:
                        pass
                try:
                    session.queue.put_nowait(payload)
                    session.frames_sent += 1
                except asyncio.QueueFull:
                    # Queue is full even after eviction attempt (rare race condition)
                    session.frames_dropped += 1
                    self._total_dropped_frames += 1

    async def broadcast_status(self, message: StatusMessage) -> None:
        """Broadcast status message to all connected clients."""
        payload = message.model_dump_json()
        async with self._lock:
            for session in list(self._clients.values()):
                if session.queue.full():
                    try:
                        session.queue.get_nowait()
                        session.frames_dropped += 1
                    except asyncio.QueueEmpty:
                        pass
                try:
                    session.queue.put_nowait(payload)
                except asyncio.QueueFull:
                    pass

    async def broadcast_heartbeat(self, message: HeartbeatMessage) -> None:
        """Broadcast heartbeat ping to all connected clients."""
        payload = message.model_dump_json()
        async with self._lock:
            for session in list(self._clients.values()):
                if not session.queue.full():
                    try:
                        session.queue.put_nowait(payload)
                    except asyncio.QueueFull:
                        pass

    async def send_error_to_client(self, client_id: str, error: ErrorMessage) -> None:
        """Send a targeted, safe error message to a specific client."""
        payload = error.model_dump_json()
        session = self._clients.get(client_id)
        if session and not session.queue.full():
            try:
                session.queue.put_nowait(payload)
            except asyncio.QueueFull:
                pass

    def get_metrics(self) -> dict[str, Any]:
        """Retrieve real-time transport diagnostic metrics."""
        return {
            "active_clients": len(self._clients),
            "max_clients": self.max_clients,
            "queue_size": self.queue_size,
            "total_broadcast_frames": self._total_broadcast_frames,
            "total_dropped_frames": self._total_dropped_frames,
        }
