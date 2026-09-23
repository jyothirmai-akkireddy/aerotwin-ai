"""Deterministic 24-feature extraction layer for Phase 6 Machine Learning models.

Feature Schema: v1.0.0
Produces a fixed 24-dimensional feature vector from TelemetryFrame and Phase 5 PhysicsTwinResult.
"""

import math
from typing import Any

import numpy as np

from app.domain.entities.telemetry import TelemetryFrame
from app.domain.physics.models import PhysicsTwinResult

FEATURE_SCHEMA_VERSION = "1.0.0"

FEATURE_NAMES: list[str] = [
    # 1. Raw Primary Telemetry Channels (10 features)
    "rpm",
    "manifold_pressure",
    "throttle_position",
    "fuel_flow",
    "oil_pressure",
    "oil_temperature",
    "coolant_temp",
    "vibration_rms",
    "battery_voltage",
    "true_airspeed",
    # 2. Derived Cylinder Balance & Spread Channels (6 features)
    "cht_mean",
    "cht_spread",
    "egt_mean",
    "egt_spread",
    "cht_cyl1_dev",
    "egt_cyl1_dev",
    # 3. Physics Twin Analytical Residuals (8 features)
    "res_map_raw",
    "res_map_norm",
    "res_ff_norm",
    "res_oil_p_raw",
    "res_oil_p_norm",
    "res_oil_t_norm",
    "res_vib_norm",
    "res_mean_abs_norm",
]

# Nominal fallback baselines for invalid or missing inputs
NOMINAL_BASELINES: dict[str, float] = {
    "rpm": 2400.0,
    "manifold_pressure": 29.5,
    "throttle_position": 45.0,
    "fuel_flow": 16.5,
    "oil_pressure": 3.8,
    "oil_temperature": 85.0,
    "coolant_temp": 82.0,
    "vibration_rms": 1.15,
    "battery_voltage": 28.2,
    "true_airspeed": 45.0,
    "cht_mean": 95.0,
    "cht_spread": 5.0,
    "egt_mean": 720.0,
    "egt_spread": 15.0,
    "cht_cyl1_dev": 0.0,
    "egt_cyl1_dev": 0.0,
    "res_map_raw": 0.0,
    "res_map_norm": 0.0,
    "res_ff_norm": 0.0,
    "res_oil_p_raw": 0.0,
    "res_oil_p_norm": 0.0,
    "res_oil_t_norm": 0.0,
    "res_vib_norm": 0.0,
    "res_mean_abs_norm": 0.0,
}


class FeatureExtractor:
    """Deterministic, causal feature extractor transforming engine telemetry into ML vectors."""

    def __init__(self) -> None:
        self.feature_names = list(FEATURE_NAMES)
        self.schema_version = FEATURE_SCHEMA_VERSION

    @property
    def feature_count(self) -> int:
        return len(self.feature_names)

    def extract(
        self,
        frame: TelemetryFrame,
        physics: PhysicsTwinResult | None = None,
    ) -> np.ndarray:
        """Extract a 24-dimensional feature vector from a TelemetryFrame and optional PhysicsTwinResult.

        Returns:
            1D numpy array of shape (24,) with dtype float64.
        """

        # Helper to safely sanitize floats against NaN / Inf
        def _safe_float(val: Any, default_key: str) -> float:
            if val is None or not isinstance(val, int | float) or not math.isfinite(val):
                return NOMINAL_BASELINES[default_key]
            return float(val)

        # 1. Raw Telemetry
        rpm = _safe_float(frame.rpm, "rpm")
        map_val = _safe_float(frame.manifold_pressure, "manifold_pressure")
        throttle = _safe_float(frame.throttle_position, "throttle_position")
        ff = _safe_float(frame.fuel_flow, "fuel_flow")
        oil_p = _safe_float(frame.oil_pressure, "oil_pressure")
        oil_t = _safe_float(frame.oil_temperature, "oil_temperature")
        coolant = _safe_float(frame.coolant_temp, "coolant_temp")
        vib = _safe_float(frame.vibration_rms, "vibration_rms")
        v_bat = _safe_float(frame.battery_voltage, "battery_voltage")
        tas = _safe_float(frame.true_airspeed, "true_airspeed")

        # 2. Derived Cylinder Metrics
        chts = [
            _safe_float(c, "cht_mean") for c in (frame.cht if len(frame.cht) == 4 else [95.0] * 4)
        ]
        egts = [
            _safe_float(e, "egt_mean") for e in (frame.egt if len(frame.egt) == 4 else [720.0] * 4)
        ]

        cht_mean = sum(chts) / 4.0
        cht_spread = max(chts) - min(chts)
        egt_mean = sum(egts) / 4.0
        egt_spread = max(egts) - min(egts)
        cht_cyl1_dev = chts[0] - cht_mean
        egt_cyl1_dev = egts[0] - egt_mean

        # 3. Phase 5 Analytical Residuals
        res_map_raw = 0.0
        res_map_norm = 0.0
        res_ff_norm = 0.0
        res_oil_p_raw = 0.0
        res_oil_p_norm = 0.0
        res_oil_t_norm = 0.0
        res_vib_norm = 0.0
        res_mean_abs_norm = 0.0

        if physics is not None and physics.residuals is not None:
            raw_dict = physics.residuals.raw_residuals or {}
            norm_dict = physics.residuals.normalized_residuals or {}

            def _get_scalar(d: dict[str, Any], k: str) -> float:
                v = d.get(k, 0.0)
                if isinstance(v, list):
                    return float(v[0]) if v else 0.0
                if isinstance(v, int | float) and math.isfinite(v):
                    return float(v)
                return 0.0

            res_map_raw = _get_scalar(raw_dict, "manifold_pressure")
            res_map_norm = _get_scalar(norm_dict, "manifold_pressure")
            res_ff_norm = _get_scalar(norm_dict, "fuel_flow")
            res_oil_p_raw = _get_scalar(raw_dict, "oil_pressure")
            res_oil_p_norm = _get_scalar(norm_dict, "oil_pressure")
            res_oil_t_norm = _get_scalar(norm_dict, "oil_temperature")
            res_vib_norm = _get_scalar(norm_dict, "vibration_rms")
            res_mean_abs_norm = _safe_float(
                physics.residuals.mean_absolute_normalized_residual, "res_mean_abs_norm"
            )

        vector = np.array(
            [
                rpm,
                map_val,
                throttle,
                ff,
                oil_p,
                oil_t,
                coolant,
                vib,
                v_bat,
                tas,
                cht_mean,
                cht_spread,
                egt_mean,
                egt_spread,
                cht_cyl1_dev,
                egt_cyl1_dev,
                res_map_raw,
                res_map_norm,
                res_ff_norm,
                res_oil_p_raw,
                res_oil_p_norm,
                res_oil_t_norm,
                res_vib_norm,
                res_mean_abs_norm,
            ],
            dtype=np.float64,
        )
        return vector

    def extract_from_dict(self, row: dict[str, Any]) -> np.ndarray:
        """Extract a 24-dimensional feature vector from a flat dictionary (e.g. parquet record)."""

        def _get(k: str, default: float) -> float:
            v = row.get(k, default)
            if v is None or not isinstance(v, int | float) or not math.isfinite(v):
                return default
            return float(v)

        rpm = _get("rpm", 2400.0)
        map_val = _get("manifold_pressure", 29.5)
        throttle = _get("throttle_position", 45.0)
        ff = _get("fuel_flow", 16.5)
        oil_p = _get("oil_pressure", 3.8)
        oil_t = _get("oil_temperature", 85.0)
        coolant = _get("coolant_temp", 82.0)
        vib = _get("vibration_rms", 1.15)
        v_bat = _get("battery_voltage", 28.2)
        tas = _get("true_airspeed", 45.0)

        # CHT channels
        cht1 = _get("cht_1", 95.0)
        cht2 = _get("cht_2", 92.5)
        cht3 = _get("cht_3", 98.0)
        cht4 = _get("cht_4", 94.0)
        chts = [cht1, cht2, cht3, cht4]
        cht_mean = sum(chts) / 4.0
        cht_spread = max(chts) - min(chts)
        cht_cyl1_dev = cht1 - cht_mean

        # EGT channels
        egt1 = _get("egt_1", 720.0)
        egt2 = _get("egt_2", 715.0)
        egt3 = _get("egt_3", 730.0)
        egt4 = _get("egt_4", 722.0)
        egts = [egt1, egt2, egt3, egt4]
        egt_mean = sum(egts) / 4.0
        egt_spread = max(egts) - min(egts)
        egt_cyl1_dev = egt1 - egt_mean

        # Residual channels if present in dictionary
        res_map_raw = _get("res_map_raw", 0.0)
        res_map_norm = _get("res_map_norm", 0.0)
        res_ff_norm = _get("res_ff_norm", 0.0)
        res_oil_p_raw = _get("res_oil_p_raw", 0.0)
        res_oil_p_norm = _get("res_oil_p_norm", 0.0)
        res_oil_t_norm = _get("res_oil_t_norm", 0.0)
        res_vib_norm = _get("res_vib_norm", 0.0)
        res_mean_abs_norm = _get("res_mean_abs_norm", 0.0)

        return np.array(
            [
                rpm,
                map_val,
                throttle,
                ff,
                oil_p,
                oil_t,
                coolant,
                vib,
                v_bat,
                tas,
                cht_mean,
                cht_spread,
                egt_mean,
                egt_spread,
                cht_cyl1_dev,
                egt_cyl1_dev,
                res_map_raw,
                res_map_norm,
                res_ff_norm,
                res_oil_p_raw,
                res_oil_p_norm,
                res_oil_t_norm,
                res_vib_norm,
                res_mean_abs_norm,
            ],
            dtype=np.float64,
        )
