"""Integration tests for Simulation API endpoints."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_simulation_config_endpoint():
    response = client.get("/api/v1/simulation/config")
    assert response.status_code == 200
    data = response.json()
    assert "Generic 4-cylinder" in data["engine_baseline"]
    assert "prototype simulation assumptions" in data["prototype_disclaimer"]
    assert data["telemetry_rate_hz"] == 10
    assert data["dt_seconds"] == 0.1
    assert "available_scenarios" in data
    assert "ENGINE_START" in data["available_scenarios"]


def test_simulation_step_endpoint():
    response = client.post(
        "/api/v1/simulation/step",
        json={
            "phase_name": "TEST_STEP",
            "target_throttle_pct": 30.0,
            "target_altitude_m": 500.0,
            "ignition_on": True,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "sequence_id" in data
    assert "timestamp" in data
    assert "rpm" in data
    assert len(data["cht"]) == 4
    assert len(data["egt"]) == 4
    assert data["quality_flag"] == "VALID"


def test_simulation_batch_endpoint():
    response = client.post(
        "/api/v1/simulation/batch",
        json={"count": 5, "persist": True},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["frames_generated"] == 5
    assert data["telemetry_rate_hz"] == 10


def test_simulation_reset_endpoint():
    response = client.post("/api/v1/simulation/reset", json={"seed": 42})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "reset"
    assert data["seed"] == 42
    assert data["sim_time"] == 0.0
    assert data["sequence_id"] == 0


def test_simulation_scenarios_endpoint():
    response = client.get("/api/v1/simulation/scenarios")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    scenario_names = [s["scenario_name"] for s in data]
    assert "COMPLETE_FLIGHT_PROFILE" in scenario_names
    assert "TAKEOFF" in scenario_names


def test_simulation_fault_lifecycle_endpoints():
    # 1. Clear faults
    del_resp = client.delete("/api/v1/simulation/faults")
    assert del_resp.status_code == 200

    # 2. Inject fault
    post_resp = client.post(
        "/api/v1/simulation/faults",
        json={
            "target_channel": "oil_pressure",
            "fault_type": "BIAS",
            "start_time_sec": 1.0,
            "end_time_sec": 5.0,
            "magnitude": 2.5,
        },
    )
    assert post_resp.status_code == 201
    assert post_resp.json()["status"] == "fault_injected"

    # 3. List faults
    list_resp = client.get("/api/v1/simulation/faults")
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1
    assert list_resp.json()[0]["target_channel"] == "oil_pressure"

    # 4. Clear faults
    del_resp2 = client.delete("/api/v1/simulation/faults")
    assert del_resp2.status_code == 200
    assert len(client.get("/api/v1/simulation/faults").json()) == 0


def test_simulation_records_endpoint():
    # Generate batch with persist=True
    client.post("/api/v1/simulation/batch", json={"count": 3, "persist": True})

    response = client.get("/api/v1/simulation/records?limit=3")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
