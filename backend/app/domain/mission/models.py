"""Domain models for mission phases, mission definitions, execution summaries, and telemetry context.

PROTOTYPE DISCLAIMER:
These schemas define engineering prototype structures for research/prototyping.
They do not represent certified airworthiness flight procedures or OEM specifications.
"""

import math

from pydantic import BaseModel, Field, model_validator

from app.domain.mission.enums import MissionPhaseType
from app.domain.mission.events import MissionControlEvent, MissionFaultEvent
from app.domain.mission.profiles import ProfileCurve


class MissionPhaseDefinition(BaseModel):
    """Discrete operational phase within a structured flight mission."""

    phase_id: str = Field(
        ..., min_length=1, description="Unique identifier for the phase within mission"
    )
    phase_type: MissionPhaseType = Field(..., description="Authoritative flight phase category")
    duration_sec: float = Field(..., gt=0.0, description="Phase duration in seconds")
    throttle_profile: ProfileCurve = Field(
        ..., description="Throttle angle percentage profile [0..100]"
    )
    altitude_profile: ProfileCurve = Field(
        ..., description="Target altitude profile in meters [-200..12000]"
    )
    airspeed_profile: ProfileCurve = Field(
        ..., description="Target true airspeed profile in m/s [0..120]"
    )
    ambient_temp_profile: ProfileCurve = Field(
        ..., description="Ambient temperature profile in °C [-60..60]"
    )
    ignition_on: bool = Field(default=True, description="Ignition circuit state")
    starter_engaged: bool = Field(default=False, description="Starter motor engagement state")
    description: str = Field(default="", description="Phase operational descriptor")

    @model_validator(mode="after")
    def validate_durations(self) -> "MissionPhaseDefinition":
        """Verify profile curve durations match phase duration."""
        if not math.isclose(self.throttle_profile.duration_sec, self.duration_sec, rel_tol=1e-5):
            raise ValueError(
                f"throttle_profile duration ({self.throttle_profile.duration_sec}s) must match phase duration ({self.duration_sec}s)"
            )
        if not math.isclose(self.altitude_profile.duration_sec, self.duration_sec, rel_tol=1e-5):
            raise ValueError(
                f"altitude_profile duration ({self.altitude_profile.duration_sec}s) must match phase duration ({self.duration_sec}s)"
            )
        if not math.isclose(self.airspeed_profile.duration_sec, self.duration_sec, rel_tol=1e-5):
            raise ValueError(
                f"airspeed_profile duration ({self.airspeed_profile.duration_sec}s) must match phase duration ({self.duration_sec}s)"
            )
        if not math.isclose(
            self.ambient_temp_profile.duration_sec, self.duration_sec, rel_tol=1e-5
        ):
            raise ValueError(
                f"ambient_temp_profile duration ({self.ambient_temp_profile.duration_sec}s) must match phase duration ({self.duration_sec}s)"
            )
        return self

    def get_operating_inputs(
        self, elapsed_sec: float
    ) -> tuple[float, float, float, float, bool, bool]:
        """Evaluate physical target inputs at elapsed seconds within the phase.

        Returns:
            (throttle_pct, altitude_m, true_airspeed_ms, ambient_temp_c, ignition_on, starter_engaged)
        """
        throttle = self.throttle_profile.evaluate(elapsed_sec)
        alt = self.altitude_profile.evaluate(elapsed_sec)
        tas = self.airspeed_profile.evaluate(elapsed_sec)
        amb_t = self.ambient_temp_profile.evaluate(elapsed_sec)
        return throttle, alt, tas, amb_t, self.ignition_on, self.starter_engaged


class MissionDefinition(BaseModel):
    """Authoritative domain specification of a complete flight mission."""

    mission_id: str = Field(..., min_length=1, description="Unique alphanumeric mission identifier")
    name: str = Field(..., min_length=1, description="Human-readable mission name")
    description: str = Field(
        default="", description="Mission operational objectives and profile description"
    )
    initial_altitude_m: float = Field(default=0.0, ge=-200.0, le=12000.0)
    initial_ambient_temp_c: float = Field(default=15.0, ge=-60.0, le=60.0)
    phases: list[MissionPhaseDefinition] = Field(
        ..., min_length=1, description="Sequential phase definitions"
    )
    control_events: list[MissionControlEvent] = Field(
        default_factory=list, description="Transient control disturbances"
    )
    fault_events: list[MissionFaultEvent] = Field(
        default_factory=list, description="Sensor fault injections"
    )
    is_synthetic: bool = Field(default=True, description="Explicit prototype label")
    version: str = Field(default="1.0.0", description="Mission schema version")

    @property
    def total_duration_sec(self) -> float:
        """Calculate total scheduled mission duration in seconds."""
        return sum(p.duration_sec for p in self.phases)

    @property
    def phase_count(self) -> int:
        """Return total number of phases in the mission."""
        return len(self.phases)

    @model_validator(mode="after")
    def validate_mission_events(self) -> "MissionDefinition":
        """Verify events occur within total mission duration and IDs are unique."""
        total_dur = self.total_duration_sec
        event_ids: set[str] = set()

        for ce in self.control_events:
            if ce.event_id in event_ids:
                raise ValueError(f"Duplicate event_id detected in mission: {ce.event_id}")
            event_ids.add(ce.event_id)
            if ce.start_time_sec >= total_dur:
                raise ValueError(
                    f"Control event {ce.event_id} start time ({ce.start_time_sec}s) exceeds total mission duration ({total_dur}s)"
                )

        for fe in self.fault_events:
            if fe.event_id in event_ids:
                raise ValueError(f"Duplicate event_id detected in mission: {fe.event_id}")
            event_ids.add(fe.event_id)
            if fe.start_time_sec >= total_dur:
                raise ValueError(
                    f"Fault event {fe.event_id} start time ({fe.start_time_sec}s) exceeds total mission duration ({total_dur}s)"
                )

        return self


class PhaseSummary(BaseModel):
    """Statistical summary for an individual phase execution."""

    phase_id: str
    phase_type: MissionPhaseType
    start_time_sec: float
    duration_sec: float
    fuel_burned_liters: float
    avg_rpm: float
    max_cht_c: float
    max_egt_c: float


class MissionSimulationSummary(BaseModel):
    """Cumulative operational metrics computed over a completed mission simulation."""

    run_id: str
    mission_id: str
    mission_version: str = "1.0.0"
    total_duration_sec: float
    total_frames: int
    fuel_consumed_liters: float
    fuel_mass_kg: float
    max_cht_c: float
    max_egt_c: float
    max_oil_temp_c: float
    min_oil_pressure_bar: float
    peak_vibration_rms: float
    max_altitude_m: float
    phase_summaries: list[PhaseSummary]
    dataset_path: str | None = None
    is_deterministic: bool = True
    prototype_disclaimer: str = (
        "PROTOTYPE NON-CERTIFIED BENCHMARK DATA: Results are simulated approximations."
    )


class MissionTelemetryContext(BaseModel):
    """Dynamic mission progress information attached to real-time telemetry broadcasts."""

    mission_id: str
    mission_name: str
    current_phase_id: str
    current_phase_type: MissionPhaseType
    phase_elapsed_sec: float
    phase_duration_sec: float
    mission_elapsed_sec: float
    total_duration_sec: float
    mission_progress_pct: float
