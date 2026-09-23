"""Ports for telemetry source streaming and persistence."""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from app.domain.entities.telemetry import TelemetryFrame


class ITelemetrySource(ABC):
    """Abstract port for receiving sequential telemetry frames (Simulation, File Replay, or Hardware CAN)."""

    @abstractmethod
    async def connect(self) -> None:
        """Connect to the underlying telemetry stream or initialize generator."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Safely disconnect or shut down the stream."""
        pass

    @abstractmethod
    async def get_next_frame(self) -> TelemetryFrame:
        """Produce or fetch the next telemetry frame."""
        pass

    @abstractmethod
    def stream_frames(self) -> AsyncIterator[TelemetryFrame]:
        """Asynchronously stream validated telemetry frames."""
        pass


class ITelemetryRepository(ABC):
    """Abstract port for persisting and retrieving telemetry records."""

    @abstractmethod
    async def save_frame(self, frame: TelemetryFrame) -> None:
        """Persist a single validated telemetry frame."""
        pass

    @abstractmethod
    async def save_batch(self, frames: list[TelemetryFrame]) -> None:
        """Persist a batch of frames in bulk."""
        pass

    @abstractmethod
    async def get_recent_frames(self, limit: int = 100) -> list[TelemetryFrame]:
        """Retrieve recent historical frames."""
        pass

    @abstractmethod
    async def query_range(self, start_time: float, end_time: float) -> list[TelemetryFrame]:
        """Retrieve telemetry frames within a specified UTC epoch timestamp range."""
        pass
