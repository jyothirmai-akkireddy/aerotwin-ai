"""Fuel delivery and stoichiometric consumption model.

PROTOTYPE APPROXIMATION:
Speed-density combustion demand with power enrichment for a generic
turbocharged aero-piston engine.
"""

import math

from app.domain.physics.models import ModelValidity, PhysicsCalibrationParameters


class FuelDeliveryModel:
    """Estimates expected fuel flow rate (L/h) given air induction and operating point."""

    def __init__(self, calibration: PhysicsCalibrationParameters):
        self.cal = calibration
        self.fuel_density_kg_l = 0.72  # Standard aviation gasoline / Mogas density

    def evaluate(
        self,
        air_mass_flow_kg_h: float,
        rpm: float,
        throttle_pct: float,
    ) -> tuple[float, ModelValidity, str | None]:
        """Estimate expected fuel consumption rate in L/h.

        Returns: (expected_fuel_flow_l_h, validity, diagnostic_err)
        """
        if not (
            math.isfinite(air_mass_flow_kg_h) and math.isfinite(rpm) and math.isfinite(throttle_pct)
        ):
            return 0.0, ModelValidity.INVALID, "Non-finite input detected in fuel model"

        if rpm < 100.0:
            # Engine stopped
            return 0.0, ModelValidity.DEGRADED, None

        if air_mass_flow_kg_h < 0.0 or throttle_pct < 0.0 or throttle_pct > 100.0:
            return 0.0, ModelValidity.OUT_OF_RANGE, "Input values out of physical domain"

        # Target Air-Fuel Ratio (AFR)
        # Cruise is near stoichiometric (14.7); full throttle enriches for knock protection and cooling
        if throttle_pct > 75.0:
            enrichment_factor = (throttle_pct - 75.0) / 25.0
            afr_target = 14.7 - (14.7 - 12.6) * enrichment_factor
        elif rpm < self.cal.idle_rpm:
            afr_target = 13.5  # Richer idle mixture
        else:
            afr_target = 14.7

        # Fuel mass flow in kg/h
        fuel_mass_flow_kg_h = air_mass_flow_kg_h / (afr_target + 1e-6)

        # Volumetric flow rate in L/h
        fuel_flow_l_h = fuel_mass_flow_kg_h / self.fuel_density_kg_l

        # Apply minimum idle sustaining flow
        if rpm > 600.0:
            fuel_flow_l_h = max(1.8, fuel_flow_l_h)

        validity = ModelValidity.VALID if rpm >= self.cal.idle_rpm * 0.7 else ModelValidity.DEGRADED
        return fuel_flow_l_h, validity, None
