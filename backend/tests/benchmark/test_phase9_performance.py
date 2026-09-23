"""Performance and multi-client scalability benchmark.

SIH26054 — AeroTwin AI
Phase 9 Performance Gate

Validates:
1. 1000-frame disaggregated analytical latency benchmarking:
   - Physics Twin latency (p50, p95, p99)
   - ML Inference latency (p50, p95, p99)
   - Prognostics latency (p50, p95, p99)
   - End-to-end frame serialization latency (p50, p95, p99)
2. Multi-client broadcast scalability (1, 5, 10, 25, 50 clients).
3. Slow client isolation: bounded queue drop policy protects fast clients from slow consumers.
4. All test scenarios explicitly tagged as SYNTHETIC / PROTOTYPE SCENARIO.
"""

import json
import time
from unittest.mock import AsyncMock

import numpy as np
import pytest

from app.application.services.ml_service import MLInferenceService
from app.application.services.physics_twin_service import PhysicsTwinService
from app.application.services.prognostics_service import PrognosticsService
from app.infrastructure.logging.logger import get_logger
from app.infrastructure.physics.calibration_repository import PhysicsCalibrationRepository
from app.infrastructure.simulation.engine_simulator import EngineSimulator
from app.infrastructure.websocket.broadcaster import WebSocketBroadcastManager

logger = get_logger("aerotwin.benchmark.performance")

PROTOTYPE_SCENARIO_TAG = "SYNTHETIC / PROTOTYPE SCENARIO — Phase 9 Performance Benchmark"


def test_analytical_pipeline_1000_frames_latency():
    """Benchmark disaggregated execution latency across >= 1000 consecutive frames."""
    logger.info(f"Executing: {PROTOTYPE_SCENARIO_TAG} - 1000 Frames Latency")

    sim = EngineSimulator(telemetry_rate_hz=10)
    cal_repo = PhysicsCalibrationRepository()
    physics_service = PhysicsTwinService(calibration_repo=cal_repo)
    ml_service = MLInferenceService()
    prognostics_service = PrognosticsService()

    physics_latencies_ms: list[float] = []
    ml_latencies_ms: list[float] = []
    prognostics_latencies_ms: list[float] = []
    e2e_latencies_ms: list[float] = []

    target_frames = 1000
    for _ in range(target_frames):
        frame = sim.step()

        t0 = time.perf_counter()
        p_res = physics_service.evaluate_frame(frame)
        t1 = time.perf_counter()
        m_res = ml_service.evaluate(frame, p_res)
        t2 = time.perf_counter()
        prog_res = prognostics_service.evaluate(frame, p_res, m_res)
        t3 = time.perf_counter()

        # Serialization to JSON
        _ = json.dumps(
            {
                "physics": p_res.model_dump(mode="json"),
                "ml": m_res.model_dump(mode="json"),
                "prognostics": prog_res.model_dump(mode="json"),
            }
        )
        t4 = time.perf_counter()

        physics_latencies_ms.append((t1 - t0) * 1000.0)
        ml_latencies_ms.append((t2 - t1) * 1000.0)
        prognostics_latencies_ms.append((t3 - t2) * 1000.0)
        e2e_latencies_ms.append((t4 - t0) * 1000.0)

    # Compute percentiles
    p50_phys = np.percentile(physics_latencies_ms, 50)
    p95_phys = np.percentile(physics_latencies_ms, 95)
    p99_phys = np.percentile(physics_latencies_ms, 99)

    p50_ml = np.percentile(ml_latencies_ms, 50)
    p95_ml = np.percentile(ml_latencies_ms, 95)
    p99_ml = np.percentile(ml_latencies_ms, 99)

    p50_prog = np.percentile(prognostics_latencies_ms, 50)
    p95_prog = np.percentile(prognostics_latencies_ms, 95)
    p99_prog = np.percentile(prognostics_latencies_ms, 99)

    p50_e2e = np.percentile(e2e_latencies_ms, 50)
    p95_e2e = np.percentile(e2e_latencies_ms, 95)
    p99_e2e = np.percentile(e2e_latencies_ms, 99)

    logger.info(
        f"1000-Frame Latency Benchmark Results:\n"
        f"  Physics Twin    : p50={p50_phys:.3f}ms | p95={p95_phys:.3f}ms | p99={p99_phys:.3f}ms\n"
        f"  ML Diagnostics  : p50={p50_ml:.3f}ms | p95={p95_ml:.3f}ms | p99={p99_ml:.3f}ms\n"
        f"  Prognostics     : p50={p50_prog:.3f}ms | p95={p95_prog:.3f}ms | p99={p99_prog:.3f}ms\n"
        f"  End-to-End E2E  : p50={p50_e2e:.3f}ms | p95={p95_e2e:.3f}ms | p99={p99_e2e:.3f}ms"
    )

    # Verification assertions (prototype engineering limits)
    assert p50_phys < 5.0, f"Physics p50 latency {p50_phys:.2f}ms exceeded 5.0ms target"
    assert p50_ml < 15.0, f"ML p50 latency {p50_ml:.2f}ms exceeded 15.0ms target"
    assert p50_prog < 5.0, f"Prognostics p50 latency {p50_prog:.2f}ms exceeded 5.0ms target"
    assert p95_e2e < 50.0, f"E2E p95 latency {p95_e2e:.2f}ms exceeded 50.0ms target"


@pytest.mark.asyncio
async def test_multi_client_broadcast_scalability():
    """Verify broadcaster scalability and throughput across 1, 5, 10, 25, 50 clients."""
    logger.info(f"Executing: {PROTOTYPE_SCENARIO_TAG} - Multi-Client Scalability")

    client_counts = [1, 5, 10, 25, 50]
    frames_to_broadcast = 50

    for num_clients in client_counts:
        broadcaster = WebSocketBroadcastManager(max_clients=num_clients + 5, queue_size=500)
        sessions = []
        for i in range(num_clients):
            mock_ws = AsyncMock()
            session = await broadcaster.register(f"client-{i}", websocket=mock_ws)
            sessions.append(session)

        # Generate sample frame and message
        sim = EngineSimulator(telemetry_rate_hz=10)
        cal_repo = PhysicsCalibrationRepository()
        phys = PhysicsTwinService(calibration_repo=cal_repo)
        f = sim.step()
        p = phys.evaluate_frame(f)

        from app.infrastructure.websocket.protocol import TelemetryMessage

        msg = TelemetryMessage(
            timestamp=f.timestamp,
            sequence_id=f.sequence_id,
            server_time=time.time(),
            source_mode="LIVE",
            payload=f,
            physics=p,
        )

        t_start = time.perf_counter()
        for _ in range(frames_to_broadcast):
            await broadcaster.broadcast_telemetry(msg)
        elapsed_sec = time.perf_counter() - t_start

        rate = (frames_to_broadcast * num_clients) / max(0.0001, elapsed_sec)

        # Check queue depth in each client
        for session in sessions:
            assert session.queue.qsize() == frames_to_broadcast
            await broadcaster.unregister(session.client_id)

        logger.info(
            f"Clients: {num_clients:2d} | Broadcast time: {elapsed_sec * 1000.0:.2f}ms | "
            f"Message Throughput: {rate:.0f} msg/sec"
        )


@pytest.mark.asyncio
async def test_slow_client_isolation():
    """Verify that a slow consumer dropping frames does not block fast clients or pipeline."""
    logger.info(f"Executing: {PROTOTYPE_SCENARIO_TAG} - Slow Client Isolation")

    broadcaster = WebSocketBroadcastManager(max_clients=10, queue_size=10)

    # Fast client 1
    s_fast = await broadcaster.register("fast-client", websocket=AsyncMock())
    # Slow client 2 (will never consume)
    s_slow = await broadcaster.register("slow-client", websocket=AsyncMock())

    sim = EngineSimulator(telemetry_rate_hz=10)
    from app.infrastructure.websocket.protocol import TelemetryMessage

    # Broadcast 50 frames while fast client drains immediately and slow client never drains
    fast_received = 0
    for _i in range(50):
        f = sim.step()
        msg = TelemetryMessage(
            timestamp=f.timestamp,
            sequence_id=f.sequence_id,
            server_time=time.time(),
            source_mode="LIVE",
            payload=f,
        )
        await broadcaster.broadcast_telemetry(msg)

        # Fast client consumes immediately
        if not s_fast.queue.empty():
            s_fast.queue.get_nowait()
            s_fast.queue.task_done()
            fast_received += 1

    # Fast client consumed all 50 frames with 0 drops
    assert fast_received == 50
    assert s_fast.frames_dropped == 0

    # Slow client's bounded queue of size 10 must have dropped 40 frames without crashing
    assert s_slow.queue.qsize() == 10
    assert s_slow.frames_dropped == 40

    await broadcaster.unregister("fast-client")
    await broadcaster.unregister("slow-client")

    logger.info(
        "Slow client isolation verified: Fast client received 50 frames (0 drops); Slow client dropped 40 frames safely."
    )
