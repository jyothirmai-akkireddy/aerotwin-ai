"""Unit test verifying that replayed frames drive the full downstream Physics, ML, and Prognostics stack."""

import pytest

from app.api.dependencies import (
    get_ml_inference_service,
    get_physics_twin_service,
    get_prognostics_service,
)
from app.domain.entities.telemetry import TelemetryFrame, TelemetrySource
from app.infrastructure.replay.replay_source import ReplayTelemetrySource


@pytest.fixture
def replayed_frames() -> list[TelemetryFrame]:
    frames = []
    for i in range(15):
        frames.append(
            TelemetryFrame(
                timestamp=100.0 + i * 0.1,
                sequence_id=i,
                source_type=TelemetrySource.REPLAY,
                rpm=2500.0,
                manifold_pressure=28.0,
                throttle_position=50.0,
                fuel_flow=16.0,
                fuel_pressure=3.2,
                injection_timing=20.0,
                cht=[95.0, 96.0, 94.0, 95.0],
                egt=[710.0, 712.0, 709.0, 711.0],
                coolant_temp=85.0,
                oil_temperature=88.0,
                oil_pressure=3.8,
                vibration_rms=1.1,
                battery_voltage=28.0,
                alternator_current=15.0,
                alternator_status="OK",
                altitude=1000.0,
                ambient_temp=15.0,
                true_airspeed=45.0,
            )
        )
    return frames


def test_replayed_frames_execute_through_unmodified_ai_pipeline(replayed_frames):
    physics_service = get_physics_twin_service()
    ml_service = get_ml_inference_service()
    prognostics_service = get_prognostics_service()

    source = ReplayTelemetrySource(frames=replayed_frames)
    source.play()

    processed_count = 0
    while source.cursor.playback_state != "COMPLETED":
        # Get next frame
        idx = source.cursor.current_index
        frame = replayed_frames[idx]

        # 1. Physics Twin evaluation
        physics_res = physics_service.evaluate_frame(frame)
        assert physics_res is not None
        assert physics_res.expected_state.rpm > 0.0

        # 2. ML diagnostics evaluation
        ml_res = ml_service.evaluate(frame, physics_res)
        assert ml_res is not None
        assert ml_res.anomaly is not None
        assert ml_res.fault is not None

        # 3. Prognostics evaluation
        prog_res = prognostics_service.evaluate(frame, physics_res, ml_res)
        assert prog_res is not None
        assert 0.0 <= prog_res.health_index <= 1.0

        processed_count += 1
        if source.cursor.advance() is None:
            break

    assert processed_count == 15
