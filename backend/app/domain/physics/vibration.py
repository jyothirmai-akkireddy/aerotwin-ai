"""Rotational harmonic vibration baseline model.

PROTOTYPE APPROXIMATION:
Baseline airframe vibration scaling quadratically with rotational frequency and engine load.
"""

import math

from app.domain.physics.models import ModelValidity, PhysicsCalibrationParameters


class VibrationBaselineModel:
    """Estimates expected tri-axial vibration RMS baseline (g)."""

    def __init__(self, calibration: PhysicsCalibrationParameters):
        self.cal = calibration

    def evaluate(
        self,
        rpm: float,
        manifold_pressure_inhg: float,
    ) -> tuple[float, ModelValidity, str | None]:
        """Estimate expected vibration RMS in g (1g = 9.80665 m/s^2).

        Returns: (expected_vibration_rms, validity, diagnostic_err)
        """
        if not (math.isfinite(rpm) and math.isfinite(manifold_pressure_inhg)):
            return 0.0, ModelValidity.INVALID, "Non-finite input in vibration model"

        if rpm < 100.0:
            return 0.05, ModelValidity.DEGRADED, None

        if manifold_pressure_inhg < 5.0 or manifold_pressure_inhg > 55.0:
            validity = ModelValidity.OUT_OF_RANGE
        else:
            validity = ModelValidity.VALID

        # Rotational unbalance scales with square of RPM, load scales with MAP
        rpm_ratio = rpm / (self.cal.rated_rpm + 1e-6)
        load_ratio = manifold_pressure_inhg / 29.92

        expected_vib_g = 0.35 + 0.75 * math.pow(rpm_ratio, 2.0) + 0.35 * load_ratio
        return max(0.1, min(10.0, expected_vib_g)), validity, None
