"""Integration tests for Prognostics REST endpoints, readiness probe, and WebSocket broadcast."""

import pytest
from starlette.testclient import TestClient

from app.domain.entities.telemetry import TelemetryFrame
from app.main import create_app


@pytest.fixture(scope="module")
def client():
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


def _make_dummy_frame_payload() -> dict:
    frame = TelemetryFrame(
        timestamp=100.0,
        sequence_id=42,
        source_type="SIMULATED",
        quality_flag="VALID",
        rpm=2400.0,
        manifold_pressure=29.5,
        throttle_position=45.0,
        fuel_flow=16.5,
        fuel_pressure=3.0,
        injection_timing=15.0,
        cht=(95.0, 95.0, 95.0, 95.0),
        egt=(720.0, 720.0, 720.0, 720.0),
        coolant_temp=82.0,
        oil_temperature=85.0,
        oil_pressure=3.8,
        vibration_rms=1.15,
        battery_voltage=28.2,
        alternator_current=14.0,
        alternator_status="OK",
        altitude=1500.0,
        ambient_temp=15.0,
        true_airspeed=45.0,
    )
    return frame.model_dump()


def test_get_prognostics_status(client):
    """GET /api/v1/prognostics/status returns operational diagnostics and model provenance."""
    resp = client.get("/api/v1/prognostics/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ready"] is True
    assert data["feature_schema_version"] == "1.0.0"
    assert "PROTOTYPE RESEARCH MODEL" in data["disclaimer"]


def test_evaluate_prognostics_endpoint(client):
    """POST /api/v1/prognostics/evaluate executes on-demand prognostics evaluation."""
    payload = {"frame": _make_dummy_frame_payload()}
    resp = client.post("/api/v1/prognostics/evaluate", json=payload)
    assert resp.status_code == 200
    result = resp.json()

    assert "health_index" in result
    assert "subsystems" in result
    assert "rul" in result
    assert "indicators" in result
    assert 0.0 <= result["health_index"] <= 1.0
    assert result["degradation_state"] in [
        "NOMINAL",
        "EARLY_DEGRADATION",
        "MODERATE_DEGRADATION",
        "SEVERE_DEGRADATION",
        "CRITICAL_SIMULATED_STATE",
    ]
    assert result["rul"]["status"] in (
        "DEGRADATION_NOT_DETECTED",
        "INSUFFICIENT_HISTORY",
        "RUL_UNAVAILABLE",
        "ACTIVE",
    )


def test_get_current_prognostics(client):
    """GET /api/v1/prognostics/current returns the most recent evaluation result."""
    # First evaluate a frame
    payload = {"frame": _make_dummy_frame_payload()}
    client.post("/api/v1/prognostics/evaluate", json=payload)

    resp = client.get("/api/v1/prognostics/current")
    assert resp.status_code == 200
    current = resp.json()
    assert current is not None
    assert "health_index" in current


def test_readiness_probe_includes_prognostics(client):
    """GET /api/v1/ready confirms prognostics_engine component is reported as READY."""
    resp = client.get("/api/v1/ready")
    assert resp.status_code == 200
    data = resp.json()
    assert data["components"]["prognostics_engine"] == "READY"


def test_websocket_telemetry_includes_prognostics(client):
    """Verify WebSocket streaming broadcast includes validated prognostics payload."""
    with client.websocket_connect("/api/v1/ws/telemetry") as ws:
        # Start streaming
        ws.send_json({"type": "command", "version": "1.0.0", "command": "start"})

        # Advance messages until telemetry frame arrives (skipping initial status messages)
        msg = None
        for _ in range(5):
            candidate = ws.receive_json()
            if candidate.get("type") == "telemetry":
                msg = candidate
                break

        assert msg is not None, "Did not receive telemetry message within 5 frames"
        assert msg["type"] == "telemetry"
        assert "payload" in msg
        assert "prognostics" in msg
        if msg["prognostics"] is not None:
            assert "health_index" in msg["prognostics"]
            assert "subsystems" in msg["prognostics"]
            assert "rul" in msg["prognostics"]
            assert 0.0 <= msg["prognostics"]["health_index"] <= 1.0

        # Pause stream before closing
        ws.send_json({"type": "command", "version": "1.0.0", "command": "pause"})
