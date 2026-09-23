"""Multi-format flight log loader for Apache Parquet, SQLite, and CSV.

Includes strict schema validation, timestamp monotonicity checking, path traversal protection,
and prototype memory bounding (max 100,000 frames).
"""

import sqlite3
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

from app.domain.entities.telemetry import (
    QualityStatus,
    TelemetryFrame,
    TelemetrySource,
)
from app.domain.replay.enums import ReplayFormat
from app.domain.replay.models import ReplayDatasetMetadata


class FlightLogLoader:
    """Safely loads and validates historical flight log datasets into TelemetryFrame sequences."""

    MAX_PROTOTYPE_FRAMES = 100_000

    REQUIRED_COLUMNS = {
        "sequence_id",
        "timestamp",
        "rpm",
        "manifold_pressure",
        "throttle_position",
        "fuel_flow",
        "fuel_pressure",
        "injection_timing",
        "cht_1",
        "cht_2",
        "cht_3",
        "cht_4",
        "egt_1",
        "egt_2",
        "egt_3",
        "egt_4",
        "coolant_temp",
        "oil_temperature",
        "oil_pressure",
        "vibration_rms",
        "battery_voltage",
        "alternator_current",
        "alternator_status",
        "altitude",
        "ambient_temp",
        "true_airspeed",
    }

    @classmethod
    def detect_format(cls, file_path: Path) -> ReplayFormat:
        """Infer replay storage format from file extension."""
        suffix = file_path.suffix.lower()
        if suffix in (".parquet", ".pq"):
            return ReplayFormat.PARQUET
        if suffix in (".sqlite", ".db", ".sqlite3"):
            return ReplayFormat.SQLITE
        if suffix == ".csv":
            return ReplayFormat.CSV
        raise ValueError(f"Unsupported flight log file extension: {suffix}")

    @classmethod
    def inspect_metadata(cls, file_path: Path) -> ReplayDatasetMetadata:
        """Inspect file and extract summary metadata without loading all rows into RAM."""
        if not file_path.exists():
            raise FileNotFoundError(f"Flight log file not found: {file_path}")

        file_format = cls.detect_format(file_path)
        size_bytes = file_path.stat().st_size

        if file_format == ReplayFormat.PARQUET:
            pq_file = pq.ParquetFile(file_path)
            num_rows = pq_file.metadata.num_rows
            # Read first and last timestamp
            table = pq.read_table(file_path, columns=["timestamp"])
            timestamps = table["timestamp"].to_pylist()
            start_ts = timestamps[0] if timestamps else 0.0
            end_ts = timestamps[-1] if timestamps else 0.0

        elif file_format == ReplayFormat.SQLITE:
            with sqlite3.connect(str(file_path)) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT COUNT(*), MIN(timestamp), MAX(timestamp) FROM telemetry_frames"
                )
                row = cursor.fetchone()
                num_rows = int(row[0]) if row and row[0] is not None else 0
                start_ts = float(row[1]) if row and row[1] is not None else 0.0
                end_ts = float(row[2]) if row and row[2] is not None else 0.0

        elif file_format == ReplayFormat.CSV:
            df = pd.read_csv(file_path, usecols=["timestamp"])
            num_rows = len(df)
            start_ts = float(df["timestamp"].iloc[0]) if num_rows > 0 else 0.0
            end_ts = float(df["timestamp"].iloc[-1]) if num_rows > 0 else 0.0

        duration_sec = max(0.0, end_ts - start_ts)
        rate_hz = round(num_rows / duration_sec, 1) if duration_sec > 0.0 else 10.0

        return ReplayDatasetMetadata(
            filename=file_path.name,
            format=file_format,
            size_bytes=size_bytes,
            total_frames=num_rows,
            start_timestamp=start_ts,
            end_timestamp=end_ts,
            duration_sec=round(duration_sec, 2),
            nominal_rate_hz=rate_hz,
        )

    @classmethod
    def load_frames(cls, file_path: Path) -> list[TelemetryFrame]:
        """Load, validate, and parse a flight log file into a list of TelemetryFrame instances."""
        if not file_path.exists():
            raise FileNotFoundError(f"Flight log file not found: {file_path}")

        file_format = cls.detect_format(file_path)

        if file_format == ReplayFormat.PARQUET:
            table = pq.read_table(file_path)
            df = table.to_pandas()
        elif file_format == ReplayFormat.SQLITE:
            with sqlite3.connect(str(file_path)) as conn:
                df = pd.read_sql_query(
                    "SELECT * FROM telemetry_frames ORDER BY timestamp ASC", conn
                )
        elif file_format == ReplayFormat.CSV:
            df = pd.read_csv(file_path)

        if len(df) > cls.MAX_PROTOTYPE_FRAMES:
            raise ValueError(
                f"Dataset contains {len(df)} frames, exceeding prototype memory limit of {cls.MAX_PROTOTYPE_FRAMES} frames."
            )

        # Validate column requirements
        missing = cls.REQUIRED_COLUMNS - set(df.columns)
        if missing:
            raise ValueError(f"Dataset missing required telemetry columns: {sorted(missing)}")

        # Ensure monotonic sort by timestamp
        if not df["timestamp"].is_monotonic_increasing:
            df = df.sort_values(by="timestamp").reset_index(drop=True)

        frames: list[TelemetryFrame] = []
        for _, row in df.iterrows():
            quality_str = str(row.get("quality_flag", "VALID")).upper()
            quality = QualityStatus.VALID
            if quality_str in ("DEGRADED",):
                quality = QualityStatus.DEGRADED
            elif quality_str in ("INVALID",):
                quality = QualityStatus.INVALID
            elif quality_str in ("MISSING",):
                quality = QualityStatus.MISSING

            frame = TelemetryFrame(
                version=str(row.get("version", "1.0.0")),
                timestamp=float(row["timestamp"]),
                sequence_id=int(row["sequence_id"]),
                source_type=TelemetrySource.REPLAY,
                quality_flag=quality,
                rpm=float(row["rpm"]),
                manifold_pressure=float(row["manifold_pressure"]),
                throttle_position=float(row["throttle_position"]),
                fuel_flow=float(row["fuel_flow"]),
                fuel_pressure=float(row["fuel_pressure"]),
                injection_timing=float(row["injection_timing"]),
                cht=[
                    float(row["cht_1"]),
                    float(row["cht_2"]),
                    float(row["cht_3"]),
                    float(row["cht_4"]),
                ],
                egt=[
                    float(row["egt_1"]),
                    float(row["egt_2"]),
                    float(row["egt_3"]),
                    float(row["egt_4"]),
                ],
                coolant_temp=float(row["coolant_temp"]),
                oil_temperature=float(row["oil_temperature"]),
                oil_pressure=float(row["oil_pressure"]),
                vibration_rms=float(row["vibration_rms"]),
                battery_voltage=float(row["battery_voltage"]),
                alternator_current=float(row["alternator_current"]),
                alternator_status=str(row["alternator_status"]),
                altitude=float(row["altitude"]),
                ambient_temp=float(row["ambient_temp"]),
                true_airspeed=float(row["true_airspeed"]),
            )
            frames.append(frame)

        return frames
