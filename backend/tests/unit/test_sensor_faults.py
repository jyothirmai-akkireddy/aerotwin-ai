"""Unit tests for reproducible sensor fault injection modes."""

from app.domain.entities.telemetry import QualityStatus
from app.domain.simulation.faults import (
    FaultController,
    SensorFaultConfig,
    SensorFaultType,
)
from app.domain.simulation.scenarios import ScenarioPhase
from app.infrastructure.simulation.engine_simulator import EngineSimulator
from app.infrastructure.simulation.noise import DeterministicNoiseGenerator


def test_bias_sensor_fault():
    """Verify constant additive offset is applied to target channel during active window."""
    sim_nominal = EngineSimulator(
        noise_generator=DeterministicNoiseGenerator(seed=42),
        telemetry_rate_hz=10,
    )
    sim_faulted = EngineSimulator(
        noise_generator=DeterministicNoiseGenerator(seed=42),
        telemetry_rate_hz=10,
    )

    # Inject +15.0°C bias to cht_1 between sim_time 0.5s and 1.5s
    fault = SensorFaultConfig(
        target_channel="cht_1",
        fault_type=SensorFaultType.BIAS,
        start_time_sec=0.5,
        end_time_sec=1.5,
        magnitude=15.0,
    )
    sim_faulted.faults.add_fault(fault)

    phase = ScenarioPhase(
        phase_name="CRUISE_STEP",
        duration_sec=2.0,
        target_throttle_pct=50.0,
        ignition_on=True,
    )

    # Step through 2.0s (20 steps)
    for _ in range(20):
        fn = sim_nominal.step(phase)
        ff = sim_faulted.step(phase)

        # Before 0.5s: identical
        if sim_nominal.state.sim_time < 0.5:
            assert abs(fn.cht[0] - ff.cht[0]) < 0.01
        # During [0.5, 1.5]: faulted is biased by exactly 15.0°C
        elif 0.5 <= sim_nominal.state.sim_time <= 1.4:
            assert abs((ff.cht[0] - fn.cht[0]) - 15.0) < 0.05


def test_drift_sensor_fault():
    """Verify linear ramp offset grows with elapsed fault time."""
    sim = EngineSimulator(
        noise_generator=DeterministicNoiseGenerator(seed=42),
        telemetry_rate_hz=10,
    )

    # Incur drift of +0.5 bar/s on oil_pressure starting at 1.0s
    fault = SensorFaultConfig(
        target_channel="oil_pressure",
        fault_type=SensorFaultType.DRIFT,
        start_time_sec=1.0,
        drift_rate_per_sec=0.5,
    )
    sim.faults.add_fault(fault)

    phase = ScenarioPhase(
        phase_name="RUN_STEP",
        duration_sec=3.0,
        target_throttle_pct=40.0,
        ignition_on=True,
    )

    frames = [sim.step(phase) for _ in range(30)]

    # At sim_time = 2.0s (1.0s elapsed into fault), drift should add ~0.5 bar
    f_at_1s = frames[9]  # sim_time ~ 1.0s
    f_at_2s = frames[19]  # sim_time ~ 2.0s
    f_at_3s = frames[29]  # sim_time ~ 3.0s

    assert f_at_2s.oil_pressure > f_at_1s.oil_pressure
    assert f_at_3s.oil_pressure > f_at_2s.oil_pressure


def test_stuck_sensor_fault():
    """Verify sensor reading freezes at frozen value regardless of dynamic engine changes."""
    sim = EngineSimulator(
        noise_generator=DeterministicNoiseGenerator(seed=42),
        telemetry_rate_hz=10,
    )

    fault = SensorFaultConfig(
        target_channel="throttle_position",
        fault_type=SensorFaultType.STUCK,
        start_time_sec=0.5,
        magnitude=25.0,  # Stuck at 25%
    )
    sim.faults.add_fault(fault)

    phase = ScenarioPhase(
        phase_name="ACCEL_STEP",
        duration_sec=2.0,
        target_throttle_pct=90.0,
        ignition_on=True,
    )

    frames = [sim.step(phase) for _ in range(20)]

    # Beyond 0.5s, throttle_position remains frozen at 25.0%
    for f in frames[6:]:
        assert f.throttle_position == 25.0


def test_dropout_sensor_fault():
    """Verify sensor dropout drops reading to zero and causes validator to flag INVALID."""
    sim = EngineSimulator(
        noise_generator=DeterministicNoiseGenerator(seed=42),
        telemetry_rate_hz=10,
    )

    # Battery voltage normal is 28V, drops out to 0.0 at 0.5s
    fault = SensorFaultConfig(
        target_channel="battery_voltage",
        fault_type=SensorFaultType.DROPOUT,
        start_time_sec=0.5,
        end_time_sec=1.5,
    )
    sim.faults.add_fault(fault)

    phase = ScenarioPhase(
        phase_name="CRUISE",
        duration_sec=2.0,
        target_throttle_pct=40.0,
        ignition_on=True,
    )

    frames = [sim.step(phase) for _ in range(20)]

    # During fault, battery voltage is 0.0 and frame quality is INVALID
    dropout_frames = [f for f in frames if 0.6 <= f.timestamp - sim.start_epoch <= 1.4]
    assert len(dropout_frames) > 0
    for df in dropout_frames:
        assert df.battery_voltage == 0.0
        assert df.quality_flag == QualityStatus.INVALID


def test_fault_controller_clearing():
    """Verify clearing faults restores nominal simulation behavior."""
    ctrl = FaultController()
    fault = SensorFaultConfig(
        target_channel="oil_pressure",
        fault_type=SensorFaultType.BIAS,
        start_time_sec=0.0,
        magnitude=2.0,
    )
    ctrl.add_fault(fault)
    assert len(ctrl.fault_configs) == 1

    ctrl.clear()
    assert len(ctrl.fault_configs) == 0
