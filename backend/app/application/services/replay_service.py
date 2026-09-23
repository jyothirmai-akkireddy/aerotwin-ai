"""Application service for managing replay sessions, dataset discovery, and transport controls."""

from pathlib import Path
from typing import Any

from app.config import settings
from app.domain.replay.enums import PlaybackState, ReplayExecutionMode
from app.domain.replay.models import ReplayCursorStatus, ReplayDatasetMetadata
from app.infrastructure.logging.logger import get_logger
from app.infrastructure.replay.loader import FlightLogLoader
from app.infrastructure.replay.replay_source import ReplayTelemetrySource

logger = get_logger("aerotwin.service.replay")


class ReplayService:
    """Coordinates dataset cataloging, dataset ingestion, and replay cursor controls."""

    def __init__(self, search_directories: list[str | Path] | None = None):
        if search_directories is None:
            base_dir = Path(settings.storage.parquet_data_dir).parent
            self.search_dirs = [
                Path(settings.storage.parquet_data_dir),
                base_dir / "sqlite",
                base_dir / "missions",
            ]
        else:
            self.search_dirs = [Path(p) for p in search_directories]

        for d in self.search_dirs:
            d.mkdir(parents=True, exist_ok=True)

        self._active_source: ReplayTelemetrySource | None = None
        self._active_metadata: ReplayDatasetMetadata | None = None

    @property
    def active_source(self) -> ReplayTelemetrySource | None:
        return self._active_source

    @property
    def is_loaded(self) -> bool:
        return self._active_source is not None

    def list_available_datasets(self) -> list[ReplayDatasetMetadata]:
        """Scan configured search directories and return metadata for valid flight logs."""
        datasets: list[ReplayDatasetMetadata] = []
        seen_names: set[str] = set()

        for d in self.search_dirs:
            if not d.exists():
                continue

            for ext in ("*.parquet", "*.sqlite", "*.db", "*.csv"):
                for file_path in d.glob(ext):
                    if file_path.name in seen_names:
                        continue
                    seen_names.add(file_path.name)
                    try:
                        meta = FlightLogLoader.inspect_metadata(file_path)
                        datasets.append(meta)
                    except Exception as e:
                        logger.warning(
                            f"Skipping unreadable or invalid log file {file_path.name}: {e}"
                        )

        # Sort by latest modification time or name
        return sorted(datasets, key=lambda m: m.filename)

    def resolve_dataset_path(self, filename: str) -> Path:
        """Resolve dataset filename against search directories with path traversal protection."""
        clean_name = Path(filename).name
        for d in self.search_dirs:
            target = (d / clean_name).resolve()
            # Ensure target is strictly inside search directory
            if target.is_relative_to(d.resolve()) and target.is_file():
                return target

        raise FileNotFoundError(
            f"Dataset '{clean_name}' not found in authorized storage locations."
        )

    def load_dataset(self, filename: str) -> ReplayCursorStatus:
        """Load a specified flight log into an active ReplayTelemetrySource."""
        file_path = self.resolve_dataset_path(filename)
        frames = FlightLogLoader.load_frames(file_path)

        if not frames:
            raise ValueError(f"Dataset '{filename}' contains zero valid telemetry frames.")

        self._active_source = ReplayTelemetrySource(
            frames=frames,
            source_filename=file_path.name,
        )
        self._active_metadata = FlightLogLoader.inspect_metadata(file_path)
        logger.info(f"Loaded replay dataset '{file_path.name}' ({len(frames)} frames)")
        return self._active_source.get_status()

    def control(self, action: str, target: Any = None) -> ReplayCursorStatus:
        """Execute a transport control action on the active replay cursor."""
        if not self._active_source:
            raise RuntimeError("No replay dataset currently loaded. Call load_dataset() first.")

        act = action.lower()
        if act == "play":
            self._active_source.play()
        elif act == "pause":
            self._active_source.pause()
        elif act == "resume":
            self._active_source.resume()
        elif act == "reset":
            self._active_source.reset()
        elif act == "seek":
            if target is not None:
                # Disambiguate frame index vs timestamp
                if isinstance(target, int):
                    self._active_source.seek_index(target)
                elif isinstance(target, float):
                    self._active_source.seek_timestamp(target)
                else:
                    try:
                        self._active_source.seek_index(int(target))
                    except ValueError:
                        self._active_source.seek_timestamp(float(target))
        elif act == "speed":
            if target is not None:
                target_str = str(target).strip().upper()
                if target_str == "MAX":
                    raise ValueError(
                        "MAX is not an externally supported playback speed. "
                        "For unpaced execution, use OFFLINE_BATCH mode."
                    )
                if target_str in ("OFFLINE_BATCH", "BATCH"):
                    self._active_source.set_speed(0.0, mode=ReplayExecutionMode.OFFLINE_BATCH)
                else:
                    try:
                        val = float(target)
                    except (ValueError, TypeError) as e:
                        raise ValueError(f"Invalid playback speed target: {target}") from e
                    self._active_source.set_speed(val)
        elif act == "mode":
            if target is not None:
                mode_str = str(target).strip().upper()
                if mode_str == "MAX":
                    raise ValueError(
                        "MAX is not an externally supported mode. "
                        "For unpaced execution, use OFFLINE_BATCH."
                    )
                if mode_str == "REALTIME":
                    self._active_source.set_speed(1.0, mode=ReplayExecutionMode.REALTIME)
                elif mode_str in ("OFFLINE_BATCH", "BATCH"):
                    self._active_source.set_speed(0.0, mode=ReplayExecutionMode.OFFLINE_BATCH)
                elif mode_str == "ACCELERATED":
                    self._active_source.set_speed(2.0, mode=ReplayExecutionMode.ACCELERATED)
                else:
                    raise ValueError(
                        f"Unsupported replay execution mode: {target}. "
                        f"Approved modes: REALTIME, ACCELERATED, OFFLINE_BATCH."
                    )
        else:
            raise ValueError(f"Unsupported replay control action: {action}")

        return self._active_source.get_status()

    def get_status(self) -> ReplayCursorStatus:
        """Return current status of active replay cursor."""
        if not self._active_source:
            return ReplayCursorStatus(
                playback_state=PlaybackState.IDLE,
                execution_mode=ReplayExecutionMode.REALTIME,
                current_index=0,
                total_frames=0,
                data_timestamp=0.0,
                start_timestamp=0.0,
                end_timestamp=0.0,
                elapsed_sim_time_sec=0.0,
                total_sim_time_sec=0.0,
                progress_pct=0.0,
                playback_speed=1.0,
                source_filename=None,
                is_looping=False,
            )
        return self._active_source.get_status()
