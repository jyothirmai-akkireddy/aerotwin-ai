"""Unit tests verifying numerical robustness, division-by-zero protection, and validity propagation."""

import math

from app.domain.entities.telemetry import (
    QualityStatus,
    TelemetryFrame,
    TelemetrySource,
)
from app.domain.physics.models import (
    ModelValidity,
    PhysicsCalibrationParameters,
    PhysicsExpectedState,
)
from app.domain.physics.residual_engine import ResidualEngine


def _make_frame(**kwargs) -> TelemetryFrame:
    default_kwargs = {
        "timestamp": 100.0,
        "sequence_id": 1,
        "source_type": TelemetrySource.SIMULATED,
        "quality_flag": QualityStatus.VALID,
        "rpm": 2400.0,
        "manifold_pressure": 29.5,
        "throttle_position": 50.0,
        "fuel_flow": 16.5,
        "fuel_pressure": 3.0,
        "injection_timing": 24.0,
        "cht": [95.0, 95.0, 95.0, 95.0],
        "egt": [720.0, 720.0, 720.0, 720.0],
        "coolant_temp": 82.0,
        "oil_temperature": 85.0,
        "oil_pressure": 3.8,
        "vibration_rms": 1.10,
        "battery_voltage": 28.2,
        "alternator_current": 18.0,
        "alternator_status": "OK",
        "altitude": 1000.0,
        "ambient_temp": 15.0,
        "true_airspeed": 45.0,
    }
    default_kwargs.update(kwargs)
    return TelemetryFrame(**default_kwargs)


def _make_expected(**kwargs) -> PhysicsExpectedState:
    default_kwargs = {
        "timestamp": 100.0,
        "sequence_id": 1,
        "rpm": 2400.0,
        "manifold_pressure": 29.5,
        "air_mass_flow": 180.0,
        "fuel_flow": 16.5,
        "cht": [95.0, 95.0, 95.0, 95.0],
        "egt": [720.0, 720.0, 720.0, 720.0],
        "coolant_temp": 82.0,
        "oil_temperature": 85.0,
        "oil_pressure": 3.8,
        "vibration_rms": 1.10,
        "validity": ModelValidity.VALID,
        "confidence": 0.98,
        "model_version": "1.0.0",
    }
    default_kwargs.update(kwargs)
    return PhysicsExpectedState(**default_kwargs)


def test_zero_sigma_division_guard():
    """Verify zero or near-zero sigma scale does not raise ZeroDivisionError."""
    cal = PhysicsCalibrationParameters(sigma_scales={"rpm": 0.0, "manifold_pressure": 1e-8})
    engine = ResidualEngine(cal)

    obs = _make_frame(rpm=2600.0, manifold_pressure=32.0)
    exp = _make_expected(rpm=2400.0, manifold_pressure=29.5)

    res = engine.compute_residuals(obs, exp)

    # Safe division guards must return 0.0 without crashing
    assert res.normalized_residuals["rpm"] == 0.0
    assert res.normalized_residuals["manifold_pressure"] == 0.0
    assert math.isfinite(res.mean_absolute_normalized_residual)


def test_invalid_telemetry_quality_propagation():
    """Verify corrupted telemetry quality flags force ModelValidity.INVALID and zero confidence."""
    cal = PhysicsCalibrationParameters()
    engine = ResidualEngine(cal)

    obs = _make_frame(quality_flag=QualityStatus.INVALID)
    exp = _make_expected()

    res = engine.compute_residuals(obs, exp)
    assert res.validity == ModelValidity.INVALID
    assert res.confidence == 0.0


def test_expected_state_out_of_range_propagation():
    """Verify out-of-range expected state propagates validity and reduced confidence."""
    cal = PhysicsCalibrationParameters()
    engine = ResidualEngine(cal)

    obs = _make_frame()
    exp = _make_expected(validity=ModelValidity.OUT_OF_RANGE, confidence=0.3)

    res = engine.compute_residuals(obs, exp)
    assert res.validity == ModelValidity.OUT_OF_RANGE
    assert res.confidence <= 0.3


def test_non_silent_clamping_policy():
    """Verify large deviations are not silently clamped to arbitrary values."""
    cal = PhysicsCalibrationParameters()
    engine = ResidualEngine(cal)

    # Very large physical deviation (e.g. severe manifold leak: MAP is 50 inHg vs 29.5)
    obs = _make_frame(manifold_pressure=50.0)
    exp = _make_expected(manifold_pressure=29.5)

    res = engine.compute_residuals(obs, exp)

    # Raw residual is exactly preserved as 20.5, not clamped to e.g. 5.0
    assert abs(res.raw_residuals["manifold_pressure"] - 20.5) < 1e-4
    sigma = cal.sigma_scales["manifold_pressure"]
    assert abs(res.normalized_residuals["manifold_pressure"] - (20.5 / sigma)) < 1e-4
