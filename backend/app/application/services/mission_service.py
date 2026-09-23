"""Application service for managing mission definitions, execution, and persistence."""

from pathlib import Path

from app.application.services.mission_simulator import MissionSimulator
from app.config import settings
from app.domain.entities.telemetry import TelemetryFrame
from app.domain.mission.catalog import STANDARD_MISSIONS, get_predefined_mission
from app.domain.mission.models import MissionDefinition, MissionSimulationSummary
from app.infrastructure.logging.logger import get_logger
from app.infrastructure.persistence.telemetry_repository import SqliteTelemetryRepository

logger = get_logger("aerotwin.service.mission")


class MissionService:
    """Application service coordinating mission simulation and dataset persistence."""

    MAX_INLINE_FRAMES = 500

    def __init__(self, missions_storage_dir: str | Path | None = None):
        if missions_storage_dir is None:
            self.storage_dir = Path(settings.storage.parquet_data_dir).parent / "missions"
        else:
            self.storage_dir = Path(missions_storage_dir)

        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def list_predefined_missions(self) -> list[dict]:
        """List summary information for all predefined benchmark missions."""
        results = []
        for _mission_id, m in STANDARD_MISSIONS.items():
            results.append(
                {
                    "mission_id": m.mission_id,
                    "name": m.name,
                    "description": m.description,
                    "total_duration_sec": m.total_duration_sec,
                    "phase_count": m.phase_count,
                    "is_synthetic": m.is_synthetic,
                    "version": m.version,
                }
            )
        return results

    def get_mission_definition(self, mission_id: str) -> MissionDefinition | None:
        """Retrieve full domain MissionDefinition by identifier."""
        return get_predefined_mission(mission_id)

    def simulate_mission(
        self,
        mission: MissionDefinition,
        rate_hz: int = 10,
        seed: int = 42,
        persist_dataset: bool = True,
        include_frames: bool = False,
    ) -> tuple[MissionSimulationSummary, list[TelemetryFrame] | None]:
        """Execute a deterministic mission simulation.

        Returns:
            (MissionSimulationSummary, optional_bounded_inline_frames)
        """
        simulator = MissionSimulator(mission=mission, telemetry_rate_hz=rate_hz, seed=seed)
        summary, frames = simulator.run_sync()

        # Persist to disk if requested or if dataset exceeds inline boundary
        if persist_dataset or (include_frames and len(frames) > self.MAX_INLINE_FRAMES):
            dataset_filename = f"{summary.run_id}_{mission.mission_id}.parquet"
            dataset_dest = self.storage_dir / dataset_filename
            SqliteTelemetryRepository.export_frames_to_parquet(frames, dataset_dest)
            summary.dataset_path = str(dataset_dest)
            logger.info(f"Persisted mission dataset ({len(frames)} frames) to {dataset_dest}")

        inline_result: list[TelemetryFrame] | None = None
        if include_frames:
            if len(frames) <= self.MAX_INLINE_FRAMES:
                inline_result = frames
            else:
                logger.info(
                    f"Frame count ({len(frames)}) exceeds MAX_INLINE_FRAMES ({self.MAX_INLINE_FRAMES}); "
                    f"omitting inline frames. Data persisted to {summary.dataset_path}"
                )

        return summary, inline_result
