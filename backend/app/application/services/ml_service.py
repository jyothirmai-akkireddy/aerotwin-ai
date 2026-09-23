"""Machine Learning Application Service for Engine Anomaly Detection and Fault Diagnostics."""

import json
import os
import threading
import time
from typing import Any

from app.domain.entities.telemetry import QualityStatus, TelemetryFrame
from app.domain.ml.anomaly import IAnomalyDetector, IsolationForestAnomalyDetector
from app.domain.ml.classifier import IFaultClassifier, XGBoostFaultClassifier
from app.domain.ml.explainability import ExplainabilityAttributor
from app.domain.ml.features import FEATURE_SCHEMA_VERSION, FeatureExtractor
from app.domain.ml.models import (
    AnomalyInferenceResult,
    AnomalyStatus,
    DecisionReason,
    FaultCategory,
    FaultInferenceResult,
    MLInferenceResult,
)
from app.domain.physics.models import PhysicsTwinResult
from app.infrastructure.logging.logger import get_logger

logger = get_logger("aerotwin.ml.service")

# Resolve models dir either at repo root (d:/sih/models) or backend/models
_repo_models = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../models"))
_backend_models = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../models"))
MODELS_BASE_DIR = _repo_models if os.path.exists(_repo_models) else _backend_models


class MLInferenceService:
    """Coordinates feature extraction, anomaly detection, fault classification, and explainability."""

    def __init__(self, models_dir: str | None = None) -> None:
        self.models_dir = models_dir or MODELS_BASE_DIR
        self._lock = threading.Lock()

        self.extractor = FeatureExtractor()
        self.anomaly_detector: IAnomalyDetector | None = None
        self.fault_classifier: IFaultClassifier | None = None
        self.attributor = ExplainabilityAttributor()

        self._last_result: MLInferenceResult | None = None

        # Diagnostic and performance counters
        self._eval_count: int = 0
        self._anomaly_count: int = 0
        self._fault_counts: dict[str, int] = {fc.value: 0 for fc in FaultCategory}
        self._total_pipeline_time_ms: float = 0.0
        self._total_feat_time_ms: float = 0.0
        self._total_anom_time_ms: float = 0.0
        self._total_class_time_ms: float = 0.0
        self._total_xai_time_ms: float = 0.0

        # Model metadata cache
        self._anomaly_meta: dict[str, Any] = {}
        self._classifier_meta: dict[str, Any] = {}

        self._load_models()

    def _load_models(self) -> None:
        """Load persisted anomaly and classifier model artifacts if present."""
        anom_path = os.path.join(self.models_dir, "anomaly", "isolation_forest_v1.joblib")
        anom_meta_path = os.path.join(self.models_dir, "anomaly", "metadata.json")
        class_path = os.path.join(self.models_dir, "classifier", "fault_classifier_v1.joblib")
        class_meta_path = os.path.join(self.models_dir, "classifier", "metadata.json")

        # 1. Load Anomaly Detector
        if os.path.exists(anom_path):
            try:
                self.anomaly_detector = IsolationForestAnomalyDetector.load(anom_path)
                logger.info(f"Loaded Anomaly Detector from {anom_path}")
            except Exception as e:
                logger.error(f"Failed to load Anomaly Detector artifact: {e}")
                self.anomaly_detector = IsolationForestAnomalyDetector()
        else:
            logger.warning(f"Anomaly detector artifact not found at {anom_path}, using default")
            self.anomaly_detector = IsolationForestAnomalyDetector()

        if os.path.exists(anom_meta_path):
            try:
                with open(anom_meta_path, encoding="utf-8") as f:
                    self._anomaly_meta = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to parse anomaly metadata: {e}")

        # 2. Load Fault Classifier
        if os.path.exists(class_path):
            try:
                self.fault_classifier = XGBoostFaultClassifier.load(class_path)
                logger.info(f"Loaded Fault Classifier from {class_path}")
                # Update explainability importance weights from fitted tree model
                if (
                    hasattr(self.fault_classifier, "model")
                    and self.fault_classifier.model is not None
                ):
                    self.attributor.update_from_model(self.fault_classifier.model)
            except Exception as e:
                logger.error(f"Failed to load Fault Classifier artifact: {e}")
                self.fault_classifier = XGBoostFaultClassifier()
        else:
            logger.warning(f"Fault classifier artifact not found at {class_path}, using default")
            self.fault_classifier = XGBoostFaultClassifier()

        if os.path.exists(class_meta_path):
            try:
                with open(class_meta_path, encoding="utf-8") as f:
                    self._classifier_meta = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to parse classifier metadata: {e}")

    @property
    def is_ready(self) -> bool:
        """Return True if both anomaly and classification models are successfully fitted/loaded."""
        anom_ready = self.anomaly_detector is not None and getattr(
            self.anomaly_detector, "is_fitted", False
        )
        class_ready = self.fault_classifier is not None and getattr(
            self.fault_classifier, "is_fitted", False
        )
        return anom_ready and class_ready

    def evaluate(
        self,
        frame: TelemetryFrame,
        physics: PhysicsTwinResult | None = None,
    ) -> MLInferenceResult:
        """Execute synchronous deterministic feature extraction and ML diagnostic inference."""
        t_pipeline_start = time.perf_counter()

        # Step 1: Feature Extraction
        t0_feat = time.perf_counter()
        features = self.extractor.extract(frame, physics)
        t_feat = (time.perf_counter() - t0_feat) * 1000.0

        # Step 2: Unsupervised Anomaly Detection
        t0_anom = time.perf_counter()
        if self.anomaly_detector is not None and getattr(self.anomaly_detector, "is_fitted", False):
            anom_result = self.anomaly_detector.predict(features)
        else:
            anom_result = AnomalyInferenceResult(
                flag=False,
                status=AnomalyStatus.NORMAL,
                score=0.0,
                raw_score=0.0,
                threshold=0.60,
                confidence=0.50,
                detector_name="UninitializedDetector",
                model_version="0.0.0",
            )
        t_anom = (time.perf_counter() - t0_anom) * 1000.0

        # Step 3: Supervised Fault Classification
        t0_class = time.perf_counter()
        if self.fault_classifier is not None and getattr(self.fault_classifier, "is_fitted", False):
            fault_result = self.fault_classifier.predict(features, is_anom=anom_result.flag)
        else:
            fault_result = FaultInferenceResult(
                fault_class=FaultCategory.UNKNOWN,
                reason=DecisionReason.LOW_CONFIDENCE,
                confidence=0.0,
                probabilities={},
                threshold_applied=0.60,
                classifier_name="UninitializedClassifier",
                model_version="0.0.0",
            )
        t_class = (time.perf_counter() - t0_class) * 1000.0

        # Step 4: Explainability Attribution
        t0_xai = time.perf_counter()
        top_contributions = self.attributor.attribute(features, top_k=4)
        t_xai = (time.perf_counter() - t0_xai) * 1000.0

        t_total = (time.perf_counter() - t_pipeline_start) * 1000.0

        # Validity determination
        if frame.quality_flag == QualityStatus.INVALID:
            validity = "INVALID"
        elif frame.quality_flag == QualityStatus.DEGRADED or not self.is_ready:
            validity = "DEGRADED"
        else:
            validity = "VALID"

        result = MLInferenceResult(
            timestamp=frame.timestamp,
            sequence_id=frame.sequence_id,
            feature_schema_version=FEATURE_SCHEMA_VERSION,
            anomaly=anom_result,
            fault=fault_result,
            top_contributions=top_contributions,
            inference_latency_ms=round(t_total, 3),
            disaggregated_latencies={
                "feature_extraction_ms": round(t_feat, 4),
                "anomaly_detection_ms": round(t_anom, 4),
                "fault_classification_ms": round(t_class, 4),
                "explainability_ms": round(t_xai, 4),
                "total_inference_ms": round(t_total, 3),
            },
            validity=validity,
            prototype_notice="PROTOTYPE RESEARCH MODEL — NOT FOR CERTIFIED FLIGHT OPERATIONS",
        )

        with self._lock:
            self._eval_count += 1
            if anom_result.flag:
                self._anomaly_count += 1
            self._fault_counts[fault_result.fault_class.value] = (
                self._fault_counts.get(fault_result.fault_class.value, 0) + 1
            )
            self._total_pipeline_time_ms += t_total
            self._total_feat_time_ms += t_feat
            self._total_anom_time_ms += t_anom
            self._total_class_time_ms += t_class
            self._total_xai_time_ms += t_xai
            self._last_result = result

        return result

    def get_latest_result(self) -> MLInferenceResult | None:
        """Retrieve most recent ML evaluation result."""
        with self._lock:
            return self._last_result

    def get_diagnostics(self) -> dict[str, Any]:
        """Retrieve operational and performance metrics."""
        with self._lock:
            cnt = max(1, self._eval_count)
            return {
                "evaluation_count": self._eval_count,
                "anomaly_count": self._anomaly_count,
                "anomaly_rate_pct": round((self._anomaly_count / cnt) * 100.0, 2),
                "fault_breakdown": dict(self._fault_counts),
                "status": "READY" if self.is_ready else "DEGRADED",
                "average_latencies_ms": {
                    "feature_extraction": round(self._total_feat_time_ms / cnt, 4),
                    "anomaly_detection": round(self._total_anom_time_ms / cnt, 4),
                    "fault_classification": round(self._total_class_time_ms / cnt, 4),
                    "explainability": round(self._total_xai_time_ms / cnt, 4),
                    "total_pipeline": round(self._total_pipeline_time_ms / cnt, 4),
                },
            }

    def get_model_metadata(self) -> dict[str, Any]:
        """Retrieve model metadata, versions, and provenance."""
        return {
            "feature_schema_version": FEATURE_SCHEMA_VERSION,
            "anomaly_detector": {
                "name": getattr(self.anomaly_detector, "detector_name", "IsolationForest"),
                "version": getattr(self.anomaly_detector, "model_version", "1.0.0"),
                "threshold": getattr(self.anomaly_detector, "threshold", 0.60),
                "fitted": getattr(self.anomaly_detector, "is_fitted", False),
                "metadata": self._anomaly_meta,
            },
            "fault_classifier": {
                "name": getattr(self.fault_classifier, "classifier_name", "XGBoostFaultClassifier"),
                "version": getattr(self.fault_classifier, "model_version", "1.0.0"),
                "confidence_threshold": getattr(
                    self.fault_classifier, "confidence_threshold", 0.60
                ),
                "fitted": getattr(self.fault_classifier, "is_fitted", False),
                "metadata": self._classifier_meta,
            },
            "provenance": "SYNTHETIC_SIMULATED_PROTOTYPE",
            "prototype_notice": "PROTOTYPE RESEARCH MODEL — NOT FOR CERTIFIED FLIGHT OPERATIONS",
        }
