"""Configuration and operational parameter validation tests.

SIH26054 — AeroTwin AI
Phase 9 Reliability & Configuration Gate

Validates:
1. Pacing rate limits (rejection of non-positive or extreme frequencies).
2. Broadcaster limits (max clients, queue size constraints).
3. Physics and simulator calibration bounds.
4. Error handling for boundary and out-of-spec operational configurations.
"""

import pytest

from app.application.services.realtime_service import RealtimeTelemetryService
from app.domain.physics.models import PhysicsCalibrationParameters
from app.infrastructure.simulation.engine_simulator import EngineSimulator
from app.infrastructure.telemetry.synthetic_source import SyntheticTelemetrySource
from app.infrastructure.websocket.broadcaster import WebSocketBroadcastManager


def test_engine_simulator_frequency_bounds():
    """Verify EngineSimulator validates telemetry frequency bounds."""
    # Zero or negative Hz must raise ValueError
    with pytest.raises(ValueError, match="Telemetry rate must be positive"):
        EngineSimulator(telemetry_rate_hz=0)

    with pytest.raises(ValueError, match="Telemetry rate must be positive"):
        EngineSimulator(telemetry_rate_hz=-10)


def test_broadcaster_queue_and_client_limits():
    """Verify WebSocketBroadcastManager configuration constraints."""
    bm = WebSocketBroadcastManager(max_clients=10, queue_size=50)
    assert bm.max_clients == 10
    assert bm.queue_size == 50
    assert bm.active_client_count == 0


@pytest.mark.asyncio
async def test_realtime_service_rate_adjustment_bounds():
    """Verify dynamic rate adjustments on RealtimeTelemetryService respect [1, 100] Hz bounds."""
    sim = EngineSimulator(telemetry_rate_hz=10)
    source = SyntheticTelemetrySource(simulator=sim)
    broadcaster = WebSocketBroadcastManager(max_clients=5, queue_size=100)

    service = RealtimeTelemetryService(
        telemetry_source=source,
        broadcaster=broadcaster,
        rate_hz=10,
    )

    # Valid updates
    await service.set_rate(25)
    assert service.rate_hz == 25

    await service.set_rate(1)
    assert service.rate_hz == 1

    await service.set_rate(100)
    assert service.rate_hz == 100

    # Out of bounds updates (ignored, rate preserved)
    await service.set_rate(0)
    assert service.rate_hz == 100

    await service.set_rate(-5)
    assert service.rate_hz == 100

    await service.set_rate(200)
    assert service.rate_hz == 100


def test_physics_calibration_pydantic_bounds():
    """Verify PhysicsCalibrationParameters enforces physical engineering bounds via Pydantic."""
    # Valid default
    cal = PhysicsCalibrationParameters()
    assert cal.engine_displacement_cc == 1352.0

    from pydantic import ValidationError

    # Out of range displacement (displacement < 500 or > 3000)
    with pytest.raises(ValidationError):
        PhysicsCalibrationParameters(engine_displacement_cc=200.0)

    with pytest.raises(ValidationError):
        PhysicsCalibrationParameters(engine_displacement_cc=5000.0)

    # Out of range boost PR
    with pytest.raises(ValidationError):
        PhysicsCalibrationParameters(max_boost_pr=0.5)
