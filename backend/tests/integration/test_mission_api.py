"""Integration tests for Mission simulation and catalog REST API endpoints."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_list_predefined_missions():
    resp = client.get("/api/v1/missions/predefined")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 5
    mission_ids = [m["mission_id"] for m in data]
    assert "SURVEILLANCE_MISSION" in mission_ids
    assert "RAPID_CLIMB_HOT_DAY" in mission_ids
    for m in data:
        assert m["is_synthetic"] is True


def test_get_mission_definition_success():
    resp = client.get("/api/v1/missions/predefined/SURVEILLANCE_MISSION")
    assert resp.status_code == 200
    data = resp.json()
    assert data["mission_id"] == "SURVEILLANCE_MISSION"
    assert len(data["phases"]) > 0


def test_get_mission_definition_not_found():
    resp = client.get("/api/v1/missions/predefined/UNKNOWN_MISSION_ID")
    assert resp.status_code == 404


def test_simulate_mission_bounded_response():
    payload = {
        "mission_id": "THROTTLE_DYNAMICS_BENCHMARK",
        "rate_hz": 10,
        "seed": 42,
        "persist_dataset": True,
        "include_frames": True,
    }
    resp = client.post("/api/v1/missions/simulate", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert "run_id" in data
    assert data["mission_id"] == "THROTTLE_DYNAMICS_BENCHMARK"
    assert data["duration_sec"] > 0
    assert data["frame_count"] > 0
    assert "summary" in data
    assert "fuel_consumed_liters" in data["summary"]
    assert "dataset_path" in data
    assert "prototype_disclaimer" in data

    # Since THROTTLE_DYNAMICS_BENCHMARK duration is 70s -> 700 frames > MAX_INLINE_FRAMES (500)
    # inline_frames must be null (omitted) to preserve bounded JSON response!
    assert data["inline_frames"] is None
    assert data["dataset_path"] is not None


def test_simulate_mission_missing_params():
    resp = client.post("/api/v1/missions/simulate", json={})
    assert resp.status_code == 422
