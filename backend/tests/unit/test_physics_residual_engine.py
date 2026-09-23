"""Unit tests for the ResidualEngine validating directional invariants and normalization."""

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
    """Helper to build TelemetryFrame with sensible defaults."""
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
    """Helper to build PhysicsExpectedState matching default frame."""
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


def test_residual_zero_invariant_when_identical():
    """Verify observed == expected yields exactly zero residual across all channels."""
    cal = PhysicsCalibrationParameters()
    engine = ResidualEngine(cal)

    obs = _make_frame()
    exp = _make_expected()

    res = engine.compute_residuals(obs, exp)

    assert res.validity == ModelValidity.VALID
    assert res.raw_residuals["rpm"] == 0.0
    assert res.raw_residuals["manifold_pressure"] == 0.0
    assert res.raw_residuals["fuel_flow"] == 0.0
    assert res.raw_residuals["cht"] == [0.0, 0.0, 0.0, 0.0]
    assert res.raw_residuals["egt"] == [0.0, 0.0, 0.0, 0.0]
    assert res.raw_residuals["oil_pressure"] == 0.0
    assert res.raw_residuals["oil_temperature"] == 0.0
    assert res.raw_residuals["vibration_rms"] == 0.0
    assert res.mean_absolute_normalized_residual == 0.0


def test_residual_directionality_invariants():
    """Verify observed > expected -> positive residual; observed < expected -> negative residual."""
    cal = PhysicsCalibrationParameters()
    engine = ResidualEngine(cal)

    # Positive deviation
    obs_pos = _make_frame(manifold_pressure=32.0, fuel_flow=18.0)
    exp_pos = _make_expected(manifold_pressure=29.5, fuel_flow=16.5)
    res_pos = engine.compute_residuals(obs_pos, exp_pos)

    assert res_pos.raw_residuals["manifold_pressure"] > 0.0
    assert res_pos.raw_residuals["fuel_flow"] > 0.0
    assert res_pos.normalized_residuals["manifold_pressure"] > 0.0
    assert res_pos.normalized_residuals["fuel_flow"] > 0.0

    # Negative deviation
    obs_neg = _make_frame(manifold_pressure=27.0, fuel_flow=15.0)
    exp_neg = _make_expected(manifold_pressure=29.5, fuel_flow=16.5)
    res_neg = engine.compute_residuals(obs_neg, exp_neg)

    assert res_neg.raw_residuals["manifold_pressure"] < 0.0
    assert res_neg.raw_residuals["fuel_flow"] < 0.0
    assert res_neg.normalized_residuals["manifold_pressure"] < 0.0
    assert res_neg.normalized_residuals["fuel_flow"] < 0.0


def test_residual_normalization_scaling():
    """Verify normalized residuals equal raw residual divided by empirical sigma."""
    cal = PhysicsCalibrationParameters()
    engine = ResidualEngine(cal)

    sigma_map = cal.sigma_scales["manifold_pressure"]
    obs = _make_frame(manifold_pressure=29.5 + 2 * sigma_map)
    exp = _make_expected(manifold_pressure=29.5)

    res = engine.compute_residuals(obs, exp)

    # Normalized deviation should equal approximately 2.0 sigma
    norm_val = res.normalized_residuals["manifold_pressure"]
    assert abs(norm_val - 2.0) < 1e-4


def test_cylinder_spread_imbalance():
    """Verify CHT and EGT multi-cylinder spread computation."""
    cal = PhysicsCalibrationParameters()
    engine = ResidualEngine(cal)

    obs = _make_frame(
        cht=[90.0, 92.0, 105.0, 91.0],  # Spread: 105 - 90 = 15°C
        egt=[710.0, 740.0, 725.0, 715.0],  # Spread: 740 - 710 = 30°C
    )
    exp = _make_expected()

    res = engine.compute_residuals(obs, exp)
    assert res.cht_max_imbalance_celsius == 15.0
    assert res.egt_max_imbalance_celsius == 30.0
