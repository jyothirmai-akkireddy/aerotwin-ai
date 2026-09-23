"""Explainability and Feature Attribution Engine for Phase 6 Machine Learning models.

Computes top contributing features using model importance weighting and deviation scaling.
Optimized for real-time streaming execution (< 0.1 ms latency).
"""

from typing import Any

import numpy as np

from app.domain.ml.features import FEATURE_NAMES, NOMINAL_BASELINES
from app.domain.ml.models import FeatureContribution


class ExplainabilityAttributor:
    """Computes top contributing features driving anomaly and fault diagnostic decisions."""

    def __init__(
        self,
        feature_names: list[str] | None = None,
        feature_importances: np.ndarray | None = None,
        feature_std_devs: dict[str, float] | None = None,
    ) -> None:
        self.feature_names = feature_names or list(FEATURE_NAMES)
        self.feature_importances = (
            feature_importances
            if feature_importances is not None
            else np.ones(len(self.feature_names), dtype=np.float64) / len(self.feature_names)
        )
        self.feature_std_devs = feature_std_devs or {
            "rpm": 45.0,
            "manifold_pressure": 0.65,
            "throttle_position": 5.0,
            "fuel_flow": 0.85,
            "oil_pressure": 0.22,
            "oil_temperature": 2.10,
            "coolant_temp": 2.20,
            "vibration_rms": 0.08,
            "battery_voltage": 0.50,
            "true_airspeed": 5.0,
            "cht_mean": 3.50,
            "cht_spread": 2.0,
            "egt_mean": 14.20,
            "egt_spread": 8.0,
            "cht_cyl1_dev": 2.0,
            "egt_cyl1_dev": 5.0,
            "res_map_raw": 0.65,
            "res_map_norm": 1.0,
            "res_ff_norm": 1.0,
            "res_oil_p_raw": 0.22,
            "res_oil_p_norm": 1.0,
            "res_oil_t_norm": 1.0,
            "res_vib_norm": 1.0,
            "res_mean_abs_norm": 1.0,
        }

    def update_from_model(self, model: Any) -> None:
        """Extract native feature importances from fitted tree-based model."""
        if hasattr(model, "feature_importances_"):
            importances = np.array(model.feature_importances_, dtype=np.float64)
            if len(importances) == len(self.feature_names):
                sum_imp = float(np.sum(importances))
                if sum_imp > 0:
                    self.feature_importances = importances / sum_imp

    def attribute(
        self,
        features: np.ndarray,
        top_k: int = 4,
    ) -> list[FeatureContribution]:
        """Compute top-k feature contributions for a given 1D feature vector."""
        if len(features) != len(self.feature_names):
            return []

        scores: list[tuple[str, float, str]] = []

        for idx, name in enumerate(self.feature_names):
            val = float(features[idx])
            baseline = NOMINAL_BASELINES.get(name, 0.0)
            std = self.feature_std_devs.get(name, 1.0)
            std = max(1e-4, std)

            delta = val - baseline
            norm_dev = abs(delta) / std

            # Impact = model feature importance * normalized deviation
            importance = (
                float(self.feature_importances[idx])
                if idx < len(self.feature_importances)
                else 0.04
            )
            impact = importance * norm_dev

            # Determine qualitative direction
            if delta > 1.5 * std:
                direction = "ELEVATED"
            elif delta < -1.5 * std:
                direction = "DEPRESSED"
            else:
                direction = "IRREGULAR" if norm_dev > 1.0 else "ELEVATED"

            scores.append((name, impact, direction))

        # Sort descending by impact
        scores.sort(key=lambda x: x[1], reverse=True)
        top_scores = scores[:top_k]

        total_top_impact = sum(s[1] for s in top_scores)
        denom = total_top_impact if total_top_impact > 1e-6 else 1.0

        contributions: list[FeatureContribution] = []
        for name, impact, direction in top_scores:
            weight = float(np.clip(impact / denom, 0.0, 1.0))
            contributions.append(
                FeatureContribution(
                    feature_name=name,
                    contribution_weight=round(weight, 3),
                    direction=direction,  # type: ignore[arg-type]
                )
            )

        return contributions
