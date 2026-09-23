"""Deterministic aero-piston engine simulator producing correlated synthetic telemetry frames.

PROTOTYPE DISCLAIMER:
Physical relationships and thermodynamic equations implemented herein are simplified
prototype engineering approximations for a generic 4-cylinder horizontally-opposed
turbocharged aero-piston engine inspired by the Rotax 914/915 class. They do NOT
represent certified aerospace performance models or OEM-validated engine dynamics.
"""

import math

from app.domain.engine.models import EngineSpecifications
from app.domain.entities.telemetry import (
    QualityStatus,
    TelemetryFrame,
    TelemetrySource,
)
from app.domain.simulation.faults import FaultController
from app.domain.simulation.scenarios import ScenarioPhase, ScenarioProfile
from app.domain.simulation.state import EngineOperatingState, SimulationInternalState
from app.domain.telemetry.validation import TelemetryValidator
from app.infrastructure.simulation.noise import DeterministicNoiseGenerator


class EngineSimulator:
    """Stateful, deterministic engine simulator.

    Calculates dynamic temporal evolution of engine operating parameters
    (RPM, MAP, CHT, EGT, Oil P/T, Fuel Flow, Vibration, Electrical) based on
    scenario phase inputs, with rate-configurable time delta dt.
    """

    def __init__(
        self,
        specs: EngineSpecifications | None = None,
        noise_generator: DeterministicNoiseGenerator | None = None,
        fault_controller: FaultController | None = None,
        telemetry_rate_hz: int = 10,
        start_epoch: float = 1774358400.0,
    ):
        self.specs = specs or EngineSpecifications()
        self.noise = noise_generator or DeterministicNoiseGenerator(seed=42)
        self.faults = fault_controller or FaultController()

        # Configurable sampling rate (never hardcoded)
        if telemetry_rate_hz <= 0:
            raise ValueError(f"Telemetry rate must be positive, got {telemetry_rate_hz}")
        self.rate_hz = telemetry_rate_hz
        self.dt = 1.0 / self.rate_hz
        self.start_epoch = start_epoch

        self.validator = TelemetryValidator(track_history=True)
        self.sequence_id = 0
        self.state = SimulationInternalState()
        self._active_phase: ScenarioPhase | None = None
        self._phase_elapsed_sec = 0.0

    def reset(self, seed: int | None = None) -> None:
        """Reset the simulator to initial cold-engine conditions."""
        if seed is not None:
            self.noise.reset(seed)
        self.validator.reset()
        self.sequence_id = 0
        self.state = SimulationInternalState()
        self._active_phase = None
        self._phase_elapsed_sec = 0.0

    def step(self, phase: ScenarioPhase | None = None) -> TelemetryFrame:
        """Advance the simulation by one discrete time step dt and return a validated TelemetryFrame."""
        if phase is not None:
            self._active_phase = phase

        # Use active phase parameters or fallback to default idle
        target_throttle = self._active_phase.target_throttle_pct if self._active_phase else 0.0
        target_alt = self._active_phase.target_altitude_m if self._active_phase else 0.0
        ambient_temp = self._active_phase.ambient_temp_c if self._active_phase else 15.0
        target_tas = self._active_phase.target_airspeed_ms if self._active_phase else 0.0
        ignition = self._active_phase.ignition_on if self._active_phase else True
        starter = self._active_phase.starter_engaged if self._active_phase else False

        # 1. Update Flight / Environment State (first-order approach)
        self.state.ambient_temp_c = ambient_temp
        self.state.altitude_m += (target_alt - self.state.altitude_m) * min(1.0, 0.1 * self.dt)
        self.state.true_airspeed_ms += (target_tas - self.state.true_airspeed_ms) * min(
            1.0, 0.2 * self.dt
        )

        # Ambient pressure from altitude (ISA approximation inHg)
        p_amb = 29.92 * math.pow(max(0.01, 1.0 - 2.25577e-5 * self.state.altitude_m), 5.25588)

        # 2. Throttle Response Dynamics (Lag and Slew Rate)
        max_throttle_rate = 80.0  # Max 80% throttle change per second
        throttle_delta = target_throttle - self.state.throttle_pct
        max_step = max_throttle_rate * self.dt
        clamped_throttle_delta = max(-max_step, min(max_step, throttle_delta))
        self.state.throttle_pct += clamped_throttle_delta
        self.state.commanded_throttle_pct = target_throttle

        # 3. Engine Target RPM & Operating State Machine
        if not ignition:
            # Ignition off: spin-down to 0 RPM
            self.state.target_rpm = 0.0
            if self.state.rpm > 100.0:
                self.state.operating_state = EngineOperatingState.SHUTDOWN
            else:
                self.state.operating_state = EngineOperatingState.OFF
        elif starter and self.state.rpm < self.specs.idle_rpm:
            # Starter cranking
            self.state.target_rpm = 350.0 + (self.state.throttle_pct * 5.0)
            self.state.operating_state = EngineOperatingState.STARTING
        else:
            # Engine running: map throttle (0..100) to RPM (idle..takeoff)
            rpm_range = self.specs.takeoff_max_rpm - self.specs.idle_rpm
            self.state.target_rpm = (
                self.specs.idle_rpm + (self.state.throttle_pct / 100.0) * rpm_range
            )

            if self.state.throttle_pct > 85.0:
                self.state.operating_state = EngineOperatingState.HIGH_POWER
            elif self.state.throttle_pct > 30.0:
                self.state.operating_state = EngineOperatingState.CRUISE
            elif self.state.throttle_pct > 12.0:
                self.state.operating_state = EngineOperatingState.IDLE
            else:
                self.state.operating_state = EngineOperatingState.IDLE

        # RPM First-Order Lag (inertia tau = 0.6s)
        tau_rpm = 0.6
        alpha_rpm = min(1.0, self.dt / tau_rpm)
        rpm_change = alpha_rpm * (self.state.target_rpm - self.state.rpm)
        self.state.rpm += rpm_change

        # Determine acceleration / deceleration states
        if ignition and abs(rpm_change / self.dt) > 80.0:
            if rpm_change > 0:
                self.state.operating_state = EngineOperatingState.ACCELERATING
            else:
                self.state.operating_state = EngineOperatingState.DECELERATING

        # 4. Turbocharged Manifold Absolute Pressure (MAP inHg)
        if self.state.rpm < 200.0:
            target_map = p_amb
        else:
            # Turbo boost scales with RPM and throttle above ambient pressure
            boost_factor = (self.state.throttle_pct / 100.0) * (
                self.state.rpm / self.specs.takeoff_max_rpm
            )
            max_boost_inhg = 12.0  # ~12 inHg boost over ambient
            target_map = p_amb * (0.8 + 0.2 * (self.state.throttle_pct / 100.0)) + (
                boost_factor * max_boost_inhg
            )
            target_map = min(40.0, max(12.0, target_map))

        tau_map = 0.4  # Turbo lag time constant
        self.state.manifold_pressure_inhg += (target_map - self.state.manifold_pressure_inhg) * min(
            1.0, self.dt / tau_map
        )

        # 5. Fuel System Dynamics
        if self.state.rpm > 300.0 and ignition:
            # Correlated fuel flow: L/h scales with MAP and RPM
            norm_load = (self.state.manifold_pressure_inhg / 29.92) * (self.state.rpm / 5000.0)
            target_ff = 5.0 + (norm_load * 22.0)
            self.state.fuel_pressure_bar = 3.0 + (self.state.throttle_pct / 100.0) * 0.4
            self.state.injection_timing_deg = (
                18.0 + (1.0 - (self.state.throttle_pct / 100.0)) * 10.0
            )
        else:
            target_ff = 0.0
            self.state.fuel_pressure_bar = 0.8 if starter else 0.0
            self.state.injection_timing_deg = 10.0

        self.state.fuel_flow_lph += (target_ff - self.state.fuel_flow_lph) * min(1.0, self.dt / 0.3)

        # 6. Thermal Dynamics (EGT, CHT, Coolant, Oil Temp)
        # EGT target: scales with load, cooled at high airspeed
        if self.state.rpm > 300.0 and ignition:
            egt_target_base = 650.0 + (self.state.throttle_pct / 100.0) * 190.0
            cht_target_base = (
                75.0 + (self.state.throttle_pct / 100.0) * 48.0 + (ambient_temp - 15.0) * 0.3
            )
            # Ram air cooling effect on CHT
            cooling_loss = min(15.0, self.state.true_airspeed_ms * 0.2)
            cht_target_base -= cooling_loss
            oil_temp_target = (
                80.0 + (self.state.throttle_pct / 100.0) * 32.0 + (ambient_temp - 15.0) * 0.2
            )
        else:
            egt_target_base = ambient_temp
            cht_target_base = ambient_temp
            oil_temp_target = ambient_temp

        # EGT response (moderate lag tau = 1.2s)
        tau_egt = 1.2
        for cyl in range(4):
            # Slight cylinder-to-cylinder thermal asymmetry
            cyl_offset = (cyl - 1.5) * 6.0
            t_egt = max(ambient_temp, egt_target_base + cyl_offset)
            self.state.egt_c[cyl] += (t_egt - self.state.egt_c[cyl]) * min(1.0, self.dt / tau_egt)

        # CHT response (slow thermal inertia tau = 14.0s)
        tau_cht = 14.0
        for cyl in range(4):
            cyl_offset = (1.5 - cyl) * 2.5
            t_cht = max(ambient_temp, cht_target_base + cyl_offset)
            self.state.cht_c[cyl] += (t_cht - self.state.cht_c[cyl]) * min(1.0, self.dt / tau_cht)

        # Coolant tracks CHT (tau = 16.0s)
        mean_cht = sum(self.state.cht_c) / 4.0
        coolant_target = max(ambient_temp, mean_cht * 0.75)
        self.state.coolant_temp_c += (coolant_target - self.state.coolant_temp_c) * min(
            1.0, self.dt / 16.0
        )

        # Oil temperature (very slow thermal mass tau = 35.0s)
        self.state.oil_temperature_c += (oil_temp_target - self.state.oil_temperature_c) * min(
            1.0, self.dt / 35.0
        )

        # 7. Lubrication Oil Pressure
        if self.state.rpm < 200.0:
            target_oil_p = 0.0
        else:
            # Positive function of RPM, negative function of temperature (viscosity thinning)
            viscosity_factor = 1.0 - max(0.0, (self.state.oil_temperature_c - 80.0) * 0.005)
            target_oil_p = min(4.8, (0.8 + (self.state.rpm / 5000.0) * 3.4) * viscosity_factor)
            target_oil_p = max(0.5, target_oil_p)

        self.state.oil_pressure_bar += (target_oil_p - self.state.oil_pressure_bar) * min(
            1.0, self.dt / 0.5
        )

        # 8. Mechanical Vibration (RMS g)
        if self.state.rpm < 100.0:
            target_vib = 0.05
        else:
            # Scales with rotational speed squared plus imbalance
            norm_rpm = self.state.rpm / 5000.0
            target_vib = 0.4 + (norm_rpm * norm_rpm * 1.6)

        self.state.vibration_rms_g += (target_vib - self.state.vibration_rms_g) * min(
            1.0, self.dt / 0.2
        )

        # 9. Electrical System
        if self.state.rpm > 1800.0 and ignition:
            self.state.battery_voltage_v = 28.2
            self.state.alternator_current_a = 15.0 + (self.state.throttle_pct / 100.0) * 12.0
            self.state.alternator_status = "OK"
        elif self.state.rpm > 400.0 and ignition:
            self.state.battery_voltage_v = 25.5
            self.state.alternator_current_a = 4.0
            self.state.alternator_status = "WARNING"
        else:
            self.state.battery_voltage_v = 24.2
            self.state.alternator_current_a = 0.0
            self.state.alternator_status = "OK"

        # Advance simulation clock
        self.state.sim_time += self.dt
        self._phase_elapsed_sec += self.dt
        timestamp = self.start_epoch + self.state.sim_time
        seq_id = self.sequence_id
        self.sequence_id += 1

        # 10. Sensor Measurement Stage: Noise + Fault Injection
        raw_noise = self.noise.gaussian(std=1.0)

        # Apply noise and faults to each channel
        measured_rpm, _ = self.faults.apply_scalar_fault(
            "rpm",
            max(0.0, self.state.rpm + self.noise.gaussian(std=4.0)),
            self.state.sim_time,
            raw_noise,
        )
        measured_map, _ = self.faults.apply_scalar_fault(
            "manifold_pressure",
            max(10.0, self.state.manifold_pressure_inhg + self.noise.gaussian(std=0.08)),
            self.state.sim_time,
            raw_noise,
        )
        measured_throttle, _ = self.faults.apply_scalar_fault(
            "throttle_position",
            max(0.0, min(100.0, self.state.throttle_pct + self.noise.gaussian(std=0.05))),
            self.state.sim_time,
            raw_noise,
        )
        measured_ff, _ = self.faults.apply_scalar_fault(
            "fuel_flow",
            max(0.0, self.state.fuel_flow_lph + self.noise.gaussian(std=0.15)),
            self.state.sim_time,
            raw_noise,
        )
        measured_fp, _ = self.faults.apply_scalar_fault(
            "fuel_pressure",
            max(0.5, self.state.fuel_pressure_bar + self.noise.gaussian(std=0.02)),
            self.state.sim_time,
            raw_noise,
        )
        measured_inj, _ = self.faults.apply_scalar_fault(
            "injection_timing",
            max(0.0, self.state.injection_timing_deg + self.noise.gaussian(std=0.05)),
            self.state.sim_time,
            raw_noise,
        )

        measured_cht: list[float] = []
        for i in range(4):
            val, _ = self.faults.apply_scalar_fault(
                f"cht_{i + 1}",
                self.state.cht_c[i] + self.noise.gaussian(std=0.2),
                self.state.sim_time,
                raw_noise,
            )
            measured_cht.append(round(val, 2))

        measured_egt: list[float] = []
        for i in range(4):
            val, _ = self.faults.apply_scalar_fault(
                f"egt_{i + 1}",
                self.state.egt_c[i] + self.noise.gaussian(std=1.5),
                self.state.sim_time,
                raw_noise,
            )
            measured_egt.append(round(val, 2))

        measured_coolant, _ = self.faults.apply_scalar_fault(
            "coolant_temp",
            self.state.coolant_temp_c + self.noise.gaussian(std=0.2),
            self.state.sim_time,
            raw_noise,
        )
        measured_oil_t, _ = self.faults.apply_scalar_fault(
            "oil_temperature",
            self.state.oil_temperature_c + self.noise.gaussian(std=0.15),
            self.state.sim_time,
            raw_noise,
        )
        measured_oil_p, _ = self.faults.apply_scalar_fault(
            "oil_pressure",
            max(0.0, self.state.oil_pressure_bar + self.noise.gaussian(std=0.03)),
            self.state.sim_time,
            raw_noise,
        )
        measured_vib, _ = self.faults.apply_scalar_fault(
            "vibration_rms",
            max(0.0, self.state.vibration_rms_g + self.noise.gaussian(std=0.04)),
            self.state.sim_time,
            raw_noise,
        )
        measured_v_bat, _ = self.faults.apply_scalar_fault(
            "battery_voltage",
            self.state.battery_voltage_v + self.noise.gaussian(std=0.05),
            self.state.sim_time,
            raw_noise,
        )
        measured_i_alt, _ = self.faults.apply_scalar_fault(
            "alternator_current",
            max(0.0, self.state.alternator_current_a + self.noise.gaussian(std=0.2)),
            self.state.sim_time,
            raw_noise,
        )

        frame = TelemetryFrame(
            version="1.0.0",
            timestamp=round(timestamp, 4),
            sequence_id=seq_id,
            source_type=TelemetrySource.SIMULATED,
            quality_flag=QualityStatus.VALID,
            rpm=round(measured_rpm, 1),
            manifold_pressure=round(measured_map, 2),
            throttle_position=round(measured_throttle, 1),
            fuel_flow=round(measured_ff, 2),
            fuel_pressure=round(measured_fp, 2),
            injection_timing=round(measured_inj, 1),
            cht=measured_cht,
            egt=measured_egt,
            coolant_temp=round(measured_coolant, 1),
            oil_temperature=round(measured_oil_t, 1),
            oil_pressure=round(measured_oil_p, 2),
            vibration_rms=round(measured_vib, 3),
            battery_voltage=round(measured_v_bat, 2),
            alternator_current=round(measured_i_alt, 1),
            alternator_status=self.state.alternator_status,
            altitude=round(self.state.altitude_m, 1),
            ambient_temp=round(self.state.ambient_temp_c, 1),
            true_airspeed=round(self.state.true_airspeed_ms, 1),
        )

        # 11. Run telemetry validator and attach resultant quality flag
        validation_res = self.validator.validate(frame)
        frame.quality_flag = validation_res.quality

        return frame

    def run_scenario(self, profile: ScenarioProfile) -> list[TelemetryFrame]:
        """Execute a multi-phase scenario synchronously in simulation time and return all frames."""
        frames: list[TelemetryFrame] = []
        for phase in profile.phases:
            step_count = int(math.ceil(phase.duration_sec / self.dt))
            for _ in range(step_count):
                frame = self.step(phase)
                frames.append(frame)
        return frames
