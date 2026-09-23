"""Unit tests for prognostics model persistence, metadata loading, and service reset."""

import os
import tempfile

from app.application.services.prognostics_service import PrognosticsService
from app.domain.prognostics.rul_model import RULEstimator


def test_estimator_save_and_load():
    """Verify RULEstimator can save and load model bundles including conformal_margin."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "test_rul.joblib")
        estimator = RULEstimator()
        estimator.is_fitted = True
        estimator.conformal_margin = 1.75

        estimator.save(path)
        assert os.path.exists(path)

        loaded = RULEstimator(model_artifact_path=path)
        assert loaded.is_fitted is True
        assert loaded.conformal_margin == 1.75


def test_missing_model_fallback():
    """Verify initializing with non-existent artifact path falls back gracefully."""
    estimator = RULEstimator(model_artifact_path="/non/existent/path/rul.joblib")
    assert estimator.is_fitted is False
    assert estimator.conformal_margin == 0.0


def test_prognostics_service_lifecycle_and_reset():
    """Verify PrognosticsService initializes, evaluates, and clears on reset."""
    service = PrognosticsService()
    assert service.is_ready is True

    # Seed the buffer
    service.buffer.append({"timestamp": 10.0, "health_index": 0.95})
    assert service.buffer.size == 1

    service.reset()
    assert service.buffer.size == 0
    assert service.get_current_result() is None
