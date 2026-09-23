"""End-to-End LIVE pipeline integration test.

Validates:
EngineSimulator -> TelemetryFrame -> RealtimeTelemetryService -> PhysicsTwinService
-> MLInferenceService -> PrognosticsService -> WebSocket broadcast.

Continuously runs for 60 seconds of telemetry (600 frames at 10 Hz) and measures
sequence monotonicity, timestamp validity, zero drops, zero duplicates,
and disaggregated processing latencies.
"""

import asyncio
import json
import statistics
import time
from unittest.mock import AsyncMock

import pytest

from app.application.services.ml_service import MLInferenceService
from app.application.services.physics_twin_service import PhysicsTwinService
from app.application.services.prognostics_service import PrognosticsService
from app.application.services.realtime_service import RealtimeTelemetryService
from app.infrastructure.logging.logger import get_logger
from app.infrastructure.physics.calibration_repository import PhysicsCalibrationRepository
from app.infrastructure.simulation.engine_simulator import EngineSimulator
from app.infrastructure.telemetry.synthetic_source import SyntheticTelemetrySource
from app.infrastructure.websocket.broadcaster import WebSocketBroadcastManager

logger = get_logger("aerotwin.test.pipeline_e2e")


@pytest.mark.asyncio
async def test_live_pipeline_e2e_60_seconds():
    """Verify complete analytical telemetry flow across 600 consecutive frames (60 seconds at 10 Hz)."""
    # 1. Instantiate full stack singletons
    simulator = EngineSimulator(telemetry_rate_hz=10)
    source = SyntheticTelemetrySource(simulator=simulator)
    broadcaster = WebSocketBroadcastManager(max_clients=10, queue_size=2000)

    calibration_repo = PhysicsCalibrationRepository()
    physics_service = PhysicsTwinService(calibration_repo=calibration_repo)
    ml_service = MLInferenceService()
    prognostics_service = PrognosticsService()

    realtime_service = RealtimeTelemetryService(
        telemetry_source=source,
        broadcaster=broadcaster,
        rate_hz=100,  # Fast processing rate to execute 600 frames cleanly without backpressure drops
        strict_validation=True,
        heartbeat_interval_sec=10.0,
        physics_service=physics_service,
        ml_service=ml_service,
        prognostics_service=prognostics_service,
    )

    # 2. Register mock client session
    client_id = "test-live-client-001"
    mock_ws = AsyncMock()
    session = await broadcaster.register(client_id, websocket=mock_ws)
    assert session is not None, "Failed to register mock client session"

    target_frames = 600
    received_frames = []
    e2e_latencies_ms = []

    # 3. Start realtime streaming loop
    await realtime_service.start()

    start_wall = time.perf_counter()
    try:
        while len(received_frames) < target_frames:
            t_recv_start = time.perf_counter()
            raw_msg = await asyncio.wait_for(session.queue.get(), timeout=5.0)
            session.queue.task_done()
            t_recv_end = time.perf_counter()
            e2e_latencies_ms.append((t_recv_end - t_recv_start) * 1000.0)

            msg = json.loads(raw_msg)
            if msg.get("type") == "telemetry":
                received_frames.append(msg)
    finally:
        await realtime_service.stop()
        await broadcaster.unregister(client_id)

    total_wall_sec = time.perf_counter() - start_wall

    # 4. Assert frame count and integrity
    assert len(received_frames) == target_frames, (
        f"Expected {target_frames} frames, received {len(received_frames)}"
    )

    prev_seq = None
    prev_time = None
    duplicate_count = 0
    ordering_violations = 0
    seen_sequences = set()

    ml_latencies = []
    prognostics_latencies = []

    for idx, frame in enumerate(received_frames):
        # A. Protocol and metadata
        assert frame["type"] == "telemetry"
        assert frame.get("source_mode") == "LIVE"
        assert "payload" in frame

        seq = frame["sequence_id"]
        ts = frame["timestamp"]

        # Duplicate checking
        if seq in seen_sequences:
            duplicate_count += 1
        seen_sequences.add(seq)

        # Monotonicity checking
        if prev_seq is not None:
            if seq != prev_seq + 1:
                ordering_violations += 1
        if prev_time is not None:
            assert ts > prev_time, f"Timestamp non-monotonic at frame {idx}: {ts} <= {prev_time}"

        prev_seq = seq
        prev_time = ts

        # B. Physics Twin Output Verification
        assert "physics" in frame and frame["physics"] is not None
        phys = frame["physics"]
        assert "expected_state" in phys
        assert "residuals" in phys
        assert phys["residuals"]["validity"] in ("VALID", "DEGRADED", "INVALID")
        assert "cht" in phys["residuals"]["raw_residuals"]
        assert len(phys["residuals"]["raw_residuals"]["cht"]) == 4

        # C. ML Inference Output Verification
        assert "ml" in frame and frame["ml"] is not None
        ml = frame["ml"]
        assert "anomaly" in ml
        assert isinstance(ml["anomaly"]["flag"], bool)
        assert 0.0 <= ml["anomaly"]["score"] <= 1.0
        assert "fault" in ml
        assert ml["fault"]["fault_class"] is not None
        assert ml["fault"]["reason"] in (
            "CONFIDENT_MATCH",
            "NOMINAL_FLIGHT",
            "LOW_CONFIDENCE",
            "OUT_OF_DISTRIBUTION",
        )
        if "inference_latency_ms" in ml:
            ml_latencies.append(ml["inference_latency_ms"])

        # D. Prognostics Output Verification
        assert "prognostics" in frame and frame["prognostics"] is not None
        prog = frame["prognostics"]
        assert 0.0 <= prog["health_index"] <= 1.0
        assert prog["degradation_state"] in (
            "NOMINAL",
            "EARLY_DEGRADATION",
            "MODERATE_DEGRADATION",
            "SEVERE_DEGRADATION",
            "CRITICAL_SIMULATED_STATE",
        )
        assert prog["trend_direction"] in ("STABLE", "DEGRADING", "IMPROVING", "UNKNOWN")
        assert "subsystems" in prog
        if "pipeline_latency_ms" in prog:
            prognostics_latencies.append(prog["pipeline_latency_ms"])

    # 5. Assert Zero Frame Integrity Violations
    assert duplicate_count == 0, f"Detected {duplicate_count} duplicate frames"
    assert ordering_violations == 0, f"Detected {ordering_violations} sequence ordering violations"

    # 6. Compute and report performance statistics
    avg_ml_lat = statistics.mean(ml_latencies) if ml_latencies else 0.0
    avg_prog_lat = statistics.mean(prognostics_latencies) if prognostics_latencies else 0.0
    avg_e2e_lat = statistics.mean(e2e_latencies_ms) if e2e_latencies_ms else 0.0

    logger.info(
        f"LIVE E2E Pipeline 60s Benchmark: 600 frames processed in {total_wall_sec:.2f}s "
        f"({600 / total_wall_sec:.1f} fps). "
        f"Mean ML latency: {avg_ml_lat:.3f}ms | Mean Prog latency: {avg_prog_lat:.3f}ms | "
        f"Mean Frame Queue Delay: {avg_e2e_lat:.3f}ms. Drops: 0, Dups: 0, OrderViolations: 0."
    )
