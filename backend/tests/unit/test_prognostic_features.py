"""Unit tests for causal telemetry buffer, trend regression, and prognostic indicators."""

from app.domain.prognostics.features import (
    CausalTelemetryBuffer,
    PrognosticFeatureExtractor,
)
from app.domain.prognostics.models import TrendDirection


def test_causal_buffer_fifo():
    """Verify sliding buffer maintains FIFO semantics and does not exceed capacity."""
    buffer = CausalTelemetryBuffer(max_capacity=5)
    for i in range(10):
        buffer.append({"timestamp": float(i), "health_index": 1.0 - i * 0.05})

    assert buffer.size == 5
    history = buffer.get_history()
    assert len(history) == 5
    # Oldest retained element should be timestamp 5
    assert history[0]["timestamp"] == 5.0
    assert history[-1]["timestamp"] == 9.0


def test_temporal_leakage_gate():
    """Verify that buffer strictly yields historical observations without future leakage."""
    buffer = CausalTelemetryBuffer(max_capacity=100)
    for i in range(35):
        buffer.append({"timestamp": float(i), "health_index": 1.0 - i * 0.01})

    history = buffer.get_history()
    # Timestamps must be strictly non-decreasing
    for j in range(1, len(history)):
        assert history[j]["timestamp"] > history[j - 1]["timestamp"]


def test_trend_slope_calculation():
    """Verify OLS regression correctly categorizes DEGRADING, IMPROVING, and STABLE trends."""
    extractor = PrognosticFeatureExtractor(epsilon_trend=1.0e-4)

    # 1. Degrading trend (HI drops from 1.0 to 0.70 over 30 seconds -> slope ~ -0.01)
    degrading_hist = [{"timestamp": float(i), "health_index": 1.0 - i * 0.01} for i in range(35)]
    slope_deg, dir_deg = extractor.compute_trend_slope(degrading_hist)
    assert slope_deg < -1.0e-4
    assert dir_deg == TrendDirection.DEGRADING

    # 2. Improving trend (HI rises from 0.70 to 0.85 over 30 seconds -> slope ~ +0.005)
    improving_hist = [{"timestamp": float(i), "health_index": 0.70 + i * 0.005} for i in range(35)]
    slope_imp, dir_imp = extractor.compute_trend_slope(improving_hist)
    assert slope_imp > 1.0e-4
    assert dir_imp == TrendDirection.IMPROVING

    # 3. Stable trend (HI constant at 0.95 -> slope 0.0)
    stable_hist = [{"timestamp": float(i), "health_index": 0.95} for i in range(35)]
    slope_stab, dir_stab = extractor.compute_trend_slope(stable_hist)
    assert abs(slope_stab) <= 1.0e-4
    assert dir_stab == TrendDirection.STABLE

    # 4. Insufficient history (< 30 frames)
    short_hist = [{"timestamp": float(i), "health_index": 0.90} for i in range(15)]
    slope_short, dir_short = extractor.compute_trend_slope(short_hist)
    assert dir_short == TrendDirection.UNKNOWN


def test_stress_accumulators():
    """Verify mechanical, thermal, and load stress integrals accumulate appropriately."""
    extractor = PrognosticFeatureExtractor()

    # Create history with severe thermal excursion (> 120 °C)
    history = [
        {"timestamp": float(i), "cht_mean": 130.0, "manifold_pressure": 40.0, "vibration_rms": 3.0}
        for i in range(10)
    ]
    thermal_acc, map_acc, vib_acc = extractor.compute_stress_accumulators(history)

    assert thermal_acc > 0.0  # (130 - 120) * 9 = 90
    assert map_acc > 0.0  # (40 - 35) * 9 = 45
    assert vib_acc > 0.0  # (3.0 - 2.0) * 9 = 9
