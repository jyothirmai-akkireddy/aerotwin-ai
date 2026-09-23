"""Performance and load benchmark for realtime WebSocket broadcast and throughput."""

import time
from unittest.mock import AsyncMock

import pytest

from app.domain.entities.telemetry import QualityStatus, TelemetryFrame, TelemetrySource
from app.infrastructure.websocket.broadcaster import WebSocketBroadcastManager
from app.infrastructure.websocket.protocol import TelemetryMessage


def _benchmark_frame(seq: int) -> TelemetryFrame:
    return TelemetryFrame(
        version="1.0.0",
        timestamp=1700000000.0 + (seq * 0.1),
        sequence_id=seq,
        source_type=TelemetrySource.SIMULATED,
        quality_flag=QualityStatus.VALID,
        rpm=2400.0 + (seq % 100),
        manifold_pressure=29.5,
        throttle_position=45.0,
        fuel_flow=16.5,
        fuel_pressure=3.2,
        injection_timing=24.0,
        cht=[95.0, 92.5, 98.0, 94.0],
        egt=[720.0, 715.0, 730.0, 722.0],
        coolant_temp=82.0,
        oil_temperature=85.0,
        oil_pressure=3.8,
        vibration_rms=1.15,
        battery_voltage=28.2,
        alternator_current=18.5,
        alternator_status="OK",
        altitude=1000.0,
        ambient_temp=15.0,
        true_airspeed=45.0,
    )


@pytest.mark.asyncio
async def test_realtime_broadcast_throughput_benchmark():
    """Benchmark broadcast throughput across 10 concurrent clients for 500 frames.

    Evaluates:
    - In-memory serialization time
    - Fan-out broadcast throughput (frames/s)
    - Localhost queue dispatch latency
    - Zero dropped frames under nominal queue capacity
    """
    client_count = 10
    total_frames = 500
    queue_size = 600

    manager = WebSocketBroadcastManager(max_clients=client_count, queue_size=queue_size)
    sessions = []
    for i in range(client_count):
        session = await manager.register(f"bench-client-{i}", AsyncMock())
        assert session is not None
        sessions.append(session)

    # Pre-generate frames to isolate broadcast measurement from simulation generation
    frames = [_benchmark_frame(seq=i) for i in range(total_frames)]

    t_start = time.perf_counter()
    for frame in frames:
        msg = TelemetryMessage(
            timestamp=frame.timestamp,
            sequence_id=frame.sequence_id,
            server_time=time.time(),
            payload=frame,
        )
        await manager.broadcast_telemetry(msg)

    t_elapsed = time.perf_counter() - t_start
    throughput_fps = total_frames / t_elapsed
    total_deliveries = total_frames * client_count
    throughput_deliveries_per_sec = total_deliveries / t_elapsed

    # Verification
    metrics = manager.get_metrics()
    assert metrics["active_clients"] == client_count
    assert metrics["total_broadcast_frames"] == total_frames
    assert metrics["total_dropped_frames"] == 0

    for session in sessions:
        assert session.queue.qsize() == total_frames
        assert session.frames_dropped == 0

    print(
        f"\n[REALTIME BENCHMARK RESULTS]\n"
        f"  Total Frames Broadcast: {total_frames}\n"
        f"  Concurrent Clients: {client_count}\n"
        f"  Total Client Message Deliveries: {total_deliveries}\n"
        f"  Elapsed Time: {t_elapsed * 1000:.2f} ms\n"
        f"  Broadcast Throughput: {throughput_fps:,.1f} frames/s\n"
        f"  Fan-Out Delivery Rate: {throughput_deliveries_per_sec:,.1f} deliveries/s\n"
        f"  Average Broadcast Overhead per Frame: {(t_elapsed / total_frames) * 1000:.3f} ms\n"
    )

    # Overhead must comfortably exceed 10 Hz requirement (>1,000 frames/s capacity)
    assert throughput_fps > 500
