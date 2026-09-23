"""REST API endpoints for flight replay dataset cataloging, loading, and cursor transport controls."""

from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.api.dependencies import get_realtime_service, get_replay_service
from app.application.services.realtime_service import RealtimeTelemetryService
from app.application.services.replay_service import ReplayService
from app.domain.replay.models import ReplayCursorStatus, ReplayDatasetMetadata

router = APIRouter(prefix="/api/v1/replay", tags=["replay"])


class ReplayLoadRequest(BaseModel):
    """Request payload for loading a dataset into the replay engine."""

    filename: str = Field(
        ..., min_length=1, description="Filename of historical flight log in storage"
    )


class ReplayControlRequest(BaseModel):
    """Request payload for controlling replay cursor transport."""

    action: Literal["play", "pause", "resume", "reset", "seek", "speed", "mode"] = Field(
        ..., description="Transport action to execute"
    )
    target: Any = Field(
        default=None,
        description="Optional target value for seek (index/timestamp), speed (multiplier), or mode (REALTIME/ACCELERATED/OFFLINE_BATCH)",
    )


class ReplayModeRequest(BaseModel):
    """Request payload for switching active global telemetry source mode."""

    mode: Literal["LIVE", "REPLAY"] = Field(
        ..., description="Target telemetry operational source mode"
    )


@router.get("/datasets", response_model=list[ReplayDatasetMetadata])
def list_replay_datasets(
    service: ReplayService = Depends(get_replay_service),
) -> list[ReplayDatasetMetadata]:
    """Scan configured storage folders and return catalog of available flight log datasets."""
    return service.list_available_datasets()


@router.post("/load", response_model=ReplayCursorStatus)
def load_replay_dataset(
    req: ReplayLoadRequest,
    service: ReplayService = Depends(get_replay_service),
) -> ReplayCursorStatus:
    """Load a historical flight log dataset into memory for replay playback."""
    try:
        return service.load_dataset(req.filename)
    except FileNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load dataset: {e}",
        ) from e


@router.post("/control", response_model=ReplayCursorStatus)
def control_replay(
    req: ReplayControlRequest,
    service: ReplayService = Depends(get_replay_service),
) -> ReplayCursorStatus:
    """Send transport control command (play, pause, resume, reset, seek, speed) to replay cursor."""
    try:
        return service.control(req.action, req.target)
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/status", response_model=ReplayCursorStatus)
def get_replay_status(
    service: ReplayService = Depends(get_replay_service),
) -> ReplayCursorStatus:
    """Retrieve current replay cursor playback state and timeline position."""
    return service.get_status()


@router.post("/mode")
async def switch_telemetry_mode(
    req: ReplayModeRequest,
    realtime_service: RealtimeTelemetryService = Depends(get_realtime_service),
) -> dict[str, str]:
    """Switch active global telemetry streaming mode between LIVE and REPLAY."""
    success = await realtime_service.set_source_mode(req.mode)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to transition to {req.mode} mode. Verify dataset is loaded if selecting REPLAY.",
        )
    return {"status": "success", "mode": req.mode}
