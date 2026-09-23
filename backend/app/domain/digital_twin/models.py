"""Digital Twin state entities tracking synchronization and residual vectors."""

from enum import Enum

from pydantic import BaseModel, Field

from app.domain.engine.models import EngineState
from app.domain.value_objects.residuals import ResidualVector


class TwinSyncStatus(str, Enum):
    UNINITIALIZED = "UNINITIALIZED"
    SYNCHRONIZING = "SYNCHRONIZING"
    SYNCHRONIZED = "SYNCHRONIZED"
    DESYNCHRONIZED = "DESYNCHRONIZED"
    OFFLINE = "OFFLINE"


class DigitalTwinState(BaseModel):
    """Aggregate state comparing actual physical observations against virtual twin expectations."""

    timestamp: float = Field(..., description="Epoch observation timestamp")
    sync_status: TwinSyncStatus = TwinSyncStatus.UNINITIALIZED
    actual_state: EngineState | None = None
    expected_state: EngineState | None = None
    residuals: ResidualVector | None = None
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0)
    latency_ms: float = Field(default=0.0, description="Measured processing time in milliseconds")
