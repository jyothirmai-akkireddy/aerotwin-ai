"""Unit tests for mission profile curves (CONSTANT, STEP, LINEAR_RAMP, SMOOTH_RAMP)."""

import pytest

from app.domain.mission.enums import ProfileTransitionType
from app.domain.mission.profiles import ProfileCurve


def test_constant_profile():
    curve = ProfileCurve.constant(value=45.0, duration_sec=10.0)
    assert curve.transition_type == ProfileTransitionType.CONSTANT
    assert curve.evaluate(-1.0) == 45.0
    assert curve.evaluate(0.0) == 45.0
    assert curve.evaluate(5.0) == 45.0
    assert curve.evaluate(10.0) == 45.0
    assert curve.evaluate(20.0) == 45.0


def test_step_profile():
    curve = ProfileCurve.step(start=20.0, end=90.0, step_time_sec=4.0, duration_sec=10.0)
    assert curve.transition_type == ProfileTransitionType.STEP
    assert curve.evaluate(0.0) == 20.0
    assert curve.evaluate(3.99) == 20.0
    assert curve.evaluate(4.0) == 90.0
    assert curve.evaluate(8.0) == 90.0
    assert curve.evaluate(12.0) == 90.0


def test_linear_ramp_profile():
    curve = ProfileCurve.linear(start=10.0, end=50.0, duration_sec=10.0)
    assert curve.transition_type == ProfileTransitionType.LINEAR_RAMP
    assert curve.evaluate(-5.0) == 10.0
    assert curve.evaluate(0.0) == 10.0
    assert curve.evaluate(2.5) == 20.0
    assert curve.evaluate(5.0) == 30.0
    assert curve.evaluate(7.5) == 40.0
    assert curve.evaluate(10.0) == 50.0
    assert curve.evaluate(15.0) == 50.0


def test_smooth_ramp_cubic_hermite_smoothstep():
    curve = ProfileCurve.smooth(start=100.0, end=200.0, duration_sec=20.0)
    assert curve.transition_type == ProfileTransitionType.SMOOTH_RAMP

    # Boundary values: S(0) = 0, S(1) = 1
    assert curve.evaluate(0.0) == 100.0
    assert curve.evaluate(20.0) == 200.0

    # Boundary derivative verification: dS/dtau = 6*tau*(1-tau) -> 0 at tau=0 and tau=1
    # Check that slope near start and end is extremely gentle (derivative approaches zero)
    delta_t = 0.01
    start_slope = (curve.evaluate(delta_t) - curve.evaluate(0.0)) / delta_t
    end_slope = (curve.evaluate(20.0) - curve.evaluate(20.0 - delta_t)) / delta_t
    assert abs(start_slope) < 0.2
    assert abs(end_slope) < 0.2

    # Midpoint: S(0.5) = 3*(0.25) - 2*(0.125) = 0.75 - 0.25 = 0.5
    assert curve.evaluate(10.0) == 150.0

    # Monotonicity test across 100 samples (zero overshoot, zero reversal)
    prev = 100.0
    for i in range(101):
        t = (i / 100.0) * 20.0
        val = curve.evaluate(t)
        assert 100.0 <= val <= 200.0
        assert val >= prev, f"Monotonicity violated at t={t}: {val} < {prev}"
        prev = val


def test_profile_curve_validation():
    # Negative duration must raise ValueError
    with pytest.raises(ValueError):
        ProfileCurve(
            transition_type=ProfileTransitionType.CONSTANT,
            start_value=10.0,
            end_value=10.0,
            duration_sec=-5.0,
        )

    # step_time exceeding duration must raise ValueError
    with pytest.raises(ValueError):
        ProfileCurve(
            transition_type=ProfileTransitionType.STEP,
            start_value=10.0,
            end_value=20.0,
            step_time_sec=15.0,
            duration_sec=10.0,
        )

    # Non-finite values must raise ValueError
    with pytest.raises(ValueError):
        ProfileCurve(
            transition_type=ProfileTransitionType.LINEAR_RAMP,
            start_value=float("inf"),
            end_value=20.0,
            duration_sec=10.0,
        )
