"""Deterministic Health Index Calculator with 3-tier metrics and threshold-gated anomaly penalty."""

import math
from typing import Literal

from app.domain.entities.telemetry import TelemetryFrame
from app.domain.ml.models import MLInferenceResult
from app.domain.physics.models import PhysicsTwinResult
from app.domain.prognostics.models import (
    DegradationState,
    SubsystemDegradation,
    SubsystemDegradationMetric,
)


class HealthIndexCalculator:
    """Calculates 3-tier subsystem degradation and bounded composite Health Index [0.0, 1.0].

    Implements:
    1. Zero Residuals Invariant: If all physical residuals are zero and no anomaly is present,
       HI is guaranteed to be 1.0.
    2. 3-Tier Representation: Retains raw deviations, normalized sigma ratios, and bounded penalties.
    3. Mathematical Monotonicity: Increasing residual deviations strictly decreases or maintains HI.
    4. Non-Finite Safety: Gracefully handles NaN/Inf telemetry without crashing.
    """

    def __init__(
        self,
        sigma_oil_p: float = 0.25,
        sigma_oil_t: float = 3.0,
        sigma_cht: float = 5.0,
        sigma_cht_spread: float = 8.0,
        sigma_map: float = 1.0,
        sigma_vib: float = 0.25,
        tau_anom: float = 0.5402,
    ) -> None:
        self.sigma_oil_p = max(1e-6, sigma_oil_p)
        self.sigma_oil_t = max(1e-6, sigma_oil_t)
        self.sigma_cht = max(1e-6, sigma_cht)
        self.sigma_cht_spread = max(1e-6, sigma_cht_spread)
        self.sigma_map = max(1e-6, sigma_map)
        self.sigma_vib = max(1e-6, sigma_vib)
        self.tau_anom = tau_anom

        # Normalized weights summing to 1.0
        self.w_oil = 0.25
        self.w_therm = 0.25
        self.w_turbo = 0.20
        self.w_vib = 0.15
        self.w_anom = 0.15

    def _sanitize(self, val: float, default: float = 0.0) -> tuple[float, bool]:
        """Verify finiteness; return (sanitized_val, is_clean)."""
        if math.isnan(val) or math.isinf(val):
            return default, False
        return val, True

    def calculate(
        self,
        frame: TelemetryFrame,
        physics: PhysicsTwinResult | None = None,
        ml: MLInferenceResult | None = None,
    ) -> tuple[
        float, DegradationState, SubsystemDegradation, Literal["VALID", "DEGRADED", "INVALID"]
    ]:
        """Compute composite Health Index and 3-tier subsystem breakdown."""
        validity: Literal["VALID", "DEGRADED", "INVALID"] = "VALID"

        # Check telemetry validity
        frame_valid = all(
            math.isfinite(v)
            for v in (
                frame.rpm,
                frame.manifold_pressure,
                frame.oil_pressure,
                frame.oil_temperature,
                frame.vibration_rms,
                *frame.cht,
            )
        )
        if not frame_valid:
            validity = "DEGRADED"

        # 1. Lubrication Subsystem
        if physics and physics.expected_state:
            exp_oil_p = physics.expected_state.oil_pressure
            exp_oil_t = physics.expected_state.oil_temperature
        else:
            exp_oil_p = 3.8
            exp_oil_t = 85.0

        r_oil_p_val, clean_op = self._sanitize(frame.oil_pressure - exp_oil_p)
        r_oil_t_val, clean_ot = self._sanitize(frame.oil_temperature - exp_oil_t)
        if not (clean_op and clean_ot):
            validity = "DEGRADED"

        z_oil_p = abs(r_oil_p_val) / self.sigma_oil_p
        z_oil_t = abs(r_oil_t_val) / self.sigma_oil_t
        z_oil = 0.60 * z_oil_p + 0.40 * z_oil_t
        d_oil = min(1.0, max(0.0, z_oil / 3.0))

        metric_oil = SubsystemDegradationMetric(
            raw_deviation=round(abs(r_oil_p_val) + abs(r_oil_t_val), 4),
            normalized_deviation=round(z_oil, 4),
            bounded_penalty=round(d_oil, 4),
            unit="bar/°C",
        )

        # 2. Thermal Balance Subsystem
        cht_spread = max(frame.cht) - min(frame.cht)
        cht_mean = sum(frame.cht) / len(frame.cht)

        if physics and physics.expected_state:
            exp_cht = sum(physics.expected_state.cht) / len(physics.expected_state.cht)
        else:
            exp_cht = 95.0

        cht_spread_val, clean_cs = self._sanitize(cht_spread)
        r_cht_mean_val, clean_cm = self._sanitize(cht_mean - exp_cht)
        if not (clean_cs and clean_cm):
            validity = "DEGRADED"

        z_cht_spread = max(0.0, cht_spread_val) / self.sigma_cht_spread
        z_cht_mean = abs(r_cht_mean_val) / self.sigma_cht
        z_therm = 0.50 * z_cht_spread + 0.50 * z_cht_mean
        d_therm = min(1.0, max(0.0, z_therm / 3.0))

        metric_therm = SubsystemDegradationMetric(
            raw_deviation=round(abs(r_cht_mean_val) + cht_spread_val, 4),
            normalized_deviation=round(z_therm, 4),
            bounded_penalty=round(d_therm, 4),
            unit="°C",
        )

        # 3. Turbocharger Induction Subsystem
        if physics and physics.expected_state:
            exp_map = physics.expected_state.manifold_pressure
        else:
            exp_map = 29.5

        r_map_val, clean_map = self._sanitize(frame.manifold_pressure - exp_map)
        if not clean_map:
            validity = "DEGRADED"

        z_turbo = abs(r_map_val) / self.sigma_map
        d_turbo = min(1.0, max(0.0, z_turbo / 3.0))

        metric_turbo = SubsystemDegradationMetric(
            raw_deviation=round(abs(r_map_val), 4),
            normalized_deviation=round(z_turbo, 4),
            bounded_penalty=round(d_turbo, 4),
            unit="inHg",
        )

        # 4. Mechanical / Vibration Subsystem
        if physics and physics.expected_state:
            exp_vib = physics.expected_state.vibration_rms
        else:
            exp_vib = 1.15

        r_vib_val, clean_vib = self._sanitize(frame.vibration_rms - exp_vib)
        if not clean_vib:
            validity = "DEGRADED"

        z_vib = abs(r_vib_val) / self.sigma_vib
        d_vib = min(1.0, max(0.0, z_vib / 3.0))

        metric_vib = SubsystemDegradationMetric(
            raw_deviation=round(abs(r_vib_val), 4),
            normalized_deviation=round(z_vib, 4),
            bounded_penalty=round(d_vib, 4),
            unit="g",
        )

        # 5. Threshold-Gated Anomaly Penalty
        # Must be 0.0 during nominal flight or when score <= tau_anom, preventing false degradation
        d_anom = 0.0
        if ml and ml.anomaly:
            anom_flag = bool(ml.anomaly.flag)
            anom_score = float(ml.anomaly.score)
            if anom_flag and anom_score > self.tau_anom:
                excess = (anom_score - self.tau_anom) / max(1e-6, 1.0 - self.tau_anom)
                d_anom = min(1.0, max(0.0, excess))

        # Composite Health Index
        total_penalty = (
            self.w_oil * d_oil
            + self.w_therm * d_therm
            + self.w_turbo * d_turbo
            + self.w_vib * d_vib
            + self.w_anom * d_anom
        )
        health_index = max(0.0, min(1.0, 1.0 - total_penalty))

        # Percentage health scores for subsystems
        hi_oil_pct = round((1.0 - d_oil) * 100.0, 1)
        hi_therm_pct = round((1.0 - d_therm) * 100.0, 1)
        hi_turbo_pct = round((1.0 - d_turbo) * 100.0, 1)
        hi_vib_pct = round((1.0 - d_vib) * 100.0, 1)

        # Identify limiting subsystem
        penalties = {
            "lubrication": d_oil,
            "thermal": d_therm,
            "turbocharger": d_turbo,
            "rotational_vibration": d_vib,
        }
        limiting_subsystem = (
            max(penalties, key=penalties.get) if total_penalty > 0.05 else "nominal"
        )

        subsystems = SubsystemDegradation(
            lubrication=metric_oil,
            thermal=metric_therm,
            turbocharger=metric_turbo,
            rotational_vibration=metric_vib,
            anomaly_penalty=round(d_anom, 4),
            lubrication_health_pct=hi_oil_pct,
            thermal_health_pct=hi_therm_pct,
            turbocharger_health_pct=hi_turbo_pct,
            rotational_health_pct=hi_vib_pct,
            limiting_subsystem=limiting_subsystem,
        )

        # Prototype/Synthetic Degradation State Mapping
        if health_index >= 0.90:
            deg_state = DegradationState.NOMINAL
        elif health_index >= 0.75:
            deg_state = DegradationState.EARLY_DEGRADATION
        elif health_index >= 0.50:
            deg_state = DegradationState.MODERATE_DEGRADATION
        elif health_index >= 0.25:
            deg_state = DegradationState.SEVERE_DEGRADATION
        else:
            deg_state = DegradationState.CRITICAL_SIMULATED_STATE

        return round(health_index, 4), deg_state, subsystems, validity
