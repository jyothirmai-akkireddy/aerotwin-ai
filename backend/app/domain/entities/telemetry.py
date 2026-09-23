"""TelemetryFrame domain entity representing a single time-stamped flight observation."""

from enum import Enum

from pydantic import BaseModel, Field, field_validator


class TelemetrySource(str, Enum):
    SIMULATED = "SIMULATED"
    REPLAY = "REPLAY"
    CAN_HARDWARE = "CAN_HARDWARE"


class QualityStatus(str, Enum):
    VALID = "VALID"
    GOOD = "GOOD"  # Backwards compatibility alias for VALID
    DEGRADED = "DEGRADED"
    INVALID = "INVALID"
    MISSING = "MISSING"


class TelemetryFrame(BaseModel):
    """Normalized, versioned telemetry frame for 4-cylinder MALE UAV aero-piston engines."""

    version: str = Field(default="1.0.0")
    timestamp: float = Field(..., gt=0.0, description="UTC epoch seconds")
    sequence_id: int = Field(..., ge=0, description="Sequential frame counter")
    source_type: TelemetrySource = Field(default=TelemetrySource.SIMULATED)
    quality_flag: QualityStatus = Field(default=QualityStatus.VALID)

    # Powertrain & Actuation
    rpm: float = Field(..., ge=0.0, le=7000.0, description="Crankshaft rotational speed (RPM)")
    manifold_pressure: float = Field(
        ..., ge=0.0, le=55.0, description="Manifold absolute pressure (inHg)"
    )
    throttle_position: float = Field(
        ..., ge=0.0, le=100.0, description="Commanded throttle angle percentage"
    )
    fuel_flow: float = Field(..., ge=0.0, le=80.0, description="Instantaneous fuel flow (L/h)")
    fuel_pressure: float = Field(
        ..., ge=0.0, le=6.5, description="Fuel rail differential pressure (bar)"
    )
    injection_timing: float = Field(..., ge=0.0, le=45.0, description="Spark advance (°BTDC)")

    # Thermal Dynamics (4-cylinder opposed engine: Rotax 914/915 iS class)
    cht: list[float] = Field(
        ...,
        min_length=4,
        max_length=4,
        description="Cylinder head temperatures for Cylinders 1-4 (°C)",
    )
    egt: list[float] = Field(
        ...,
        min_length=4,
        max_length=4,
        description="Exhaust gas temperatures for Cylinders 1-4 (°C)",
    )
    coolant_temp: float = Field(..., ge=-40.0, le=150.0, description="Cylinder jacket coolant (°C)")
    oil_temperature: float = Field(..., ge=-30.0, le=180.0, description="Sump oil temperature (°C)")

    # Lubrication & Mechanical
    oil_pressure: float = Field(..., ge=0.0, le=12.0, description="Main gallery oil pressure (bar)")
    vibration_rms: float = Field(..., ge=0.0, le=20.0, description="Tri-axial vibration RMS (g)")

    # Electrical & Avionics
    battery_voltage: float = Field(..., ge=0.0, le=35.0, description="Avionics bus voltage (V)")
    alternator_current: float = Field(..., ge=0.0, le=70.0, description="Alternator load (A)")
    alternator_status: str = Field(default="OK")

    # Environmental & Flight Conditions
    altitude: float = Field(..., ge=-500.0, le=15000.0, description="Pressure altitude (m ASL)")
    ambient_temp: float = Field(..., ge=-70.0, le=70.0, description="Outside air temperature (°C)")
    true_airspeed: float = Field(..., ge=0.0, le=150.0, description="True airspeed (m/s)")

    @field_validator("cht", "egt")
    @classmethod
    def validate_cylinder_temperatures(cls, values: list[float]) -> list[float]:
        if len(values) != 4:
            raise ValueError(
                "Exactly 4 cylinder readings required for horizontally-opposed aero-engine"
            )
        for temp in values:
            if not (-50.0 <= temp <= 1100.0):
                raise ValueError(
                    f"Temperature value {temp}°C is outside plausible aerospace bounds"
                )
        return values


# Domain-level alias conforming to domain vocabulary
TelemetrySample = TelemetryFrame
