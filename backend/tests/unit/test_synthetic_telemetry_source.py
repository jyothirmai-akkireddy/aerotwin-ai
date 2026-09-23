"""Unit tests for SyntheticTelemetrySource adapter."""

import pytest

from app.application.ports.telemetry_ports import ITelemetrySource
from app.domain.entities.telemetry import TelemetryFrame
from app.domain.simulation.faults import SensorFaultConfig, SensorFaultType
from app.domain.simulation.scenarios import SCENARIO_IDLE
from app.infrastructure.telemetry.synthetic_source import SyntheticTelemetrySource


def test_source_implements_telemetry_source_port():
    source = SyntheticTelemetrySource(telemetry_rate_hz=10)
    assert isinstance(source, ITelemetrySource)


@pytest.mark.asyncio
async def test_source_connection_lifecycle():
    source = SyntheticTelemetrySource(telemetry_rate_hz=10)
    assert not source.is_connected

    await source.connect()
    assert source.is_connected

    await source.disconnect()
    assert not source.is_connected


@pytest.mark.asyncio
async def test_get_next_frame_sequential_ordering():
    source = SyntheticTelemetrySource(telemetry_rate_hz=10)
    await source.connect()

    f1 = await source.get_next_frame()
    f2 = await source.get_next_frame()

    assert isinstance(f1, TelemetryFrame)
    assert isinstance(f2, TelemetryFrame)
    assert f2.sequence_id == f1.sequence_id + 1
    assert round(f2.timestamp - f1.timestamp, 4) == 0.1


def test_generate_batch_synchronous():
    source = SyntheticTelemetrySource(telemetry_rate_hz=10)
    frames = source.generate_batch(count=25)
    assert len(frames) == 25
    assert frames[0].sequence_id == 0
    assert frames[-1].sequence_id == 24


@pytest.mark.asyncio
async def test_stream_frames_async_iteration():
    source = SyntheticTelemetrySource(telemetry_rate_hz=10)
    frames = []

    async for frame in source.stream_frames(max_frames=20, realtime=False):
        frames.append(frame)

    assert len(frames) == 20
    assert frames[-1].sequence_id == 19


def test_run_scenario_convenience():
    source = SyntheticTelemetrySource(telemetry_rate_hz=10)
    frames = source.run_scenario(SCENARIO_IDLE)
    assert len(frames) == int(SCENARIO_IDLE.total_duration_sec * 10)


def test_fault_injection_delegation():
    source = SyntheticTelemetrySource(telemetry_rate_hz=10)
    fault = SensorFaultConfig(
        target_channel="manifold_pressure",
        fault_type=SensorFaultType.BIAS,
        start_time_sec=1.0,
        magnitude=5.0,
    )
    source.inject_fault(fault)
    assert len(source.faults.fault_configs) == 1

    source.clear_faults()
    assert len(source.faults.fault_configs) == 0
