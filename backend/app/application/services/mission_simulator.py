"""Deterministic mission flight simulator orchestrator.

Translates mission phase definitions, mathematical profile curves, and transient events
into discrete control inputs driving the EngineSimulator, strictly preserving physical
and architectural separation.
"""

import math
import uuid

from app.domain.entities.telemetry import TelemetryFrame
from app.domain.mission.enums import ControlTargetParameter
from app.domain.mission.models import (
    MissionDefinition,
    MissionSimulationSummary,
    PhaseSummary,
)
from app.domain.simulation.scenarios import ScenarioPhase
from app.infrastructure.simulation.engine_simulator import EngineSimulator
from app.infrastructure.simulation.noise import DeterministicNoiseGenerator


class MissionSimulator:
    """Orchestrates deterministic multi-phase mission execution."""

    def __init__(
        self,
        mission: MissionDefinition,
        telemetry_rate_hz: int = 10,
        seed: int = 42,
        start_epoch: float = 1774358400.0,
    ):
        if telemetry_rate_hz <= 0:
            raise ValueError(f"Telemetry rate must be positive, got {telemetry_rate_hz}")

        self.mission = mission
        self.rate_hz = telemetry_rate_hz
        self.dt = 1.0 / self.rate_hz
        self.seed = seed
        self.start_epoch = start_epoch

        # Noise generator is the ONLY consumer of the random seed
        noise_gen = DeterministicNoiseGenerator(seed=self.seed)
        self.engine_simulator = EngineSimulator(
            noise_generator=noise_gen,
            telemetry_rate_hz=self.rate_hz,
            start_epoch=self.start_epoch,
        )

        # Set initial environmental conditions from mission definition
        self.engine_simulator.state.altitude_m = self.mission.initial_altitude_m
        self.engine_simulator.state.ambient_temp_c = self.mission.initial_ambient_temp_c

        # Pre-register any sensor fault events into engine simulator fault controller
        for fe in self.mission.fault_events:
            self.engine_simulator.faults.add_fault(fe.to_sensor_fault_config())

    def run_sync(self) -> tuple[MissionSimulationSummary, list[TelemetryFrame]]:
        """Synchronously execute complete mission and compile summary metrics.

        Returns:
            (MissionSimulationSummary, list[TelemetryFrame])
        """
        frames: list[TelemetryFrame] = []
        phase_summaries: list[PhaseSummary] = []

        mission_elapsed_sec = 0.0
        run_id = f"run-{uuid.uuid4().hex[:12]}"

        for phase in self.mission.phases:
            phase_start_time = mission_elapsed_sec
            phase_frames: list[TelemetryFrame] = []
            steps_in_phase = int(math.ceil(phase.duration_sec / self.dt))

            for step_idx in range(steps_in_phase):
                phase_t = min(phase.duration_sec, step_idx * self.dt)
                current_mission_t = phase_start_time + phase_t

                # 1. Base control inputs evaluated from profile curves
                (
                    target_throttle,
                    target_alt,
                    target_tas,
                    ambient_temp,
                    ignition_on,
                    starter_engaged,
                ) = phase.get_operating_inputs(phase_t)

                # 2. Additive control events evaluation
                for ce in self.mission.control_events:
                    if ce.is_active(current_mission_t):
                        offset = ce.evaluate_offset(current_mission_t)
                        if ce.target_parameter == ControlTargetParameter.THROTTLE_PCT:
                            target_throttle += offset
                        elif ce.target_parameter == ControlTargetParameter.ALTITUDE_M:
                            target_alt += offset
                        elif ce.target_parameter == ControlTargetParameter.AMBIENT_TEMP_C:
                            ambient_temp += offset
                        elif ce.target_parameter == ControlTargetParameter.AIRSPEED_MS:
                            target_tas += offset

                # Clamp physical inputs to valid operational domains
                target_throttle = max(0.0, min(100.0, target_throttle))
                target_alt = max(-200.0, min(12000.0, target_alt))
                target_tas = max(0.0, min(150.0, target_tas))
                ambient_temp = max(-60.0, min(60.0, ambient_temp))

                # 3. Create synthetic ScenarioPhase slice for this single step
                dynamic_slice = ScenarioPhase(
                    phase_name=phase.phase_id,
                    duration_sec=self.dt,
                    target_throttle_pct=target_throttle,
                    target_altitude_m=target_alt,
                    ambient_temp_c=ambient_temp,
                    target_airspeed_ms=target_tas,
                    ignition_on=ignition_on,
                    starter_engaged=starter_engaged,
                )

                # 4. Advance engine physics simulation by 1 dt
                frame = self.engine_simulator.step(dynamic_slice)
                phase_frames.append(frame)
                frames.append(frame)

            mission_elapsed_sec += phase.duration_sec

            # Compute individual phase summary metrics
            phase_fuel = sum((f.fuel_flow / 3600.0) * self.dt for f in phase_frames)
            avg_rpm = sum(f.rpm for f in phase_frames) / max(1, len(phase_frames))
            max_cht = max(max(f.cht) for f in phase_frames) if phase_frames else 0.0
            max_egt = max(max(f.egt) for f in phase_frames) if phase_frames else 0.0

            phase_summaries.append(
                PhaseSummary(
                    phase_id=phase.phase_id,
                    phase_type=phase.phase_type,
                    start_time_sec=phase_start_time,
                    duration_sec=phase.duration_sec,
                    fuel_burned_liters=round(phase_fuel, 4),
                    avg_rpm=round(avg_rpm, 1),
                    max_cht_c=round(max_cht, 1),
                    max_egt_c=round(max_egt, 1),
                )
            )

        # Cumulative mission metrics calculation
        # fuel_flow is in L/h; dt in seconds -> fuel_liters = sum(fuel_flow / 3600.0 * dt)
        total_fuel_liters = sum((f.fuel_flow / 3600.0) * self.dt for f in frames)
        fuel_density_kg_l = 0.72  # Standard calibrated aviation Mogas/Avgas density
        total_fuel_kg = total_fuel_liters * fuel_density_kg_l

        summary = MissionSimulationSummary(
            run_id=run_id,
            mission_id=self.mission.mission_id,
            mission_version=self.mission.version,
            total_duration_sec=round(self.mission.total_duration_sec, 2),
            total_frames=len(frames),
            fuel_consumed_liters=round(total_fuel_liters, 4),
            fuel_mass_kg=round(total_fuel_kg, 4),
            max_cht_c=round(max(max(f.cht) for f in frames), 1) if frames else 0.0,
            max_egt_c=round(max(max(f.egt) for f in frames), 1) if frames else 0.0,
            max_oil_temp_c=round(max(f.oil_temperature for f in frames), 1) if frames else 0.0,
            min_oil_pressure_bar=round(min(f.oil_pressure for f in frames), 2) if frames else 0.0,
            peak_vibration_rms=round(max(f.vibration_rms for f in frames), 3) if frames else 0.0,
            max_altitude_m=round(max(f.altitude for f in frames), 1) if frames else 0.0,
            phase_summaries=phase_summaries,
            is_deterministic=True,
            prototype_disclaimer=(
                "PROTOTYPE NON-CERTIFIED BENCHMARK DATA: Results are simulated approximations."
            ),
        )

        return summary, frames
