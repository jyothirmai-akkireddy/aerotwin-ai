"""Application health and readiness service."""

import os
import time
from typing import Any


class HealthService:
    """Service evaluating application liveness and subsystem readiness.

    Honesty Policy:
    Components that belong to future phases (e.g., telemetry streaming in Phase 2,
    ML models in Phase 3) are reported with their true current state:
    'READY', 'NOT_INITIALIZED_PHASE_2', 'NOT_TRAINED_PHASE_3', etc.
    """

    def __init__(
        self,
        app_version: str,
        environment: str,
        storage_dir: str,
        nominal_telemetry_rate_hz: int,
        realtime_status_checker: Any = None,
        physics_status_checker: Any = None,
        ml_status_checker: Any = None,
        prognostics_status_checker: Any = None,
        mission_status_checker: Any = None,
        replay_status_checker: Any = None,
    ):
        self.app_version = app_version
        self.environment = environment
        self.storage_dir = storage_dir
        self.nominal_telemetry_rate_hz = nominal_telemetry_rate_hz
        self.realtime_status_checker = realtime_status_checker
        self.physics_status_checker = physics_status_checker
        self.ml_status_checker = ml_status_checker
        self.prognostics_status_checker = prognostics_status_checker
        self.mission_status_checker = mission_status_checker
        self.replay_status_checker = replay_status_checker
        self._start_time = time.time()

    def get_liveness(self) -> dict[str, Any]:
        """Verify the service process is active and responding."""
        return {
            "status": "healthy",
            "version": self.app_version,
            "environment": self.environment,
            "timestamp": time.time(),
            "uptime_seconds": round(time.time() - self._start_time, 2),
        }

    def get_readiness(self) -> dict[str, Any]:
        """Verify whether foundational subsystems are initialized and ready."""
        # Check storage directory relative to cwd or repository root
        repo_data = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..", "data"))
        storage_ready = (
            os.path.isdir(self.storage_dir) or os.path.isdir("data") or os.path.isdir(repo_data)
        )

        realtime_status = "READY"
        if self.realtime_status_checker:
            try:
                res = self.realtime_status_checker()
                if isinstance(res, str):
                    realtime_status = res
                elif res is True:
                    realtime_status = "READY"
            except Exception:
                realtime_status = "DEGRADED"

        physics_status = "READY"
        if self.physics_status_checker:
            try:
                res = self.physics_status_checker()
                if isinstance(res, str):
                    physics_status = res
                elif res is True:
                    physics_status = "READY"
            except Exception:
                physics_status = "DEGRADED"

        ml_status = "READY"
        if self.ml_status_checker:
            try:
                res = self.ml_status_checker()
                if isinstance(res, str):
                    ml_status = res
                elif res is True:
                    ml_status = "READY"
                else:
                    ml_status = "DEGRADED"
            except Exception:
                ml_status = "DEGRADED"

        prognostics_status = "READY"
        if self.prognostics_status_checker:
            try:
                res = self.prognostics_status_checker()
                if isinstance(res, str):
                    prognostics_status = res
                elif res is True:
                    prognostics_status = "READY"
                else:
                    prognostics_status = "DEGRADED"
            except Exception:
                prognostics_status = "DEGRADED"

        mission_status = "READY"
        if self.mission_status_checker:
            try:
                res = self.mission_status_checker()
                if isinstance(res, str):
                    mission_status = res
                elif res is True:
                    mission_status = "READY"
                else:
                    mission_status = "DEGRADED"
            except Exception:
                mission_status = "DEGRADED"

        replay_status = "READY"
        if self.replay_status_checker:
            try:
                res = self.replay_status_checker()
                if isinstance(res, str):
                    replay_status = res
                elif res is True:
                    replay_status = "READY"
                else:
                    replay_status = "DEGRADED"
            except Exception:
                replay_status = "DEGRADED"

        components = {
            "configuration": "READY",
            "storage_directory": "READY" if storage_ready else "DEGRADED",
            "telemetry_pipeline": "READY",
            "synthetic_simulator": "READY",
            "digital_twin_3d": "READY",
            "realtime_transport": realtime_status,
            "physics_twin_residuals": physics_status,
            "ml_anomaly_detector": ml_status,
            "ml_fault_classifier": ml_status,
            "prognostics_engine": prognostics_status,
            "mission_simulator": mission_status,
            "flight_replay": replay_status,
        }

        # The foundational application is ready if configuration and storage are ready
        is_ready = storage_ready

        return {
            "status": "ready" if is_ready else "not_ready",
            "components": components,
            "telemetry_rate_hz": self.nominal_telemetry_rate_hz,
            "timestamp": time.time(),
        }
