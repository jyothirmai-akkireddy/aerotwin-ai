"""Unit tests for RUL estimation, 4-stage gating policy, and prediction intervals."""

from app.domain.prognostics.models import (
    RULStatus,
    SubsystemDegradation,
    SubsystemDegradationMetric,
    TrendDirection,
)
from app.domain.prognostics.rul_model import RULEstimator


def _make_dummy_subsystems(limiting: str = "lubrication") -> SubsystemDegradation:
    metric = SubsystemDegradationMetric(
        raw_deviation=1.0,
        normalized_deviation=2.5,
        bounded_penalty=0.8,
        unit="bar",
    )
    return SubsystemDegradation(
        lubrication=metric,
        thermal=metric,
        turbocharger=metric,
        rotational_vibration=metric,
        anomaly_penalty=0.0,
        lubrication_health_pct=20.0,
        thermal_health_pct=20.0,
        turbocharger_health_pct=20.0,
        rotational_health_pct=20.0,
        limiting_subsystem=limiting,
    )


def test_insufficient_history_gate():
    """Verify that fewer than 30 frames returns INSUFFICIENT_HISTORY and None hours."""
    estimator = RULEstimator()
    subsystems = _make_dummy_subsystems()

    res = estimator.estimate(
        health_index=0.80,
        beta_slope=-0.005,
        trend_dir=TrendDirection.DEGRADING,
        subsystems=subsystems,
        buffer_size=15,  # < 30
        history=[{"timestamp": float(i), "health_index": 0.8} for i in range(15)],
    )

    assert res.status == RULStatus.INSUFFICIENT_HISTORY
    assert res.estimated_remaining_flight_hours is None
    assert res.confidence_interval_95 is None
    assert res.confidence == 0.0


def test_degradation_not_detected_gate():
    """Verify that nominal engine (HI >= 0.90, STABLE) returns DEGRADATION_NOT_DETECTED and None hours."""
    estimator = RULEstimator()
    subsystems = _make_dummy_subsystems(limiting="nominal")
    history = [{"timestamp": float(i), "health_index": 0.95} for i in range(40)]

    res = estimator.estimate(
        health_index=0.95,
        beta_slope=0.0,
        trend_dir=TrendDirection.STABLE,
        subsystems=subsystems,
        buffer_size=40,
        history=history,
    )

    assert res.status == RULStatus.DEGRADATION_NOT_DETECTED
    assert res.estimated_remaining_flight_hours is None
    assert res.confidence_interval_95 is None


def test_rul_unavailable_gate():
    """Verify that invalid or non-finite inputs return RUL_UNAVAILABLE and None hours."""
    estimator = RULEstimator()
    subsystems = _make_dummy_subsystems()
    history = [{"timestamp": float(i), "health_index": 0.50} for i in range(40)]

    res = estimator.estimate(
        health_index=float("nan"),
        beta_slope=-0.01,
        trend_dir=TrendDirection.DEGRADING,
        subsystems=subsystems,
        buffer_size=40,
        history=history,
        validity="INVALID",
    )

    assert res.status == RULStatus.RUL_UNAVAILABLE
    assert res.estimated_remaining_flight_hours is None
    assert res.confidence_interval_95 is None


def test_active_degradation_interval_ordering():
    """Verify that active degradation returns ACTIVE status with lower <= point_est <= upper bounds."""
    estimator = RULEstimator()
    subsystems = _make_dummy_subsystems(limiting="lubrication")
    history = [{"timestamp": float(i), "health_index": 0.80 - i * 0.002} for i in range(50)]

    res = estimator.estimate(
        health_index=0.70,
        beta_slope=-0.002,
        trend_dir=TrendDirection.DEGRADING,
        subsystems=subsystems,
        buffer_size=50,
        history=history,
    )

    assert res.status == RULStatus.ACTIVE
    assert res.estimated_remaining_flight_hours is not None
    assert res.confidence_interval_95 is not None

    point_est = res.estimated_remaining_flight_hours
    lower, upper = res.confidence_interval_95

    # Strict ordering requirement
    assert 0.0 < lower <= point_est <= upper
    assert 0.0 <= res.confidence <= 1.0
    assert res.limiting_subsystem == "lubrication"
    assert res.degradation_rate_per_hour is not None
