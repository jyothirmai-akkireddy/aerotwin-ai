"""Rigorous frame-by-frame determinism proof comparing simulated telemetry sequences."""

import math

from app.application.services.mission_simulator import MissionSimulator
from app.domain.mission.catalog import THROTTLE_DYNAMICS_BENCHMARK


def test_frame_by_frame_determinism_identical_seed():
    """Verify that two simulation runs with identical mission, config, and seed produce identical frames."""
    mission = THROTTLE_DYNAMICS_BENCHMARK
    rate_hz = 10
    seed = 12345

    sim1 = MissionSimulator(mission=mission, telemetry_rate_hz=rate_hz, seed=seed)
    summary1, frames1 = sim1.run_sync()

    sim2 = MissionSimulator(mission=mission, telemetry_rate_hz=rate_hz, seed=seed)
    summary2, frames2 = sim2.run_sync()

    # 1. Total frame counts must be identical
    assert len(frames1) == len(frames2), f"Frame count mismatch: {len(frames1)} vs {len(frames2)}"
    assert summary1.total_frames == summary2.total_frames
    assert summary1.total_duration_sec == summary2.total_duration_sec

    # 2. Strict Frame-by-Frame comparison
    tolerance = 1e-6
    mismatched_frames = 0
    max_abs_diff = 0.0
    abs_diffs: list[float] = []
    first_mismatch_info = None

    scalar_fields = [
        "rpm",
        "manifold_pressure",
        "throttle_position",
        "fuel_flow",
        "fuel_pressure",
        "injection_timing",
        "coolant_temp",
        "oil_temperature",
        "oil_pressure",
        "vibration_rms",
        "battery_voltage",
        "alternator_current",
        "altitude",
        "ambient_temp",
        "true_airspeed",
    ]

    for idx, (f1, f2) in enumerate(zip(frames1, frames2, strict=True)):
        # Exact discrete equality
        assert f1.sequence_id == f2.sequence_id, f"Sequence ID mismatch at index {idx}"
        assert f1.quality_flag == f2.quality_flag, f"Quality flag mismatch at index {idx}"
        assert f1.alternator_status == f2.alternator_status, (
            f"Alternator status mismatch at index {idx}"
        )
        assert math.isclose(f1.timestamp, f2.timestamp, abs_tol=tolerance), (
            f"Timestamp mismatch at index {idx}"
        )

        frame_had_diff = False

        # Compare scalar channels
        for field in scalar_fields:
            v1 = getattr(f1, field)
            v2 = getattr(f2, field)
            diff = abs(v1 - v2)
            abs_diffs.append(diff)
            if diff > max_abs_diff:
                max_abs_diff = diff
            if diff > tolerance:
                frame_had_diff = True
                if first_mismatch_info is None:
                    first_mismatch_info = (idx, field, v1, v2, diff)

        # Compare cylinder arrays (CHT and EGT)
        for cyl in range(4):
            cht_diff = abs(f1.cht[cyl] - f2.cht[cyl])
            egt_diff = abs(f1.egt[cyl] - f2.egt[cyl])
            abs_diffs.append(cht_diff)
            abs_diffs.append(egt_diff)
            max_abs_diff = max(max_abs_diff, cht_diff, egt_diff)
            if cht_diff > tolerance or egt_diff > tolerance:
                frame_had_diff = True
                if first_mismatch_info is None:
                    first_mismatch_info = (idx, f"cyl_{cyl}", f1.cht[cyl], f2.cht[cyl], cht_diff)

        if frame_had_diff:
            mismatched_frames += 1

    mean_abs_diff = sum(abs_diffs) / len(abs_diffs) if abs_diffs else 0.0

    # Assert 100% determinism with zero mismatched frames
    assert mismatched_frames == 0, (
        f"Determinism failed: {mismatched_frames} mismatched frames. "
        f"Max diff: {max_abs_diff}, Mean diff: {mean_abs_diff}. "
        f"First mismatch: {first_mismatch_info}"
    )
    assert max_abs_diff <= tolerance, (
        f"Max numeric difference ({max_abs_diff}) exceeded tolerance ({tolerance})"
    )
    assert mean_abs_diff <= tolerance


def test_seed_isolation_and_sensor_noise_difference():
    """Verify that different seeds produce distinct sensor noise while mission trajectory remains identical."""
    mission = THROTTLE_DYNAMICS_BENCHMARK
    rate_hz = 10

    sim_seed_a = MissionSimulator(mission=mission, telemetry_rate_hz=rate_hz, seed=42)
    _, frames_a = sim_seed_a.run_sync()

    sim_seed_b = MissionSimulator(mission=mission, telemetry_rate_hz=rate_hz, seed=999)
    _, frames_b = sim_seed_b.run_sync()

    assert len(frames_a) == len(frames_b)

    # Commanded/true state inputs are identical (e.g. throttle, commanded altitude)
    # But measured outputs containing Gaussian sensor noise (e.g. vibration_rms, rpm noise) must differ
    rpm_diffs = [abs(fa.rpm - fb.rpm) for fa, fb in zip(frames_a, frames_b, strict=True)]
    max_rpm_diff = max(rpm_diffs)

    # Sensor noise causes non-zero difference between seeds
    assert max_rpm_diff > 0.0, (
        "Different random seeds unexpectedly produced identical sensor noise!"
    )
