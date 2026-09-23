"""Statistical and data quality analysis utilities for telemetry frame sequences."""

import math

from pydantic import BaseModel, Field

from app.domain.entities.telemetry import QualityStatus, TelemetryFrame


class ChannelStatistics(BaseModel):
    """Statistical summary for a single scalar channel."""

    channel_name: str
    count: int
    min_value: float
    max_value: float
    mean: float
    std_dev: float


class TimingMetrics(BaseModel):
    """Timing and temporal jitter analysis of telemetry sequence."""

    sample_count: int
    expected_rate_hz: float
    expected_dt_sec: float
    observed_mean_dt_sec: float
    min_dt_sec: float
    max_dt_sec: float
    jitter_std_sec: float
    dropped_sequence_count: int = 0
    out_of_order_count: int = 0


class TelemetryStatistics(BaseModel):
    """Comprehensive statistical and data quality summary of a telemetry stream."""

    total_samples: int
    valid_samples: int
    degraded_samples: int
    invalid_samples: int
    missing_samples: int
    quality_ratio_valid: float = Field(..., description="Valid samples / total samples")
    timing: TimingMetrics
    channels: dict[str, ChannelStatistics] = Field(default_factory=dict)


def compute_telemetry_statistics(
    frames: list[TelemetryFrame],
    expected_rate_hz: float = 10.0,
) -> TelemetryStatistics:
    """Compute channel distributions, quality counts, and timing jitter across a sequence of frames."""
    total = len(frames)
    if total == 0:
        expected_dt = 1.0 / expected_rate_hz if expected_rate_hz > 0 else 0.1
        return TelemetryStatistics(
            total_samples=0,
            valid_samples=0,
            degraded_samples=0,
            invalid_samples=0,
            missing_samples=0,
            quality_ratio_valid=0.0,
            timing=TimingMetrics(
                sample_count=0,
                expected_rate_hz=expected_rate_hz,
                expected_dt_sec=expected_dt,
                observed_mean_dt_sec=0.0,
                min_dt_sec=0.0,
                max_dt_sec=0.0,
                jitter_std_sec=0.0,
            ),
            channels={},
        )

    # 1. Quality Distribution
    quality_counts = {
        QualityStatus.VALID: 0,
        QualityStatus.GOOD: 0,
        QualityStatus.DEGRADED: 0,
        QualityStatus.INVALID: 0,
        QualityStatus.MISSING: 0,
    }

    for f in frames:
        quality_counts[f.quality_flag] = quality_counts.get(f.quality_flag, 0) + 1

    valid_count = quality_counts.get(QualityStatus.VALID, 0) + quality_counts.get(
        QualityStatus.GOOD, 0
    )
    degraded_count = quality_counts.get(QualityStatus.DEGRADED, 0)
    invalid_count = quality_counts.get(QualityStatus.INVALID, 0)
    missing_count = quality_counts.get(QualityStatus.MISSING, 0)

    # 2. Timing and Jitter Analysis
    expected_dt = 1.0 / expected_rate_hz if expected_rate_hz > 0 else 0.1
    dts: list[float] = []
    dropped_seq = 0
    out_of_order = 0

    for i in range(1, total):
        dt = frames[i].timestamp - frames[i - 1].timestamp
        dts.append(dt)

        seq_diff = frames[i].sequence_id - frames[i - 1].sequence_id
        if seq_diff > 1:
            dropped_seq += seq_diff - 1
        elif seq_diff < 1:
            out_of_order += 1

    if dts:
        mean_dt = sum(dts) / len(dts)
        min_dt = min(dts)
        max_dt = max(dts)
        variance = sum((x - mean_dt) ** 2 for x in dts) / len(dts)
        jitter_std = math.sqrt(variance)
    else:
        mean_dt = expected_dt
        min_dt = expected_dt
        max_dt = expected_dt
        jitter_std = 0.0

    timing = TimingMetrics(
        sample_count=total,
        expected_rate_hz=expected_rate_hz,
        expected_dt_sec=expected_dt,
        observed_mean_dt_sec=round(mean_dt, 6),
        min_dt_sec=round(min_dt, 6),
        max_dt_sec=round(max_dt, 6),
        jitter_std_sec=round(jitter_std, 6),
        dropped_sequence_count=dropped_seq,
        out_of_order_count=out_of_order,
    )

    # 3. Scalar Channel Statistics
    scalar_fields = [
        "rpm",
        "manifold_pressure",
        "throttle_position",
        "fuel_flow",
        "oil_pressure",
        "oil_temperature",
        "coolant_temp",
        "vibration_rms",
        "battery_voltage",
        "altitude",
        "ambient_temp",
    ]

    channels: dict[str, ChannelStatistics] = {}
    for field_name in scalar_fields:
        vals = [
            getattr(f, field_name)
            for f in frames
            if math.isfinite(getattr(f, field_name, float("nan")))
        ]
        if vals:
            c_min = min(vals)
            c_max = max(vals)
            c_mean = sum(vals) / len(vals)
            c_var = sum((v - c_mean) ** 2 for v in vals) / len(vals)
            c_std = math.sqrt(c_var)
            channels[field_name] = ChannelStatistics(
                channel_name=field_name,
                count=len(vals),
                min_value=round(c_min, 4),
                max_value=round(c_max, 4),
                mean=round(c_mean, 4),
                std_dev=round(c_std, 4),
            )

    # 4. Multi-cylinder averages (CHT and EGT)
    cht_vals = [f.cht for f in frames if f.cht and len(f.cht) == 4]
    if cht_vals:
        for cyl in range(4):
            c_vals = [c[cyl] for c in cht_vals if math.isfinite(c[cyl])]
            if c_vals:
                c_mean = sum(c_vals) / len(c_vals)
                c_std = math.sqrt(sum((v - c_mean) ** 2 for v in c_vals) / len(c_vals))
                channels[f"cht_cyl_{cyl + 1}"] = ChannelStatistics(
                    channel_name=f"cht_cyl_{cyl + 1}",
                    count=len(c_vals),
                    min_value=round(min(c_vals), 4),
                    max_value=round(max(c_vals), 4),
                    mean=round(c_mean, 4),
                    std_dev=round(c_std, 4),
                )

    return TelemetryStatistics(
        total_samples=total,
        valid_samples=valid_count,
        degraded_samples=degraded_count,
        invalid_samples=invalid_count,
        missing_samples=missing_count,
        quality_ratio_valid=round(valid_count / total, 4) if total > 0 else 0.0,
        timing=timing,
        channels=channels,
    )
