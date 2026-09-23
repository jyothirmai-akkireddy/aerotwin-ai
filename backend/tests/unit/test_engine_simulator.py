"""Unit tests for deterministic EngineSimulator dynamics and state machine."""

from app.domain.simulation.scenarios import SCENARIO_ENGINE_START, ScenarioPhase
from app.domain.simulation.state import EngineOperatingState
from app.infrastructure.simulation.engine_simulator import EngineSimulator
from app.infrastructure.simulation.noise import DeterministicNoiseGenerator


def test_simulation_exact_determinism():
    """Verify that identical seeds produce bit-identical telemetry outputs."""
    sim1 = EngineSimulator(
        noise_generator=DeterministicNoiseGenerator(seed=123),
        telemetry_rate_hz=10,
    )
    sim2 = EngineSimulator(
        noise_generator=DeterministicNoiseGenerator(seed=123),
        telemetry_rate_hz=10,
    )

    phase = ScenarioPhase(
        phase_name="TEST_RUN",
        duration_sec=5.0,
        target_throttle_pct=60.0,
        target_altitude_m=1000.0,
        ignition_on=True,
    )

    frames1 = [sim1.step(phase) for _ in range(30)]
    frames2 = [sim2.step(phase) for _ in range(30)]

    for f1, f2 in zip(frames1, frames2, strict=False):
        assert f1.sequence_id == f2.sequence_id
        assert f1.timestamp == f2.timestamp
        assert f1.rpm == f2.rpm
        assert f1.manifold_pressure == f2.manifold_pressure
        assert f1.cht == f2.cht
        assert f1.egt == f2.egt
        assert f1.vibration_rms == f2.vibration_rms


def test_seed_diversity():
    """Verify that different seeds produce statistically distinct noise traces."""
    sim1 = EngineSimulator(
        noise_generator=DeterministicNoiseGenerator(seed=100),
        telemetry_rate_hz=10,
    )
    sim2 = EngineSimulator(
        noise_generator=DeterministicNoiseGenerator(seed=200),
        telemetry_rate_hz=10,
    )

    phase = ScenarioPhase(
        phase_name="IDLE_RUN",
        duration_sec=2.0,
        target_throttle_pct=10.0,
        ignition_on=True,
    )

    frame1 = sim1.step(phase)
    frame2 = sim2.step(phase)

    # Base physics are identical, but PRNG noise produces distinct fine variations
    assert frame1.vibration_rms != frame2.vibration_rms
    assert frame1.rpm != frame2.rpm
    assert frame1.battery_voltage != frame2.battery_voltage


def test_throttle_transient_slew_rate():
    """Verify throttle position cannot jump instantaneously and obeys dynamic rate clamping."""
    sim = EngineSimulator(telemetry_rate_hz=10)
    # Start at 0% throttle, command instant 100% throttle
    high_throttle_phase = ScenarioPhase(
        phase_name="MAX_POWER",
        duration_sec=1.0,
        target_throttle_pct=100.0,
        ignition_on=True,
    )

    first_step = sim.step(high_throttle_phase)
    # Max rate is 80%/s -> In 0.1s dt, maximum throttle increment is ~8.0%
    assert first_step.throttle_position < 15.0
    assert first_step.throttle_position > 5.0


def test_thermal_lag_continuity():
    """Verify CHT and EGT follow thermal inertial lag rather than instantaneous step jumps."""
    sim = EngineSimulator(telemetry_rate_hz=10)
    sim.state.operating_state = EngineOperatingState.IDLE

    phase = ScenarioPhase(
        phase_name="TAKEOFF_POWER",
        duration_sec=2.0,
        target_throttle_pct=100.0,
        ignition_on=True,
    )

    initial_cht = sim.state.cht_c[0]
    initial_egt = sim.state.egt_c[0]

    # Step for 1 second (10 ticks)
    for _ in range(10):
        frame = sim.step(phase)

    # Temperatures should have increased, but bounded by thermal mass time constants
    delta_cht = frame.cht[0] - initial_cht
    delta_egt = frame.egt[0] - initial_egt

    assert delta_cht > 0.0
    assert delta_cht < 30.0  # CHT has high thermal inertia
    assert delta_egt > 0.0  # EGT rises faster than CHT


def test_engine_state_machine_start_sequence():
    """Verify state transitions during engine startup scenario."""
    sim = EngineSimulator(telemetry_rate_hz=10)
    assert sim.state.operating_state == EngineOperatingState.OFF

    frames = sim.run_scenario(SCENARIO_ENGINE_START)
    # After start scenario, engine must be running or idling
    assert sim.state.operating_state in (
        EngineOperatingState.IDLE,
        EngineOperatingState.CRUISE,
        EngineOperatingState.STARTING,
    )
    assert frames[-1].rpm > 1000.0


def test_telemetry_rate_configurability():
    """Verify simulator properly adapts dt and timestamps to configurable rate_hz."""
    sim_5hz = EngineSimulator(telemetry_rate_hz=5)
    sim_20hz = EngineSimulator(telemetry_rate_hz=20)

    assert sim_5hz.dt == 0.2
    assert sim_20hz.dt == 0.05

    f1 = sim_5hz.step()
    f2 = sim_5hz.step()
    assert round(f2.timestamp - f1.timestamp, 4) == 0.2

    f3 = sim_20hz.step()
    f4 = sim_20hz.step()
    assert round(f4.timestamp - f3.timestamp, 4) == 0.05
