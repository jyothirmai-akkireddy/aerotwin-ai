"""Prognostics Application Service for Engine Degradation and RUL Evaluation."""

import json
import os
import threading
import time
from typing import Any

from app.domain.entities.telemetry import TelemetryFrame
from app.domain.ml.models import MLInferenceResult
from app.domain.physics.models import PhysicsTwinResult
from app.domain.prognostics.features import (
    PROGNOSTIC_FEATURE_SCHEMA_VERSION,
    CausalTelemetryBuffer,
    PrognosticFeatureExtractor,
)
from app.domain.prognostics.health_index import HealthIndexCalculator
from app.domain.prognostics.models import (
    PrognosticResult,
)
from app.domain.prognostics.rul_model import RULEstimator
from app.infrastructure.logging.logger import get_logger

logger = get_logger("aerotwin.prognostics.service")

# Resolve models dir either at repo root (d:/sih/models) or backend/models
_repo_models = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../../../models/prognostics")
)
_backend_models = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../../models/prognostics")
)
PROGNOSTICS_MODELS_DIR = _repo_models if os.path.exists(_repo_models) else _backend_models


class PrognosticsService:
    """Thread-safe application service orchestrating degradation tracking and RUL prognostics."""

    def __init__(self, models_dir: str | None = None) -> None:
        self.models_dir = models_dir or PROGNOSTICS_MODELS_DIR
        self._lock = threading.Lock()

        self.buffer = CausalTelemetryBuffer(max_capacity=300)
        self.hi_calc = HealthIndexCalculator()
        self.extractor = PrognosticFeatureExtractor()
        self.rul_estimator = RULEstimator()

        self._last_result: PrognosticResult | None = None
        self._eval_count: int = 0
        self._total_pipeline_time_ms: float = 0.0
        self._total_hi_time_ms: float = 0.0
        self._total_trend_time_ms: float = 0.0
        self._total_rul_time_ms: float = 0.0

        self._metadata: dict[str, Any] = {}
        self._load_models()

    def _load_models(self) -> None:
        """Load persisted RUL model artifacts and metadata if present."""
        artifact_path = os.path.join(self.models_dir, "rul_estimator_v1.joblib")
        meta_path = os.path.join(self.models_dir, "metadata.json")

        if os.path.exists(artifact_path):
            try:
                self.rul_estimator.load(artifact_path)
                logger.info(f"Loaded Prognostics RUL Estimator from {artifact_path}")
            except Exception as e:
                logger.error(f"Failed to load RUL model bundle: {e}")
                self.rul_estimator = RULEstimator()
        else:
            logger.warning(
                f"RUL model artifact not found at {artifact_path}, using analytical default"
            )
            self.rul_estimator = RULEstimator()

        if os.path.exists(meta_path):
            try:
                with open(meta_path, encoding="utf-8") as f:
                    self._metadata = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load prognostics metadata: {e}")

    @property
    def is_ready(self) -> bool:
        """Report ready if components are initialized."""
        return True

    def reset(self) -> None:
        """Clear historical rolling buffer and reset evaluation state."""
        with self._lock:
            self.buffer.clear()
            self._last_result = None
            logger.info("Prognostics causal history buffer reset")

    def evaluate(
        self,
        frame: TelemetryFrame,
        physics: PhysicsTwinResult | None = None,
        ml: MLInferenceResult | None = None,
    ) -> PrognosticResult:
        """Evaluate engine degradation, health index, trends, and RUL for a single telemetry frame."""
        t_start = time.perf_counter()

        with self._lock:
            # 1. Health Index & 3-tier Subsystem Degradation
            t_hi_start = time.perf_counter()
            hi, deg_state, subsystems, val_flag = self.hi_calc.calculate(
                frame=frame, physics=physics, ml=ml
            )
            t_hi = (time.perf_counter() - t_hi_start) * 1000.0

            # 2. Append observation to causal ring buffer
            buffer_entry = {
                "timestamp": frame.timestamp,
                "health_index": hi,
                "rpm": frame.rpm,
                "manifold_pressure": frame.manifold_pressure,
                "oil_pressure": frame.oil_pressure,
                "oil_temperature": frame.oil_temperature,
                "cht_mean": sum(frame.cht) / len(frame.cht),
                "vibration_rms": frame.vibration_rms,
            }
            self.buffer.append(buffer_entry)

            # 3. Causal Trend & Stress Accumulators
            t_trend_start = time.perf_counter()
            history = self.buffer.get_history()
            beta_slope, trend_dir = self.extractor.compute_trend_slope(history)
            stress_acc = self.extractor.compute_stress_accumulators(history)
            indicators = self.extractor.extract_indicators(
                frame=frame,
                physics=physics,
                subsystems=subsystems,
                trend_dir=trend_dir,
            )
            t_trend = (time.perf_counter() - t_trend_start) * 1000.0

            # 4. Feature vector construction & RUL estimation
            t_rul_start = time.perf_counter()
            feat_vec = self.extractor.construct_feature_vector(
                health_index=hi,
                beta_slope=beta_slope,
                subsystems=subsystems,
                frame=frame,
                stress_accumulators=stress_acc,
                ml=ml,
            )
            rul_est = self.rul_estimator.estimate(
                health_index=hi,
                beta_slope=beta_slope,
                trend_dir=trend_dir,
                subsystems=subsystems,
                buffer_size=self.buffer.size,
                history=history,
                feature_vector=feat_vec,
                validity=val_flag,
            )
            t_rul = (time.perf_counter() - t_rul_start) * 1000.0

            t_total = (time.perf_counter() - t_start) * 1000.0

            # Performance counters
            self._eval_count += 1
            self._total_pipeline_time_ms += t_total
            self._total_hi_time_ms += t_hi
            self._total_trend_time_ms += t_trend
            self._total_rul_time_ms += t_rul

            disaggregated = {
                "health_index_ms": round(t_hi, 3),
                "trend_analysis_ms": round(t_trend, 3),
                "rul_estimation_ms": round(t_rul, 3),
            }

            result = PrognosticResult(
                timestamp=frame.timestamp,
                sequence_id=frame.sequence_id,
                feature_schema_version=PROGNOSTIC_FEATURE_SCHEMA_VERSION,
                health_index=hi,
                degradation_state=deg_state,
                trend_direction=trend_dir,
                trend_slope_per_sec=beta_slope,
                subsystems=subsystems,
                rul=rul_est,
                indicators=indicators,
                pipeline_latency_ms=round(t_total, 3),
                disaggregated_latencies=disaggregated,
                validity=val_flag,
            )

            self._last_result = result
            return result

    def get_current_result(self) -> PrognosticResult | None:
        """Return the most recently computed prognostic result."""
        with self._lock:
            return self._last_result

    def get_status(self) -> dict[str, Any]:
        """Return current status, buffer telemetry, performance metrics, and model metadata."""
        with self._lock:
            avg_latency = (
                self._total_pipeline_time_ms / self._eval_count if self._eval_count > 0 else 0.0
            )
            return {
                "ready": self.is_ready,
                "model_fitted": self.rul_estimator.is_fitted,
                "feature_schema_version": PROGNOSTIC_FEATURE_SCHEMA_VERSION,
                "buffer_size": self.buffer.size,
                "buffer_capacity": self.buffer.max_capacity,
                "evaluations_count": self._eval_count,
                "mean_pipeline_latency_ms": round(avg_latency, 3),
                "disclaimer": (
                    "PROTOTYPE RESEARCH MODEL — NOT FOR CERTIFIED FLIGHT OPERATIONS OR REAL-WORLD LIFING"
                ),
                "model_metadata": self._metadata,
                "last_result": self._last_result.model_dump() if self._last_result else None,
            }
