"""Unit tests for the Induction Pressure Model (MAP and air mass flow)."""

import math

from app.domain.physics.induction import InductionPressureModel
from app.domain.physics.models import ModelValidity, PhysicsCalibrationParameters


def test_isa_pressure_calculation():
    """Verify standard sea level barometric pressure and atmospheric lapse."""
    cal = PhysicsCalibrationParameters()
    model = InductionPressureModel(cal)

    # Sea level ISA is ~29.92 inHg
    p_sl = model.compute_isa_pressure_inhg(0.0)
    assert abs(p_sl - 29.921) < 0.01

    # Pressure decreases with altitude in troposphere
    p_3000m = model.compute_isa_pressure_inhg(3000.0)
    assert p_3000m < p_sl
    assert 20.0 < p_3000m < 22.0

    # Non-finite input falls back safely
    p_inf = model.compute_isa_pressure_inhg(math.nan)
    assert p_inf == 29.921


def test_induction_throttle_and_boost_response():
    """Verify throttle opening and spool RPM increase manifold pressure."""
    cal = PhysicsCalibrationParameters()
    model = InductionPressureModel(cal)

    # Idle at sea level -> low MAP due to closed throttle plate
    p_idle, flow_idle, val_idle, _ = model.evaluate(
        throttle_pct=0.0, rpm=1400.0, altitude_m=0.0, ambient_temp_c=15.0
    )
    assert val_idle == ModelValidity.VALID
    assert 10.0 <= p_idle <= 15.0
    assert flow_idle > 0.0

    # Wide Open Throttle (WOT) at cruise RPM -> boosted MAP
    p_cruise, flow_cruise, val_cruise, _ = model.evaluate(
        throttle_pct=100.0, rpm=5000.0, altitude_m=0.0, ambient_temp_c=15.0
    )
    assert val_cruise == ModelValidity.VALID
    assert p_cruise > p_idle
    assert p_cruise > 29.92  # Turbo boost active above spool RPM
    assert flow_cruise > flow_idle


def test_induction_out_of_range_and_invalid():
    """Verify out-of-envelope environmental conditions and NaN inputs."""
    cal = PhysicsCalibrationParameters()
    model = InductionPressureModel(cal)

    # Extreme altitude -> ModelValidity.OUT_OF_RANGE
    _, _, val_alt, _ = model.evaluate(
        throttle_pct=50.0, rpm=2400.0, altitude_m=15000.0, ambient_temp_c=15.0
    )
    assert val_alt == ModelValidity.OUT_OF_RANGE

    # NaN input -> ModelValidity.INVALID
    _, _, val_nan, err = model.evaluate(
        throttle_pct=math.nan, rpm=2400.0, altitude_m=0.0, ambient_temp_c=15.0
    )
    assert val_nan == ModelValidity.INVALID
    assert err is not None
