"""Integration tests for Phase 6 Machine Learning REST API endpoints."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_ml_status_endpoint(client: TestClient):
    """GET /api/v1/ml/status returns operational diagnostics and latencies."""
    response = client.get("/api/v1/ml/status")
    assert response.status_code == 200
    data = response.json()

    assert "evaluation_count" in data
    assert "anomaly_count" in data
    assert "fault_breakdown" in data
    assert "status" in data
    assert data["status"] in ("READY", "DEGRADED")
    assert "average_latencies_ms" in data


def test_ml_models_endpoint(client: TestClient):
    """GET /api/v1/ml/models returns loaded model details and provenance."""
    response = client.get("/api/v1/ml/models")
    assert response.status_code == 200
    data = response.json()

    assert data["feature_schema_version"] == "1.0.0"
    assert data["provenance"] == "SYNTHETIC_SIMULATED_PROTOTYPE"
    assert "PROTOTYPE" in data["prototype_notice"]

    assert "anomaly_detector" in data
    assert data["anomaly_detector"]["name"] == "IsolationForest"

    assert "fault_classifier" in data
    assert data["fault_classifier"]["name"] == "XGBoostFaultClassifier"
    assert data["fault_classifier"]["confidence_threshold"] == 0.60


def test_ml_features_endpoint(client: TestClient):
    """GET /api/v1/ml/features returns deterministic 24-feature schema manifest."""
    response = client.get("/api/v1/ml/features")
    assert response.status_code == 200
    data = response.json()

    assert data["schema_version"] == "1.0.0"
    assert data["feature_count"] == 24
    assert len(data["features"]) == 24
    assert "rpm" in data["features"]
    assert "res_oil_p_norm" in data["features"]
    assert "nominal_baselines" in data


def test_ml_evaluate_endpoint(client: TestClient):
    """POST /api/v1/ml/evaluate returns standardized MLInferenceResult."""
    payload = {
        "frame": {
            "timestamp": 100.0,
            "sequence_id": 1,
            "rpm": 2400.0,
            "manifold_pressure": 29.5,
            "throttle_position": 45.0,
            "fuel_flow": 16.5,
            "fuel_pressure": 3.0,
            "injection_timing": 15.0,
            "cht": [95.0, 95.0, 95.0, 95.0],
            "egt": [720.0, 720.0, 720.0, 720.0],
            "coolant_temp": 82.0,
            "oil_temperature": 85.0,
            "oil_pressure": 3.8,
            "vibration_rms": 1.15,
            "battery_voltage": 28.2,
            "alternator_current": 20.0,
            "alternator_status": "OK",
            "altitude": 500.0,
            "ambient_temp": 20.0,
            "ambient_pressure": 29.92,
            "true_airspeed": 45.0,
        }
    }

    response = client.post("/api/v1/ml/evaluate", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["timestamp"] == 100.0
    assert data["sequence_id"] == 1
    assert data["feature_schema_version"] == "1.0.0"

    # Anomaly payload
    assert "anomaly" in data
    assert "flag" in data["anomaly"]
    assert "status" in data["anomaly"]
    assert "score" in data["anomaly"]
    assert "threshold" in data["anomaly"]

    # Fault payload
    assert "fault" in data
    assert "fault_class" in data["fault"]
    assert "confidence" in data["fault"]
    assert "reason" in data["fault"]

    # Explainability attributions
    assert "top_contributions" in data
    assert isinstance(data["top_contributions"], list)

    # Disaggregated latencies
    assert "disaggregated_latencies" in data
    assert "feature_extraction_ms" in data["disaggregated_latencies"]
    assert "anomaly_detection_ms" in data["disaggregated_latencies"]
    assert "fault_classification_ms" in data["disaggregated_latencies"]
    assert "explainability_ms" in data["disaggregated_latencies"]


def test_health_readiness_includes_ml_subsystems(client: TestClient):
    """GET /api/v1/ready reports READY for ML anomaly detector and fault classifier."""
    response = client.get("/api/v1/ready")
    assert response.status_code == 200
    data = response.json()

    components = data["components"]
    assert components["ml_anomaly_detector"] == "READY"
    assert components["ml_fault_classifier"] == "READY"
    assert components["physics_twin_residuals"] == "READY"
