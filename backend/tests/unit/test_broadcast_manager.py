"""Unit tests for WebSocketBroadcastManager, client limits, and backpressure."""

from unittest.mock import AsyncMock

import pytest

from app.domain.entities.telemetry import QualityStatus, TelemetryFrame, TelemetrySource
from app.infrastructure.websocket.broadcaster import WebSocketBroadcastManager
from app.infrastructure.websocket.protocol import TelemetryMessage


def _dummy_frame(seq: int = 1) -> TelemetryFrame:
    return TelemetryFrame(
        version="1.0.0",
        timestamp=100.0 + seq,
        sequence_id=seq,
        source_type=TelemetrySource.SIMULATED,
        quality_flag=QualityStatus.VALID,
        rpm=2500.0,
        manifold_pressure=30.0,
        throttle_position=50.0,
        fuel_flow=17.0,
        fuel_pressure=3.5,
        injection_timing=25.0,
        cht=[100.0, 100.0, 100.0, 100.0],
        egt=[700.0, 700.0, 700.0, 700.0],
        coolant_temp=80.0,
        oil_temperature=85.0,
        oil_pressure=4.0,
        vibration_rms=1.0,
        battery_voltage=28.0,
        alternator_current=20.0,
        alternator_status="OK",
        altitude=1200.0,
        ambient_temp=12.0,
        true_airspeed=50.0,
    )


@pytest.mark.asyncio
async def test_broadcast_manager_registration():
    """Verify client registration and count tracking."""
    manager = WebSocketBroadcastManager(max_clients=2, queue_size=5)
    mock_ws = AsyncMock()

    session1 = await manager.register("client-1", mock_ws)
    assert session1 is not None
    assert manager.active_client_count == 1

    session2 = await manager.register("client-2", mock_ws)
    assert session2 is not None
    assert manager.active_client_count == 2

    # Exceed maximum client limit
    session3 = await manager.register("client-3", mock_ws)
    assert session3 is None
    assert manager.active_client_count == 2

    # Clean unregister
    await manager.unregister("client-1")
    assert manager.active_client_count == 1


@pytest.mark.asyncio
async def test_broadcast_manager_multi_client_dispatch():
    """Verify that multiple clients receive identical broadcast payloads."""
    manager = WebSocketBroadcastManager(max_clients=5, queue_size=10)
    mock_ws1 = AsyncMock()
    mock_ws2 = AsyncMock()

    s1 = await manager.register("c1", mock_ws1)
    s2 = await manager.register("c2", mock_ws2)

    frame = _dummy_frame(seq=101)
    msg = TelemetryMessage(
        timestamp=frame.timestamp,
        sequence_id=frame.sequence_id,
        server_time=123456.0,
        payload=frame,
    )

    await manager.broadcast_telemetry(msg)

    assert s1.queue.qsize() == 1
    assert s2.queue.qsize() == 1

    msg_c1 = await s1.queue.get()
    msg_c2 = await s2.queue.get()
    assert msg_c1 == msg_c2
    assert '"sequence_id":101' in msg_c1


@pytest.mark.asyncio
async def test_backpressure_latest_value_drop_strategy():
    """Verify that a slow client queue drops oldest frame and keeps newest."""
    # Queue size = 2
    manager = WebSocketBroadcastManager(max_clients=2, queue_size=2)
    mock_ws = AsyncMock()
    session = await manager.register("slow-client", mock_ws)

    # Send 3 messages to queue of size 2
    for i in range(1, 4):
        f = _dummy_frame(seq=i)
        m = TelemetryMessage(timestamp=f.timestamp, sequence_id=f.sequence_id, payload=f)
        await manager.broadcast_telemetry(m)

    assert session.queue.qsize() == 2
    assert session.frames_dropped == 1
    metrics = manager.get_metrics()
    assert metrics["total_dropped_frames"] == 1

    # First message in queue should now be seq=2 (seq=1 was dropped)
    first_msg = await session.queue.get()
    assert '"sequence_id":2' in first_msg

    # Second message should be seq=3
    second_msg = await session.queue.get()
    assert '"sequence_id":3' in second_msg
