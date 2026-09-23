"""API routes for AI Anomaly Detection and Supervised Fault Classification (Phase 6)."""

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.api.dependencies import get_ml_inference_service, get_physics_twin_service
from app.application.services.ml_service import MLInferenceService
from app.application.services.physics_twin_service import PhysicsTwinService
from app.domain.entities.telemetry import TelemetryFrame
from app.domain.ml.features import FEATURE_NAMES, FEATURE_SCHEMA_VERSION, NOMINAL_BASELINES
from app.domain.ml.models import MLInferenceResult
from app.domain.physics.models import PhysicsTwinResult

router = APIRouter(prefix="/api/v1/ml", tags=["Machine Learning"])


class MLEvaluationRequest(BaseModel):
    """Evaluation request payload containing telemetry frame and optional physics twin result."""

    frame: TelemetryFrame = Field(..., description="Observed telemetry frame")
    physics: PhysicsTwinResult | None = Field(
        default=None, description="Optional accompanying Phase 5 PhysicsTwinResult"
    )


@router.get(
    "/status",
    summary="Get ML diagnostic service operational status and diagnostics",
    response_model=dict[str, Any],
)
async def get_ml_status(
    service: MLInferenceService = Depends(get_ml_inference_service),
) -> dict[str, Any]:
    """Retrieve operational diagnostics, cumulative fault counts, and average latencies."""
    return service.get_diagnostics()


@router.get(
    "/models",
    summary="Get ML model metadata, versions, thresholds, and provenance",
    response_model=dict[str, Any],
)
async def get_ml_models(
    service: MLInferenceService = Depends(get_ml_inference_service),
) -> dict[str, Any]:
    """Retrieve details on loaded Anomaly Detector and Fault Classifier artifacts."""
    return service.get_model_metadata()


@router.get(
    "/features",
    summary="Get 24-feature schema manifest and baseline values",
    response_model=dict[str, Any],
)
async def get_ml_features() -> dict[str, Any]:
    """Retrieve the deterministic 24-feature schema manifest."""
    return {
        "schema_version": FEATURE_SCHEMA_VERSION,
        "feature_count": len(FEATURE_NAMES),
        "features": FEATURE_NAMES,
        "nominal_baselines": NOMINAL_BASELINES,
    }


@router.get(
    "/current",
    summary="Get most recent ML evaluation result",
    response_model=MLInferenceResult | None,
)
async def get_current_ml(
    service: MLInferenceService = Depends(get_ml_inference_service),
) -> MLInferenceResult | None:
    """Retrieve the most recent evaluated ML diagnostic result."""
    return service.get_latest_result()


@router.post(
    "/evaluate",
    summary="Evaluate ML diagnostics for an uploaded telemetry frame",
    response_model=MLInferenceResult,
)
async def evaluate_frame(
    request: MLEvaluationRequest,
    service: MLInferenceService = Depends(get_ml_inference_service),
    physics_service: PhysicsTwinService = Depends(get_physics_twin_service),
) -> MLInferenceResult:
    """Execute feature extraction, anomaly detection, and fault classification on provided frame."""
    physics_res = request.physics
    if physics_res is None and physics_service is not None:
        try:
            physics_res = physics_service.evaluate_frame(request.frame)
        except Exception:
            physics_res = None

    return service.evaluate(request.frame, physics_res)
