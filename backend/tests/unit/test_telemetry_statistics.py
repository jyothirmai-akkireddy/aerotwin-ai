"""Unit tests for TelemetryStatistics calculation."""

from app.domain.entities.telemetry import QualityStatus, TelemetryFrame, TelemetrySource
from app.domain.telemetry.statistics import compute_telemetry_statistics


def create_frame(seq: int, ts: float, rpm: float, quality: QualityStatus) -> TelemetryFrame:
    return TelemetryFrame(
        version="1.0.0",
        timestamp=ts,
        sequence_id=seq,
        source_type=TelemetrySource.SIMULATED,
        quality_flag=quality,
        rpm=rpm,
        manifold_pressure=29.0,
        throttle_position=50.0,
        fuel_flow=15.0,
        fuel_pressure=3.0,
        injection_timing=20.0,
        cht=[90.0, 90.0, 90.0, 90.0],
        egt=[700.0, 700.0, 700.0, 700.0],
        coolant_temp=70.0,
        oil_temperature=80.0,
        oil_pressure=3.0,
        vibration_rms=1.0,
        battery_voltage=28.0,
        alternator_current=15.0,
        alternator_status="OK",
        altitude=1000.0,
        ambient_temp=15.0,
        true_airspeed=40.0,
    )


def test_empty_sequence_returns_zero_summary():
    stats = compute_telemetry_statistics([], expected_rate_hz=10.0)
    assert stats.total_samples == 0
    assert stats.valid_samples == 0
    assert stats.quality_ratio_valid == 0.0


def test_channel_statistics_mean_and_extremes():
    frames = [
        create_frame(0, 100.0, 2000.0, QualityStatus.VALID),
        create_frame(1, 100.1, 3000.0, QualityStatus.VALID),
        create_frame(2, 100.2, 4000.0, QualityStatus.VALID),
    ]

    stats = compute_telemetry_statistics(frames, expected_rate_hz=10.0)
    assert stats.total_samples == 3
    assert stats.valid_samples == 3
    assert stats.quality_ratio_valid == 1.0

    rpm_stat = stats.channels["rpm"]
    assert rpm_stat.min_value == 2000.0
    assert rpm_stat.max_value == 4000.0
    assert rpm_stat.mean == 3000.0
    assert round(rpm_stat.std_dev, 2) == 816.50  # Population std of [2000, 3000, 4000]


def test_timing_metrics_constant_rate():
    frames = [create_frame(i, 100.0 + i * 0.1, 2500.0, QualityStatus.VALID) for i in range(11)]

    stats = compute_telemetry_statistics(frames, expected_rate_hz=10.0)
    assert stats.timing.sample_count == 11
    assert stats.timing.expected_rate_hz == 10.0
    assert round(stats.timing.observed_mean_dt_sec, 4) == 0.1
    assert round(stats.timing.min_dt_sec, 4) == 0.1
    assert round(stats.timing.max_dt_sec, 4) == 0.1
    assert stats.timing.jitter_std_sec == 0.0
    assert stats.timing.dropped_sequence_count == 0


def test_quality_distribution_breakdown():
    frames = [
        create_frame(0, 100.0, 2500.0, QualityStatus.VALID),
        create_frame(1, 100.1, 2500.0, QualityStatus.DEGRADED),
        create_frame(2, 100.2, 2500.0, QualityStatus.INVALID),
        create_frame(3, 100.3, 2500.0, QualityStatus.VALID),
    ]

    stats = compute_telemetry_statistics(frames, expected_rate_hz=10.0)
    assert stats.total_samples == 4
    assert stats.valid_samples == 2
    assert stats.degraded_samples == 1
    assert stats.invalid_samples == 1
    assert stats.quality_ratio_valid == 0.5
