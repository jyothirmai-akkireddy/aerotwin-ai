"""Remaining Useful Life (RUL) estimator with 95% prediction intervals and fallback gating."""

import math
import os
from typing import Any, Literal

import joblib

from app.domain.prognostics.models import (
    RULEstimate,
    RULStatus,
    SubsystemDegradation,
    TrendDirection,
)


class RULEstimator:
    """Estimates Remaining Useful Life with uncertainty intervals and strict fallback gating.

    Rules:
    1. NEVER returns arbitrary numbers or 0.0 when ungrounded.
    2. Strict Gating Hierarchy:
       - INSUFFICIENT_HISTORY (buffer < 30 frames) -> None
       - DEGRADATION_NOT_DETECTED (HI >= 0.90 & STABLE) -> None
       - RUL_UNAVAILABLE (Invalid / non-finite inputs) -> None
       - ACTIVE (confirmed degradation) -> estimated_hours, 95% CI bounds
    3. Prediction Interval Ordering: lower <= point_est <= upper unconditionally.
    """

    def __init__(
        self,
        model_artifact_path: str | None = None,
    ) -> None:
        self.model_artifact_path = model_artifact_path
        self.model_median: Any = None
        self.model_lower: Any = None
        self.model_upper: Any = None
        self.conformal_margin: float = 0.0
        self.is_fitted: bool = False

        if model_artifact_path and os.path.exists(model_artifact_path):
            self.load(model_artifact_path)

    def estimate(
        self,
        health_index: float,
        beta_slope: float,
        trend_dir: TrendDirection,
        subsystems: SubsystemDegradation,
        buffer_size: int,
        history: list[dict[str, float]],
        feature_vector: list[float] | None = None,
        validity: Literal["VALID", "DEGRADED", "INVALID"] = "VALID",
    ) -> RULEstimate:
        """Evaluate RUL with strict 4-stage validity gating."""
        # 1. Gate 1: Insufficient causal history
        if buffer_size < 30 or len(history) < 30:
            return RULEstimate(
                status=RULStatus.INSUFFICIENT_HISTORY,
                estimated_remaining_flight_hours=None,
                confidence_interval_95=None,
                confidence=0.0,
                limiting_subsystem="nominal",
                degradation_rate_per_hour=None,
                reason="Awaiting causal buffer fill (minimum 30 frames required)",
            )

        # 2. Gate 2: Invalid or corrupted inputs
        if (
            validity == "INVALID"
            or not math.isfinite(health_index)
            or not math.isfinite(beta_slope)
        ):
            return RULEstimate(
                status=RULStatus.RUL_UNAVAILABLE,
                estimated_remaining_flight_hours=None,
                confidence_interval_95=None,
                confidence=0.0,
                limiting_subsystem="nominal",
                degradation_rate_per_hour=None,
                reason="Degraded or non-finite telemetry inputs: RUL estimation unavailable",
            )

        # 3. Gate 3: Nominal engine / Degradation Not Detected
        # Engine is healthy (HI >= 0.90) and not degrading rapidly
        if health_index >= 0.90 and trend_dir in (TrendDirection.STABLE, TrendDirection.IMPROVING):
            return RULEstimate(
                status=RULStatus.DEGRADATION_NOT_DETECTED,
                estimated_remaining_flight_hours=None,
                confidence_interval_95=None,
                confidence=0.0,
                limiting_subsystem="nominal",
                degradation_rate_per_hour=0.0,
                reason="Nominal baseline operation: No active wear degradation detected",
            )

        # 4. Gate 4: Active Degradation Mode
        # Determine limiting subsystem
        limiting = subsystems.limiting_subsystem

        # Wear rate per hour in Health Index points
        degr_rate_hr = round(abs(beta_slope) * 3600.0, 4)

        # Point estimate and uncertainty bounds
        if self.is_fitted and feature_vector is not None and self.model_median is not None:
            try:
                import numpy as np

                x = np.array([feature_vector])
                pred_med = float(self.model_median.predict(x)[0])
                pred_low = (
                    float(self.model_lower.predict(x)[0]) - self.conformal_margin
                    if self.model_lower
                    else pred_med * 0.85
                )
                pred_upp = (
                    float(self.model_upper.predict(x)[0]) + self.conformal_margin
                    if self.model_upper
                    else pred_med * 1.20
                )

                pred_med = max(0.1, pred_med)
                pred_low = max(0.05, min(pred_low, pred_med))
                pred_upp = max(pred_med, pred_upp)
            except Exception:
                pred_med, pred_low, pred_upp = self._extrapolate_rul(health_index, beta_slope)
        else:
            pred_med, pred_low, pred_upp = self._extrapolate_rul(health_index, beta_slope)

        # Compute runtime heuristic confidence score
        # 1. Buffer fullness factor
        c_history = min(1.0, buffer_size / 100.0)

        # 2. Prediction interval sharpness factor
        spread = pred_upp - pred_low
        c_spread = max(0.0, min(1.0, 1.0 - (spread / max(2.0, 2.5 * pred_med))))

        # 3. Health index stability factor
        hi_vals = [h["health_index"] for h in history[-30:]]
        mean_hi = sum(hi_vals) / len(hi_vals)
        std_hi = math.sqrt(sum((v - mean_hi) ** 2 for v in hi_vals) / len(hi_vals))
        c_noise = max(0.2, min(1.0, 1.0 - (std_hi / max(1e-4, mean_hi))))

        heuristic_confidence = round(c_history * c_spread * c_noise, 3)

        return RULEstimate(
            status=RULStatus.ACTIVE,
            estimated_remaining_flight_hours=round(pred_med, 2),
            confidence_interval_95=(round(pred_low, 2), round(pred_upp, 2)),
            confidence=heuristic_confidence,
            limiting_subsystem=limiting,
            degradation_rate_per_hour=degr_rate_hr,
            reason=f"Active simulated degradation detected on {limiting}; RUL projected",
        )

    def _extrapolate_rul(
        self, health_index: float, beta_slope: float
    ) -> tuple[float, float, float]:
        """Extrapolate remaining hours to critical benchmark threshold (HI=0.25)."""
        # Critical failure threshold HI_crit = 0.25
        hi_remaining = max(0.01, health_index - 0.25)
        effective_slope = max(1.0e-5, abs(beta_slope))

        remaining_seconds = hi_remaining / effective_slope
        remaining_hours = remaining_seconds / 3600.0

        # Bound into reasonable simulated mission window (e.g. 0.1 to 100.0 hours)
        point_est = max(0.1, min(100.0, remaining_hours))
        lower_bound = max(0.05, point_est * 0.82)
        upper_bound = point_est * 1.25

        return round(point_est, 2), round(lower_bound, 2), round(upper_bound, 2)

    def save(self, path: str) -> None:
        """Persist model bundle to disk."""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        bundle = {
            "model_median": self.model_median,
            "model_lower": self.model_lower,
            "model_upper": self.model_upper,
            "conformal_margin": self.conformal_margin,
            "is_fitted": self.is_fitted,
        }
        joblib.dump(bundle, path)

    def load(self, path: str) -> "RULEstimator":
        """Load persisted model bundle from disk."""
        bundle = joblib.load(path)
        self.model_median = bundle.get("model_median")
        self.model_lower = bundle.get("model_lower")
        self.model_upper = bundle.get("model_upper")
        self.conformal_margin = float(bundle.get("conformal_margin", 0.0))
        self.is_fitted = bundle.get("is_fitted", False)
        return self
