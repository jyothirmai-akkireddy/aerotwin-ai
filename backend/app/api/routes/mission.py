"""REST API endpoints for mission flight definitions, deterministic simulation, and dataset export."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.api.dependencies import get_mission_service
from app.application.services.mission_service import MissionService
from app.domain.entities.telemetry import TelemetryFrame
from app.domain.mission.models import MissionDefinition, MissionSimulationSummary

router = APIRouter(prefix="/api/v1/missions", tags=["missions"])


class MissionSimulateRequest(BaseModel):
    """Request payload for initiating a mission simulation."""

    mission_id: str | None = Field(
        default=None, description="Identifier of a predefined mission to execute"
    )
    custom_definition: MissionDefinition | None = Field(
        default=None, description="Optional custom MissionDefinition payload"
    )
    rate_hz: int = Field(default=10, ge=1, le=100, description="Telemetry generation rate in Hz")
    seed: int = Field(
        default=42, description="Random seed for deterministic sensor noise generation"
    )
    persist_dataset: bool = Field(
        default=True, description="Whether to export simulation dataset to disk"
    )
    include_frames: bool = Field(
        default=False,
        description="Opt-in to return inline frames (strictly bounded to max 500 frames)",
    )


class MissionSimulateResponse(BaseModel):
    """Bounded response payload for mission simulation execution."""

    run_id: str
    mission_id: str
    mission_version: str
    duration_sec: float
    frame_count: int
    summary: dict[str, Any]
    phase_summaries: list[dict[str, Any]]
    dataset_path: str | None = None
    inline_frames: list[TelemetryFrame] | None = None
    prototype_disclaimer: str


@router.get("/predefined", response_model=list[dict[str, Any]])
def list_predefined_missions(
    service: MissionService = Depends(get_mission_service),
) -> list[dict[str, Any]]:
    """List all available predefined synthetic reference missions."""
    return service.list_predefined_missions()


@router.get("/predefined/{mission_id}", response_model=MissionDefinition)
def get_mission_definition(
    mission_id: str,
    service: MissionService = Depends(get_mission_service),
) -> MissionDefinition:
    """Retrieve full definition of a predefined mission."""
    mission = service.get_mission_definition(mission_id)
    if not mission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Predefined mission '{mission_id}' not found.",
        )
    return mission


@router.post("/simulate", response_model=MissionSimulateResponse)
def simulate_mission(
    req: MissionSimulateRequest,
    service: MissionService = Depends(get_mission_service),
) -> MissionSimulateResponse:
    """Execute a mission simulation and return bounded summary metrics.

    If inline_frames=True is requested, frames are returned only if frame_count <= 500.
    Otherwise, frames are persisted to disk and accessible via flight replay.
    """
    if req.custom_definition:
        mission = req.custom_definition
    elif req.mission_id:
        mission = service.get_mission_definition(req.mission_id)
        if not mission:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Predefined mission '{req.mission_id}' not found.",
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Either 'mission_id' or 'custom_definition' must be provided.",
        )

    try:
        summary, inline_frames = service.simulate_mission(
            mission=mission,
            rate_hz=req.rate_hz,
            seed=req.seed,
            persist_dataset=req.persist_dataset,
            include_frames=req.include_frames,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Simulation failed: {e}",
        ) from e

    return MissionSimulateResponse(
        run_id=summary.run_id,
        mission_id=summary.mission_id,
        mission_version=summary.mission_version,
        duration_sec=summary.total_duration_sec,
        frame_count=summary.total_frames,
        summary={
            "fuel_consumed_liters": summary.fuel_consumed_liters,
            "fuel_mass_kg": summary.fuel_mass_kg,
            "max_cht_c": summary.max_cht_c,
            "max_egt_c": summary.max_egt_c,
            "max_oil_temp_c": summary.max_oil_temp_c,
            "min_oil_pressure_bar": summary.min_oil_pressure_bar,
            "peak_vibration_rms": summary.peak_vibration_rms,
            "max_altitude_m": summary.max_altitude_m,
        },
        phase_summaries=[ps.model_dump() for ps in summary.phase_summaries],
        dataset_path=summary.dataset_path,
        inline_frames=inline_frames,
        prototype_disclaimer=summary.prototype_disclaimer,
    )


@router.post("/export", response_model=MissionSimulationSummary)
def export_mission_dataset(
    req: MissionSimulateRequest,
    service: MissionService = Depends(get_mission_service),
) -> MissionSimulationSummary:
    """Execute a mission simulation and export to persistent storage."""
    req.persist_dataset = True
    req.include_frames = False
    if req.custom_definition:
        mission = req.custom_definition
    elif req.mission_id:
        mission = service.get_mission_definition(req.mission_id)
        if not mission:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Predefined mission '{req.mission_id}' not found.",
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Either 'mission_id' or 'custom_definition' must be provided.",
        )

    summary, _ = service.simulate_mission(
        mission=mission,
        rate_hz=req.rate_hz,
        seed=req.seed,
        persist_dataset=True,
        include_frames=False,
    )
    return summary
