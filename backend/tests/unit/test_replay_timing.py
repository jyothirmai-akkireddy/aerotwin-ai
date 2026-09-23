"""Unit tests verifying separation between Data Time and Wall-Clock Playback Time."""

import time

import pytest

from app.domain.entities.telemetry import TelemetryFrame, TelemetrySource
from app.infrastructure.replay.replay_source import ReplayTelemetrySource


@pytest.fixture
def mock_frames() -> list[TelemetryFrame]:
    frames = []
    # 5 frames at 0.1s data delta: t = 100.0, 100.1, 100.2, 100.3, 100.4
    for i in range(5):
        frames.append(
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
        )
    return frames


@pytest.mark.asyncio
async def test_data_time_is_invariant_under_speed_scaling(mock_frames):
    source = ReplayTelemetrySource(frames=mock_frames)
    source.set_speed(5.0)  # 5x playback speed

    emitted_frames = []
    async for frame in source.stream_frames(realtime=False):
        emitted_frames.append(frame)

    assert len(emitted_frames) == 5
    # Original timestamps must be 100% preserved
    for idx, frame in enumerate(emitted_frames):
        assert frame.timestamp == 100.0 + idx * 0.1


@pytest.mark.asyncio
async def test_wall_clock_delay_scales_with_speed(mock_frames):
    # At 10x speed, 4 intervals of 0.1s data dt (total 0.4s data time)
    # should take ~0.04s wall-clock time
    source = ReplayTelemetrySource(frames=mock_frames)
    source.set_speed(10.0)

    start_wall = time.perf_counter()
    count = 0
    async for _ in source.stream_frames(realtime=True):
        count += 1
    elapsed_wall = time.perf_counter() - start_wall

    assert count == 5
    # Wall clock duration should be roughly 0.04s (allowing tolerance for OS scheduler)
    assert 0.02 <= elapsed_wall <= 0.25
