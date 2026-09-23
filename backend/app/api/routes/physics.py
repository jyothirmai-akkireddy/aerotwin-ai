"""API routes for Physics-Informed Digital Twin (PIDT) state, residuals, and calibration."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_engine_simulator, get_physics_twin_service
from app.application.services.physics_twin_service import PhysicsTwinService
from app.domain.entities.telemetry import TelemetryFrame
from app.domain.physics.models import (
    PhysicsCalibrationParameters,
    PhysicsResidualSet,
    PhysicsTwinResult,
)

router = APIRouter(prefix="/api/v1/physics", tags=["Physics Twin"])


@router.get(
    "/status",
    summary="Get Physics Twin operational status and diagnostics",
    response_model=dict[str, Any],
)
async def get_physics_status(
    service: PhysicsTwinService = Depends(get_physics_twin_service),
) -> dict[str, Any]:
    """Retrieve operational diagnostics, calibration version, and average evaluation latency."""
    return service.get_diagnostics()


@router.get(
    "/current",
    summary="Get latest Physics Twin state and residuals",
    response_model=PhysicsTwinResult,
)
async def get_current_physics(
    service: PhysicsTwinService = Depends(get_physics_twin_service),
    simulator=Depends(get_engine_simulator),
) -> PhysicsTwinResult:
    """Retrieve current analytical expected state and residual vector.

    If no frame has been evaluated yet, evaluates the current simulator frame.
    """
    latest = service.get_latest_result()
    if latest is not None:
        return latest

    # Fall back to evaluating current simulator state
    frame = simulator.step()
    return service.evaluate_frame(frame)


@router.get(
    "/residuals",
    summary="Get latest calculated residual set",
    response_model=PhysicsResidualSet,
)
async def get_current_residuals(
    service: PhysicsTwinService = Depends(get_physics_twin_service),
    simulator=Depends(get_engine_simulator),
) -> PhysicsResidualSet:
    """Retrieve current directional raw and normalized residuals."""
    latest = service.get_latest_result()
    if latest is not None:
        return latest.residuals

    frame = simulator.step()
    result = service.evaluate_frame(frame)
    return result.residuals


@router.get(
    "/calibration",
    summary="Get active physics calibration parameters",
    response_model=PhysicsCalibrationParameters,
)
async def get_calibration_parameters(
    service: PhysicsTwinService = Depends(get_physics_twin_service),
) -> PhysicsCalibrationParameters:
    """Retrieve current engine physical constants, time constants, and empirical sigma scales."""
    return service.cal


@router.post(
    "/calibration",
    summary="Update physics calibration parameters",
    response_model=PhysicsCalibrationParameters,
)
async def update_calibration_parameters(
    params: PhysicsCalibrationParameters,
    service: PhysicsTwinService = Depends(get_physics_twin_service),
) -> PhysicsCalibrationParameters:
    """Update and persist calibration parameters across physics sub-models."""
    try:
        service.reload_calibration(params)
        return service.cal
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to apply calibration parameters: {e}",
        ) from e


@router.post(
    "/evaluate",
    summary="Evaluate expected state and residuals for a telemetry frame",
    response_model=PhysicsTwinResult,
)
async def evaluate_frame(
    frame: TelemetryFrame,
    service: PhysicsTwinService = Depends(get_physics_twin_service),
) -> PhysicsTwinResult:
    """Perform on-demand physics evaluation of an arbitrary telemetry frame."""
    return service.evaluate_frame(frame)
