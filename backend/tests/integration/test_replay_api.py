"""Integration tests for Flight Replay REST API endpoints."""

from pathlib import Path

from fastapi.testclient import TestClient

from app.domain.entities.telemetry import TelemetryFrame, TelemetrySource
from app.infrastructure.persistence.telemetry_repository import SqliteTelemetryRepository
from app.main import app

client = TestClient(app)


def test_replay_api_lifecycle(tmp_path):
    # 1. Create a dummy parquet dataset inside data/missions
    from app.config import settings

    missions_dir = Path(settings.storage.parquet_data_dir).parent / "missions"
    missions_dir.mkdir(parents=True, exist_ok=True)
    test_parquet = missions_dir / "test_api_replay.parquet"

    frames = [
        TelemetryFrame(
            timestamp=100.0 + i * 0.1,
            sequence_id=i,
            source_type=TelemetrySource.SIMULATED,
            rpm=2200.0,
            manifold_pressure=27.0,
            throttle_position=45.0,
            fuel_flow=14.0,
            fuel_pressure=3.0,
            injection_timing=18.0,
            cht=[88.0, 88.0, 88.0, 88.0],
            egt=[690.0, 690.0, 690.0, 690.0],
            coolant_temp=82.0,
            oil_temperature=84.0,
            oil_pressure=3.6,
            vibration_rms=1.02,
            battery_voltage=28.1,
            alternator_current=11.0,
            alternator_status="OK",
            altitude=200.0,
            ambient_temp=14.0,
            true_airspeed=35.0,
        )
        for i in range(20)
    ]
    SqliteTelemetryRepository.export_frames_to_parquet(frames, test_parquet)

    # 2. List datasets
    resp_list = client.get("/api/v1/replay/datasets")
    assert resp_list.status_code == 200
    datasets = resp_list.json()
    assert any(d["filename"] == "test_api_replay.parquet" for d in datasets)

    # 3. Load dataset
    resp_load = client.post("/api/v1/replay/load", json={"filename": "test_api_replay.parquet"})
    assert resp_load.status_code == 200
    status_data = resp_load.json()
    assert status_data["total_frames"] == 20
    assert status_data["playback_state"] == "IDLE"

    # 4. Status endpoint
    resp_status = client.get("/api/v1/replay/status")
    assert resp_status.status_code == 200
    assert resp_status.json()["total_frames"] == 20

    # 5. Control: Play
    resp_play = client.post("/api/v1/replay/control", json={"action": "play"})
    assert resp_play.status_code == 200
    assert resp_play.json()["playback_state"] == "PLAYING"

    # 6. Control: Seek
    resp_seek = client.post("/api/v1/replay/control", json={"action": "seek", "target": 10})
    assert resp_seek.status_code == 200
    assert resp_seek.json()["current_index"] == 10

    # 7. Control: Speed (batch)
    resp_speed = client.post("/api/v1/replay/control", json={"action": "speed", "target": "BATCH"})
    assert resp_speed.status_code == 200
    assert resp_speed.json()["execution_mode"] == "OFFLINE_BATCH"

    # 8. Switch telemetry mode
    resp_mode = client.post("/api/v1/replay/mode", json={"mode": "REPLAY"})
    assert resp_mode.status_code == 200
    assert resp_mode.json()["mode"] == "REPLAY"

    # Switch back to LIVE
    resp_mode_live = client.post("/api/v1/replay/mode", json={"mode": "LIVE"})
    assert resp_mode_live.status_code == 200
    assert resp_mode_live.json()["mode"] == "LIVE"


def test_replay_load_non_existent():
    resp = client.post("/api/v1/replay/load", json={"filename": "non_existent_file.parquet"})
    assert resp.status_code == 404
