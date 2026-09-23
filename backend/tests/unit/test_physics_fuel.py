"""Unit tests for the Fuel Delivery Model."""

import math

from app.domain.physics.fuel import FuelDeliveryModel
from app.domain.physics.models import ModelValidity, PhysicsCalibrationParameters


def test_fuel_delivery_nominal():
    """Verify fuel flow calculation scales with air flow and enrichment."""
    cal = PhysicsCalibrationParameters()
    model = FuelDeliveryModel(cal)

    # Moderate cruise operating point
    ff_cruise, val_cruise, _ = model.evaluate(
        air_mass_flow_kg_h=180.0, rpm=2400.0, throttle_pct=50.0
    )
    assert val_cruise == ModelValidity.VALID
    assert 14.0 < ff_cruise < 20.0

    # High power enrichment (throttle > 75%) results in richer AFR and higher fuel flow
    ff_wot, val_wot, _ = model.evaluate(air_mass_flow_kg_h=180.0, rpm=2400.0, throttle_pct=100.0)
    assert val_wot == ModelValidity.VALID
    assert ff_wot > ff_cruise


def test_fuel_delivery_engine_off_and_invalid():
    """Verify engine stop and non-finite input handling."""
    cal = PhysicsCalibrationParameters()
    model = FuelDeliveryModel(cal)

    # Engine off (RPM < 100) -> 0.0 flow, DEGRADED
    ff_off, val_off, _ = model.evaluate(air_mass_flow_kg_h=0.0, rpm=0.0, throttle_pct=0.0)
    assert ff_off == 0.0
    assert val_off == ModelValidity.DEGRADED

    # Inf input -> INVALID
    ff_inf, val_inf, err = model.evaluate(
        air_mass_flow_kg_h=math.inf, rpm=2400.0, throttle_pct=50.0
    )
    assert ff_inf == 0.0
    assert val_inf == ModelValidity.INVALID
    assert err is not None
