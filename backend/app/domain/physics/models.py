"""Domain models, value objects, and calibration schemas for the Physics-Informed Digital Twin."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ModelValidity(str, Enum):
    """Operational validity classification for analytical physics models."""

    VALID = "VALID"  # Operating point within nominal validated flight envelope
    DEGRADED = "DEGRADED"  # Engine transient / starting / non-critical parameter degraded
    OUT_OF_RANGE = "OUT_OF_RANGE"  # Operating conditions exceed physical calibration envelope
    INVALID = "INVALID"  # Missing telemetry, non-finite values (NaN/Inf), or corrupted quality


class PhysicsExpectedState(BaseModel):
    """Estimated nominal engine physical state computed by first-principles sub-models."""

    timestamp: float = Field(..., description="Epoch observation timestamp (seconds)")
    sequence_id: int = Field(..., ge=0, description="Sequential telemetry frame index")
    rpm: float = Field(..., description="Expected crankshaft rotational speed (RPM)")
    manifold_pressure: float = Field(..., description="Expected manifold absolute pressure (inHg)")
    air_mass_flow: float = Field(..., description="Expected air induction mass flow (kg/h)")
    fuel_flow: float = Field(..., description="Expected fuel consumption rate (L/h)")
    cht: list[float] = Field(
        ..., min_length=4, max_length=4, description="Expected CHT for Cylinders 1-4 (°C)"
    )
    egt: list[float] = Field(
        ..., min_length=4, max_length=4, description="Expected EGT for Cylinders 1-4 (°C)"
    )
    coolant_temp: float = Field(..., description="Expected coolant jacket temperature (°C)")
    oil_temperature: float = Field(..., description="Expected sump oil temperature (°C)")
    oil_pressure: float = Field(..., description="Expected gallery oil pressure (bar)")
    vibration_rms: float = Field(..., description="Expected baseline vibration RMS (g)")
    validity: ModelValidity = Field(default=ModelValidity.VALID)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    model_version: str = Field(default="1.0.0")


class PhysicsResidualSet(BaseModel):
    """Deviations (observed - expected) evaluated across all primary physical parameters."""

    timestamp: float = Field(..., description="Observation timestamp")
    sequence_id: int = Field(..., ge=0)
    raw_residuals: dict[str, float | list[float]] = Field(
        default_factory=dict, description="Algebraic differences in physical engineering units"
    )
    normalized_residuals: dict[str, float | list[float]] = Field(
        default_factory=dict, description="Residuals scaled by empirical sigma standard deviations"
    )
    cht_max_imbalance_celsius: float = Field(
        default=0.0, description="Maximum cylinder head temperature spread among cylinders (°C)"
    )
    egt_max_imbalance_celsius: float = Field(
        default=0.0, description="Maximum exhaust gas temperature spread among cylinders (°C)"
    )
    mean_absolute_normalized_residual: float = Field(
        default=0.0, description="Overall normalized residual magnitude across all primary channels"
    )
    validity: ModelValidity = Field(default=ModelValidity.VALID)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class PhysicsCalibrationParameters(BaseModel):
    """Configurable coefficients and empirical sigma scales for the Physics Twin."""

    version: str = Field(default="1.0.0")
    engine_displacement_cc: float = Field(
        default=1352.0, ge=500.0, le=3000.0, description="Engine displacement volume (cc)"
    )
    idle_rpm: float = Field(default=1400.0, ge=600.0, le=2500.0)
    rated_rpm: float = Field(default=5500.0, ge=3000.0, le=7000.0)
    spool_rpm: float = Field(default=2200.0, ge=1000.0, le=3500.0)
    max_boost_pr: float = Field(default=1.45, ge=1.0, le=2.5)

    # Thermal time constants (seconds)
    tau_cht_seconds: float = Field(default=14.0, ge=2.0, le=60.0)
    tau_egt_seconds: float = Field(default=1.2, ge=0.2, le=10.0)
    tau_oil_seconds: float = Field(default=35.0, ge=5.0, le=120.0)
    tau_coolant_seconds: float = Field(default=16.0, ge=2.0, le=60.0)

    # Cylinder geometric bias factors [cyl 1, cyl 2, cyl 3, cyl 4]
    cht_cylinder_bias: list[float] = Field(
        default_factory=lambda: [1.00, 0.98, 1.03, 0.99],
        min_length=4,
        max_length=4,
    )
    egt_cylinder_bias: list[float] = Field(
        default_factory=lambda: [1.00, 0.99, 1.02, 1.00],
        min_length=4,
        max_length=4,
    )

    # Empirical sigma scales for normalized residual calculation
    # Derived as empirical standard deviation from Phase 2 steady-state flight dataset
    sigma_scales: dict[str, float] = Field(
        default_factory=lambda: {
            "rpm": 45.0,
            "manifold_pressure": 0.65,
            "fuel_flow": 0.55,
            "cht": 3.50,
            "egt": 14.20,
            "coolant_temp": 2.20,
            "oil_temperature": 2.80,
            "oil_pressure": 0.28,
            "vibration_rms": 0.22,
        }
    )


class PhysicsTwinResult(BaseModel):
    """Composite container holding expected state, residuals, and model diagnostics."""

    expected_state: PhysicsExpectedState
    residuals: PhysicsResidualSet
    diagnostics: dict[str, Any] = Field(default_factory=dict)
