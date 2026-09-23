"""Unit tests for ML model artifacts and metadata integrity."""

import json
import os

from app.application.services.ml_service import MODELS_BASE_DIR, MLInferenceService


def test_model_artifact_files_exist():
    """Verify persisted joblib bundles and metadata JSON files exist."""
    anom_model = os.path.join(MODELS_BASE_DIR, "anomaly", "isolation_forest_v1.joblib")
    anom_meta = os.path.join(MODELS_BASE_DIR, "anomaly", "metadata.json")
    class_model = os.path.join(MODELS_BASE_DIR, "classifier", "fault_classifier_v1.joblib")
    class_meta = os.path.join(MODELS_BASE_DIR, "classifier", "metadata.json")

    assert os.path.isfile(anom_model), f"Missing {anom_model}"
    assert os.path.isfile(anom_meta), f"Missing {anom_meta}"
    assert os.path.isfile(class_model), f"Missing {class_model}"
    assert os.path.isfile(class_meta), f"Missing {class_meta}"


def test_anomaly_metadata_contents():
    """Verify anomaly metadata contains required provenance and metrics."""
    meta_path = os.path.join(MODELS_BASE_DIR, "anomaly", "metadata.json")
    with open(meta_path, encoding="utf-8") as f:
        meta = json.load(f)

    assert meta["model_version"] == "1.0.0"
    assert meta["detector_name"] == "IsolationForest"
    assert meta["feature_schema_version"] == "1.0.0"
    assert meta["provenance"] == "SYNTHETIC_SIMULATED_PROTOTYPE"
    assert "threshold" in meta
    assert "test_metrics" in meta
    assert meta["test_metrics"]["false_positive_rate"] <= 0.02


def test_classifier_metadata_contents():
    """Verify classifier metadata contains class names and test accuracy."""
    meta_path = os.path.join(MODELS_BASE_DIR, "classifier", "metadata.json")
    with open(meta_path, encoding="utf-8") as f:
        meta = json.load(f)

    assert meta["model_version"] == "1.0.0"
    assert meta["feature_schema_version"] == "1.0.0"
    assert meta["provenance"] == "SYNTHETIC_SIMULATED_PROTOTYPE"
    assert len(meta["class_names"]) == 6
    assert meta["test_metrics"]["accuracy"] >= 0.90
    assert meta["test_metrics"]["macro_f1"] >= 0.90


def test_ml_inference_service_initialization():
    """Verify MLInferenceService initializes and loads both models."""
    service = MLInferenceService()
    assert service.is_ready

    meta = service.get_model_metadata()
    assert meta["feature_schema_version"] == "1.0.0"
    assert meta["provenance"] == "SYNTHETIC_SIMULATED_PROTOTYPE"
    assert meta["anomaly_detector"]["fitted"] is True
    assert meta["fault_classifier"]["fitted"] is True
