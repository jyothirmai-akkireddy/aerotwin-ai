"""Hydrodynamic lubrication pressure and oil temperature model.

PROTOTYPE APPROXIMATION:
Positive displacement pump delivery offset by temperature-dependent clearance loss.
"""

import math

from app.domain.physics.models import ModelValidity, PhysicsCalibrationParameters


class LubricationOilModel:
    """Estimates expected oil gallery pressure (bar) and sump oil temperature (°C)."""

    def __init__(self, calibration: PhysicsCalibrationParameters):
        self.cal = calibration

    def evaluate(
        self,
        rpm: float,
        oil_temperature_c: float,
        ambient_temp_c: float,
        dt_seconds: float,
        previous_oil_temp: float | None = None,
    ) -> tuple[float, float, ModelValidity, str | None]:
        """Estimate expected oil gallery pressure (bar) and oil temperature (°C).

        Returns: (expected_oil_pressure_bar, expected_oil_temp_c, validity, diagnostic_err)
        """
        if not (
            math.isfinite(rpm)
            and math.isfinite(oil_temperature_c)
            and math.isfinite(ambient_temp_c)
            and math.isfinite(dt_seconds)
        ):
            return 0.0, 0.0, ModelValidity.INVALID, "Non-finite input in lubrication model"

        if dt_seconds <= 0.0:
            dt_seconds = 0.1

        if rpm < 100.0:
            # Engine stopped, zero pump pressure
            return 0.0, oil_temperature_c, ModelValidity.DEGRADED, None

        if oil_temperature_c < -30.0 or oil_temperature_c > 160.0:
            validity = ModelValidity.OUT_OF_RANGE
        else:
            validity = ModelValidity.VALID

        # Positive-displacement pump pressure curve
        # Idle (1400 RPM) -> ~2.0 bar; Rated (5000 RPM) -> ~5.0 bar (relief valve limit)
        rpm_ratio = max(
            0.0,
            min(1.0, (rpm - self.cal.idle_rpm) / (self.cal.rated_rpm - self.cal.idle_rpm + 1e-6)),
        )
        p_pump = 2.0 + 3.0 * rpm_ratio

        # Viscosity thinning effect: warmer oil leaks more past bearings, lowering pressure
        # Reference temperature: 85°C
        k_visc = 0.020  # bar per °C deviation
        p_visc_loss = k_visc * (oil_temperature_c - 85.0)

        expected_pressure_bar = max(0.5, min(5.0, p_pump - p_visc_loss))

        # Expected sump oil temperature dynamics (slow thermal inertia)
        if previous_oil_temp is None or not math.isfinite(previous_oil_temp):
            prev_temp = oil_temperature_c
        else:
            prev_temp = previous_oil_temp

        # Sump equilibrium temperature scales with engine speed and load
        t_oil_ss = ambient_temp_c + 55.0 * (rpm / (self.cal.rated_rpm + 1e-6))
        tau_oil = self.cal.tau_oil_seconds
        decay_oil = math.exp(-dt_seconds / (tau_oil + 1e-6))
        expected_temp_c = t_oil_ss + (prev_temp - t_oil_ss) * decay_oil

        return expected_pressure_bar, expected_temp_c, validity, None
