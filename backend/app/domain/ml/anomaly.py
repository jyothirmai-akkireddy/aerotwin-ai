"""Unsupervised Anomaly Detection using Isolation Forest with monotonic score normalization."""

import os
from abc import ABC, abstractmethod
from typing import Any

import joblib
import numpy as np
from sklearn.ensemble import IsolationForest

from app.domain.ml.models import AnomalyInferenceResult, AnomalyStatus


class IAnomalyDetector(ABC):
    """Abstract port for unsupervised engine anomaly detection."""

    @abstractmethod
    def predict(self, features: np.ndarray) -> AnomalyInferenceResult:
        """Evaluate a 1D or 2D feature vector and return standardized anomaly result."""
        pass


class IsolationForestAnomalyDetector(IAnomalyDetector):
    """Unsupervised Isolation Forest detector with normalized application score in [0.0, 1.0]."""

    # Indices of primary normalized residuals: res_map_norm (17), res_ff_norm (18), res_oil_p_norm (20), res_oil_t_norm (21), res_vib_norm (22)
    RESIDUAL_INDICES: list[int] = [17, 18, 20, 21, 22]
    BATTERY_VOLTAGE_IDX: int = 8

    def __init__(
        self,
        model: IsolationForest | None = None,
        threshold: float = 0.60,
        score_min: float = -0.25,
        score_max: float = 0.25,
        res_min: np.ndarray | None = None,
        res_max: np.ndarray | None = None,
        res_std: np.ndarray | None = None,
        model_version: str = "1.0.0",
    ) -> None:
        self.model = model
        self.threshold = threshold
        self.score_min = score_min
        self.score_max = score_max
        self.res_min = (
            res_min if res_min is not None else np.array([-5.74, -4.85, -11.45, 0.0, -1.22])
        )
        self.res_max = (
            res_max if res_max is not None else np.array([30.03, 29.49, 0.78, 20.41, 4.40])
        )
        self.res_std = res_std if res_std is not None else np.array([7.34, 5.48, 1.82, 6.18, 1.37])
        self.model_version = model_version
        self.detector_name = "IsolationForest"

    @property
    def is_fitted(self) -> bool:
        return self.model is not None and hasattr(self.model, "estimators_")

    def fit(
        self,
        X_train: np.ndarray,
        contamination: float = 0.03,
        random_state: int = 42,
    ) -> "IsolationForestAnomalyDetector":
        """Train Isolation Forest on normal baseline flight data and calibrate envelope."""
        clf = IsolationForest(
            n_estimators=100,
            contamination=contamination,
            random_state=random_state,
            n_jobs=-1,
        )
        clf.fit(X_train)
        self.model = clf

        # Standard range for IsolationForest decision_function: +0.25 (dense inlier) to -0.25 (severe outlier)
        self.score_min = -0.25
        self.score_max = 0.25

        # Record normal residual envelope
        if X_train.shape[1] >= 24:
            X_res = X_train[:, self.RESIDUAL_INDICES]
            self.res_min = np.percentile(X_res, 0.1, axis=0)
            self.res_max = np.percentile(X_res, 99.9, axis=0)
            self.res_std = np.std(X_res, axis=0) + 1e-4

        return self

    def _compute_score(self, features: np.ndarray, raw_score: float) -> float:
        """Calculate monotonic [0.0, 1.0] anomaly score combining density isolation and residual excursion."""
        denom = max(1e-6, self.score_max - self.score_min)
        # Tree density score: 1.0 at severe outlier (-0.25), 0.0 at deep inlier (+0.25)
        s_iso = float(np.clip(1.0 - ((raw_score - self.score_min) / denom), 0.0, 1.0))

        feat_1d = features.flatten() if features.ndim > 1 else features
        s_res = 0.0
        v_drop = 0.0

        if (
            len(feat_1d) >= 24
            and self.res_min is not None
            and self.res_max is not None
            and self.res_std is not None
        ):
            res_vals = feat_1d[self.RESIDUAL_INDICES]
            over = np.maximum(0.0, res_vals - self.res_max) / self.res_std
            under = np.maximum(0.0, self.res_min - res_vals) / self.res_std
            res_dev = float(np.max(over + under))
            s_res = float(np.clip(res_dev / 2.0, 0.0, 1.0))

            v_bat = float(feat_1d[self.BATTERY_VOLTAGE_IDX])
            v_drop = float(np.clip((12.0 - v_bat) / 12.0, 0.0, 1.0))

        return float(max(s_iso, max(s_res, v_drop)))

    def calibrate_threshold(
        self,
        X_val_normal: np.ndarray,
        target_fpr: float = 0.01,
    ) -> float:
        """Empirically derive decision threshold on validation normal split to achieve target FPR."""
        raw_scores = self.model.decision_function(X_val_normal)
        scores = [
            self._compute_score(X_val_normal[i], raw_scores[i]) for i in range(len(X_val_normal))
        ]
        # Threshold at 1 - target_fpr quantile
        self.threshold = float(np.percentile(scores, (1.0 - target_fpr) * 100.0))
        return self.threshold

    def predict(self, features: np.ndarray) -> AnomalyInferenceResult:
        """Evaluate single feature vector x in R^24."""
        if not self.is_fitted:
            # Fallback if model uninitialized
            return AnomalyInferenceResult(
                flag=False,
                status=AnomalyStatus.NORMAL,
                score=0.0,
                raw_score=0.0,
                threshold=self.threshold,
                confidence=0.50,
                detector_name=self.detector_name,
                model_version=self.model_version,
            )

        X = features.reshape(1, -1) if features.ndim == 1 else features
        raw_score = float(self.model.decision_function(X)[0])
        score = self._compute_score(features, raw_score)
        is_anom = bool(score >= self.threshold)

        # Confidence: scales with distance from decision threshold
        max_dist = max(self.threshold, 1.0 - self.threshold, 1e-4)
        dist = abs(score - self.threshold)
        confidence = float(np.clip(0.50 + (dist / (2.0 * max_dist)), 0.50, 1.00))

        return AnomalyInferenceResult(
            flag=is_anom,
            status=AnomalyStatus.ANOMALOUS if is_anom else AnomalyStatus.NORMAL,
            score=round(score, 4),
            raw_score=round(raw_score, 4),
            threshold=round(self.threshold, 4),
            confidence=round(confidence, 4),
            detector_name=self.detector_name,
            model_version=self.model_version,
        )

    def save(self, filepath: str) -> None:
        """Persist trained detector bundle via joblib."""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        bundle = {
            "model": self.model,
            "threshold": self.threshold,
            "score_min": self.score_min,
            "score_max": self.score_max,
            "res_min": self.res_min,
            "res_max": self.res_max,
            "res_std": self.res_std,
            "model_version": self.model_version,
            "detector_name": self.detector_name,
        }
        joblib.dump(bundle, filepath)

    @classmethod
    def load(cls, filepath: str) -> "IsolationForestAnomalyDetector":
        """Load trained detector bundle from disk."""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Anomaly detector artifact not found at: {filepath}")
        bundle: dict[str, Any] = joblib.load(filepath)
        return cls(
            model=bundle.get("model"),
            threshold=bundle.get("threshold", 0.60),
            score_min=bundle.get("score_min", -0.25),
            score_max=bundle.get("score_max", 0.25),
            res_min=bundle.get("res_min"),
            res_max=bundle.get("res_max"),
            res_std=bundle.get("res_std"),
            model_version=bundle.get("model_version", "1.0.0"),
        )
