"""Engine domain entities and specifications for MALE UAV aero-piston propulsion.

PROTOTYPE DISCLAIMER:
Parameters and thermodynamic limits defined herein represent generalized engineering
prototype assumptions for a 4-cylinder horizontally-opposed turbocharged aero-piston
engine inspired by the Rotax 914/915 class. They do NOT represent certified OEM values.
"""

from enum import Enum

from pydantic import BaseModel, Field


class EngineOperatingMode(str, Enum):
    OFF = "OFF"
    CRANKING = "CRANKING"
    IDLE = "IDLE"
    CRUISE = "CRUISE"
    TAKEOFF_CLIMB = "TAKEOFF_CLIMB"
    DESCENT = "DESCENT"
    MAX_CONTINUOUS = "MAX_CONTINUOUS"


class EngineSpecifications(BaseModel):
    """Generic specifications and prototype assumptions for aero-piston engine baseline."""

    designation: str = "Generic 4-Cyl Boxer Turbo Aero-Piston (Rotax 914/915 Class Inspired)"
    cylinder_count: int = Field(default=4, description="Four horizontally-opposed cylinders")
    displacement_liters: float = Field(
        default=1.352, description="Prototype assumption: ~1.35L displacement"
    )
    compression_ratio: float = Field(
        default=9.0, description="Prototype assumption: 9.0:1 compression ratio"
    )
    turbocharged: bool = True
    max_continuous_rpm: float = Field(
        default=5500.0, description="Prototype assumption: 5500 RPM continuous"
    )
    takeoff_max_rpm: float = Field(
        default=5800.0, description="Prototype assumption: 5800 RPM max 5-min takeoff"
    )
    redline_rpm: float = Field(
        default=6500.0, description="Prototype assumption: 6500 RPM transient redline"
    )
    idle_rpm: float = Field(
        default=1400.0, description="Prototype assumption: 1400 RPM nominal ground idle"
    )

    # Thermal boundaries (prototype assumptions)
    max_continuous_cht_c: float = Field(default=135.0, description="Max continuous CHT °C")
    max_transient_cht_c: float = Field(default=150.0, description="Max transient CHT °C")
    normal_egt_range_c: tuple[float, float] = (700.0, 880.0)

    # Lubrication boundaries (prototype assumptions)
    nominal_oil_pressure_bar: float = Field(
        default=3.5, description="Nominal oil gallery pressure bar"
    )
    min_oil_pressure_bar: float = Field(
        default=1.5, description="Critical minimum oil pressure bar"
    )
    max_oil_temperature_c: float = Field(default=130.0, description="Max oil temperature °C")


class EngineState(BaseModel):
    """Instantaneous operational state of the physical or virtual engine."""

    timestamp: float = Field(..., description="Epoch observation timestamp")
    mode: EngineOperatingMode = EngineOperatingMode.OFF
    rpm: float = Field(..., ge=0.0)
    manifold_pressure_inhg: float = Field(..., ge=0.0)
    throttle_pct: float = Field(..., ge=0.0, le=100.0)
    cht_c: list[float] = Field(..., min_length=4, max_length=4)
    egt_c: list[float] = Field(..., min_length=4, max_length=4)
    oil_pressure_bar: float = Field(..., ge=0.0)
    oil_temperature_c: float = Field(...)
    fuel_flow_lph: float = Field(..., ge=0.0)
    vibration_g: float = Field(..., ge=0.0)
    running_hours: float = Field(default=0.0, ge=0.0)
