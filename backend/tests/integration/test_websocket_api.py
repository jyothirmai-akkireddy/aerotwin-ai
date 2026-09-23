"""Integration tests for the /api/v1/ws/telemetry WebSocket endpoint."""

import json

from starlette.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_websocket_connection_and_telemetry_stream():
    """Verify handshake, status message, and reception of valid telemetry frames."""
    with client.websocket_connect("/api/v1/ws/telemetry") as websocket:
        # 1. First message must be StatusMessage(status='connected')
        init_msg = websocket.receive_json()
        assert init_msg["type"] == "status"
        assert init_msg["status"] == "connected"
        assert "Session ID" in init_msg["message"]

        # 2. Subsequent message should be TelemetryMessage
        frame_msg = websocket.receive_json()
        # It could be another status or telemetry, advance until telemetry
        if frame_msg["type"] == "status":
            frame_msg = websocket.receive_json()

        assert frame_msg["type"] == "telemetry"
        assert frame_msg["version"] == "1.0.0"
        assert "sequence_id" in frame_msg
        assert "timestamp" in frame_msg
        assert "server_time" in frame_msg
        assert "payload" in frame_msg
        payload = frame_msg["payload"]
        assert "rpm" in payload
        assert "manifold_pressure" in payload
        assert len(payload["cht"]) == 4

        # Verify ML diagnostics payload
        assert "ml" in frame_msg
        if frame_msg["ml"] is not None:
            ml = frame_msg["ml"]
            assert "anomaly" in ml
            assert "fault" in ml
            assert "top_contributions" in ml
            assert "inference_latency_ms" in ml


def test_websocket_ping_pong():
    """Verify client ping triggers a server pong response."""
    with client.websocket_connect("/api/v1/ws/telemetry") as websocket:
        _ = websocket.receive_json()  # init status

        websocket.send_text(json.dumps({"type": "ping"}))

        # Look for pong in the incoming stream
        received_pong = False
        for _ in range(5):
            msg = websocket.receive_json()
            if msg.get("type") == "status" and msg.get("message") == "pong":
                received_pong = True
                break
        assert received_pong is True


def test_websocket_command_handling():
    """Verify client pause and resume commands."""
    with client.websocket_connect("/api/v1/ws/telemetry") as websocket:
        _ = websocket.receive_json()

        # Send pause command
        websocket.send_text(
            json.dumps({"type": "command", "version": "1.0.0", "command": "pause", "params": {}})
        )

        # Confirm paused status arrives
        received_paused = False
        for _ in range(5):
            msg = websocket.receive_json()
            if msg.get("type") == "status" and msg.get("status") == "paused":
                received_paused = True
                break
        assert received_paused is True

        # Send resume command
        websocket.send_text(
            json.dumps({"type": "command", "version": "1.0.0", "command": "resume", "params": {}})
        )

        # Confirm running status arrives before exiting
        received_running = False
        for _ in range(5):
            msg = websocket.receive_json()
            if msg.get("type") == "status" and msg.get("status") == "running":
                received_running = True
                break
        assert received_running is True


def test_websocket_set_scenario_command():
    """Verify client set_scenario command switches scenario and stream continues."""
    with client.websocket_connect("/api/v1/ws/telemetry") as websocket:
        _ = websocket.receive_json()

        # Send set_scenario with root-level 'scenario' parameter
        websocket.send_text(
            json.dumps(
                {
                    "type": "command",
                    "version": "1.0.0",
                    "command": "set_scenario",
                    "scenario": "CRUISE",
                }
            )
        )

        received_scenario_switch = False
        for _ in range(5):
            msg = websocket.receive_json()
            if msg.get("type") == "status" and "Scenario switched to CRUISE" in msg.get(
                "message", ""
            ):
                received_scenario_switch = True
                break
        assert received_scenario_switch is True


def test_websocket_malformed_json_handling():
    """Verify that malformed JSON triggers an error message without crashing the server."""
    with client.websocket_connect("/api/v1/ws/telemetry") as websocket:
        _ = websocket.receive_json()

        # Send non-JSON text
        websocket.send_text("INVALID_NOT_JSON{{{")

        received_err = False
        for _ in range(5):
            msg = websocket.receive_json()
            if msg.get("type") == "error" and msg.get("code") == "INVALID_JSON":
                received_err = True
                break
        assert received_err is True


def test_websocket_metrics_endpoint():
    """Verify GET /api/v1/ws/metrics returns transport metrics."""
    response = client.get("/api/v1/ws/metrics")
    assert response.status_code == 200
    data = response.json()
    assert "active_clients" in data
    assert "max_clients" in data
    assert "queue_size" in data
    assert "total_broadcast_frames" in data
    assert "rate_hz" in data
