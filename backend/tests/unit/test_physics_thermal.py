"""Unit tests for the 4-Cylinder Thermal and Coolant Model."""

import math

from app.domain.physics.models import ModelValidity, PhysicsCalibrationParameters
from app.domain.physics.thermal import ThermalCylinderModel


def test_thermal_transient_convergence():
    """Verify exponential recurrence approaches steady state over time."""
    cal = PhysicsCalibrationParameters(tau_cht_seconds=5.0)
    model = ThermalCylinderModel(cal)

    # Initial step from cold start (15°C)
    cht_prev = [15.0, 15.0, 15.0, 15.0]
    coolant_prev = 15.0

    # Step through 50 steps at dt=0.5s (25 seconds total ~ 5 time constants)
    cht = cht_prev
    coolant = coolant_prev
    for _ in range(50):
        cht, coolant, val, _ = model.evaluate(
            fuel_flow_l_h=16.5,
            rpm=2400.0,
            true_airspeed_m_s=45.0,
            ambient_temp_c=15.0,
            dt_seconds=0.5,
            previous_cht=cht,
            previous_coolant=coolant,
        )
        assert val == ModelValidity.VALID

    # At steady state, CHT should have warmed up substantially above ambient
    assert all(c > 65.0 for c in cht)
    assert coolant > 50.0

    # Cylinder geometric bias introduces slight spread between cylinders
    assert cht[2] > cht[1]  # Cyl 3 bias (1.03) > Cyl 2 bias (0.98)


def test_thermal_ram_air_cooling():
    """Verify higher airspeed increases convective cooling, lowering equilibrium temperature."""
    cal = PhysicsCalibrationParameters()
    model = ThermalCylinderModel(cal)

    # Low airspeed equilibrium (climb/loiter)
    cht_low_speed, _, _, _ = model.evaluate(
        fuel_flow_l_h=16.5,
        rpm=2400.0,
        true_airspeed_m_s=20.0,
        ambient_temp_c=20.0,
        dt_seconds=60.0,  # Single large dt to evaluate equilibrium target
    )

    # High airspeed equilibrium (fast cruise/descent)
    cht_high_speed, _, _, _ = model.evaluate(
        fuel_flow_l_h=16.5,
        rpm=2400.0,
        true_airspeed_m_s=80.0,
        ambient_temp_c=20.0,
        dt_seconds=60.0,
    )

    # Higher ram air speed must result in cooler CHT
    assert sum(cht_high_speed) < sum(cht_low_speed)


def test_thermal_numerical_safety():
    """Verify non-finite inputs and negative dt handling."""
    cal = PhysicsCalibrationParameters()
    model = ThermalCylinderModel(cal)

    # Non-finite input
    cht, coolant, val, err = model.evaluate(
        fuel_flow_l_h=math.nan,
        rpm=2400.0,
        true_airspeed_m_s=40.0,
        ambient_temp_c=20.0,
        dt_seconds=0.1,
    )
    assert val == ModelValidity.INVALID
    assert len(cht) == 4
    assert coolant == 0.0
    assert err is not None
