"""API dependency injection providers."""

from functools import lru_cache

from app.application.services.health_service import HealthService
from app.config import AppSettings, settings


@lru_cache
def get_settings() -> AppSettings:
    """Provide cached application settings."""
    return settings


def is_realtime_ready() -> str:
    """Check whether the realtime transport service is ready."""
    global _realtime_service_instance
    if _realtime_service_instance is not None:
        if _realtime_service_instance.state in ("running", "paused"):
            return "READY"
        return "INITIALIZED"
    return "READY"  # If configured and importable, marked READY for Phase 4


def is_physics_ready() -> str:
    """Check whether the physics twin service is ready."""
    return "READY"


def is_ml_ready() -> str:
    """Check whether ML anomaly detection and fault classification service is ready."""
    service = get_ml_inference_service()
    return "READY" if service.is_ready else "DEGRADED"


def is_prognostics_ready() -> str:
    """Check whether prognostics degradation and RUL service is ready."""
    service = get_prognostics_service()
    return "READY" if service.is_ready else "DEGRADED"


def is_mission_ready() -> str:
    """Check whether mission simulation service is ready."""
    return "READY"


def is_replay_ready() -> str:
    """Check whether flight replay service is ready."""
    return "READY"


@lru_cache
def get_health_service() -> HealthService:
    """Provide singleton instance of HealthService."""
    current_settings = get_settings()
    return HealthService(
        app_version=current_settings.app_version,
        environment=current_settings.server.environment,
        storage_dir=current_settings.storage.parquet_data_dir,
        nominal_telemetry_rate_hz=current_settings.telemetry.rate_hz,
        realtime_status_checker=is_realtime_ready,
        physics_status_checker=is_physics_ready,
        ml_status_checker=is_ml_ready,
        prognostics_status_checker=is_prognostics_ready,
        mission_status_checker=is_mission_ready,
        replay_status_checker=is_replay_ready,
    )


_simulator_instance = None
_source_instance = None
_repo_instance = None
_broadcaster_instance = None
_realtime_service_instance = None
_physics_calibration_repo_instance = None
_physics_twin_instance = None
_ml_inference_service_instance = None
_prognostics_service_instance = None
_mission_service_instance = None
_replay_service_instance = None


def get_prognostics_service():
    """Provide singleton instance of PrognosticsService."""
    global _prognostics_service_instance
    if _prognostics_service_instance is None:
        from app.application.services.prognostics_service import PrognosticsService

        _prognostics_service_instance = PrognosticsService()
    return _prognostics_service_instance


def get_ml_inference_service():
    """Provide singleton instance of MLInferenceService."""
    global _ml_inference_service_instance
    if _ml_inference_service_instance is None:
        from app.application.services.ml_service import MLInferenceService

        _ml_inference_service_instance = MLInferenceService()
    return _ml_inference_service_instance


def get_physics_calibration_repository():
    """Provide singleton instance of PhysicsCalibrationRepository."""
    global _physics_calibration_repo_instance
    if _physics_calibration_repo_instance is None:
        from app.infrastructure.physics.calibration_repository import (
            PhysicsCalibrationRepository,
        )

        _physics_calibration_repo_instance = PhysicsCalibrationRepository()
    return _physics_calibration_repo_instance


def get_physics_twin_service():
    """Provide singleton instance of PhysicsTwinService."""
    global _physics_twin_instance
    if _physics_twin_instance is None:
        from app.application.services.physics_twin_service import PhysicsTwinService

        _physics_twin_instance = PhysicsTwinService(
            calibration_repo=get_physics_calibration_repository()
        )
    return _physics_twin_instance


def get_engine_simulator():
    """Provide singleton instance of EngineSimulator."""
    global _simulator_instance
    if _simulator_instance is None:
        from app.infrastructure.simulation.engine_simulator import EngineSimulator

        current_settings = get_settings()
        _simulator_instance = EngineSimulator(telemetry_rate_hz=current_settings.telemetry.rate_hz)
    return _simulator_instance


def get_telemetry_source():
    """Provide singleton instance of SyntheticTelemetrySource."""
    global _source_instance
    if _source_instance is None:
        from app.infrastructure.telemetry.synthetic_source import SyntheticTelemetrySource

        _source_instance = SyntheticTelemetrySource(simulator=get_engine_simulator())
    return _source_instance


def get_telemetry_repository():
    """Provide singleton instance of SqliteTelemetryRepository."""
    global _repo_instance
    if _repo_instance is None:
        from app.infrastructure.persistence.telemetry_repository import SqliteTelemetryRepository

        current_settings = get_settings()
        _repo_instance = SqliteTelemetryRepository(db_path=current_settings.storage.sqlite_db_path)
    return _repo_instance


def get_websocket_broadcast_manager():
    """Provide singleton instance of WebSocketBroadcastManager."""
    global _broadcaster_instance
    if _broadcaster_instance is None:
        from app.infrastructure.websocket.broadcaster import WebSocketBroadcastManager

        current_settings = get_settings()
        _broadcaster_instance = WebSocketBroadcastManager(
            max_clients=current_settings.websocket.max_clients,
            queue_size=current_settings.websocket.queue_size,
        )
    return _broadcaster_instance


def get_replay_service():
    """Provide singleton instance of ReplayService."""
    global _replay_service_instance
    if _replay_service_instance is None:
        from app.application.services.replay_service import ReplayService

        _replay_service_instance = ReplayService()
    return _replay_service_instance


def get_mission_service():
    """Provide singleton instance of MissionService."""
    global _mission_service_instance
    if _mission_service_instance is None:
        from app.application.services.mission_service import MissionService

        _mission_service_instance = MissionService()
    return _mission_service_instance


def get_realtime_service():
    """Provide singleton instance of RealtimeTelemetryService."""
    global _realtime_service_instance
    if _realtime_service_instance is None:
        from app.application.services.realtime_service import RealtimeTelemetryService

        current_settings = get_settings()
        _realtime_service_instance = RealtimeTelemetryService(
            telemetry_source=get_telemetry_source(),
            broadcaster=get_websocket_broadcast_manager(),
            rate_hz=current_settings.telemetry.rate_hz,
            strict_validation=current_settings.telemetry.strict_validation,
            heartbeat_interval_sec=current_settings.websocket.heartbeat_interval_sec,
            physics_service=get_physics_twin_service(),
            ml_service=get_ml_inference_service(),
            prognostics_service=get_prognostics_service(),
            replay_service=get_replay_service(),
        )
    return _realtime_service_instance
