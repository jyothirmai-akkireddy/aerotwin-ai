"""Realtime WebSocket endpoint and transport metrics."""

import asyncio
import json
import uuid
from typing import Any

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from app.api.dependencies import (
    get_realtime_service,
    get_settings,
    get_websocket_broadcast_manager,
)
from app.application.services.realtime_service import RealtimeTelemetryService
from app.config import AppSettings
from app.infrastructure.logging.logger import get_logger
from app.infrastructure.websocket.broadcaster import WebSocketBroadcastManager
from app.infrastructure.websocket.protocol import (
    CommandMessage,
    ErrorMessage,
    StatusMessage,
)

logger = get_logger("aerotwin.api.websocket")

router = APIRouter(tags=["realtime"])


@router.websocket("/api/v1/ws/telemetry")
async def websocket_telemetry_endpoint(
    websocket: WebSocket,
    broadcaster: WebSocketBroadcastManager = Depends(get_websocket_broadcast_manager),
    realtime_service: RealtimeTelemetryService = Depends(get_realtime_service),
    settings: AppSettings = Depends(get_settings),
) -> None:
    """Versioned v1.0.0 WebSocket endpoint for streaming real-time engine telemetry."""
    await websocket.accept()

    client_id = f"client-{uuid.uuid4().hex[:8]}"
    session = await broadcaster.register(client_id, websocket)

    if session is None:
        err = ErrorMessage(
            code="CLIENT_LIMIT_EXCEEDED",
            message=f"Maximum concurrent connections ({broadcaster.max_clients}) reached",
        )
        await websocket.send_text(err.model_dump_json())
        await websocket.close(code=1008)
        return

    # Ensure realtime publication loop is running when a client connects
    if not realtime_service.is_running and realtime_service.state != "paused":
        await realtime_service.start()

    init_status = StatusMessage(
        status="connected",
        message=f"AeroTwin AI Realtime Stream v1.0.0. Session ID: {client_id}",
    )
    await websocket.send_text(init_status.model_dump_json())

    async def writer():
        """Pulls messages from the client's bounded queue and sends over WebSocket."""
        try:
            while True:
                data = await session.queue.get()
                await websocket.send_text(data)
                session.queue.task_done()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.debug(f"Writer task terminated for {client_id}: {e}")

    async def reader():
        """Reads incoming client command or ping messages."""
        try:
            while True:
                raw_text = await websocket.receive_text()

                # Guard against oversized messages
                if len(raw_text.encode("utf-8")) > settings.websocket.max_message_size:
                    err = ErrorMessage(
                        code="OVERSIZED_MESSAGE",
                        message=f"Message size exceeds maximum allowed {settings.websocket.max_message_size} bytes",
                    )
                    await broadcaster.send_error_to_client(client_id, err)
                    continue

                try:
                    payload = json.loads(raw_text)
                except json.JSONDecodeError:
                    err = ErrorMessage(
                        code="INVALID_JSON",
                        message="Malformed JSON syntax received",
                    )
                    await broadcaster.send_error_to_client(client_id, err)
                    continue

                msg_type = payload.get("type")
                if msg_type == "ping":
                    ack = StatusMessage(
                        status="running" if realtime_service.is_running else "paused",
                        message="pong",
                    )
                    payload_json = ack.model_dump_json()
                    if not session.queue.full():
                        session.queue.put_nowait(payload_json)
                elif msg_type == "command":
                    try:
                        cmd = CommandMessage.model_validate(payload)
                        await realtime_service.execute_command(cmd.command, cmd.params)
                    except ValidationError as ve:
                        err = ErrorMessage(
                            code="INVALID_COMMAND",
                            message=f"Command validation failed: {ve.errors()[0].get('msg', 'Invalid command')}",
                        )
                        await broadcaster.send_error_to_client(client_id, err)
                else:
                    err = ErrorMessage(
                        code="UNKNOWN_MESSAGE_TYPE",
                        message=f"Unrecognized message type: '{msg_type}'",
                    )
                    await broadcaster.send_error_to_client(client_id, err)

        except (WebSocketDisconnect, asyncio.CancelledError):
            pass
        except Exception as e:
            logger.warning(f"Reader task error for {client_id}: {e}")

    writer_task = asyncio.create_task(writer(), name=f"ws-writer-{client_id}")
    reader_task = asyncio.create_task(reader(), name=f"ws-reader-{client_id}")

    try:
        done, pending = await asyncio.wait(
            [writer_task, reader_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
    finally:
        await broadcaster.unregister(client_id)
        try:
            await websocket.close()
        except Exception:
            pass


@router.get("/api/v1/ws/metrics")
async def get_websocket_metrics(
    broadcaster: WebSocketBroadcastManager = Depends(get_websocket_broadcast_manager),
    realtime_service: RealtimeTelemetryService = Depends(get_realtime_service),
) -> dict[str, Any]:
    """Retrieve realtime WebSocket transport diagnostics and backpressure statistics."""
    metrics = broadcaster.get_metrics()
    metrics["stream_state"] = realtime_service.state
    metrics["rate_hz"] = realtime_service.rate_hz
    return metrics
