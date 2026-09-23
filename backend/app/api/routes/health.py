"""Health, readiness, and system metadata endpoints."""

from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_health_service, get_settings
from app.api.schemas.common import (
    HealthResponseDTO,
    ReadinessResponseDTO,
    SystemInfoDTO,
)
from app.application.services.health_service import HealthService
from app.config import AppSettings

router = APIRouter(tags=["System Diagnostics & Health"])


@router.get("/health", response_model=HealthResponseDTO, summary="Root Liveness Probe")
@router.get("/api/v1/health", response_model=HealthResponseDTO, summary="API v1 Liveness Probe")
async def health_check(
    health_service: HealthService = Depends(get_health_service),
) -> HealthResponseDTO:
    """Liveness probe verifying that the FastAPI server process is alive and responsive."""
    data = health_service.get_liveness()
    return HealthResponseDTO(**data)


@router.get(
    "/ready",
    response_model=ReadinessResponseDTO,
    status_code=status.HTTP_200_OK,
    summary="Root Readiness Probe",
)
@router.get(
    "/api/v1/ready",
    response_model=ReadinessResponseDTO,
    status_code=status.HTTP_200_OK,
    summary="API v1 Readiness Probe",
)
async def readiness_check(
    health_service: HealthService = Depends(get_health_service),
) -> ReadinessResponseDTO:
    """Readiness probe checking foundational storage directories and configuration status."""
    data = health_service.get_readiness()
    return ReadinessResponseDTO(**data)


@router.get("/api/v1/info", response_model=SystemInfoDTO, summary="System Metadata")
async def system_info(
    settings: AppSettings = Depends(get_settings),
) -> SystemInfoDTO:
    """Return general system architecture info, engine baseline designation, and telemetry rates."""
    return SystemInfoDTO(
        name=settings.app_name,
        version=settings.app_version,
        description=settings.app_description,
        environment=settings.server.environment,
        engine_baseline=settings.simulation.engine_model,
        telemetry_rate_hz=settings.telemetry.rate_hz,
        dt_seconds=settings.telemetry.dt_seconds,
    )
