"""Synthetic telemetry streaming source adapter implementing ITelemetrySource.

Drives the EngineSimulator to produce deterministically correlated telemetry frames
either in real-time pace or accelerated non-blocking batch mode.
"""

import asyncio
from collections.abc import AsyncIterator

from app.application.ports.telemetry_ports import ITelemetrySource
from app.domain.entities.telemetry import TelemetryFrame
from app.domain.simulation.faults import FaultController, SensorFaultConfig
from app.domain.simulation.scenarios import ScenarioPhase, ScenarioProfile, get_scenario
from app.infrastructure.simulation.engine_simulator import EngineSimulator
from app.infrastructure.simulation.noise import DeterministicNoiseGenerator


class SyntheticTelemetrySource(ITelemetrySource):
    """Adapter bridging the deterministic EngineSimulator to application telemetry consumers."""

    def __init__(
        self,
        simulator: EngineSimulator | None = None,
        telemetry_rate_hz: int = 10,
        seed: int = 42,
    ):
        if simulator is not None:
            self.simulator = simulator
        else:
            noise_gen = DeterministicNoiseGenerator(seed=seed)
            fault_ctrl = FaultController()
            self.simulator = EngineSimulator(
                noise_generator=noise_gen,
                fault_controller=fault_ctrl,
                telemetry_rate_hz=telemetry_rate_hz,
            )

        self._is_connected = False
        self._current_phase: ScenarioPhase | None = None

    @property
    def is_connected(self) -> bool:
        """Return stream connection state."""
        return self._is_connected

    @property
    def faults(self) -> FaultController:
        """Access the underlying fault controller."""
        return self.simulator.faults

    def inject_fault(self, fault: SensorFaultConfig) -> None:
        """Inject a sensor fault into the telemetry generation stream."""
        self.simulator.faults.add_fault(fault)

    def clear_faults(self) -> None:
        """Clear all active sensor faults."""
        self.simulator.faults.clear()

    @property
    def current_phase(self) -> ScenarioPhase | None:
        """Return the currently configured scenario phase."""
        return self._current_phase

    def set_phase(self, phase: ScenarioPhase | None) -> None:
        """Set the active flight scenario phase driving the engine simulation.

        Raises:
            TypeError: If phase is not an instance of ScenarioPhase or None.
        """
        if phase is not None and not isinstance(phase, ScenarioPhase):
            raise TypeError(f"Expected ScenarioPhase or None, got {type(phase).__name__}")
        self._current_phase = phase

    def set_scenario(self, scenario: ScenarioProfile | str) -> bool:
        """Set the active flight scenario driving the engine simulation.

        Accepts a ScenarioProfile instance or a standard scenario name string.
        Extracts the initial ScenarioPhase from the profile and updates the active phase.

        Returns:
            True if the scenario was successfully resolved and applied, False otherwise.
        """
        if isinstance(scenario, str):
            profile = get_scenario(scenario)
        elif isinstance(scenario, ScenarioProfile):
            profile = scenario
        else:
            return False

        if profile is None or not profile.phases:
            return False

        self.set_phase(profile.phases[0])
        return True

    async def connect(self) -> None:
        """Connect to the synthetic telemetry stream."""
        self._is_connected = True

    async def disconnect(self) -> None:
        """Disconnect and halt stream generation."""
        self._is_connected = False

    async def get_next_frame(self) -> TelemetryFrame:
        """Produce the next sequential telemetry frame."""
        if not self._is_connected:
            await self.connect()
        return self.simulator.step(phase=self._current_phase)

    async def stream_frames(
        self,
        max_frames: int | None = None,
        realtime: bool = False,
    ) -> AsyncIterator[TelemetryFrame]:
        """Asynchronously stream validated telemetry frames.

        Args:
            max_frames: Optional total number of frames to emit before closing stream.
            realtime: If True, paces frame emission to 1 / telemetry_rate_hz seconds.
                      If False, yields as fast as the consumer processes (accelerated mode).
        """
        if not self._is_connected:
            await self.connect()

        frames_emitted = 0
        while self._is_connected:
            if max_frames is not None and frames_emitted >= max_frames:
                break

            frame = self.simulator.step(phase=self._current_phase)
            frames_emitted += 1
            yield frame

            if realtime:
                await asyncio.sleep(self.simulator.dt)

    def generate_batch(
        self,
        count: int,
        phase: ScenarioPhase | None = None,
    ) -> list[TelemetryFrame]:
        """Synchronously generate a specified number of frames at current or specified phase."""
        if count <= 0:
            return []
        p = phase or self._current_phase
        return [self.simulator.step(phase=p) for _ in range(count)]

    def run_scenario(self, profile: ScenarioProfile) -> list[TelemetryFrame]:
        """Synchronously execute a full scenario profile and return all generated frames."""
        return self.simulator.run_scenario(profile)
