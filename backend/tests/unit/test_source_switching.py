"""Unit tests verifying safe telemetry source switching between LIVE and REPLAY modes."""

import pytest

from app.application.services.realtime_service import RealtimeTelemetryService
from app.application.services.replay_service import ReplayService
from app.domain.entities.telemetry import TelemetryFrame, TelemetrySource
from app.infrastructure.persistence.telemetry_repository import SqliteTelemetryRepository
from app.infrastructure.telemetry.synthetic_source import SyntheticTelemetrySource
from app.infrastructure.websocket.broadcaster import WebSocketBroadcastManager


@pytest.fixture
def mock_broadcaster():
    return WebSocketBroadcastManager(max_clients=10, queue_size=10)


@pytest.fixture
def sample_parquet(tmp_path):
    frames = [
        TelemetryFrame(
            timestamp=100.0 + i * 0.1,
            sequence_id=i,
            source_type=TelemetrySource.SIMULATED,
            rpm=2000.0,
            manifold_pressure=25.0,
            throttle_position=40.0,
            fuel_flow=12.0,
            fuel_pressure=3.0,
            injection_timing=18.0,
            cht=[85.0, 85.0, 85.0, 85.0],
            egt=[680.0, 680.0, 680.0, 680.0],
            coolant_temp=80.0,
            oil_temperature=80.0,
            oil_pressure=3.5,
            vibration_rms=1.0,
            battery_voltage=28.0,
            alternator_current=10.0,
            alternator_status="OK",
            altitude=100.0,
            ambient_temp=15.0,
            true_airspeed=30.0,
        )
        for i in range(10)
    ]
    path = tmp_path / "replay_sample.parquet"
    SqliteTelemetryRepository.export_frames_to_parquet(frames, path)
    return path


@pytest.mark.asyncio
async def test_safe_source_switching_lifecycle(mock_broadcaster, sample_parquet, tmp_path):
    synthetic_source = SyntheticTelemetrySource()
    replay_service = ReplayService(search_directories=[tmp_path])

    service = RealtimeTelemetryService(
        telemetry_source=synthetic_source,
        broadcaster=mock_broadcaster,
        rate_hz=10,
        replay_service=replay_service,
    )

    assert service.source_mode == "LIVE"

    # Attempting to switch to REPLAY without loading a dataset must safely fail
    res_fail = await service.set_source_mode("REPLAY")
    assert not res_fail
    assert service.source_mode == "LIVE"

    # Load dataset in replay_service
    replay_service.load_dataset(sample_parquet.name)
    assert replay_service.is_loaded

    # Now switch to REPLAY must succeed
    res_success = await service.set_source_mode("REPLAY")
    assert res_success
    assert service.source_mode == "REPLAY"
    assert service.telemetry_source == replay_service.active_source

    # Switch back to LIVE
    res_live = await service.set_source_mode("LIVE")
    assert res_live
    assert service.source_mode == "LIVE"
    assert service.telemetry_source == synthetic_source
