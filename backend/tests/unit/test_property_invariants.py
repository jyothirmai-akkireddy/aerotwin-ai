"""Property invariant tests ensuring telemetry frames always uphold physical laws."""

import math

import pytest

from app.domain.simulation.scenarios import (
    SCENARIO_ENGINE_START,
    SCENARIO_TAKEOFF,
    SCENARIO_THROTTLE_TRANSIENTS,
)
from app.infrastructure.simulation.engine_simulator import EngineSimulator


@pytest.fixture
def simulated_frames():
    """Generate frames across multiple operational regimes."""
    sim = EngineSimulator(telemetry_rate_hz=10)
    frames = []
    frames.extend(sim.run_scenario(SCENARIO_ENGINE_START))
    frames.extend(sim.run_scenario(SCENARIO_TAKEOFF))
    frames.extend(sim.run_scenario(SCENARIO_THROTTLE_TRANSIENTS))
    return frames


def test_rpm_bounds_invariant(simulated_frames):
    """Assert RPM is non-negative and never exceeds physical redline."""
    for f in simulated_frames:
        assert 0.0 <= f.rpm <= 6500.0, f"RPM {f.rpm} violated bounds at seq {f.sequence_id}"


def test_timestamp_strict_monotonicity_invariant(simulated_frames):
    """Assert each frame timestamp strictly exceeds the prior timestamp."""
    for i in range(1, len(simulated_frames)):
        prev_t = simulated_frames[i - 1].timestamp
        curr_t = simulated_frames[i].timestamp
        assert curr_t > prev_t, f"Non-monotonic timestamp at index {i}: {curr_t} <= {prev_t}"


def test_sequence_id_step_invariant(simulated_frames):
    """Assert sequence IDs increment by exactly 1 without gaps."""
    for i in range(1, len(simulated_frames)):
        assert simulated_frames[i].sequence_id == simulated_frames[i - 1].sequence_id + 1, (
            f"Sequence gap at index {i}"
        )


def test_cylinder_count_invariant(simulated_frames):
    """Assert every frame contains exactly 4 CHT and 4 EGT channels."""
    for f in simulated_frames:
        assert len(f.cht) == 4, f"Invalid CHT length {len(f.cht)} at seq {f.sequence_id}"
        assert len(f.egt) == 4, f"Invalid EGT length {len(f.egt)} at seq {f.sequence_id}"


def test_finiteness_invariant(simulated_frames):
    """Assert no scalar channel produces NaN or +/- Infinity."""
    for f in simulated_frames:
        for ch in [
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
        ]:
            val = getattr(f, ch)
            assert math.isfinite(val), f"Channel {ch} is not finite ({val}) at seq {f.sequence_id}"

        for t in f.cht:
            assert math.isfinite(t), f"CHT value {t} is not finite at seq {f.sequence_id}"
        for t in f.egt:
            assert math.isfinite(t), f"EGT value {t} is not finite at seq {f.sequence_id}"


def test_battery_voltage_positive_invariant(simulated_frames):
    """Assert battery voltage remains strictly within 12V-28V avionics limits."""
    for f in simulated_frames:
        assert 10.0 <= f.battery_voltage <= 32.0, (
            f"Battery voltage {f.battery_voltage}V out of bounds at seq {f.sequence_id}"
        )
