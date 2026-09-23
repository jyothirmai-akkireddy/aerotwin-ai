"""Exhaust gas temperature (EGT) energy balance model.

PROTOTYPE APPROXIMATION:
Post-combustion enthalpy release with spark timing and thermocouple lag.
"""

import math

from app.domain.physics.models import ModelValidity, PhysicsCalibrationParameters


class ExhaustEnergyModel:
    """Estimates expected Exhaust Gas Temperature (EGT) for Cylinders 1-4 (°C)."""

    def __init__(self, calibration: PhysicsCalibrationParameters):
        self.cal = calibration

    def evaluate(
        self,
        fuel_flow_l_h: float,
        manifold_pressure_inhg: float,
        injection_timing_deg: float,
        rpm: float,
        dt_seconds: float,
        previous_egt: list[float] | None = None,
    ) -> tuple[list[float], ModelValidity, str | None]:
        """Estimate expected EGT for Cylinders 1-4 (°C).

        Returns: (expected_egt_list, validity, diagnostic_err)
        """
        if not (
            math.isfinite(fuel_flow_l_h)
            and math.isfinite(manifold_pressure_inhg)
            and math.isfinite(injection_timing_deg)
            and math.isfinite(rpm)
            and math.isfinite(dt_seconds)
        ):
            return [0.0, 0.0, 0.0, 0.0], ModelValidity.INVALID, "Non-finite input in exhaust model"

        if dt_seconds <= 0.0:
            dt_seconds = 0.1

        if rpm < 300.0:
            return [50.0, 50.0, 50.0, 50.0], ModelValidity.DEGRADED, None

        if injection_timing_deg < 0.0 or injection_timing_deg > 50.0:
            validity = ModelValidity.OUT_OF_RANGE
        else:
            validity = ModelValidity.VALID

        # Steady-state combustion gas temperature approximation
        t_base = 550.0
        load_scale = (manifold_pressure_inhg / 29.92) * math.sqrt(max(0.1, fuel_flow_l_h / 16.0))
        timing_offset = 4.5 * (injection_timing_deg - 24.0)

        if previous_egt is None or len(previous_egt) != 4:
            prev_egt = [650.0] * 4
        else:
            prev_egt = [e if math.isfinite(e) else 650.0 for e in previous_egt]

        tau_egt = self.cal.tau_egt_seconds
        decay_egt = math.exp(-dt_seconds / (tau_egt + 1e-6))

        expected_egt = []
        for i in range(4):
            bias = self.cal.egt_cylinder_bias[i]
            t_ss_i = (t_base + 220.0 * load_scale - timing_offset) * bias
            t_next_i = t_ss_i + (prev_egt[i] - t_ss_i) * decay_egt
            expected_egt.append(t_next_i)

        return expected_egt, validity, None
