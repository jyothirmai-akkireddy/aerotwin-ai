"""Lumped-parameter cylinder and coolant jacket heat balance model.

PROTOTYPE APPROXIMATION:
First-order lumped thermal capacitance with exponential recurrence.
"""

import math

from app.domain.physics.models import ModelValidity, PhysicsCalibrationParameters


class ThermalCylinderModel:
    """Estimates expected 4-cylinder CHT and coolant jacket temperatures."""

    def __init__(self, calibration: PhysicsCalibrationParameters):
        self.cal = calibration

    def evaluate(
        self,
        fuel_flow_l_h: float,
        rpm: float,
        true_airspeed_m_s: float,
        ambient_temp_c: float,
        dt_seconds: float,
        previous_cht: list[float] | None = None,
        previous_coolant: float | None = None,
    ) -> tuple[list[float], float, ModelValidity, str | None]:
        """Estimate expected CHT for Cylinders 1-4 and Coolant temperature (°C).

        Returns: (expected_cht_list, expected_coolant_c, validity, diagnostic_err)
        """
        # Guard against non-finite inputs
        if not (
            math.isfinite(fuel_flow_l_h)
            and math.isfinite(rpm)
            and math.isfinite(true_airspeed_m_s)
            and math.isfinite(ambient_temp_c)
            and math.isfinite(dt_seconds)
        ):
            return (
                [0.0, 0.0, 0.0, 0.0],
                0.0,
                ModelValidity.INVALID,
                "Non-finite input detected in thermal model",
            )

        if dt_seconds <= 0.0:
            dt_seconds = 0.1

        # Check physical bounds
        if ambient_temp_c < -60.0 or ambient_temp_c > 65.0 or true_airspeed_m_s < 0.0:
            validity = ModelValidity.OUT_OF_RANGE
        elif rpm < 300.0:
            validity = ModelValidity.DEGRADED
        else:
            validity = ModelValidity.VALID

        # Ram air convective cooling factor
        v_norm = max(0.0, min(120.0, true_airspeed_m_s)) / 50.0
        cooling_factor = 1.0 + 0.40 * math.pow(v_norm, 0.8)

        # Baseline combustion heat rise proportional to fuel flow
        # Nominal cruise (16.5 L/h) -> ~95°C CHT rise above ambient
        heat_rise_scale = 75.0 * (fuel_flow_l_h / 16.0)

        # Initialize previous states if cold starting
        if previous_cht is None or len(previous_cht) != 4:
            prev_cht = [ambient_temp_c] * 4
        else:
            prev_cht = [c if math.isfinite(c) else ambient_temp_c for c in previous_cht]

        if previous_coolant is None or not math.isfinite(previous_coolant):
            prev_coolant = ambient_temp_c
        else:
            prev_coolant = previous_coolant

        # Compute each cylinder's expected temperature
        tau_cht = self.cal.tau_cht_seconds
        decay_cht = math.exp(-dt_seconds / (tau_cht + 1e-6))

        expected_cht = []
        for i in range(4):
            bias = self.cal.cht_cylinder_bias[i]
            # Steady-state equilibrium target
            t_ss_i = ambient_temp_c + (heat_rise_scale / cooling_factor) * bias
            # Discrete exponential recurrence
            t_next_i = t_ss_i + (prev_cht[i] - t_ss_i) * decay_cht
            expected_cht.append(t_next_i)

        # Coolant jacket temperature (liquid damped, slightly lower than CHT)
        tau_coolant = self.cal.tau_coolant_seconds
        decay_coolant = math.exp(-dt_seconds / (tau_coolant + 1e-6))
        t_coolant_ss = ambient_temp_c + ((heat_rise_scale * 0.85) / cooling_factor)
        expected_coolant = t_coolant_ss + (prev_coolant - t_coolant_ss) * decay_coolant

        return expected_cht, expected_coolant, validity, None
