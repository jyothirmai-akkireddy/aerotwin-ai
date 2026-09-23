"""Versioned WebSocket protocol models (v1.0.0).

Strictly structured messages for realtime telemetry streaming, session status,
safe error delivery, and bidirectional simulation commands.
"""

import time
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from app.domain.entities.telemetry import TelemetryFrame
from app.domain.mission.models import MissionTelemetryContext
from app.domain.ml.models import MLInferenceResult
from app.domain.physics.models import PhysicsTwinResult
from app.domain.prognostics.models import PrognosticResult
from app.domain.replay.models import ReplayCursorStatus


class TelemetryMessage(BaseModel):
    """Outbound real-time telemetry observation broadcast."""

    type: Literal["telemetry"] = "telemetry"
    version: str = "1.0.0"
    timestamp: float = Field(..., description="Authoritative simulation epoch timestamp (seconds)")
    sequence_id: int = Field(..., ge=0, description="Monotonically increasing sequence ID")
    server_time: float = Field(
        default_factory=time.time, description="Server wall-clock UTC epoch timestamp (seconds)"
    )
    source_mode: Literal["LIVE", "REPLAY"] = Field(
        default="LIVE", description="Authoritative active telemetry data source mode"
    )
    payload: TelemetryFrame = Field(
        ..., description="Complete standardized domain telemetry payload"
    )
    physics: PhysicsTwinResult | None = Field(
        default=None, description="Physics Twin expected state and residuals"
    )
    ml: MLInferenceResult | None = Field(
        default=None, description="AI Anomaly Detection and Fault Classification results"
    )
    prognostics: PrognosticResult | None = Field(
        default=None,
        description="Engine degradation, health index, causal trends, and RUL prognostics",
    )
    mission: MissionTelemetryContext | None = Field(
        default=None, description="Active flight mission context"
    )
    replay: ReplayCursorStatus | None = Field(
        default=None, description="Active flight replay cursor status"
    )


class StatusMessage(BaseModel):
    """Outbound session and connection status notification."""

    type: Literal["status"] = "status"
    version: str = "1.0.0"
    status: Literal["connected", "running", "paused", "stopped", "degraded", "error"] = Field(
        ..., description="Current operational state of the telemetry stream"
    )
    message: str = Field(default="", description="Human-readable status descriptor")
    server_time: float = Field(default_factory=time.time)


class ErrorMessage(BaseModel):
    """Outbound structured and sanitized error message."""

    type: Literal["error"] = "error"
    version: str = "1.0.0"
    code: str = Field(..., description="Standardized error code (e.g. INVALID_MESSAGE)")
    message: str = Field(..., description="Safe, client-facing error description")
    server_time: float = Field(default_factory=time.time)


class HeartbeatMessage(BaseModel):
    """Outbound periodic liveness ping."""

    type: Literal["heartbeat"] = "heartbeat"
    version: str = "1.0.0"
    server_time: float = Field(default_factory=time.time)


class CommandMessage(BaseModel):
    """Inbound client simulation control command."""

    type: Literal["command"] = "command"
    version: str = "1.0.0"
    command: Literal[
        "start",
        "pause",
        "resume",
        "reset",
        "set_scenario",
        "set_rate",
        "replay_play",
        "replay_pause",
        "replay_resume",
        "replay_seek",
        "replay_speed",
        "replay_mode",
        "replay_reset",
        "set_source",
    ] = Field(..., description="Whitelisted command name")
    params: dict[str, Any] = Field(default_factory=dict, description="Validated command parameters")

    @model_validator(mode="before")
    @classmethod
    def extract_root_params(cls, values: Any) -> Any:
        """Normalize top-level parameter arguments into params dictionary."""
        if isinstance(values, dict):
            params = dict(values.get("params") or {})
            for k, v in values.items():
                if k not in ("type", "version", "command", "params"):
                    params.setdefault(k, v)
            values["params"] = params
        return values


class PingMessage(BaseModel):
    """Inbound client ping."""

    type: Literal["ping"] = "ping"
