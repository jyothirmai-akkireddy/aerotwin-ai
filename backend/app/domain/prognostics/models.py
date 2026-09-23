"""Domain models, value objects, and schemas for Phase 7 Engine Degradation & Prognostics."""

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class DegradationState(str, Enum):
    """Operational engine degradation states (Prototype/Synthetic Thresholds)."""

    NOMINAL = "NOMINAL"  # HI in [0.90, 1.00]
    EARLY_DEGRADATION = "EARLY_DEGRADATION"  # HI in [0.75, 0.90)
    MODERATE_DEGRADATION = "MODERATE_DEGRADATION"  # HI in [0.50, 0.75)
    SEVERE_DEGRADATION = "SEVERE_DEGRADATION"  # HI in [0.25, 0.50)
    CRITICAL_SIMULATED_STATE = "CRITICAL_SIMULATED_STATE"  # HI in [0.00, 0.25)


class TrendDirection(str, Enum):
    """Causal health trend direction classification."""

    IMPROVING = "IMPROVING"
    STABLE = "STABLE"
    DEGRADING = "DEGRADING"
    UNKNOWN = "UNKNOWN"


class RULStatus(str, Enum):
    """Execution and availability status for Remaining Useful Life (RUL) estimation."""

    ACTIVE = "ACTIVE"
    INSUFFICIENT_HISTORY = "INSUFFICIENT_HISTORY"
    RUL_UNAVAILABLE = "RUL_UNAVAILABLE"
    DEGRADATION_NOT_DETECTED = "DEGRADATION_NOT_DETECTED"


class SubsystemDegradationMetric(BaseModel):
    """3-tier degradation value preserving raw, normalized, and bounded penalty terms."""

    raw_deviation: float = Field(
        ..., description="Unnormalized physical delta in native engineering units"
    )
    normalized_deviation: float = Field(
        ..., ge=0.0, description="Dimensionless ratio relative to calibration sigma (|r| / sigma)"
    )
    bounded_penalty: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Clamped degradation penalty in [0.0, 1.0] for Health Index weighting",
    )
    unit: str = Field(default="", description="Native physical engineering unit")


class SubsystemDegradation(BaseModel):
    """Composite subsystem degradation metrics and percentage health indicators."""

    lubrication: SubsystemDegradationMetric
    thermal: SubsystemDegradationMetric
    turbocharger: SubsystemDegradationMetric
    rotational_vibration: SubsystemDegradationMetric
    anomaly_penalty: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Threshold-gated anomaly penalty d_anom in [0.0, 1.0]",
    )
    lubrication_health_pct: float = Field(default=100.0, ge=0.0, le=100.0)
    thermal_health_pct: float = Field(default=100.0, ge=0.0, le=100.0)
    turbocharger_health_pct: float = Field(default=100.0, ge=0.0, le=100.0)
    rotational_health_pct: float = Field(default=100.0, ge=0.0, le=100.0)
    limiting_subsystem: str = Field(default="nominal")


class RULEstimate(BaseModel):
    """Remaining Useful Life estimation with 95% prediction intervals and fallback gating."""

    status: RULStatus = Field(default=RULStatus.DEGRADATION_NOT_DETECTED)
    estimated_remaining_flight_hours: float | None = Field(
        default=None,
        ge=0.0,
        description="Point estimate of remaining flight hours (None if unavailable/nominal)",
    )
    confidence_interval_95: tuple[float, float] | None = Field(
        default=None,
        description="95% statistical prediction interval (lower_hours, upper_hours) or None",
    )
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Runtime heuristic prognostic confidence score in [0.0, 1.0]",
    )
    limiting_subsystem: str = Field(
        default="nominal", description="Primary subsystem driving life consumption"
    )
    degradation_rate_per_hour: float | None = Field(
        default=None, description="Estimated linear wear rate per flight hour"
    )
    reason: str = Field(
        default="", description="Diagnostic explanation of RUL status and gating decisions"
    )


class PrognosticIndicator(BaseModel):
    """Key diagnostic telemetry indicator with deviation severity and trend."""

    name: str = Field(..., description="Indicator identifier")
    current_value: float = Field(..., description="Current observed telemetry value")
    baseline_value: float = Field(..., description="Expected physical baseline value")
    raw_deviation: float = Field(..., description="Raw difference in native engineering units")
    normalized_deviation: float = Field(..., ge=0.0, description="Normalized deviation ratio")
    unit: str = Field(default="", description="Physical unit")
    severity: Literal["NORMAL", "ADVISORY", "WARNING", "CRITICAL"] = Field(default="NORMAL")
    trend: TrendDirection = Field(default=TrendDirection.STABLE)


class PrognosticResult(BaseModel):
    """Unified application-level prognostics and degradation container."""

    timestamp: float = Field(..., description="Simulation epoch timestamp")
    sequence_id: int = Field(..., ge=0, description="Monotonic telemetry sequence identifier")
    feature_schema_version: str = Field(default="1.0.0")
    health_index: float = Field(
        ..., ge=0.0, le=1.0, description="Composite Health Index in [0.0, 1.0]"
    )
    degradation_state: DegradationState = Field(default=DegradationState.NOMINAL)
    trend_direction: TrendDirection = Field(default=TrendDirection.STABLE)
    trend_slope_per_sec: float = Field(
        default=0.0, description="Estimated rate of change of Health Index per second"
    )
    subsystems: SubsystemDegradation
    rul: RULEstimate
    indicators: list[PrognosticIndicator] = Field(default_factory=list)
    pipeline_latency_ms: float = Field(
        ..., ge=0.0, description="Total prognostics evaluation latency in milliseconds"
    )
    disaggregated_latencies: dict[str, float] = Field(
        default_factory=dict, description="Component latency breakdown in milliseconds"
    )
    validity: Literal["VALID", "DEGRADED", "INVALID"] = Field(
        default="VALID", description="Operational validity flag"
    )
    prototype_notice: str = Field(
        default="PROTOTYPE RESEARCH MODEL — NOT FOR CERTIFIED FLIGHT OPERATIONS"
    )
