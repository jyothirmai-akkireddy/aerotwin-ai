"""Simulation domain models for mission profiles and environmental conditions."""

from enum import Enum

from pydantic import BaseModel, Field


class MissionProfile(str, Enum):
    STANDARD_SURVEILLANCE = "STANDARD_SURVEILLANCE"
    HIGH_ALTITUDE_LOITER = "HIGH_ALTITUDE_LOITER"
    HOT_WEATHER_STRESS = "HOT_WEATHER_STRESS"
    RAPID_THROTTLE_TRANSIENTS = "RAPID_THROTTLE_TRANSIENTS"
    ENDURANCE_DEGRADATION = "ENDURANCE_DEGRADATION"


class FaultInjectionCommand(BaseModel):
    """Command specification for scheduled or manual fault injection."""

    fault_code: str
    trigger_time_sec: float = Field(..., ge=0.0)
    severity_factor: float = Field(default=1.0, ge=0.0, le=1.0)
    target_cylinder: int | None = Field(default=None, ge=1, le=4)
    duration_sec: float | None = Field(default=None, gt=0.0)


class SimulationScenario(BaseModel):
    """Complete flight profile and environmental simulation scenario."""

    scenario_id: str
    profile: MissionProfile = MissionProfile.STANDARD_SURVEILLANCE
    duration_sec: float = Field(default=3600.0, gt=0.0)
    initial_altitude_m: float = Field(default=1000.0, ge=0.0)
    initial_oat_c: float = Field(default=15.0)
    target_cruise_altitude_m: float = Field(default=3500.0, ge=0.0)
    injected_faults: list[FaultInjectionCommand] = Field(default_factory=list)
