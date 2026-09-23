"""Unit tests for SqliteTelemetryRepository and Parquet persistence."""

import tempfile
from pathlib import Path

import pyarrow.parquet as pq
import pytest

from app.application.ports.telemetry_ports import ITelemetryRepository
from app.domain.entities.telemetry import QualityStatus, TelemetryFrame, TelemetrySource
from app.infrastructure.persistence.telemetry_repository import SqliteTelemetryRepository


def create_frame(seq: int, ts: float) -> TelemetryFrame:
    return TelemetryFrame(
        version="1.0.0",
        timestamp=ts,
        sequence_id=seq,
        source_type=TelemetrySource.SIMULATED,
        quality_flag=QualityStatus.VALID,
        rpm=2400.0 + seq,
        manifold_pressure=28.5,
        throttle_position=35.0,
        fuel_flow=12.5,
        fuel_pressure=3.0,
        injection_timing=20.0,
        cht=[92.0, 90.0, 88.0, 86.0],
        egt=[710.0, 705.0, 700.0, 695.0],
        coolant_temp=72.0,
        oil_temperature=82.0,
        oil_pressure=3.5,
        vibration_rms=1.0,
        battery_voltage=28.1,
        alternator_current=16.0,
        alternator_status="OK",
        altitude=1200.0,
        ambient_temp=14.0,
        true_airspeed=42.0,
    )


def test_repository_implements_port():
    repo = SqliteTelemetryRepository(":memory:")
    assert isinstance(repo, ITelemetryRepository)
    repo.close()


@pytest.mark.asyncio
async def test_save_and_retrieve_frame():
    repo = SqliteTelemetryRepository(":memory:")
    frame = create_frame(seq=1, ts=100.1)

    await repo.save_frame(frame)
    assert await repo.count() == 1

    recent = await repo.get_recent_frames(limit=10)
    assert len(recent) == 1
    assert recent[0].sequence_id == 1
    assert recent[0].rpm == 2401.0
    assert recent[0].cht == [92.0, 90.0, 88.0, 86.0]
    repo.close()


@pytest.mark.asyncio
async def test_save_batch_and_query_range():
    repo = SqliteTelemetryRepository(":memory:")
    frames = [create_frame(seq=i, ts=1000.0 + (i * 0.1)) for i in range(20)]

    await repo.save_batch(frames)
    assert await repo.count() == 20

    # Query range between ts 1000.5 and 1001.0 (should match seq 5 through 10 = 6 frames)
    matched = await repo.query_range(1000.5, 1001.0)
    assert len(matched) == 6
    assert matched[0].sequence_id == 5
    assert matched[-1].sequence_id == 10
    repo.close()


def test_export_frames_to_parquet():
    frames = [create_frame(seq=i, ts=2000.0 + i) for i in range(15)]
    with tempfile.TemporaryDirectory() as tmp_dir:
        parquet_path = Path(tmp_dir) / "test_frames.parquet"
        result_path = SqliteTelemetryRepository.export_frames_to_parquet(frames, parquet_path)

        assert result_path.exists()
        table = pq.read_table(str(result_path))
        assert table.num_rows == 15
        assert "rpm" in table.column_names
        assert "manifold_pressure" in table.column_names
        assert "cht_1" in table.column_names
        assert "cht_4" in table.column_names
        assert "egt_1" in table.column_names
        assert "true_airspeed" in table.column_names


def test_export_database_to_parquet():
    repo = SqliteTelemetryRepository(":memory:")
    frames = [create_frame(seq=i, ts=3000.0 + i) for i in range(10)]
    repo.save_batch_sync(frames)

    with tempfile.TemporaryDirectory() as tmp_dir:
        parquet_path = Path(tmp_dir) / "db_export.parquet"
        repo.export_to_parquet(parquet_path)

        assert parquet_path.exists()
        table = pq.read_table(str(parquet_path))
        assert table.num_rows == 10
    repo.close()
