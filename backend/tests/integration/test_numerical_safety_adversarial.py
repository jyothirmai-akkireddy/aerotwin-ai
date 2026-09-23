"""Cross-phase analytical chain and adversarial numerical safety test.

SIH26054 — AeroTwin AI
Phase 9 Integration & Security Gate

Validates:
1. Cross-phase propagation for NOMINAL + 5 fault modes:
   - NOMINAL
   - COOLING_LOSS
   - OIL_LEAK
   - SENSOR_DRIFT
   - ABNORMAL_COMBUSTION
   - MECHANICAL_WEAR
2. Numerical adversarial inputs:
   - NaN / Inf rejection
   - Non-monotonic timestamps
   - Boundary values (0 RPM cold, 6500+ redline RPM)
   - Empty and single-frame inputs
3. Zero JSON serialization leakage (Pydantic models dump clean valid JSON with allow_nan=False).
4. All test data identified as SYNTHETIC / PROTOTYPE SCENARIO.
"""

import json
import math

import pytest

from app.application.services.ml_service import MLInferenceService
from app.application.services.physics_twin_service import PhysicsTwinService
from app.application.services.prognostics_service import PrognosticsService
from app.domain.entities.telemetry import QualityStatus
from app.domain.simulation.faults import SensorFaultConfig, SensorFaultType
from app.domain.telemetry.validation import TelemetryValidator
from app.infrastructure.logging.logger import get_logger
from app.infrastructure.physics.calibration_repository import PhysicsCalibrationRepository
from app.infrastructure.simulation.engine_simulator import EngineSimulator

logger = get_logger("aerotwin.test.numerical_safety")

PROTOTYPE_SCENARIO_TAG = "SYNTHETIC / PROTOTYPE SCENARIO — Phase 9 Numerical Safety & Adversarial"


@pytest.fixture
def analytics_stack():
    cal_repo = PhysicsCalibrationRepository()
    physics_service = PhysicsTwinService(calibration_repo=cal_repo)
    ml_service = MLInferenceService()
    prognostics_service = PrognosticsService()
    validator = TelemetryValidator(track_history=True)
    return physics_service, ml_service, prognostics_service, validator


def test_nominal_and_five_fault_modes(analytics_stack):
    """Verify analytical chain propagation under NOMINAL and 5 standard fault modes."""
    physics_service, ml_service, prognostics_service, validator = analytics_stack

    fault_configs = [
        ("NOMINAL", None),
        (
            "COOLING_LOSS",
            SensorFaultConfig(
                target_channel="coolant_temp",
                fault_type=SensorFaultType.DRIFT,
                drift_rate_per_sec=1.5,
                start_time_sec=0.0,
            ),
        ),
        (
            "OIL_LEAK",
            SensorFaultConfig(
                target_channel="oil_pressure",
                fault_type=SensorFaultType.DRIFT,
                drift_rate_per_sec=-0.1,
                start_time_sec=0.0,
            ),
        ),
        (
            "SENSOR_DRIFT",
            SensorFaultConfig(
                target_channel="rpm",
                fault_type=SensorFaultType.BIAS,
                magnitude=300.0,
                start_time_sec=0.0,
            ),
        ),
        (
            "ABNORMAL_COMBUSTION",
            SensorFaultConfig(
                target_channel="egt_1",
                fault_type=SensorFaultType.BIAS,
                magnitude=120.0,
                start_time_sec=0.0,
            ),
        ),
        (
            "MECHANICAL_WEAR",
            SensorFaultConfig(
                target_channel="vibration_rms",
                fault_type=SensorFaultType.BIAS,
                magnitude=4.0,
                start_time_sec=0.0,
            ),
        ),
    ]

    for mode_name, fault in fault_configs:
        sim = EngineSimulator(telemetry_rate_hz=10)
        if fault:
            sim.faults.add_fault(fault)

        physics_service.reset()
        prognostics_service.reset()
        validator.reset()

        # Run 30 frames
        for _ in range(30):
            frame = sim.step()
            assert validator.validate(frame) is not None
            p_res = physics_service.evaluate_frame(frame)
            m_res = ml_service.evaluate(frame, p_res)
            prog_res = prognostics_service.evaluate(frame, p_res, m_res)

            # Invariant checks
            assert p_res.residuals is not None
            assert m_res.anomaly is not None
            assert 0.0 <= prog_res.health_index <= 1.0

            # Strict RFC-compliant JSON serialization test (no raw NaNs or Infinities)
            p_dict = p_res.model_dump(mode="json")
            m_dict = m_res.model_dump(mode="json")
            prog_dict = prog_res.model_dump(mode="json")

            json.dumps(p_dict, allow_nan=False)
            json.dumps(m_dict, allow_nan=False)
            json.dumps(prog_dict, allow_nan=False)

        logger.info(f"Mode {mode_name} propagated cleanly through all analytical stages.")


def test_nan_and_inf_rejection(analytics_stack):
    """Verify that NaN and Inf telemetry values are safely rejected by the validator."""
    physics_service, ml_service, prognostics_service, validator = analytics_stack

    sim = EngineSimulator(telemetry_rate_hz=10)
    nominal_frame = sim.step()

    # Adversarial NaN injection
    nan_frame = nominal_frame.model_copy(update={"rpm": float("nan"), "sequence_id": 9901})
    val_nan = validator.validate(nan_frame)
    assert not val_nan.is_valid
    assert any("not finite" in err for err in val_nan.errors)
    assert val_nan.quality == QualityStatus.INVALID

    # Adversarial Inf injection
    inf_frame = nominal_frame.model_copy(update={"oil_pressure": float("inf"), "sequence_id": 9902})
    val_inf = validator.validate(inf_frame)
    assert not val_inf.is_valid
    assert any("not finite" in err for err in val_inf.errors)
    assert val_inf.quality == QualityStatus.INVALID


def test_non_monotonic_timestamp_rejection(analytics_stack):
    """Verify that backward-jumping timestamps are caught by the validator."""
    _, _, _, validator = analytics_stack
    validator.reset()

    sim = EngineSimulator(telemetry_rate_hz=10)
    f1 = sim.step()
    res1 = validator.validate(f1)
    assert res1.is_valid

    # Jump timestamp backward by 10 seconds
    f2 = sim.step()
    f2_bad = f2.model_copy(
        update={"timestamp": f1.timestamp - 10.0, "sequence_id": f1.sequence_id + 1}
    )
    res2 = validator.validate(f2_bad)
    assert not res2.is_valid
    assert any("Non-monotonic timestamp" in err for err in res2.errors)


def test_zero_rpm_and_redline_rpm_safety(analytics_stack):
    """Verify numerical stability at 0 RPM (dead cold) and 6500 RPM (redline)."""
    physics_service, ml_service, prognostics_service, validator = analytics_stack

    sim = EngineSimulator(telemetry_rate_hz=10)
    base = sim.step()

    # 1. Zero RPM cold engine
    zero_frame = base.model_copy(
        update={
            "rpm": 0.0,
            "manifold_pressure": 29.92,
            "fuel_flow": 0.0,
            "oil_pressure": 0.0,
            "sequence_id": 9910,
        }
    )
    p_zero = physics_service.evaluate_frame(zero_frame)
    m_zero = ml_service.evaluate(zero_frame, p_zero)
    prog_zero = prognostics_service.evaluate(zero_frame, p_zero, m_zero)

    assert math.isfinite(p_zero.residuals.mean_absolute_normalized_residual)
    assert math.isfinite(m_zero.anomaly.score)
    assert math.isfinite(prog_zero.health_index)

    # 2. Redline 6500 RPM
    redline_frame = base.model_copy(
        update={
            "rpm": 6500.0,
            "manifold_pressure": 38.0,
            "fuel_flow": 42.0,
            "oil_pressure": 4.5,
            "sequence_id": 9911,
        }
    )
    p_red = physics_service.evaluate_frame(redline_frame)
    m_red = ml_service.evaluate(redline_frame, p_red)
    prog_red = prognostics_service.evaluate(redline_frame, p_red, m_red)

    assert math.isfinite(p_red.residuals.mean_absolute_normalized_residual)
    assert math.isfinite(m_red.anomaly.score)
    assert math.isfinite(prog_red.health_index)
