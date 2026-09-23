"""Intake induction and turbocharger manifold absolute pressure model.

PROTOTYPE APPROXIMATION:
Inspired by the wastegate boost schedule and speed-density air induction of a
generic 4-cylinder turbocharged aero-piston engine in the Rotax 914/915 class.
"""

import math

from app.domain.physics.models import ModelValidity, PhysicsCalibrationParameters


class InductionPressureModel:
    """Estimates expected manifold absolute pressure (MAP) and air mass induction flow."""

    def __init__(self, calibration: PhysicsCalibrationParameters):
        self.cal = calibration

    def compute_isa_pressure_inhg(self, altitude_m: float) -> float:
        """Calculate ICAO Standard Atmosphere (ISA) ambient barometric pressure in inHg.

        Valid region: -500m to 11,000m (troposphere).
        """
        if not math.isfinite(altitude_m) or altitude_m < -1000.0 or altitude_m > 20000.0:
            return 29.921

        # ISA troposphere barometric lapse equation
        t0 = 288.15
        lapse = 0.0065
        t_local = max(180.0, t0 - lapse * altitude_m)
        exponent = 5.2559  # (g0 * M) / (R * L)
        p_ratio = math.pow(t_local / t0, exponent)
        return max(2.0, min(35.0, 29.921 * p_ratio))

    def evaluate(
        self,
        throttle_pct: float,
        rpm: float,
        altitude_m: float,
        ambient_temp_c: float,
    ) -> tuple[float, float, ModelValidity, str | None]:
        """Estimate expected manifold pressure (inHg) and air mass flow (kg/h).

        Returns: (expected_map_inhg, air_mass_flow_kg_h, validity, diagnostic_err)
        """
        # Guard against non-finite inputs
        if not (
            math.isfinite(throttle_pct)
            and math.isfinite(rpm)
            and math.isfinite(altitude_m)
            and math.isfinite(ambient_temp_c)
        ):
            return 0.0, 0.0, ModelValidity.INVALID, "Non-finite input detected in induction model"

        if (
            altitude_m < -500.0
            or altitude_m > 12000.0
            or ambient_temp_c < -60.0
            or ambient_temp_c > 65.0
        ):
            validity = ModelValidity.OUT_OF_RANGE
        elif rpm < self.cal.idle_rpm * 0.7:
            validity = ModelValidity.DEGRADED
        else:
            validity = ModelValidity.VALID

        p_amb = self.compute_isa_pressure_inhg(altitude_m)
        alpha_norm = max(0.0, min(100.0, throttle_pct)) / 100.0

        # Naturally aspirated throttled manifold pressure
        k_closed = 0.35  # Idle vacuum fraction
        p_na = p_amb * (k_closed + (1.0 - k_closed) * alpha_norm)

        # Turbocharger pressure ratio
        n_spool = self.cal.spool_rpm
        n_rated = self.cal.rated_rpm
        rpm_ratio = max(0.0, (rpm - n_spool) / (n_rated - n_spool + 1e-6))
        boost_fraction = math.pow(min(1.0, rpm_ratio), 1.2) * alpha_norm
        pr_turbo = 1.0 + boost_fraction * (self.cal.max_boost_pr - 1.0)

        # Expected MAP in inHg
        p_map_exp = min(46.0, p_na * pr_turbo)

        # Speed-Density Air Mass Flow Rate
        t_manifold_k = max(220.0, ambient_temp_c + 273.15 + (15.0 * boost_fraction))
        r_spec_air = 287.05  # J/(kg K)
        p_map_pa = p_map_exp * 3386.39
        rho_manifold = p_map_pa / (r_spec_air * t_manifold_k + 1e-6)

        # Displacement in m^3
        v_d_m3 = (self.cal.engine_displacement_cc) * 1e-6
        # Volumetric efficiency approximation
        eta_v = max(0.65, min(0.95, 0.82 + 0.08 * (rpm / (n_rated + 1e-6))))

        # Air flow in kg/h: (Vd * RPM / (2 * 60)) * rho * eta_v * 3600
        air_mass_flow_kg_h = max(0.0, (v_d_m3 * rpm / 120.0) * rho_manifold * eta_v * 3600.0)

        return p_map_exp, air_mass_flow_kg_h, validity, None
