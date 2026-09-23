"""Ports for AI diagnostics, anomaly detection, and health evaluation."""

from abc import ABC, abstractmethod

from app.domain.fault.models import FaultEvent
from app.domain.health.models import HealthState
from app.domain.value_objects.residuals import ResidualVector


class IAnomalyDetector(ABC):
    """Port for unsupervised anomaly scoring on residual vectors."""

    @abstractmethod
    def detect(self, residuals: ResidualVector) -> tuple[bool, float]:
        """Detect anomaly on residual vector. Returns (is_anomaly, anomaly_score)."""
        pass


class IFaultClassifier(ABC):
    """Port for supervised multi-class fault classification."""

    @abstractmethod
    def classify(self, residuals: ResidualVector) -> tuple[str, float, dict[str, float]]:
        """Classify fault mode. Returns (fault_label, confidence, class_probabilities)."""
        pass


class IHealthEvaluator(ABC):
    """Port for composite engine health and RUL assessment."""

    @abstractmethod
    def evaluate(self, residuals: ResidualVector, recent_faults: list[FaultEvent]) -> HealthState:
        """Evaluate overall health index and subsystem degradation."""
        pass
