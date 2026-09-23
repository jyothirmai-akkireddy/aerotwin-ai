"""Unit tests for the Vibration Baseline Model."""

from app.domain.physics.models import ModelValidity, PhysicsCalibrationParameters
from app.domain.physics.vibration import VibrationBaselineModel


def test_vibration_baseline_speed_dependence():
    """Verify quadratic harmonic scaling with engine RPM."""
    cal = PhysicsCalibrationParameters()
    model = VibrationBaselineModel(cal)

    # Idle RPM
    vib_idle, val_idle, _ = model.evaluate(rpm=1400.0, manifold_pressure_inhg=12.0)
    assert val_idle == ModelValidity.VALID
    assert 0.4 < vib_idle < 1.5

    # High RPM
    vib_high, val_high, _ = model.evaluate(rpm=5500.0, manifold_pressure_inhg=35.0)
    assert val_high == ModelValidity.VALID
    assert vib_high > vib_idle


def test_vibration_engine_off():
    """Verify engine stopped produces near zero vibration baseline."""
    cal = PhysicsCalibrationParameters()
    model = VibrationBaselineModel(cal)

    vib_off, val_off, _ = model.evaluate(rpm=0.0, manifold_pressure_inhg=29.92)
    assert vib_off == 0.05
    assert val_off == ModelValidity.DEGRADED
