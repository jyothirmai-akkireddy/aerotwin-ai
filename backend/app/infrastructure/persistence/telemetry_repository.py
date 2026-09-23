"""SQLite and Parquet telemetry persistence adapter implementing ITelemetryRepository."""

import asyncio
import sqlite3
import threading
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from app.application.ports.telemetry_ports import ITelemetryRepository
from app.domain.entities.telemetry import (
    QualityStatus,
    TelemetryFrame,
    TelemetrySource,
)
from app.infrastructure.logging.logger import get_logger

logger = get_logger("aerotwin.repository.telemetry")


class SqliteTelemetryRepository(ITelemetryRepository):
    """SQLite-backed implementation of ITelemetryRepository with Parquet export capability."""

    SCHEMA_SQL = """
    CREATE TABLE IF NOT EXISTS telemetry_frames (
        sequence_id INTEGER PRIMARY KEY,
        timestamp REAL NOT NULL,
        version TEXT NOT NULL,
        source_type TEXT NOT NULL,
        quality_flag TEXT NOT NULL,
        rpm REAL NOT NULL,
        manifold_pressure REAL NOT NULL,
        throttle_position REAL NOT NULL,
        fuel_flow REAL NOT NULL,
        fuel_pressure REAL NOT NULL,
        injection_timing REAL NOT NULL,
        cht_1 REAL NOT NULL,
        cht_2 REAL NOT NULL,
        cht_3 REAL NOT NULL,
        cht_4 REAL NOT NULL,
        egt_1 REAL NOT NULL,
        egt_2 REAL NOT NULL,
        egt_3 REAL NOT NULL,
        egt_4 REAL NOT NULL,
        coolant_temp REAL NOT NULL,
        oil_temperature REAL NOT NULL,
        oil_pressure REAL NOT NULL,
        vibration_rms REAL NOT NULL,
        battery_voltage REAL NOT NULL,
        alternator_current REAL NOT NULL,
        alternator_status TEXT NOT NULL,
        altitude REAL NOT NULL,
        ambient_temp REAL NOT NULL,
        true_airspeed REAL NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_telemetry_timestamp ON telemetry_frames (timestamp);
    """

    INSERT_SQL = """
    INSERT OR REPLACE INTO telemetry_frames (
        sequence_id, timestamp, version, source_type, quality_flag,
        rpm, manifold_pressure, throttle_position, fuel_flow, fuel_pressure, injection_timing,
        cht_1, cht_2, cht_3, cht_4,
        egt_1, egt_2, egt_3, egt_4,
        coolant_temp, oil_temperature, oil_pressure, vibration_rms,
        battery_voltage, alternator_current, alternator_status,
        altitude, ambient_temp, true_airspeed
    ) VALUES (
        ?, ?, ?, ?, ?,
        ?, ?, ?, ?, ?, ?,
        ?, ?, ?, ?,
        ?, ?, ?, ?,
        ?, ?, ?, ?,
        ?, ?, ?,
        ?, ?, ?
    );
    """

    def __init__(self, db_path: str | Path = ":memory:"):
        self.db_path = str(db_path)
        self._lock = threading.Lock()

        # Ensure directory exists if saving to disk
        if self.db_path != ":memory:":
            try:
                Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                logger.warning(f"Could not create database directory for {self.db_path}: {e}")

        self._conn = sqlite3.connect(
            self.db_path,
            check_same_thread=False,
            isolation_level=None,  # Autocommit mode
        )
        self._conn.row_factory = sqlite3.Row

        with self._lock:
            # Enable WAL mode for high concurrent throughput if not in memory
            if self.db_path != ":memory:":
                self._conn.execute("PRAGMA journal_mode = WAL;")
                self._conn.execute("PRAGMA synchronous = NORMAL;")
            self._conn.executescript(self.SCHEMA_SQL)

    def _frame_to_row(self, f: TelemetryFrame) -> tuple:
        return (
            f.sequence_id,
            f.timestamp,
            f.version,
            f.source_type.value if hasattr(f.source_type, "value") else str(f.source_type),
            f.quality_flag.value if hasattr(f.quality_flag, "value") else str(f.quality_flag),
            f.rpm,
            f.manifold_pressure,
            f.throttle_position,
            f.fuel_flow,
            f.fuel_pressure,
            f.injection_timing,
            f.cht[0],
            f.cht[1],
            f.cht[2],
            f.cht[3],
            f.egt[0],
            f.egt[1],
            f.egt[2],
            f.egt[3],
            f.coolant_temp,
            f.oil_temperature,
            f.oil_pressure,
            f.vibration_rms,
            f.battery_voltage,
            f.alternator_current,
            f.alternator_status,
            f.altitude,
            f.ambient_temp,
            f.true_airspeed,
        )

    def _row_to_frame(self, row: sqlite3.Row) -> TelemetryFrame:
        return TelemetryFrame(
            sequence_id=row["sequence_id"],
            timestamp=row["timestamp"],
            version=row["version"],
            source_type=TelemetrySource(row["source_type"]),
            quality_flag=QualityStatus(row["quality_flag"]),
            rpm=row["rpm"],
            manifold_pressure=row["manifold_pressure"],
            throttle_position=row["throttle_position"],
            fuel_flow=row["fuel_flow"],
            fuel_pressure=row["fuel_pressure"],
            injection_timing=row["injection_timing"],
            cht=[row["cht_1"], row["cht_2"], row["cht_3"], row["cht_4"]],
            egt=[row["egt_1"], row["egt_2"], row["egt_3"], row["egt_4"]],
            coolant_temp=row["coolant_temp"],
            oil_temperature=row["oil_temperature"],
            oil_pressure=row["oil_pressure"],
            vibration_rms=row["vibration_rms"],
            battery_voltage=row["battery_voltage"],
            alternator_current=row["alternator_current"],
            alternator_status=row["alternator_status"],
            altitude=row["altitude"],
            ambient_temp=row["ambient_temp"],
            true_airspeed=row["true_airspeed"],
        )

    def save_frame_sync(self, frame: TelemetryFrame) -> None:
        """Synchronously persist a single frame."""
        with self._lock:
            self._conn.execute(self.INSERT_SQL, self._frame_to_row(frame))

    async def save_frame(self, frame: TelemetryFrame) -> None:
        """Persist a single validated telemetry frame."""
        await asyncio.to_thread(self.save_frame_sync, frame)

    def save_batch_sync(self, frames: list[TelemetryFrame]) -> None:
        """Synchronously persist a list of frames within a single transaction."""
        if not frames:
            return
        rows = [self._frame_to_row(f) for f in frames]
        with self._lock:
            self._conn.execute("BEGIN TRANSACTION;")
            try:
                self._conn.executemany(self.INSERT_SQL, rows)
                self._conn.execute("COMMIT;")
            except Exception:
                self._conn.execute("ROLLBACK;")
                raise

    async def save_batch(self, frames: list[TelemetryFrame]) -> None:
        """Persist a batch of frames in bulk."""
        await asyncio.to_thread(self.save_batch_sync, frames)

    def get_recent_frames_sync(self, limit: int = 100) -> list[TelemetryFrame]:
        """Synchronously retrieve recent frames ordered by timestamp ascending."""
        query = """
        SELECT * FROM (
            SELECT * FROM telemetry_frames ORDER BY sequence_id DESC LIMIT ?
        ) ORDER BY sequence_id ASC;
        """
        with self._lock:
            cursor = self._conn.execute(query, (limit,))
            rows = cursor.fetchall()
            return [self._row_to_frame(r) for r in rows]

    async def get_recent_frames(self, limit: int = 100) -> list[TelemetryFrame]:
        """Retrieve recent historical frames."""
        return await asyncio.to_thread(self.get_recent_frames_sync, limit)

    def query_range_sync(self, start_time: float, end_time: float) -> list[TelemetryFrame]:
        """Synchronously query frames in a timestamp interval."""
        query = """
        SELECT * FROM telemetry_frames
        WHERE timestamp >= ? AND timestamp <= ?
        ORDER BY timestamp ASC;
        """
        with self._lock:
            cursor = self._conn.execute(query, (start_time, end_time))
            rows = cursor.fetchall()
            return [self._row_to_frame(r) for r in rows]

    async def query_range(self, start_time: float, end_time: float) -> list[TelemetryFrame]:
        """Retrieve telemetry frames within a specified UTC epoch timestamp range."""
        return await asyncio.to_thread(self.query_range_sync, start_time, end_time)

    def count_sync(self) -> int:
        """Count total stored telemetry frames."""
        with self._lock:
            cursor = self._conn.execute("SELECT COUNT(*) FROM telemetry_frames;")
            row = cursor.fetchone()
            return int(row[0]) if row else 0

    async def count(self) -> int:
        """Asynchronously return total stored telemetry frames count."""
        return await asyncio.to_thread(self.count_sync)

    def close(self) -> None:
        """Close database connection."""
        with self._lock:
            self._conn.close()

    @staticmethod
    def export_frames_to_parquet(
        frames: list[TelemetryFrame],
        destination_path: str | Path,
    ) -> Path:
        """Export an in-memory list of TelemetryFrame objects directly to Parquet."""
        path = Path(destination_path)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            logger.warning(f"Could not create Parquet export directory for {path}: {e}")

        if not frames:
            # Create an empty table matching schema
            empty_dict = {
                "sequence_id": pa.array([], type=pa.int64()),
                "timestamp": pa.array([], type=pa.float64()),
                "version": pa.array([], type=pa.string()),
                "source_type": pa.array([], type=pa.string()),
                "quality_flag": pa.array([], type=pa.string()),
                "rpm": pa.array([], type=pa.float64()),
                "manifold_pressure": pa.array([], type=pa.float64()),
                "throttle_position": pa.array([], type=pa.float64()),
                "fuel_flow": pa.array([], type=pa.float64()),
                "fuel_pressure": pa.array([], type=pa.float64()),
                "injection_timing": pa.array([], type=pa.float64()),
                "cht_1": pa.array([], type=pa.float64()),
                "cht_2": pa.array([], type=pa.float64()),
                "cht_3": pa.array([], type=pa.float64()),
                "cht_4": pa.array([], type=pa.float64()),
                "egt_1": pa.array([], type=pa.float64()),
                "egt_2": pa.array([], type=pa.float64()),
                "egt_3": pa.array([], type=pa.float64()),
                "egt_4": pa.array([], type=pa.float64()),
                "coolant_temp": pa.array([], type=pa.float64()),
                "oil_temperature": pa.array([], type=pa.float64()),
                "oil_pressure": pa.array([], type=pa.float64()),
                "vibration_rms": pa.array([], type=pa.float64()),
                "battery_voltage": pa.array([], type=pa.float64()),
                "alternator_current": pa.array([], type=pa.float64()),
                "alternator_status": pa.array([], type=pa.string()),
                "altitude": pa.array([], type=pa.float64()),
                "ambient_temp": pa.array([], type=pa.float64()),
                "true_airspeed": pa.array([], type=pa.float64()),
            }
            table = pa.Table.from_pydict(empty_dict)
            pq.write_table(table, str(path), compression="snappy")
            return path

        data = {
            "sequence_id": [f.sequence_id for f in frames],
            "timestamp": [f.timestamp for f in frames],
            "version": [f.version for f in frames],
            "source_type": [
                f.source_type.value if hasattr(f.source_type, "value") else str(f.source_type)
                for f in frames
            ],
            "quality_flag": [
                f.quality_flag.value if hasattr(f.quality_flag, "value") else str(f.quality_flag)
                for f in frames
            ],
            "rpm": [f.rpm for f in frames],
            "manifold_pressure": [f.manifold_pressure for f in frames],
            "throttle_position": [f.throttle_position for f in frames],
            "fuel_flow": [f.fuel_flow for f in frames],
            "fuel_pressure": [f.fuel_pressure for f in frames],
            "injection_timing": [f.injection_timing for f in frames],
            "cht_1": [f.cht[0] for f in frames],
            "cht_2": [f.cht[1] for f in frames],
            "cht_3": [f.cht[2] for f in frames],
            "cht_4": [f.cht[3] for f in frames],
            "egt_1": [f.egt[0] for f in frames],
            "egt_2": [f.egt[1] for f in frames],
            "egt_3": [f.egt[2] for f in frames],
            "egt_4": [f.egt[3] for f in frames],
            "coolant_temp": [f.coolant_temp for f in frames],
            "oil_temperature": [f.oil_temperature for f in frames],
            "oil_pressure": [f.oil_pressure for f in frames],
            "vibration_rms": [f.vibration_rms for f in frames],
            "battery_voltage": [f.battery_voltage for f in frames],
            "alternator_current": [f.alternator_current for f in frames],
            "alternator_status": [f.alternator_status for f in frames],
            "altitude": [f.altitude for f in frames],
            "ambient_temp": [f.ambient_temp for f in frames],
            "true_airspeed": [f.true_airspeed for f in frames],
        }
        table = pa.Table.from_pydict(data)
        pq.write_table(table, str(path), compression="snappy")
        return path

    def export_to_parquet(
        self,
        destination_path: str | Path,
        start_time: float | None = None,
        end_time: float | None = None,
    ) -> Path:
        """Export stored records from SQLite into a Parquet file."""
        if start_time is not None and end_time is not None:
            frames = self.query_range_sync(start_time, end_time)
        else:
            query = "SELECT * FROM telemetry_frames ORDER BY sequence_id ASC;"
            with self._lock:
                cursor = self._conn.execute(query)
                frames = [self._row_to_frame(r) for r in cursor.fetchall()]
        return self.export_frames_to_parquet(frames, destination_path)
