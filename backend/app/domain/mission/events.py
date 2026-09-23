"""Mission transient disturbance events and sensor fault specifications.

Partitions mission events strictly into:
1. MissionControlEvent: Additive perturbations to simulator input controls (throttle, altitude, temp, airspeed).
2. MissionFaultEvent: Structured sensor faults mapped directly to Phase 2 FaultController.

PROHIBITION: Under no circumstances are physical telemetry fields directly overwritten outside the engine model.
"""

import math

from pydantic import BaseModel, Field, model_validator

from app.domain.mission.enums import ControlTargetParameter
from app.domain.simulation.faults import SensorFaultConfig, SensorFaultType


class MissionControlEvent(BaseModel):
    """Additive perturbation to physical engine control or environmental inputs."""

    event_id: str = Field(..., min_length=1, description="Unique event identifier")
    start_time_sec: float = Field(
        ..., ge=0.0, description="Mission simulation time when event begins (seconds)"
    )
    duration_sec: float = Field(..., gt=0.0, description="Active event duration (seconds)")
    target_parameter: ControlTargetParameter = Field(
        ..., description="Whitelisted simulator input control target"
    )
    magnitude: float = Field(
        ..., description="Additive perturbation magnitude (e.g. +10% throttle, -50m gust)"
    )

    @model_validator(mode="after")
    def validate_control_event(self) -> "MissionControlEvent":
        if not math.isfinite(self.start_time_sec):
            raise ValueError("start_time_sec must be finite")
        if not math.isfinite(self.duration_sec) or self.duration_sec <= 0.0:
            raise ValueError("duration_sec must be positive and finite")
        if not math.isfinite(self.magnitude):
            raise ValueError("magnitude must be finite")
        return self

    def is_active(self, mission_time_sec: float) -> bool:
        """Check if event is currently active at given mission time."""
        return self.start_time_sec <= mission_time_sec < (self.start_time_sec + self.duration_sec)

    def evaluate_offset(self, mission_time_sec: float) -> float:
        """Return additive perturbation magnitude if active, 0.0 otherwise."""
        if self.is_active(mission_time_sec):
            return self.magnitude
        return 0.0


class MissionFaultEvent(BaseModel):
    """Synthetic sensor fault injection mapped strictly to Phase 2 FaultController."""

    event_id: str = Field(..., min_length=1, description="Unique fault event identifier")
    start_time_sec: float = Field(
        ..., ge=0.0, description="Mission simulation time when fault starts (seconds)"
    )
    duration_sec: float | None = Field(
        default=None,
        description="Active fault duration in seconds (None indicates fault persists to mission end)",
    )
    target_channel: str = Field(
        ...,
        min_length=1,
        description="Instrumented telemetry sensor channel (e.g. 'oil_pressure', 'cht_2', 'manifold_pressure')",
    )
    fault_type: SensorFaultType = Field(..., description="Supported sensor fault mode")
    magnitude: float = Field(
        default=0.0, description="Fault magnitude (offset for bias, value for stuck)"
    )
    drift_rate_per_sec: float = Field(default=0.0, description="Rate of drift per second")
    noise_multiplier: float = Field(default=3.0, ge=1.0, description="Noise variance multiplier")
    is_synthetic: bool = Field(default=True, description="Explicit prototype label")

    @model_validator(mode="after")
    def validate_fault_event(self) -> "MissionFaultEvent":
        if not math.isfinite(self.start_time_sec):
            raise ValueError("start_time_sec must be finite")
        if self.duration_sec is not None:
            if not math.isfinite(self.duration_sec) or self.duration_sec <= 0.0:
                raise ValueError("duration_sec must be positive and finite when specified")
        if not math.isfinite(self.magnitude):
            raise ValueError("magnitude must be finite")
        return self

    def to_sensor_fault_config(self) -> SensorFaultConfig:
        """Convert to authoritative Phase 2 domain SensorFaultConfig."""
        end_time = (
            (self.start_time_sec + self.duration_sec) if self.duration_sec is not None else None
        )
        return SensorFaultConfig(
            target_channel=self.target_channel,
            fault_type=self.fault_type,
            start_time_sec=self.start_time_sec,
            end_time_sec=end_time,
            magnitude=self.magnitude,
            drift_rate_per_sec=self.drift_rate_per_sec,
            noise_multiplier=self.noise_multiplier,
        )
