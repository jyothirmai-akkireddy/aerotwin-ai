"""Calibration parameters repository for the Physics-Informed Digital Twin."""

import json
import os
from pathlib import Path

from app.domain.physics.models import PhysicsCalibrationParameters
from app.infrastructure.logging.logger import get_logger

logger = get_logger("aerotwin.physics.calibration")


class PhysicsCalibrationRepository:
    """Manages persistence and in-memory access to deterministic physics calibration parameters."""

    def __init__(self, config_path: str | None = None):
        if config_path:
            self.config_path = Path(config_path)
        else:
            self.config_path = Path(__file__).parent / "calibration_default.json"
        self._current_params = self._load()

    def _load(self) -> PhysicsCalibrationParameters:
        """Load parameters from JSON file or return default instance."""
        if self.config_path.exists():
            try:
                with open(self.config_path, encoding="utf-8") as f:
                    data = json.load(f)
                    params = PhysicsCalibrationParameters.model_validate(data)
                    logger.info(
                        f"Loaded physics calibration parameters v{params.version} from {self.config_path}"
                    )
                    return params
            except Exception as e:
                logger.warning(
                    f"Failed to parse calibration file {self.config_path}: {e}. Using defaults."
                )
        return PhysicsCalibrationParameters()

    def get_parameters(self) -> PhysicsCalibrationParameters:
        """Retrieve current active calibration parameters."""
        return self._current_params

    def update_parameters(
        self, new_params: PhysicsCalibrationParameters
    ) -> PhysicsCalibrationParameters:
        """Update active parameters in-memory and write to JSON if permitted."""
        self._current_params = new_params
        try:
            os.makedirs(self.config_path.parent, exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                f.write(new_params.model_dump_json(indent=2))
            logger.info(f"Saved updated physics calibration parameters v{new_params.version}")
        except Exception as e:
            logger.warning(f"Could not persist calibration to disk: {e}")
        return self._current_params
