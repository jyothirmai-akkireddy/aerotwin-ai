"""Physics Twin application service coordinating first-principles analytical estimation and residuals."""

import time

from app.domain.entities.telemetry import QualityStatus, TelemetryFrame
from app.domain.physics.exhaust import ExhaustEnergyModel
from app.domain.physics.fuel import FuelDeliveryModel
from app.domain.physics.induction import InductionPressureModel
from app.domain.physics.lubrication import LubricationOilModel
from app.domain.physics.models import (
    ModelValidity,
    PhysicsCalibrationParameters,
    PhysicsExpectedState,
    PhysicsTwinResult,
)
from app.domain.physics.residual_engine import ResidualEngine
from app.domain.physics.thermal import ThermalCylinderModel
from app.domain.physics.vibration import VibrationBaselineModel
from app.infrastructure.logging.logger import get_logger
from app.infrastructure.physics.calibration_repository import (
    PhysicsCalibrationRepository,
)

logger = get_logger("aerotwin.physics.service")


class PhysicsTwinService:
    """Orchestrates low-order analytical physics models and residual extraction."""

    def __init__(self, calibration_repo: PhysicsCalibrationRepository | None = None):
        if calibration_repo is None:
            self.calibration_repo = PhysicsCalibrationRepository()
        else:
            self.calibration_repo = calibration_repo

        self.cal: PhysicsCalibrationParameters = self.calibration_repo.get_parameters()
        self._init_submodels()

        # Transient state tracking across frames
        self._last_timestamp: float | None = None
        self._last_cht: list[float] | None = None
        self._last_egt: list[float] | None = None
        self._last_coolant: float | None = None
        self._last_oil_temp: float | None = None

        self._last_result: PhysicsTwinResult | None = None

        # Performance and diagnostic counters
        self._eval_count: int = 0
        self._total_compute_time_ms: float = 0.0
        self._invalid_count: int = 0
        self._out_of_range_count: int = 0

    def _init_submodels(self) -> None:
        """Instantiate all domain physics sub-models using active calibration."""
        self.induction_model = InductionPressureModel(self.cal)
        self.fuel_model = FuelDeliveryModel(self.cal)
        self.thermal_model = ThermalCylinderModel(self.cal)
        self.exhaust_model = ExhaustEnergyModel(self.cal)
        self.lubrication_model = LubricationOilModel(self.cal)
        self.vibration_model = VibrationBaselineModel(self.cal)
        self.residual_engine = ResidualEngine(self.cal)

    def reload_calibration(self, new_params: PhysicsCalibrationParameters) -> None:
        """Update calibration parameters and re-initialize sub-models."""
        self.cal = self.calibration_repo.update_parameters(new_params)
        self._init_submodels()
        logger.info(f"PhysicsTwinService reloaded calibration v{self.cal.version}")

    def evaluate_frame(self, frame: TelemetryFrame) -> PhysicsTwinResult:
        """Evaluate expected state and compute residuals for an observed telemetry frame."""
        t_start = time.perf_counter()

        # Determine frame delta time
        if self._last_timestamp is not None and frame.timestamp > self._last_timestamp:
            dt = frame.timestamp - self._last_timestamp
        else:
            dt = 0.1  # Nominal 10 Hz fallback

        # 1. Induction & MAP
        p_map_exp, air_flow, v_ind, _ = self.induction_model.evaluate(
            throttle_pct=frame.throttle_position,
            rpm=frame.rpm,
            altitude_m=frame.altitude,
            ambient_temp_c=frame.ambient_temp,
        )

        # 2. Fuel Delivery
        ff_exp, v_fuel, _ = self.fuel_model.evaluate(
            air_mass_flow_kg_h=air_flow,
            rpm=frame.rpm,
            throttle_pct=frame.throttle_position,
        )

        # 3. Thermal CHT & Coolant
        cht_exp, coolant_exp, v_therm, _ = self.thermal_model.evaluate(
            fuel_flow_l_h=ff_exp,
            rpm=frame.rpm,
            true_airspeed_m_s=frame.true_airspeed,
            ambient_temp_c=frame.ambient_temp,
            dt_seconds=dt,
            previous_cht=self._last_cht,
            previous_coolant=self._last_coolant,
        )

        # 4. Exhaust EGT
        egt_exp, v_exh, _ = self.exhaust_model.evaluate(
            fuel_flow_l_h=ff_exp,
            manifold_pressure_inhg=p_map_exp,
            injection_timing_deg=frame.injection_timing,
            rpm=frame.rpm,
            dt_seconds=dt,
            previous_egt=self._last_egt,
        )

        # 5. Lubrication Oil Pressure & Temp
        oil_p_exp, oil_t_exp, v_oil, _ = self.lubrication_model.evaluate(
            rpm=frame.rpm,
            oil_temperature_c=frame.oil_temperature,
            ambient_temp_c=frame.ambient_temp,
            dt_seconds=dt,
            previous_oil_temp=self._last_oil_temp,
        )

        # 6. Vibration Baseline
        vib_exp, v_vib, _ = self.vibration_model.evaluate(
            rpm=frame.rpm,
            manifold_pressure_inhg=p_map_exp,
        )

        # 7. Model Validity Aggregation
        sub_validities = [v_ind, v_fuel, v_therm, v_exh, v_oil, v_vib]
        if frame.quality_flag == QualityStatus.INVALID or ModelValidity.INVALID in sub_validities:
            combined_validity = ModelValidity.INVALID
            confidence = 0.0
            self._invalid_count += 1
        elif ModelValidity.OUT_OF_RANGE in sub_validities:
            combined_validity = ModelValidity.OUT_OF_RANGE
            confidence = 0.3
            self._out_of_range_count += 1
        elif (
            frame.quality_flag == QualityStatus.DEGRADED or ModelValidity.DEGRADED in sub_validities
        ):
            combined_validity = ModelValidity.DEGRADED
            confidence = 0.6
        else:
            combined_validity = ModelValidity.VALID
            confidence = 0.98

        expected_state = PhysicsExpectedState(
            timestamp=frame.timestamp,
            sequence_id=frame.sequence_id,
            rpm=round(frame.rpm, 1),  # RPM is authoritative operating point
            manifold_pressure=round(p_map_exp, 2),
            air_mass_flow=round(air_flow, 2),
            fuel_flow=round(ff_exp, 2),
            cht=[round(c, 2) for c in cht_exp],
            egt=[round(e, 2) for e in egt_exp],
            coolant_temp=round(coolant_exp, 2),
            oil_temperature=round(oil_t_exp, 2),
            oil_pressure=round(oil_p_exp, 2),
            vibration_rms=round(vib_exp, 3),
            validity=combined_validity,
            confidence=confidence,
            model_version=self.cal.version,
        )

        # 8. Compute Residuals
        residuals = self.residual_engine.compute_residuals(frame, expected_state)

        # Update transient history for next recurrence step
        self._last_timestamp = frame.timestamp
        self._last_cht = cht_exp
        self._last_egt = egt_exp
        self._last_coolant = coolant_exp
        self._last_oil_temp = oil_t_exp

        # Record diagnostics
        elapsed_ms = (time.perf_counter() - t_start) * 1000.0
        self._eval_count += 1
        self._total_compute_time_ms += elapsed_ms

        result = PhysicsTwinResult(
            expected_state=expected_state,
            residuals=residuals,
            diagnostics={
                "compute_time_ms": round(elapsed_ms, 3),
                "submodel_validities": {
                    "induction": v_ind.value,
                    "fuel": v_fuel.value,
                    "thermal": v_therm.value,
                    "exhaust": v_exh.value,
                    "lubrication": v_oil.value,
                    "vibration": v_vib.value,
                },
            },
        )
        self._last_result = result
        return result

    def reset(self) -> None:
        """Reset transient state tracking and history across frames."""
        self._last_timestamp = None
        self._last_cht = None
        self._last_egt = None
        self._last_coolant = None
        self._last_oil_temp = None
        self._last_result = None

    def get_latest_result(self) -> PhysicsTwinResult | None:
        """Retrieve the most recent evaluation result."""
        return self._last_result

    def get_diagnostics(self) -> dict[str, float | int | str]:
        """Retrieve performance and operational diagnostic metrics."""
        avg_latency = (
            self._total_compute_time_ms / max(1, self._eval_count) if self._eval_count > 0 else 0.0
        )
        return {
            "evaluation_count": self._eval_count,
            "average_compute_time_ms": round(avg_latency, 4),
            "invalid_frame_count": self._invalid_count,
            "out_of_range_count": self._out_of_range_count,
            "calibration_version": self.cal.version,
            "model_status": "READY",
        }
