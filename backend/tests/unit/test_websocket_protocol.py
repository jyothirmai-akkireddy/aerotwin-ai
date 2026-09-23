"""Unit tests for WebSocket protocol models and message schemas."""

import time

from app.domain.entities.telemetry import QualityStatus, TelemetryFrame, TelemetrySource
from app.infrastructure.websocket.protocol import (
    CommandMessage,
    ErrorMessage,
    HeartbeatMessage,
    StatusMessage,
    TelemetryMessage,
)


def _create_sample_frame(seq: int = 1, timestamp: float = 1000.0) -> TelemetryFrame:
    return TelemetryFrame(
        version="1.0.0",
        timestamp=timestamp,
        sequence_id=seq,
        source_type=TelemetrySource.SIMULATED,
        quality_flag=QualityStatus.VALID,
        rpm=2400.0,
        manifold_pressure=29.5,
        throttle_position=45.0,
        fuel_flow=16.5,
        fuel_pressure=3.2,
        injection_timing=24.0,
        cht=[95.0, 92.5, 98.0, 94.0],
        egt=[720.0, 715.0, 730.0, 722.0],
        coolant_temp=82.0,
        oil_temperature=85.0,
        oil_pressure=3.8,
        vibration_rms=1.15,
        battery_voltage=28.2,
        alternator_current=18.5,
        alternator_status="OK",
        altitude=1000.0,
        ambient_temp=15.0,
        true_airspeed=45.0,
    )


def test_telemetry_message_schema():
    """Verify TelemetryMessage structure, sequence ID, and dual timestamps."""
    frame = _create_sample_frame(seq=42, timestamp=1700000000.5)
    t_server = time.time()
    msg = TelemetryMessage(
        timestamp=frame.timestamp,
        sequence_id=frame.sequence_id,
        server_time=t_server,
        payload=frame,
    )

    data = msg.model_dump()
    assert data["type"] == "telemetry"
    assert data["version"] == "1.0.0"
    assert data["sequence_id"] == 42
    assert data["timestamp"] == 1700000000.5
    assert data["server_time"] == t_server
    assert data["payload"]["rpm"] == 2400.0
    assert len(data["payload"]["cht"]) == 4


def test_status_message_schema():
    """Verify StatusMessage schema and valid statuses."""
    msg = StatusMessage(status="running", message="Telemetry streaming active")
    data = msg.model_dump()
    assert data["type"] == "status"
    assert data["version"] == "1.0.0"
    assert data["status"] == "running"
    assert "server_time" in data


def test_error_message_schema():
    """Verify ErrorMessage sanitization without internal stack traces."""
    msg = ErrorMessage(code="INVALID_MESSAGE", message="Payload format unrecognized")
    data = msg.model_dump()
    assert data["type"] == "error"
    assert data["version"] == "1.0.0"
    assert data["code"] == "INVALID_MESSAGE"
    assert data["message"] == "Payload format unrecognized"
    assert "traceback" not in data


def test_heartbeat_message_schema():
    """Verify HeartbeatMessage structure."""
    msg = HeartbeatMessage()
    data = msg.model_dump()
    assert data["type"] == "heartbeat"
    assert data["version"] == "1.0.0"
    assert isinstance(data["server_time"], float)


def test_command_message_validation():
    """Verify CommandMessage validates allowed commands."""
    cmd = CommandMessage(command="pause", params={"reason": "operator_request"})
    assert cmd.command == "pause"
    assert cmd.params["reason"] == "operator_request"
