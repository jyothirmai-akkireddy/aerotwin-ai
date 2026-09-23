"""Ports for simulation engine and deterministic clock providers."""

from abc import ABC, abstractmethod

from app.domain.engine.models import EngineState
from app.domain.entities.telemetry import TelemetryFrame
from app.domain.simulation.models import FaultInjectionCommand, SimulationScenario


class ITimeProvider(ABC):
    """Abstract port for temporal references (system wall-clock vs simulated replay time)."""

    @abstractmethod
    def now_utc(self) -> float:
        """Return current epoch timestamp in seconds."""
        pass

    @abstractmethod
    def monotonic(self) -> float:
        """Return monotonic clock value in seconds."""
        pass


class ISimulationEngine(ABC):
    """Abstract port for physics simulation engines."""

    @abstractmethod
    async def configure_scenario(self, scenario: SimulationScenario) -> None:
        """Set up simulation environment and initial parameters."""
        pass

    @abstractmethod
    async def step(self, dt_seconds: float) -> tuple[EngineState, TelemetryFrame]:
        """Advance the physics simulation by dt_seconds, returning ground truth and telemetry."""
        pass

    @abstractmethod
    async def inject_fault(self, command: FaultInjectionCommand) -> None:
        """Inject simulated mechanical/thermal anomaly."""
        pass

    @abstractmethod
    async def reset(self) -> None:
        """Reset the simulation state to nominal initial conditions."""
        pass
