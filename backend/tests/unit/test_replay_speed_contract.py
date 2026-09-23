"""Unit and integration tests for Phase 8 Playback Mode Normalization & Contract Enforcement.

Tests the approved contract:
- REALTIME: exactly 1.0x
- ACCELERATED: exactly 0.5x, 1.0x, 2.0x, 5.0x, 10.0x
- Invalid 0.25x is rejected for accelerated playback.
- MAX is not an externally supported playback speed (rejected with clear guidance to OFFLINE_BATCH).
- OFFLINE_BATCH runs unpaced.
- Replay data timestamps remain unchanged regardless of wall-clock playback speed.
"""

import time

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_replay_service
from app.application.services.replay_service import ReplayService
from app.domain.entities.telemetry import TelemetryFrame, TelemetrySource
from app.domain.replay.cursor import (
    APPROVED_REALTIME_SPEED,
    ReplayCursor,
)
from app.domain.replay.enums import ReplayExecutionMode
from app.infrastructure.replay.replay_source import ReplayTelemetrySource
from app.main import app

client = TestClient(app)


@pytest.fixture
def sample_timestamps() -> list[float]:
    return [100.0, 100.1, 100.2, 100.3, 100.4, 100.5]


@pytest.fixture
def sample_frames() -> list[TelemetryFrame]:
    return [
        TelemetryFrame(
            timestamp=100.0 + i * 0.1,
            sequence_id=i,
            source_type=TelemetrySource.REPLAY,
            rpm=2400.0,
            manifold_pressure=29.0,
            throttle_position=50.0,
            fuel_flow=15.0,
            fuel_pressure=3.0,
            injection_timing=20.0,
            cht=[90.0, 90.0, 90.0, 90.0],
            egt=[700.0, 700.0, 700.0, 700.0],
            coolant_temp=80.0,
            oil_temperature=85.0,
            oil_pressure=3.5,
            vibration_rms=1.0,
            battery_voltage=28.0,
            alternator_current=12.0,
            alternator_status="OK",
            altitude=1000.0,
            ambient_temp=15.0,
            true_airspeed=45.0,
        )
        for i in range(10)
    ]


def test_realtime_accepts_exactly_1x(sample_timestamps):
    """REALTIME accepts exactly 1.0x speed; other speeds raise ValueError."""
    cursor = ReplayCursor(timestamps=sample_timestamps)

    # Explicit REALTIME mode with 1.0x -> PASS
    cursor.set_speed(1.0, mode=ReplayExecutionMode.REALTIME)
    assert cursor.execution_mode == ReplayExecutionMode.REALTIME
    assert cursor.playback_speed == APPROVED_REALTIME_SPEED

    # Inferred REALTIME mode with 1.0x -> PASS
    cursor.set_speed(1.0)
    assert cursor.execution_mode == ReplayExecutionMode.REALTIME
    assert cursor.playback_speed == 1.0

    # Helper method set_execution_mode
    cursor.set_execution_mode(ReplayExecutionMode.REALTIME)
    assert cursor.execution_mode == ReplayExecutionMode.REALTIME
    assert cursor.playback_speed == 1.0

    # REALTIME with any other speed must raise ValueError
    with pytest.raises(ValueError, match="REALTIME execution mode accepts exactly 1.0x speed"):
        cursor.set_speed(2.0, mode=ReplayExecutionMode.REALTIME)

    with pytest.raises(ValueError, match="REALTIME execution mode accepts exactly 1.0x speed"):
        cursor.set_speed(0.5, mode=ReplayExecutionMode.REALTIME)


def test_accelerated_accepts_approved_speeds(sample_timestamps):
    """ACCELERATED accepts exactly 0.5x, 1.0x, 2.0x, 5.0x, 10.0x."""
    cursor = ReplayCursor(timestamps=sample_timestamps)

    for spd in [0.5, 1.0, 2.0, 5.0, 10.0]:
        cursor.set_speed(spd, mode=ReplayExecutionMode.ACCELERATED)
        assert cursor.execution_mode == ReplayExecutionMode.ACCELERATED
        assert cursor.playback_speed == spd

    # Inferred ACCELERATED mode for speeds != 1.0
    for spd in [0.5, 2.0, 5.0, 10.0]:
        cursor.set_speed(spd)
        assert cursor.execution_mode == ReplayExecutionMode.ACCELERATED
        assert cursor.playback_speed == spd


def test_invalid_quarter_speed_rejected(sample_timestamps, sample_frames):
    """Invalid 0.25x speed is strictly rejected for playback."""
    cursor = ReplayCursor(timestamps=sample_timestamps)

    # Direct cursor rejection
    with pytest.raises(ValueError, match=r"0\.25x and other arbitrary speeds are rejected"):
        cursor.set_speed(0.25, mode=ReplayExecutionMode.ACCELERATED)

    with pytest.raises(ValueError, match=r"Playback speed 0\.25x is not permitted"):
        cursor.set_speed(0.25)

    # Service layer rejection
    source = ReplayTelemetrySource(frames=sample_frames)
    with pytest.raises(ValueError):
        source.set_speed(0.25)

    service = ReplayService()
    service._active_source = source
    with pytest.raises(ValueError, match=r"Playback speed 0\.25x is not permitted"):
        service.control("speed", 0.25)

    # API route rejection: returns HTTP 400 Bad Request
    app.dependency_overrides[get_replay_service] = lambda: service
    try:
        resp = client.post("/api/v1/replay/control", json={"action": "speed", "target": 0.25})
        assert resp.status_code == 400
        assert "0.25" in resp.json()["message"]
    finally:
        app.dependency_overrides.clear()


def test_max_pseudo_speed_rejected(sample_timestamps, sample_frames):
    """MAX is not an externally supported playback speed; rejected with guidance to OFFLINE_BATCH."""
    source = ReplayTelemetrySource(frames=sample_frames)
    service = ReplayService()
    service._active_source = source

    # Service control rejects "MAX"
    with pytest.raises(ValueError, match="MAX is not an externally supported playback speed"):
        service.control("speed", "MAX")

    with pytest.raises(ValueError, match="MAX is not an externally supported mode"):
        service.control("mode", "MAX")

    # API route rejects "MAX" with HTTP 400 Bad Request
    app.dependency_overrides[get_replay_service] = lambda: service
    try:
        resp = client.post("/api/v1/replay/control", json={"action": "speed", "target": "MAX"})
        assert resp.status_code == 400
        assert "MAX is not an externally supported playback speed" in resp.json()["message"]

        resp_mode = client.post("/api/v1/replay/control", json={"action": "mode", "target": "MAX"})
        assert resp_mode.status_code == 400
        assert "MAX is not an externally supported mode" in resp_mode.json()["message"]
    finally:
        app.dependency_overrides.clear()


def test_offline_batch_runs_unpaced(sample_timestamps, sample_frames):
    """OFFLINE_BATCH execution mode is unpaced and sets speed to 0.0."""
    cursor = ReplayCursor(timestamps=sample_timestamps)

    # Direct cursor configuration
    cursor.set_speed(0.0, mode=ReplayExecutionMode.OFFLINE_BATCH)
    assert cursor.execution_mode == ReplayExecutionMode.OFFLINE_BATCH
    assert cursor.playback_speed == 0.0

    cursor.set_speed(0.0)
    assert cursor.execution_mode == ReplayExecutionMode.OFFLINE_BATCH
    assert cursor.playback_speed == 0.0

    cursor.set_execution_mode(ReplayExecutionMode.OFFLINE_BATCH)
    assert cursor.execution_mode == ReplayExecutionMode.OFFLINE_BATCH
    assert cursor.playback_speed == 0.0

    # Service control via action="speed", target="OFFLINE_BATCH"
    source = ReplayTelemetrySource(frames=sample_frames)
    service = ReplayService()
    service._active_source = source

    status = service.control("speed", "OFFLINE_BATCH")
    assert status.execution_mode == ReplayExecutionMode.OFFLINE_BATCH
    assert status.playback_speed == 0.0

    # Service control via action="mode", target="OFFLINE_BATCH"
    status_mode = service.control("mode", "OFFLINE_BATCH")
    assert status_mode.execution_mode == ReplayExecutionMode.OFFLINE_BATCH
    assert status_mode.playback_speed == 0.0


@pytest.mark.asyncio
async def test_offline_batch_streaming_is_unpaced(sample_frames):
    """ReplayTelemetrySource.stream_frames() bypasses sleep in OFFLINE_BATCH mode."""
    source = ReplayTelemetrySource(frames=sample_frames)
    source.set_speed(0.0, mode=ReplayExecutionMode.OFFLINE_BATCH)

    start_wall = time.perf_counter()
    emitted = []
    async for frame in source.stream_frames(realtime=True):
        emitted.append(frame)
    duration_wall = time.perf_counter() - start_wall

    assert len(emitted) == 10
    # In OFFLINE_BATCH, 10 frames with realtime=True should process immediately without paced delays (< 0.05s)
    assert duration_wall < 0.05


@pytest.mark.asyncio
async def test_replay_data_timestamps_invariant_under_all_speeds(sample_frames):
    """Replay data timestamps remain strictly identical regardless of wall-clock speed/mode."""
    expected_timestamps = [100.0 + i * 0.1 for i in range(10)]

    for speed in [0.5, 1.0, 2.0, 5.0, 10.0]:
        source = ReplayTelemetrySource(frames=sample_frames)
        source.set_speed(speed)

        emitted = []
        async for frame in source.stream_frames(realtime=False):
            emitted.append(frame)

        actual_timestamps = [f.timestamp for f in emitted]
        assert actual_timestamps == expected_timestamps, f"Mismatch at speed {speed}"

    # Also test OFFLINE_BATCH
    batch_source = ReplayTelemetrySource(frames=sample_frames)
    batch_source.set_speed(0.0, mode=ReplayExecutionMode.OFFLINE_BATCH)
    emitted_batch = []
    async for frame in batch_source.stream_frames(realtime=False):
        emitted_batch.append(frame)

    actual_batch_timestamps = [f.timestamp for f in emitted_batch]
    assert actual_batch_timestamps == expected_timestamps
