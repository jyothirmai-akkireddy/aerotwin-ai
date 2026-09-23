"""Abstract ports for ML Anomaly Detection and Fault Classification."""

from abc import ABC, abstractmethod
from typing import Any

from app.domain.value_objects.residuals import ResidualVector


class IAnomalyDetector(ABC):
    """Port for unsupervised anomaly detection on residual vectors."""

    @abstractmethod
    def detect(self, residuals: ResidualVector) -> tuple[bool, float]:
        """Detect anomaly on residual vector.

        Returns:
            Tuple of (is_anomaly: bool, anomaly_score: float)
        """
        pass


class IFaultClassifier(ABC):
    """Port for supervised multi-class fault classification."""

    @abstractmethod
    def classify(self, residuals: ResidualVector) -> tuple[str, float, dict[str, float]]:
        """Classify fault mode.

        Returns:
            Tuple of (fault_label: str, confidence: float, class_probabilities: Dict[str, float])
        """
        pass


class IExplainabilityService(ABC):
    """Port for Explainable AI (SHAP value attribution)."""

    @abstractmethod
    def explain(self, residuals: ResidualVector) -> dict[str, Any]:
        """Compute feature contributions for a given diagnostic state."""
        pass
