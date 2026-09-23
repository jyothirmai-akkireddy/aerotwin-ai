"""Domain models and DTOs for flight replay status, cursor state, and dataset metadata."""

from pydantic import BaseModel, Field

from app.domain.replay.enums import PlaybackState, ReplayExecutionMode, ReplayFormat


class ReplayCursorStatus(BaseModel):
    """Dynamic snapshot of replay cursor position, pacing, and execution state."""

    playback_state: PlaybackState = Field(..., description="Current transport state")
    execution_mode: ReplayExecutionMode = Field(..., description="Active pacing execution mode")
    current_index: int = Field(..., ge=0, description="Zero-based current frame index")
    total_frames: int = Field(..., ge=0, description="Total frames loaded in dataset")
    data_timestamp: float = Field(
        ..., description="Authoritative recorded UTC epoch timestamp of current frame"
    )
    start_timestamp: float = Field(..., description="Recorded UTC epoch timestamp of first frame")
    end_timestamp: float = Field(..., description="Recorded UTC epoch timestamp of final frame")
    elapsed_sim_time_sec: float = Field(
        ..., ge=0.0, description="Elapsed flight time since mission start (seconds)"
    )
    total_sim_time_sec: float = Field(
        ..., ge=0.0, description="Total flight duration recorded in dataset (seconds)"
    )
    progress_pct: float = Field(
        ..., ge=0.0, le=100.0, description="Playback completion percentage [0..100]"
    )
    playback_speed: float = Field(
        ..., ge=0.0, description="Playback rate multiplier (1.0 = real-time; 0.0 = batch)"
    )
    source_filename: str | None = Field(default=None, description="Active dataset filename")
    is_looping: bool = Field(default=False, description="Whether replay wraps to beginning on EOF")


class ReplayDatasetMetadata(BaseModel):
    """Metadata describing an available historical flight log file."""

    filename: str = Field(..., description="Relative dataset filename within storage")
    format: ReplayFormat = Field(..., description="Storage format type")
    size_bytes: int = Field(..., ge=0, description="File size in bytes")
    total_frames: int = Field(..., ge=0, description="Total parsed telemetry frames count")
    start_timestamp: float = Field(..., description="Recorded start UTC epoch timestamp")
    end_timestamp: float = Field(..., description="Recorded end UTC epoch timestamp")
    duration_sec: float = Field(..., ge=0.0, description="Recorded flight duration in seconds")
    nominal_rate_hz: float = Field(
        default=10.0, gt=0.0, description="Inferred average telemetry frequency"
    )
