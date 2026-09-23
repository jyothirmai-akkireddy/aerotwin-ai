"""Integration tests verifying application startup, health endpoints, and request ID tracking."""

from starlette.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root_health_endpoint():
    """Verify GET /health returns 200 and healthy status."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "uptime_seconds" in data
    assert "timestamp" in data


def test_api_v1_health_endpoint():
    """Verify versioned GET /api/v1/health matches root contract."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_readiness_endpoint():
    """Verify GET /ready returns 200 and subsystem components dictionary."""
    response = client.get("/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert "components" in data
    assert "telemetry_rate_hz" in data
    # Verify honest reporting of components
    components = data["components"]
    assert components["configuration"] == "READY"
    assert components["telemetry_pipeline"] == "READY"
    assert components["synthetic_simulator"] == "READY"
    assert components["realtime_transport"] == "READY"
    assert components["physics_twin_residuals"] == "READY"
    assert components["ml_anomaly_detector"] == "READY"
    assert components["ml_fault_classifier"] == "READY"
    assert components["mission_simulator"] == "READY"
    assert components["flight_replay"] == "READY"


def test_system_info_endpoint():
    """Verify GET /api/v1/info returns system metadata and engine baseline."""
    response = client.get("/api/v1/info")
    assert response.status_code == 200
    data = response.json()
    assert "AeroTwin" in data["name"]
    assert data["telemetry_rate_hz"] == 10
    assert data["dt_seconds"] == 0.1
    assert "GENERIC" in data["engine_baseline"].upper()


def test_request_id_middleware_header():
    """Verify that every request receives an X-Request-ID and X-Response-Time header."""
    response = client.get("/health")
    assert response.status_code == 200
    assert "x-request-id" in response.headers
    assert "x-response-time" in response.headers
    assert len(response.headers["x-request-id"]) > 0


def test_custom_request_id_propagation():
    """Verify that client-provided X-Request-ID is preserved and propagated."""
    custom_id = "test-corr-id-998811"
    response = client.get("/health", headers={"X-Request-ID": custom_id})
    assert response.status_code == 200
    assert response.headers["x-request-id"] == custom_id
