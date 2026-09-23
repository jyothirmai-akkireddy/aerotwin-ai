"""Unit tests for multi-format flight log loader (Parquet, SQLite, CSV)."""

import pandas as pd
import pytest

from app.domain.entities.telemetry import TelemetryFrame, TelemetrySource
from app.infrastructure.persistence.telemetry_repository import SqliteTelemetryRepository
from app.infrastructure.replay.loader import FlightLogLoader


@pytest.fixture
def sample_frames() -> list[TelemetryFrame]:
    frames = []
    for i in range(25):
        frames.append(
            TelemetryFrame(
                timestamp=1774358400.0 + i * 0.1,
                sequence_id=i,
                source_type=TelemetrySource.SIMULATED,
                rpm=2400.0 + i * 2.0,
                manifold_pressure=29.0,
                throttle_position=45.0,
                fuel_flow=15.0,
                fuel_pressure=3.0,
                injection_timing=18.0,
                cht=[90.0, 92.0, 91.0, 89.0],
                egt=[710.0, 715.0, 712.0, 708.0],
                coolant_temp=82.0,
                oil_temperature=85.0,
                oil_pressure=3.5,
                vibration_rms=1.05,
                battery_voltage=28.1,
                alternator_current=12.0,
                alternator_status="OK",
                altitude=500.0,
                ambient_temp=12.0,
                true_airspeed=40.0,
            )
        )
    return frames


def test_parquet_export_and_load(tmp_path, sample_frames):
    pq_path = tmp_path / "test_flight.parquet"
    SqliteTelemetryRepository.export_frames_to_parquet(sample_frames, pq_path)
    assert pq_path.exists()

    meta = FlightLogLoader.inspect_metadata(pq_path)
    assert meta.total_frames == 25
    assert meta.format == "PARQUET"

    loaded = FlightLogLoader.load_frames(pq_path)
    assert len(loaded) == 25
    assert loaded[0].sequence_id == 0
    assert loaded[-1].sequence_id == 24
    assert loaded[0].source_type == TelemetrySource.REPLAY
    assert loaded[10].rpm == sample_frames[10].rpm


def test_sqlite_load(tmp_path, sample_frames):
    db_path = tmp_path / "test_flight.sqlite"
    repo = SqliteTelemetryRepository(db_path=db_path)
    repo.save_batch_sync(sample_frames)
    repo.close()

    meta = FlightLogLoader.inspect_metadata(db_path)
    assert meta.total_frames == 25
    assert meta.format == "SQLITE"

    loaded = FlightLogLoader.load_frames(db_path)
    assert len(loaded) == 25
    assert loaded[0].sequence_id == 0
    assert loaded[-1].sequence_id == 24


def test_csv_load(tmp_path, sample_frames):
    csv_path = tmp_path / "test_flight.csv"
    data = {
        "sequence_id": [f.sequence_id for f in sample_frames],
        "timestamp": [f.timestamp for f in sample_frames],
        "version": [f.version for f in sample_frames],
        "source_type": ["SIMULATED"] * len(sample_frames),
        "quality_flag": ["VALID"] * len(sample_frames),
        "rpm": [f.rpm for f in sample_frames],
        "manifold_pressure": [f.manifold_pressure for f in sample_frames],
        "throttle_position": [f.throttle_position for f in sample_frames],
        "fuel_flow": [f.fuel_flow for f in sample_frames],
        "fuel_pressure": [f.fuel_pressure for f in sample_frames],
        "injection_timing": [f.injection_timing for f in sample_frames],
        "cht_1": [f.cht[0] for f in sample_frames],
        "cht_2": [f.cht[1] for f in sample_frames],
        "cht_3": [f.cht[2] for f in sample_frames],
        "cht_4": [f.cht[3] for f in sample_frames],
        "egt_1": [f.egt[0] for f in sample_frames],
        "egt_2": [f.egt[1] for f in sample_frames],
        "egt_3": [f.egt[2] for f in sample_frames],
        "egt_4": [f.egt[3] for f in sample_frames],
        "coolant_temp": [f.coolant_temp for f in sample_frames],
        "oil_temperature": [f.oil_temperature for f in sample_frames],
        "oil_pressure": [f.oil_pressure for f in sample_frames],
        "vibration_rms": [f.vibration_rms for f in sample_frames],
        "battery_voltage": [f.battery_voltage for f in sample_frames],
        "alternator_current": [f.alternator_current for f in sample_frames],
        "alternator_status": [f.alternator_status for f in sample_frames],
        "altitude": [f.altitude for f in sample_frames],
        "ambient_temp": [f.ambient_temp for f in sample_frames],
        "true_airspeed": [f.true_airspeed for f in sample_frames],
    }
    pd.DataFrame(data).to_csv(csv_path, index=False)

    meta = FlightLogLoader.inspect_metadata(csv_path)
    assert meta.total_frames == 25
    assert meta.format == "CSV"

    loaded = FlightLogLoader.load_frames(csv_path)
    assert len(loaded) == 25


def test_missing_columns_validation(tmp_path):
    bad_csv = tmp_path / "bad.csv"
    pd.DataFrame({"timestamp": [1.0, 2.0], "rpm": [2000.0, 2100.0]}).to_csv(bad_csv, index=False)

    with pytest.raises(ValueError, match="missing required telemetry columns"):
        FlightLogLoader.load_frames(bad_csv)
