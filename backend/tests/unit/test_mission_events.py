"""Unit tests for mission control events and sensor fault event routing."""

import pytest

from app.domain.mission.enums import ControlTargetParameter
from app.domain.mission.events import MissionControlEvent, MissionFaultEvent
from app.domain.simulation.faults import SensorFaultType


def test_mission_control_event_lifecycle():
    event = MissionControlEvent(
        event_id="GUST_01",
        start_time_sec=10.0,
        duration_sec=5.0,
        target_parameter=ControlTargetParameter.ALTITUDE_M,
        magnitude=40.0,
    )

    assert not event.is_active(5.0)
    assert event.evaluate_offset(5.0) == 0.0

    assert event.is_active(10.0)
    assert event.evaluate_offset(10.0) == 40.0

    assert event.is_active(12.5)
    assert event.evaluate_offset(12.5) == 40.0

    assert not event.is_active(15.0)
    assert event.evaluate_offset(15.0) == 0.0


def test_mission_fault_event_conversion_to_phase2():
    fault_event = MissionFaultEvent(
        event_id="OIL_PRESS_BIAS_01",
        start_time_sec=20.0,
        duration_sec=30.0,
        target_channel="oil_pressure",
        fault_type=SensorFaultType.BIAS,
        magnitude=-1.2,
    )

    config = fault_event.to_sensor_fault_config()
    assert config.target_channel == "oil_pressure"
    assert config.fault_type == SensorFaultType.BIAS
    assert config.start_time_sec == 20.0
    assert config.end_time_sec == 50.0
    assert config.magnitude == -1.2

    assert not config.is_active(19.9)
    assert config.is_active(20.0)
    assert config.is_active(35.0)
    assert not config.is_active(50.0)


def test_mission_event_validation_errors():
    with pytest.raises(ValueError):
        MissionControlEvent(
            event_id="INVALID_GUST",
            start_time_sec=-1.0,  # Negative start time prohibited
            duration_sec=5.0,
            target_parameter=ControlTargetParameter.THROTTLE_PCT,
            magnitude=10.0,
        )

    with pytest.raises(ValueError):
        MissionControlEvent(
            event_id="INVALID_DUR",
            start_time_sec=0.0,
            duration_sec=0.0,  # Non-positive duration prohibited
            target_parameter=ControlTargetParameter.THROTTLE_PCT,
            magnitude=10.0,
        )
