"""Integration tests for Physics Twin REST endpoints."""

from starlette.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_physics_status_endpoint():
    """Verify GET /api/v1/physics/status returns operational diagnostics."""
    response = client.get("/api/v1/physics/status")
    assert response.status_code == 200
    data = response.json()
    assert data["model_status"] == "READY"
    assert "calibration_version" in data
    assert "average_compute_time_ms" in data
    assert "evaluation_count" in data


def test_physics_current_endpoint():
    """Verify GET /api/v1/physics/current returns expected state and residuals."""
    response = client.get("/api/v1/physics/current")
    assert response.status_code == 200
    data = response.json()
    assert "expected_state" in data
    assert "residuals" in data
    assert "diagnostics" in data

    exp = data["expected_state"]
    assert "rpm" in exp
    assert "manifold_pressure" in exp
    assert "cht" in exp
    assert len(exp["cht"]) == 4
    assert "egt" in exp
    assert len(exp["egt"]) == 4

    res = data["residuals"]
    assert "raw_residuals" in res
    assert "normalized_residuals" in res
    assert "cht_max_imbalance_celsius" in res
    assert "egt_max_imbalance_celsius" in res


def test_physics_residuals_endpoint():
    """Verify GET /api/v1/physics/residuals returns ResidualSet schema."""
    response = client.get("/api/v1/physics/residuals")
    assert response.status_code == 200
    data = response.json()
    assert "raw_residuals" in data
    assert "normalized_residuals" in data
    assert "mean_absolute_normalized_residual" in data


def test_physics_calibration_get_and_post():
    """Verify GET and POST /api/v1/physics/calibration for runtime parameter tuning."""
    # 1. Get current calibration
    get_res = client.get("/api/v1/physics/calibration")
    assert get_res.status_code == 200
    params = get_res.json()
    assert "engine_displacement_cc" in params
    assert "tau_cht_seconds" in params

    # 2. Update with modified parameter
    params["tau_cht_seconds"] = 18.5
    params["version"] = "1.0.1-test"
    post_res = client.post("/api/v1/physics/calibration", json=params)
    assert post_res.status_code == 200
    updated = post_res.json()
    assert updated["tau_cht_seconds"] == 18.5
    assert updated["version"] == "1.0.1-test"

    # Reset back to default
    params["tau_cht_seconds"] = 14.0
    params["version"] = "1.0.0"
    client.post("/api/v1/physics/calibration", json=params)


def test_physics_evaluate_endpoint():
    """Verify POST /api/v1/physics/evaluate performs on-demand frame evaluation."""
    frame_payload = {
        "version": "1.0.0",
        "timestamp": 123456.7,
        "sequence_id": 42,
        "source_type": "SIMULATED",
        "quality_flag": "VALID",
        "rpm": 2450.0,
        "manifold_pressure": 29.8,
        "throttle_position": 55.0,
        "fuel_flow": 16.8,
        "fuel_pressure": 3.1,
        "injection_timing": 24.0,
        "cht": [96.0, 94.0, 99.0, 95.0],
        "egt": [725.0, 718.0, 735.0, 722.0],
        "coolant_temp": 83.0,
        "oil_temperature": 86.0,
        "oil_pressure": 3.9,
        "vibration_rms": 1.15,
        "battery_voltage": 28.2,
        "alternator_current": 18.0,
        "alternator_status": "OK",
        "altitude": 1200.0,
        "ambient_temp": 14.0,
        "true_airspeed": 46.0,
    }
    response = client.post("/api/v1/physics/evaluate", json=frame_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["expected_state"]["sequence_id"] == 42
    assert "raw_residuals" in data["residuals"]
