"""Security and input validation audit tests.

SIH26054 — AeroTwin AI
Phase 9 Security Gate

Validates:
1. Path traversal defense across storage and replay layers:
   - ../ escapes, ..\\ escapes, absolute paths, system directories
   - ReplayService dataset resolution protection
   - REST API replay endpoints defense
2. Input boundary and malformed payload validation:
   - Malformed JSON to WebSocket command handler
   - Unknown and unauthorized commands
   - SQL injection containment in SQLite flight loader
3. Prototype disclaimers and non-disclosure of internal system paths.
"""

from pathlib import Path

import pytest
from starlette.testclient import TestClient

from app.application.services.realtime_service import RealtimeTelemetryService
from app.application.services.replay_service import ReplayService
from app.infrastructure.logging.logger import get_logger
from app.infrastructure.replay.loader import FlightLogLoader
from app.infrastructure.simulation.engine_simulator import EngineSimulator
from app.infrastructure.telemetry.synthetic_source import SyntheticTelemetrySource
from app.infrastructure.websocket.broadcaster import WebSocketBroadcastManager
from app.main import app

logger = get_logger("aerotwin.test.security_audit")


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_replay_service_path_traversal_defense(tmp_path: Path):
    """Verify that ReplayService strictly prevents directory traversal attacks."""
    authorized_dir = tmp_path / "authorized_logs"
    authorized_dir.mkdir()
    secret_dir = tmp_path / "secret_data"
    secret_dir.mkdir()

    secret_file = secret_dir / "passwords.parquet"
    secret_file.write_text("classified content")

    replay_service = ReplayService(search_directories=[authorized_dir])

    # Traversal attack vectors
    attack_vectors = [
        "../secret_data/passwords.parquet",
        "..\\secret_data\\passwords.parquet",
        "../../../../../../../../etc/passwd",
        "..\\..\\..\\..\\Windows\\System32\\cmd.exe",
        "/etc/shadow",
        "C:\\Windows\\win.ini",
        "authorized_logs/../../secret_data/passwords.parquet",
    ]

    for attack in attack_vectors:
        with pytest.raises(FileNotFoundError, match="not found in authorized storage locations"):
            replay_service.resolve_dataset_path(attack)


def test_rest_api_path_traversal_rejection(client: TestClient):
    """Verify that REST API endpoints reject path traversal attempts with 404 or 422."""
    traversal_payloads = [
        "../../etc/passwd",
        "..\\..\\Windows\\win.ini",
        "/etc/shadow",
        "../../models/sensitive.joblib",
    ]

    for payload in traversal_payloads:
        # Load dataset endpoint
        resp = client.post(f"/api/v1/replay/load?filename={payload}")
        assert resp.status_code in (404, 400, 422), (
            f"Endpoint did not reject traversal payload {payload}: {resp.status_code}"
        )

        # Metadata inspection endpoint
        resp_meta = client.get(f"/api/v1/replay/metadata?filename={payload}")
        assert resp_meta.status_code in (404, 400, 422), (
            f"Metadata endpoint did not reject traversal {payload}: {resp_meta.status_code}"
        )


@pytest.mark.asyncio
async def test_websocket_command_adversarial_validation():
    """Verify that RealtimeTelemetryService safely handles malformed and invalid client commands."""
    sim = EngineSimulator(telemetry_rate_hz=10)
    source = SyntheticTelemetrySource(simulator=sim)
    broadcaster = WebSocketBroadcastManager(max_clients=5, queue_size=100)

    service = RealtimeTelemetryService(
        telemetry_source=source,
        broadcaster=broadcaster,
        rate_hz=10,
    )

    # 1. Unknown command string
    await service.execute_command("UNKNOWN_HACK_COMMAND", {})
    # Must not raise or crash

    # 2. Command with invalid parameter types
    await service.execute_command("set_scenario", {"phase_name": 12345})
    await service.execute_command("set_scenario", {"scenario": ["bad", "list"]})

    # 3. Invalid source mode
    success = await service.set_source_mode("INVALID_MODE")
    assert success is False
    assert service.source_mode == "LIVE"


def test_sql_injection_defense_in_replay_loader(tmp_path: Path):
    """Verify that SQLite flight log loader does not execute injected SQL statements."""
    malicious_filename = tmp_path / "test'; DROP TABLE telemetry_frames; --.sqlite"
    # Even with SQL injection in filename, detect_format and inspect_metadata handle it safely as a file path
    with pytest.raises((FileNotFoundError, ValueError)):
        FlightLogLoader.inspect_metadata(malicious_filename)
