"""Phase 6 Machine Learning Domain Models, Interfaces, and Feature Extractors."""

from app.domain.ml.anomaly import IAnomalyDetector, IsolationForestAnomalyDetector
from app.domain.ml.classifier import IFaultClassifier, XGBoostFaultClassifier
from app.domain.ml.explainability import ExplainabilityAttributor
from app.domain.ml.features import (
    FEATURE_NAMES,
    FEATURE_SCHEMA_VERSION,
    FeatureExtractor,
)
from app.domain.ml.models import (
    AnomalyInferenceResult,
    AnomalyStatus,
    DecisionReason,
    FaultCategory,
    FaultInferenceResult,
    FeatureContribution,
    MLInferenceResult,
)

__all__ = [
    "IAnomalyDetector",
    "IsolationForestAnomalyDetector",
    "IFaultClassifier",
    "XGBoostFaultClassifier",
    "ExplainabilityAttributor",
    "FeatureExtractor",
    "FEATURE_NAMES",
    "FEATURE_SCHEMA_VERSION",
    "AnomalyInferenceResult",
    "AnomalyStatus",
    "DecisionReason",
    "FaultCategory",
    "FaultInferenceResult",
    "FeatureContribution",
    "MLInferenceResult",
]
