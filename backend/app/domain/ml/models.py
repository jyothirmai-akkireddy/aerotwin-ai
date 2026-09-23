"""Domain models, value objects, and result schemas for Phase 6 ML diagnostics."""

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class AnomalyStatus(str, Enum):
    """Operational anomaly status."""

    NORMAL = "NORMAL"
    ANOMALOUS = "ANOMALOUS"


class FaultCategory(str, Enum):
    """Supported fault classification categories."""

    NORMAL = "NORMAL"
    OIL_PRESSURE_BIAS = "OIL_PRESSURE_BIAS"
    OIL_TEMP_DRIFT = "OIL_TEMP_DRIFT"
    THROTTLE_STUCK = "THROTTLE_STUCK"
    SENSOR_DROPOUT = "SENSOR_DROPOUT"
    MAP_NOISE_SPIKE = "MAP_NOISE_SPIKE"
    UNKNOWN = "UNKNOWN"


class DecisionReason(str, Enum):
    """Reason behind the fault diagnostic classification decision."""

    CONFIDENT_MATCH = "CONFIDENT_MATCH"
    NOMINAL_FLIGHT = "NOMINAL_FLIGHT"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    OUT_OF_DISTRIBUTION = "OUT_OF_DISTRIBUTION"


class FeatureContribution(BaseModel):
    """Feature attribution indicating relative importance and directional deviation."""

    feature_name: str = Field(..., description="Name of the contributing feature")
    contribution_weight: float = Field(
        ..., ge=0.0, le=1.0, description="Normalized relative weight (0.0 - 1.0)"
    )
    direction: Literal["ELEVATED", "DEPRESSED", "IRREGULAR"] = Field(
        default="IRREGULAR", description="Qualitative direction of the deviation"
    )


class AnomalyInferenceResult(BaseModel):
    """Output from the unsupervised anomaly detection model."""

    flag: bool = Field(..., description="True if anomaly score exceeds threshold")
    status: AnomalyStatus = Field(default=AnomalyStatus.NORMAL)
    score: float = Field(
        ..., ge=0.0, le=1.0, description="Normalized anomaly severity score in [0.0, 1.0]"
    )
    raw_score: float = Field(..., description="Raw decision function output from detector")
    threshold: float = Field(default=0.65, ge=0.0, le=1.0, description="Decision threshold applied")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in the anomaly decision")
    detector_name: str = Field(default="IsolationForest")
    model_version: str = Field(default="1.0.0")


class FaultInferenceResult(BaseModel):
    """Output from the supervised fault classification model."""

    fault_class: FaultCategory = Field(..., description="Predicted fault category or UNKNOWN")
    reason: DecisionReason = Field(
        default=DecisionReason.CONFIDENT_MATCH,
        description="Semantic reason (CONFIDENT_MATCH, LOW_CONFIDENCE, or OUT_OF_DISTRIBUTION)",
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Top predicted class probability or confidence"
    )
    probabilities: dict[str, float] = Field(
        default_factory=dict,
        description="Calibrated class probabilities across all candidate fault categories",
    )
    threshold_applied: float = Field(
        default=0.60, description="Confidence threshold required to avoid UNKNOWN"
    )
    classifier_name: str = Field(default="XGBoostFaultClassifier")
    model_version: str = Field(default="1.0.0")


class MLInferenceResult(BaseModel):
    """Unified application-level ML diagnostic container attached to telemetry."""

    timestamp: float = Field(..., description="Epoch timestamp of evaluated telemetry frame")
    sequence_id: int = Field(..., ge=0, description="Telemetry sequence ID")
    feature_schema_version: str = Field(default="1.0.0")
    anomaly: AnomalyInferenceResult
    fault: FaultInferenceResult
    top_contributions: list[FeatureContribution] = Field(
        default_factory=list, description="Top feature attributions driving the diagnosis"
    )
    inference_latency_ms: float = Field(
        ..., ge=0.0, description="Total ML pipeline evaluation latency in milliseconds"
    )
    disaggregated_latencies: dict[str, float] = Field(
        default_factory=dict, description="Component latency breakdown in milliseconds"
    )
    validity: Literal["VALID", "DEGRADED", "INVALID"] = Field(
        default="VALID", description="Operational validity of the ML inference result"
    )
    prototype_notice: str = Field(
        default="PROTOTYPE RESEARCH MODEL — NOT FOR CERTIFIED FLIGHT OPERATIONS"
    )
