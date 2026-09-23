"""Unit tests for RealtimeTelemetryService execution, pacing, and commands."""

import asyncio

import pytest

from app.application.services.realtime_service import RealtimeTelemetryService
from app.domain.entities.telemetry import QualityStatus, TelemetryFrame, TelemetrySource
from app.infrastructure.websocket.broadcaster import WebSocketBroadcastManager


def _mock_frame(seq: int = 1) -> TelemetryFrame:
    return TelemetryFrame(
        version="1.0.0",
        timestamp=100.0 + seq,
        sequence_id=seq,
        source_type=TelemetrySource.SIMULATED,
        quality_flag=QualityStatus.VALID,
        rpm=2400.0,
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


class MockTelemetrySource:
    """In-memory telemetry source for unit testing."""

    def __init__(self):
        self._seq = 0
        self.connected = False

    async def connect(self):
        self.connected = True

    async def disconnect(self):
        self.connected = False

    async def get_next_frame(self):
        self._seq += 1
        return _mock_frame(self._seq)

    def stream_frames(self):
        raise NotImplementedError


@pytest.mark.asyncio
async def test_realtime_service_lifecycle():
    """Verify start, pause, resume, and stop transitions."""
    source = MockTelemetrySource()
    broadcaster = WebSocketBroadcastManager(max_clients=5, queue_size=10)
    service = RealtimeTelemetryService(
        telemetry_source=source,
        broadcaster=broadcaster,
        rate_hz=50,  # Fast for test
        heartbeat_interval_sec=1.0,
    )

    assert service.state == "stopped"

    # Start
    await service.start()
    assert service.is_running
    assert service.state == "running"
    assert source.connected is True

    # Allow a few frames to publish
    await asyncio.sleep(0.08)

    # Pause
    await service.pause()
    assert service.state == "paused"
    assert not service.is_running

    # Resume
    await service.resume()
    assert service.state == "running"

    # Stop
    await service.stop()
    assert service.state == "stopped"
    assert source.connected is False


@pytest.mark.asyncio
async def test_realtime_service_commands():
    """Verify execution of client control commands."""
    source = MockTelemetrySource()
    broadcaster = WebSocketBroadcastManager(max_clients=5, queue_size=10)
    service = RealtimeTelemetryService(
        telemetry_source=source,
        broadcaster=broadcaster,
        rate_hz=10,
    )

    await service.execute_command("start", {})
    assert service.is_running

    await service.execute_command("pause", {})
    assert service.state == "paused"

    await service.execute_command("resume", {})
    assert service.state == "running"

    await service.execute_command("set_rate", {"rate_hz": 20})
    assert service.rate_hz == 20

    await service.execute_command("reset", {})
    assert service.state == "running"

    await service.stop()
