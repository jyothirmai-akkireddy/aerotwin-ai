"""Supervised Multi-Class Fault Classifier with strict confidence and OOD gating."""

import os
from abc import ABC, abstractmethod
from typing import Any

import joblib
import numpy as np

try:
    import xgboost as xgb

    HAS_XGBOOST = True
except ImportError:
    HAS_XGBOOST = False

from sklearn.ensemble import HistGradientBoostingClassifier

from app.domain.ml.models import DecisionReason, FaultCategory, FaultInferenceResult

CLASS_NAMES: list[str] = [
    "NORMAL",
    "OIL_PRESSURE_BIAS",
    "OIL_TEMP_DRIFT",
    "THROTTLE_STUCK",
    "SENSOR_DROPOUT",
    "MAP_NOISE_SPIKE",
]


class IFaultClassifier(ABC):
    """Abstract port for supervised engine fault classification."""

    @abstractmethod
    def predict(self, features: np.ndarray, is_anom: bool = False) -> FaultInferenceResult:
        """Evaluate a feature vector with anomaly context and return guarded fault classification."""
        pass


class XGBoostFaultClassifier(IFaultClassifier):
    """Multi-class fault classifier with XGBoost champion and HistGradientBoosting fallback."""

    def __init__(
        self,
        model: Any = None,
        confidence_threshold: float = 0.60,
        class_names: list[str] | None = None,
        model_version: str = "1.0.0",
        classifier_name: str = "XGBoostFaultClassifier",
    ) -> None:
        self.model = model
        self.confidence_threshold = confidence_threshold
        self.class_names = class_names or list(CLASS_NAMES)
        self.model_version = model_version
        self.classifier_name = classifier_name

    @property
    def is_fitted(self) -> bool:
        if self.model is None:
            return False
        # Check XGBoost or sklearn fitted state
        return hasattr(self.model, "classes_") or hasattr(self.model, "n_classes_")

    def fit(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        use_xgboost: bool = True,
        random_state: int = 42,
    ) -> "XGBoostFaultClassifier":
        """Fit multi-class model on run-isolated synthetic training dataset."""
        if use_xgboost and HAS_XGBOOST:
            clf = xgb.XGBClassifier(
                n_estimators=100,
                max_depth=4,
                learning_rate=0.08,
                tree_method="hist",
                objective="multi:softprob",
                random_state=random_state,
                eval_metric="mlogloss",
                n_jobs=-1,
            )
            self.classifier_name = "XGBoostFaultClassifier"
        else:
            clf = HistGradientBoostingClassifier(
                max_iter=100,
                max_depth=4,
                learning_rate=0.08,
                random_state=random_state,
            )
            self.classifier_name = "HistGradientBoostingClassifier"

        clf.fit(X_train, y_train)
        self.model = clf
        return self

    def predict(self, features: np.ndarray, is_anom: bool = False) -> FaultInferenceResult:
        """Predict fault class with explicit low-confidence and OOD guards."""
        if not self.is_fitted:
            return FaultInferenceResult(
                fault_class=FaultCategory.UNKNOWN,
                reason=DecisionReason.LOW_CONFIDENCE,
                confidence=0.0,
                probabilities={},
                threshold_applied=self.confidence_threshold,
                classifier_name=self.classifier_name,
                model_version=self.model_version,
            )

        X = features.reshape(1, -1) if features.ndim == 1 else features
        probs_raw = self.model.predict_proba(X)[0]

        # Build class-to-probability mapping
        probabilities: dict[str, float] = {}
        for idx, name in enumerate(self.class_names):
            if idx < len(probs_raw):
                probabilities[name] = round(float(probs_raw[idx]), 4)
            else:
                probabilities[name] = 0.0

        top_idx = int(np.argmax(probs_raw))
        top_prob = float(probs_raw[top_idx])
        candidate_name = self.class_names[top_idx] if top_idx < len(self.class_names) else "UNKNOWN"
        candidate_class = FaultCategory(candidate_name)

        # -------------------------------------------------------------
        # Decision Guard Logic: Low-Confidence vs OOD Semantics
        # -------------------------------------------------------------
        # Case 1: Out-of-Distribution (Anomaly flagged, but classifier insists NORMAL)
        if is_anom and candidate_class == FaultCategory.NORMAL:
            return FaultInferenceResult(
                fault_class=FaultCategory.UNKNOWN,
                reason=DecisionReason.OUT_OF_DISTRIBUTION,
                confidence=round(top_prob, 4),
                probabilities=probabilities,
                threshold_applied=self.confidence_threshold,
                classifier_name=self.classifier_name,
                model_version=self.model_version,
            )

        # Case 2: Low-Confidence (Candidate probability below confidence threshold)
        if top_prob < self.confidence_threshold:
            return FaultInferenceResult(
                fault_class=FaultCategory.UNKNOWN,
                reason=DecisionReason.LOW_CONFIDENCE,
                confidence=round(top_prob, 4),
                probabilities=probabilities,
                threshold_applied=self.confidence_threshold,
                classifier_name=self.classifier_name,
                model_version=self.model_version,
            )

        # Case 3: Confident Match or Nominal Flight
        reason = (
            DecisionReason.NOMINAL_FLIGHT
            if candidate_class == FaultCategory.NORMAL
            else DecisionReason.CONFIDENT_MATCH
        )
        return FaultInferenceResult(
            fault_class=candidate_class,
            reason=reason,
            confidence=round(top_prob, 4),
            probabilities=probabilities,
            threshold_applied=self.confidence_threshold,
            classifier_name=self.classifier_name,
            model_version=self.model_version,
        )

    def save(self, filepath: str) -> None:
        """Persist trained classifier bundle via joblib."""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        bundle = {
            "model": self.model,
            "confidence_threshold": self.confidence_threshold,
            "class_names": self.class_names,
            "model_version": self.model_version,
            "classifier_name": self.classifier_name,
        }
        joblib.dump(bundle, filepath)

    @classmethod
    def load(cls, filepath: str) -> "XGBoostFaultClassifier":
        """Load trained classifier bundle from disk."""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Fault classifier artifact not found at: {filepath}")
        bundle: dict[str, Any] = joblib.load(filepath)
        return cls(
            model=bundle.get("model"),
            confidence_threshold=bundle.get("confidence_threshold", 0.60),
            class_names=bundle.get("class_names", list(CLASS_NAMES)),
            model_version=bundle.get("model_version", "1.0.0"),
            classifier_name=bundle.get("classifier_name", "XGBoostFaultClassifier"),
        )
