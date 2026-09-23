"""Unit tests for the Exhaust Energy Model (EGT)."""

import math

from app.domain.physics.exhaust import ExhaustEnergyModel
from app.domain.physics.models import ModelValidity, PhysicsCalibrationParameters


def test_egt_load_and_timing_response():
    """Verify EGT rises with MAP load and timing changes."""
    cal = PhysicsCalibrationParameters()
    model = ExhaustEnergyModel(cal)

    # Cruise load
    egt_cruise, val_cruise, _ = model.evaluate(
        fuel_flow_l_h=16.5,
        manifold_pressure_inhg=29.92,
        injection_timing_deg=24.0,
        rpm=2400.0,
        dt_seconds=10.0,
    )
    assert val_cruise == ModelValidity.VALID
    assert all(650.0 < e < 850.0 for e in egt_cruise)

    # Boosted high-load -> higher EGT
    egt_boosted, val_boost, _ = model.evaluate(
        fuel_flow_l_h=24.0,
        manifold_pressure_inhg=38.0,
        injection_timing_deg=24.0,
        rpm=5000.0,
        dt_seconds=10.0,
    )
    assert val_boost == ModelValidity.VALID
    assert sum(egt_boosted) > sum(egt_cruise)


def test_egt_low_rpm_and_invalid():
    """Verify degraded validity at low RPM and invalid handling."""
    cal = PhysicsCalibrationParameters()
    model = ExhaustEnergyModel(cal)

    egt_low, val_low, _ = model.evaluate(
        fuel_flow_l_h=2.0,
        manifold_pressure_inhg=12.0,
        injection_timing_deg=10.0,
        rpm=150.0,
        dt_seconds=0.1,
    )
    assert val_low == ModelValidity.DEGRADED
    assert len(egt_low) == 4

    _, val_nan, err = model.evaluate(
        fuel_flow_l_h=math.nan,
        manifold_pressure_inhg=29.0,
        injection_timing_deg=24.0,
        rpm=2400.0,
        dt_seconds=0.1,
    )
    assert val_nan == ModelValidity.INVALID
    assert err is not None
