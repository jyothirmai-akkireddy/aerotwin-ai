"""Abstract port for telemetry streaming sources."""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from app.domain.entities.telemetry import TelemetryFrame


class ITelemetryProvider(ABC):
    """Port for streaming telemetry frames (Simulated, Replay, or Hardware CAN)."""

    @abstractmethod
    async def connect(self) -> None:
        """Initialize telemetry source connection."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Safely close and clean up source resources."""
        pass

    @abstractmethod
    def stream_frames(self) -> AsyncIterator[TelemetryFrame]:
        """Asynchronously generate telemetry frames."""
        pass
