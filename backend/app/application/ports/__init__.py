"""Application boundary ports (abstract interfaces for dependency inversion)."""

from app.application.ports.diagnostics_ports import (
    IAnomalyDetector,
    IFaultClassifier,
    IHealthEvaluator,
)
from app.application.ports.simulation_ports import (
    ISimulationEngine,
    ITimeProvider,
)
from app.application.ports.telemetry_ports import (
    ITelemetryRepository,
    ITelemetrySource,
)

__all__ = [
    "ITelemetrySource",
    "ITelemetryRepository",
    "ISimulationEngine",
    "ITimeProvider",
    "IAnomalyDetector",
    "IFaultClassifier",
    "IHealthEvaluator",
]
