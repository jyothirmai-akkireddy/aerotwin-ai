"""Engine health evaluation and Remaining Useful Life (RUL) domain models."""

from enum import Enum

from pydantic import BaseModel, Field


class HealthStatus(str, Enum):
    EXCELLENT = "EXCELLENT"  # 90 - 100
    GOOD = "GOOD"  # 75 - 89
    DEGRADED = "DEGRADED"  # 50 - 74
    CRITICAL = "CRITICAL"  # < 50


class SubsystemHealth(BaseModel):
    """Health breakdown per major mechanical/thermal subsystem."""

    combustion_score: float = Field(default=100.0, ge=0.0, le=100.0)
    cooling_score: float = Field(default=100.0, ge=0.0, le=100.0)
    lubrication_score: float = Field(default=100.0, ge=0.0, le=100.0)
    turbocharger_score: float = Field(default=100.0, ge=0.0, le=100.0)


class RULProjection(BaseModel):
    """Remaining Useful Life estimation based on degradation trajectory."""

    estimated_hours_remaining: float = Field(..., ge=0.0)
    confidence_interval_hours: tuple[float, float] = (0.0, 0.0)
    primary_limiting_subsystem: str = "nominal"
    degradation_rate_per_hour: float = Field(default=0.0, ge=0.0)


class HealthState(BaseModel):
    """Composite health state evaluation of the engine."""

    timestamp: float = Field(..., description="Epoch observation timestamp")
    overall_health_index: float = Field(default=100.0, ge=0.0, le=100.0)
    status: HealthStatus = HealthStatus.EXCELLENT
    subsystems: SubsystemHealth = Field(default_factory=SubsystemHealth)
    rul: RULProjection | None = None
    active_risk_factors: list[str] = Field(default_factory=list)
