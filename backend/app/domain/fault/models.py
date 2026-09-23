"""Fault domain entities representing diagnostics events and advisories."""

from enum import Enum

from pydantic import BaseModel, Field


class FaultSeverity(str, Enum):
    INFO = "INFO"
    ADVISORY = "ADVISORY"
    CAUTION = "CAUTION"
    WARNING = "WARNING"


class FaultCategory(str, Enum):
    THERMAL = "THERMAL"
    COMBUSTION = "COMBUSTION"
    LUBRICATION = "LUBRICATION"
    TURBOCHARGER = "TURBOCHARGER"
    SENSOR = "SENSOR"
    MECHANICAL = "MECHANICAL"


class FaultEvent(BaseModel):
    """Discrete diagnostic event flagged by the residual and AI analysis engines."""

    fault_id: str = Field(..., description="Unique fault event identifier")
    timestamp: float = Field(..., description="Observation timestamp")
    fault_code: str = Field(..., description="Standardized fault code e.g. FAULT_MISFIRE_CYL_2")
    category: FaultCategory
    severity: FaultSeverity
    description: str
    affected_cylinder: int | None = Field(default=None, ge=1, le=4)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    is_confirmed: bool = Field(
        default=False, description="True after temporal confirmation filter passes"
    )
    recommendation: str | None = None
