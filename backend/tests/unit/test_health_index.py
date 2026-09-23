"""Unit tests for Health Index Calculator, 3-tier metrics, and invariant validation."""

import math

from app.domain.entities.telemetry import TelemetryFrame
from app.domain.ml.models import (
    AnomalyInferenceResult,
    AnomalyStatus,
    DecisionReason,
    FaultCategory,
    FaultInferenceResult,
    MLInferenceResult,
)
from app.domain.physics.models import PhysicsExpectedState, PhysicsResidualSet, PhysicsTwinResult
from app.domain.prognostics.health_index import HealthIndexCalculator
from app.domain.prognostics.models import DegradationState


def _make_dummy_frame(
    oil_p: float = 3.8,
    oil_t: float = 85.0,
    cht: tuple[float, float, float, float] = (95.0, 95.0, 95.0, 95.0),
    map_val: float = 29.5,
    vib: float = 1.15,
) -> TelemetryFrame:
    return TelemetryFrame(
        timestamp=100.0,
        sequence_id=1,
        source_type="SIMULATED",
        quality_flag="VALID",
        rpm=2400.0,
        manifold_pressure=map_val,
        throttle_position=45.0,
        fuel_flow=16.5,
        fuel_pressure=3.0,
        injection_timing=15.0,
        cht=cht,
        egt=(720.0, 720.0, 720.0, 720.0),
        coolant_temp=82.0,
        oil_temperature=oil_t,
        oil_pressure=oil_p,
        vibration_rms=vib,
        battery_voltage=28.2,
        alternator_current=14.0,
        alternator_status="OK",
        altitude=1500.0,
        ambient_temp=15.0,
        true_airspeed=45.0,
    )


def _make_dummy_physics(
    exp_oil_p: float = 3.8,
    exp_oil_t: float = 85.0,
    exp_cht: tuple[float, float, float, float] = (95.0, 95.0, 95.0, 95.0),
    exp_map: float = 29.5,
    exp_vib: float = 1.15,
) -> PhysicsTwinResult:
    expected = PhysicsExpectedState(
        timestamp=100.0,
        sequence_id=1,
        rpm=2400.0,
        manifold_pressure=exp_map,
        air_mass_flow=0.085,
        fuel_flow=16.5,
        cht=exp_cht,
        egt=(720.0, 720.0, 720.0, 720.0),
        coolant_temp=82.0,
        oil_temperature=exp_oil_t,
        oil_pressure=exp_oil_p,
        vibration_rms=exp_vib,
        validity="VALID",
        confidence=0.95,
        model_version="1.0.0",
    )
    residuals = PhysicsResidualSet(
        timestamp=100.0,
        sequence_id=1,
        raw_residuals={},
        normalized_residuals={},
        cht_max_imbalance_celsius=0.0,
        egt_max_imbalance_celsius=0.0,
        mean_absolute_normalized_residual=0.0,
        validity="VALID",
        confidence=0.95,
    )
    return PhysicsTwinResult(expected_state=expected, residuals=residuals)


def test_zero_residuals_invariant():
    """Verify the invariant: If all physical residuals are zero and no anomaly, HI == 1.0 unconditionally."""
    calc = HealthIndexCalculator()
    frame = _make_dummy_frame()
    physics = _make_dummy_physics()

    hi, state, subsystems, validity = calc.calculate(frame, physics, ml=None)

    assert hi == 1.0
    assert state == DegradationState.NOMINAL
    assert validity == "VALID"
    assert subsystems.lubrication.raw_deviation == 0.0
    assert subsystems.lubrication.normalized_deviation == 0.0
    assert subsystems.lubrication.bounded_penalty == 0.0
    assert subsystems.thermal.bounded_penalty == 0.0
    assert subsystems.turbocharger.bounded_penalty == 0.0
    assert subsystems.rotational_vibration.bounded_penalty == 0.0
    assert subsystems.anomaly_penalty == 0.0
    assert subsystems.limiting_subsystem == "nominal"


def test_3tier_metrics_preservation():
    """Verify that raw, normalized, and bounded degradation metrics are preserved without loss."""
    calc = HealthIndexCalculator(sigma_oil_p=0.25)
    # Deviation of 1.5 bar on oil pressure -> 6.0 sigma
    frame = _make_dummy_frame(oil_p=2.3)  # exp = 3.8, delta = 1.5
    physics = _make_dummy_physics(exp_oil_p=3.8)

    hi, state, subsystems, _ = calc.calculate(frame, physics, ml=None)

    # Raw deviation should reflect 1.5 bar
    assert abs(subsystems.lubrication.raw_deviation - 1.5) < 0.01
    # Normalized deviation should reflect 6.0 * 0.60 = 3.6 sigma
    assert subsystems.lubrication.normalized_deviation > 3.0
    # Bounded penalty must be clamped to 1.0
    assert subsystems.lubrication.bounded_penalty == 1.0
    # Subsystem health pct should be 0.0
    assert subsystems.lubrication_health_pct == 0.0
    # Composite HI must drop
    assert hi < 1.0


def test_threshold_gated_anomaly_penalty():
    """Verify that anomaly scores below tau_anom produce zero penalty (resolving contradiction)."""
    calc = HealthIndexCalculator(tau_anom=0.5402)
    frame = _make_dummy_frame()
    physics = _make_dummy_physics()

    # Case 1: Nominal anomaly score below threshold
    ml_normal = MLInferenceResult(
        timestamp=100.0,
        sequence_id=1,
        anomaly=AnomalyInferenceResult(
            flag=False,
            status=AnomalyStatus.NORMAL,
            score=0.45,  # <= 0.5402
            raw_score=-0.09,
            confidence=0.90,
        ),
        fault=FaultInferenceResult(
            fault_class=FaultCategory.NORMAL,
            reason=DecisionReason.NOMINAL_FLIGHT,
            confidence=0.92,
        ),
        inference_latency_ms=2.0,
    )

    hi_normal, _, subsystems_normal, _ = calc.calculate(frame, physics, ml=ml_normal)
    assert subsystems_normal.anomaly_penalty == 0.0
    assert hi_normal == 1.0  # Zero-residuals invariant preserved!

    # Case 2: Verified anomaly score above threshold
    ml_anom = MLInferenceResult(
        timestamp=100.0,
        sequence_id=1,
        anomaly=AnomalyInferenceResult(
            flag=True,
            status=AnomalyStatus.ANOMALOUS,
            score=0.85,  # > 0.5402
            raw_score=0.31,
            confidence=0.95,
        ),
        fault=FaultInferenceResult(
            fault_class=FaultCategory.NORMAL,
            reason=DecisionReason.CONFIDENT_MATCH,
            confidence=0.88,
        ),
        inference_latency_ms=2.0,
    )

    hi_anom, _, subsystems_anom, _ = calc.calculate(frame, physics, ml=ml_anom)
    assert subsystems_anom.anomaly_penalty > 0.0
    assert hi_anom < 1.0


def test_monotonicity():
    """Verify that increasing physical deviations strictly decreases or maintains Health Index."""
    calc = HealthIndexCalculator()
    physics = _make_dummy_physics()

    deltas = [0.0, 0.2, 0.5, 1.0, 1.5, 2.0]
    his = []

    for d in deltas:
        frame = _make_dummy_frame(oil_p=3.8 - d)
        hi, _, _, _ = calc.calculate(frame, physics, ml=None)
        his.append(hi)

    # Invariant: Each subsequent HI must be <= previous HI
    for i in range(1, len(his)):
        assert his[i] <= his[i - 1], f"Monotonicity violation at step {i}: {his[i]} > {his[i - 1]}"


def test_non_finite_robustness():
    """Verify non-finite telemetry (NaN/Inf) does not crash and marks validity as DEGRADED."""
    calc = HealthIndexCalculator()
    frame = TelemetryFrame.model_construct(
        timestamp=100.0,
        sequence_id=1,
        source_type="SIMULATED",
        quality_flag="VALID",
        rpm=2400.0,
        manifold_pressure=29.5,
        throttle_position=45.0,
        fuel_flow=16.5,
        fuel_pressure=3.0,
        injection_timing=15.0,
        cht=(95.0, 95.0, 95.0, 95.0),
        egt=(720.0, 720.0, 720.0, 720.0),
        coolant_temp=82.0,
        oil_temperature=85.0,
        oil_pressure=float("nan"),
        vibration_rms=float("inf"),
        battery_voltage=28.2,
        alternator_current=14.0,
        alternator_status="OK",
        altitude=1500.0,
        ambient_temp=15.0,
        true_airspeed=45.0,
    )
    physics = _make_dummy_physics()

    hi, state, subsystems, validity = calc.calculate(frame, physics, ml=None)

    assert math.isfinite(hi)
    assert 0.0 <= hi <= 1.0
    assert validity == "DEGRADED"
