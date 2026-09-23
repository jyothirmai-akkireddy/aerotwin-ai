"""API routes for Engine Degradation, Health Index, and RUL Prognostics (Phase 7)."""

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.api.dependencies import (
    get_ml_inference_service,
    get_physics_twin_service,
    get_prognostics_service,
)
from app.application.services.ml_service import MLInferenceService
from app.application.services.physics_twin_service import PhysicsTwinService
from app.application.services.prognostics_service import PrognosticsService
from app.domain.entities.telemetry import TelemetryFrame
from app.domain.ml.models import MLInferenceResult
from app.domain.physics.models import PhysicsTwinResult
from app.domain.prognostics.models import PrognosticResult

router = APIRouter(prefix="/api/v1/prognostics", tags=["Prognostics"])


class PrognosticsEvaluationRequest(BaseModel):
    """Evaluation request payload containing telemetry frame and optional physics / ML results."""

    frame: TelemetryFrame = Field(..., description="Observed telemetry frame")
    physics: PhysicsTwinResult | None = Field(
        default=None, description="Optional accompanying Phase 5 PhysicsTwinResult"
    )
    ml: MLInferenceResult | None = Field(
        default=None, description="Optional accompanying Phase 6 MLInferenceResult"
    )


@router.get(
    "/status",
    summary="Get prognostics service operational status, buffer metrics, and model provenance",
    response_model=dict[str, Any],
)
async def get_prognostics_status(
    service: PrognosticsService = Depends(get_prognostics_service),
) -> dict[str, Any]:
    """Retrieve operational diagnostics, buffer size, latency statistics, and empirical model metrics."""
    return service.get_status()


@router.get(
    "/current",
    summary="Get most recent evaluated prognostic result",
    response_model=PrognosticResult | None,
)
async def get_current_prognostics(
    service: PrognosticsService = Depends(get_prognostics_service),
) -> PrognosticResult | None:
    """Retrieve the most recently evaluated degradation and RUL result."""
    return service.get_current_result()


@router.post(
    "/evaluate",
    summary="Evaluate prognostics for an uploaded telemetry frame",
    response_model=PrognosticResult,
)
async def evaluate_prognostics_frame(
    request: PrognosticsEvaluationRequest,
    service: PrognosticsService = Depends(get_prognostics_service),
    physics_service: PhysicsTwinService = Depends(get_physics_twin_service),
    ml_service: MLInferenceService = Depends(get_ml_inference_service),
) -> PrognosticResult:
    """Execute health index calculation, causal trend analysis, and RUL estimation on provided frame."""
    physics_res = request.physics
    if physics_res is None and physics_service is not None:
        try:
            physics_res = physics_service.evaluate_frame(request.frame)
        except Exception:
            physics_res = None

    ml_res = request.ml
    if ml_res is None and ml_service is not None:
        try:
            ml_res = ml_service.evaluate(request.frame, physics_res)
        except Exception:
            ml_res = None

    return service.evaluate(request.frame, physics_res, ml_res)
