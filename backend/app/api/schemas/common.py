"""Common API response schemas maintaining separation between API DTOs and internal domain models."""

from typing import Any

from pydantic import BaseModel


class ErrorResponseDTO(BaseModel):
    """Standardized API error response payload preventing internal data leakage."""

    status: str = "error"
    error_code: str
    message: str
    request_id: str | None = None
    timestamp: float
    details: dict[str, Any] | None = None


class HealthResponseDTO(BaseModel):
    """Liveness probe response model."""

    status: str = "healthy"
    version: str
    environment: str
    timestamp: float
    uptime_seconds: float


class ReadinessResponseDTO(BaseModel):
    """Readiness probe response model detailing subsystem operational status."""

    status: str = "ready"
    components: dict[str, str]
    telemetry_rate_hz: int
    timestamp: float


class SystemInfoDTO(BaseModel):
    """General system metadata response."""

    name: str
    version: str
    description: str
    environment: str
    engine_baseline: str
    telemetry_rate_hz: int
    dt_seconds: float
