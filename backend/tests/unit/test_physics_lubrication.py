"""Unit tests for the Lubrication Oil Model."""

from app.domain.physics.lubrication import LubricationOilModel
from app.domain.physics.models import ModelValidity, PhysicsCalibrationParameters


def test_lubrication_pressure_and_temperature():
    """Verify positive-displacement pump curve and viscosity temperature effect."""
    cal = PhysicsCalibrationParameters()
    model = LubricationOilModel(cal)

    # Cold start (20°C oil) -> thick oil, strong pressure
    p_cold, t_cold, val_cold, _ = model.evaluate(
        rpm=2400.0,
        oil_temperature_c=20.0,
        ambient_temp_c=15.0,
        dt_seconds=0.1,
    )
    assert val_cold == ModelValidity.VALID
    assert p_cold > 3.0

    # Hot oil (110°C oil) -> viscosity thinning lowers gallery pressure
    p_hot, t_hot, val_hot, _ = model.evaluate(
        rpm=2400.0,
        oil_temperature_c=110.0,
        ambient_temp_c=15.0,
        dt_seconds=0.1,
    )
    assert val_hot == ModelValidity.VALID
    assert p_hot < p_cold


def test_lubrication_engine_off():
    """Verify zero oil pressure when engine is stopped."""
    cal = PhysicsCalibrationParameters()
    model = LubricationOilModel(cal)

    p_off, _, val_off, _ = model.evaluate(
        rpm=0.0,
        oil_temperature_c=25.0,
        ambient_temp_c=25.0,
        dt_seconds=0.1,
    )
    assert p_off == 0.0
    assert val_off == ModelValidity.DEGRADED
