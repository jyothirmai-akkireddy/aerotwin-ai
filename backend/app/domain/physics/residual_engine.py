"""Residual generation and normalization engine.

Evaluates raw algebraic deviations and empirical sigma-normalized diagnostic features.
"""

import math

from app.domain.entities.telemetry import QualityStatus, TelemetryFrame
from app.domain.physics.models import (
    ModelValidity,
    PhysicsCalibrationParameters,
    PhysicsExpectedState,
    PhysicsResidualSet,
)


class ResidualEngine:
    """Computes directional algebraic residuals and sigma-normalized features."""

    def __init__(self, calibration: PhysicsCalibrationParameters):
        self.cal = calibration

    def compute_residuals(
        self,
        observed: TelemetryFrame,
        expected: PhysicsExpectedState,
    ) -> PhysicsResidualSet:
        """Compute raw and normalized residual vectors comparing observed against expected states.

        Directional Invariants:
        - observed == expected -> residual == 0.0
        - observed > expected  -> residual > 0.0
        - observed < expected  -> residual < 0.0
        """
        # Determine overall validity
        if (
            observed.quality_flag == QualityStatus.INVALID
            or expected.validity == ModelValidity.INVALID
        ):
            validity = ModelValidity.INVALID
            confidence = 0.0
        elif (
            observed.quality_flag == QualityStatus.DEGRADED
            or expected.validity == ModelValidity.DEGRADED
        ):
            validity = ModelValidity.DEGRADED
            confidence = min(0.5, expected.confidence)
        elif expected.validity == ModelValidity.OUT_OF_RANGE:
            validity = ModelValidity.OUT_OF_RANGE
            confidence = min(0.3, expected.confidence)
        else:
            validity = ModelValidity.VALID
            confidence = expected.confidence

        sigmas = self.cal.sigma_scales

        def _safe_norm(raw: float, sigma_key: str) -> float:
            if not math.isfinite(raw):
                return 0.0
            sigma = sigmas.get(sigma_key, 1.0)
            if sigma <= 1e-6:
                return 0.0
            return raw / sigma

        # 1. Scalar Raw Residuals
        rpm_raw = observed.rpm - expected.rpm
        map_raw = observed.manifold_pressure - expected.manifold_pressure
        ff_raw = observed.fuel_flow - expected.fuel_flow
        coolant_raw = observed.coolant_temp - expected.coolant_temp
        oil_temp_raw = observed.oil_temperature - expected.oil_temperature
        oil_press_raw = observed.oil_pressure - expected.oil_pressure
        vib_raw = observed.vibration_rms - expected.vibration_rms

        # 2. 4-Cylinder Array Residuals
        cht_raw = [observed.cht[i] - expected.cht[i] for i in range(4)]
        egt_raw = [observed.egt[i] - expected.egt[i] for i in range(4)]

        # 3. Normalized Residuals
        rpm_norm = _safe_norm(rpm_raw, "rpm")
        map_norm = _safe_norm(map_raw, "manifold_pressure")
        ff_norm = _safe_norm(ff_raw, "fuel_flow")
        coolant_norm = _safe_norm(coolant_raw, "coolant_temp")
        oil_temp_norm = _safe_norm(oil_temp_raw, "oil_temperature")
        oil_press_norm = _safe_norm(oil_press_raw, "oil_pressure")
        vib_norm = _safe_norm(vib_raw, "vibration_rms")

        cht_norm = [_safe_norm(cht_raw[i], "cht") for i in range(4)]
        egt_norm = [_safe_norm(egt_raw[i], "egt") for i in range(4)]

        raw_residuals: dict[str, float | list[float]] = {
            "rpm": rpm_raw,
            "manifold_pressure": map_raw,
            "fuel_flow": ff_raw,
            "cht": cht_raw,
            "egt": egt_raw,
            "coolant_temp": coolant_raw,
            "oil_temperature": oil_temp_raw,
            "oil_pressure": oil_press_raw,
            "vibration_rms": vib_raw,
        }

        normalized_residuals: dict[str, float | list[float]] = {
            "rpm": rpm_norm,
            "manifold_pressure": map_norm,
            "fuel_flow": ff_norm,
            "cht": cht_norm,
            "egt": egt_norm,
            "coolant_temp": coolant_norm,
            "oil_temperature": oil_temp_norm,
            "oil_pressure": oil_press_norm,
            "vibration_rms": vib_norm,
        }

        # Cylinder Imbalance (spread among observed cylinders)
        cht_imbalance = max(observed.cht) - min(observed.cht)
        egt_imbalance = max(observed.egt) - min(observed.egt)

        # Mean absolute normalized residual across primary channels
        norm_values = [
            abs(rpm_norm),
            abs(map_norm),
            abs(ff_norm),
            *(abs(c) for c in cht_norm),
            *(abs(e) for e in egt_norm),
            abs(coolant_norm),
            abs(oil_temp_norm),
            abs(oil_press_norm),
            abs(vib_norm),
        ]
        manr = sum(norm_values) / max(1, len(norm_values))

        # Non-finite check across outputs
        if not math.isfinite(manr):
            validity = ModelValidity.INVALID
            confidence = 0.0

        return PhysicsResidualSet(
            timestamp=observed.timestamp,
            sequence_id=observed.sequence_id,
            raw_residuals=raw_residuals,
            normalized_residuals=normalized_residuals,
            cht_max_imbalance_celsius=round(cht_imbalance, 2),
            egt_max_imbalance_celsius=round(egt_imbalance, 2),
            mean_absolute_normalized_residual=round(manr, 4),
            validity=validity,
            confidence=confidence,
        )
