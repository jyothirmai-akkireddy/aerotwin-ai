"""Unit tests for TelemetryFrame domain entity and ResidualVector value object."""

import pytest
from pydantic import ValidationError

from app.domain.entities.telemetry import (
    QualityStatus,
    TelemetryFrame,
    TelemetrySource,
)
from app.domain.value_objects.residuals import ResidualVector


def test_valid_telemetry_frame_creation():
    """Verify standard valid telemetry frame instantiation."""
    frame_data = {
        "version": "1.0.0",
        "timestamp": 1774358400.1,
        "sequence_id": 1,
        "source_type": TelemetrySource.SIMULATED,
        "quality_flag": QualityStatus.GOOD,
        "rpm": 5200.0,
        "manifold_pressure": 32.5,
        "throttle_position": 75.0,
        "fuel_flow": 26.4,
        "fuel_pressure": 3.0,
        "injection_timing": 22.0,
        "cht": [115.0, 118.0, 116.5, 117.2],
        "egt": [810.0, 825.0, 812.0, 818.0],
        "coolant_temp": 85.0,
        "oil_temperature": 92.0,
        "oil_pressure": 3.5,
        "vibration_rms": 1.1,
        "battery_voltage": 28.1,
        "alternator_current": 18.5,
        "altitude": 2500.0,
        "ambient_temp": 15.0,
        "true_airspeed": 45.0,
    }
    frame = TelemetryFrame(**frame_data)
    assert frame.rpm == 5200.0
    assert len(frame.cht) == 4
    assert frame.quality_flag == QualityStatus.GOOD
    assert frame.version == "1.0.0"


def test_invalid_rpm_exceeds_redline():
    """Verify that physically impossible RPM raises validation error."""
    with pytest.raises(ValidationError):
        TelemetryFrame(
            timestamp=1774358400.1,
            sequence_id=1,
            rpm=9500.0,  # Exceeds max aerospace bound 7000
            manifold_pressure=30.0,
            throttle_position=50.0,
            fuel_flow=20.0,
            fuel_pressure=3.0,
            injection_timing=20.0,
            cht=[100.0, 100.0, 100.0, 100.0],
            egt=[800.0, 800.0, 800.0, 800.0],
            coolant_temp=80.0,
            oil_temperature=90.0,
            oil_pressure=3.0,
            vibration_rms=1.0,
            battery_voltage=28.0,
            alternator_current=15.0,
            altitude=1000.0,
            ambient_temp=20.0,
            true_airspeed=40.0,
        )


def test_invalid_cylinder_count():
    """Verify that fewer than 4 cylinders raises validation error."""
    with pytest.raises(ValidationError):
        TelemetryFrame(
            timestamp=1774358400.1,
            sequence_id=1,
            rpm=5000.0,
            manifold_pressure=30.0,
            throttle_position=50.0,
            fuel_flow=20.0,
            fuel_pressure=3.0,
            injection_timing=20.0,
            cht=[100.0, 100.0, 100.0],  # Only 3 cylinders given
            egt=[800.0, 800.0, 800.0, 800.0],
            coolant_temp=80.0,
            oil_temperature=90.0,
            oil_pressure=3.0,
            vibration_rms=1.0,
            battery_voltage=28.0,
            alternator_current=15.0,
            altitude=1000.0,
            ambient_temp=20.0,
            true_airspeed=40.0,
        )


def test_residual_vector_feature_array():
    """Verify that ResidualVector flattens correctly to 14 ML features."""
    residuals = ResidualVector(
        timestamp=1774358400.1,
        rpm_residual=50.0,
        map_residual=0.5,
        fuel_flow_residual=-1.2,
        cht_residuals=[5.0, 4.0, -2.0, 1.0],
        egt_residuals=[-15.0, 10.0, -5.0, 0.0],
        oil_pressure_residual=-0.3,
        oil_temperature_residual=2.5,
        vibration_residual=0.4,
    )
    features = residuals.to_feature_array()
    assert len(features) == 14
    assert features[0] == 50.0  # rpm_residual
    assert features[1] == 0.5  # map_residual
    assert features[3] == 5.0  # cht1
    assert features[7] == -15.0  # egt1
    assert features[13] == 0.4  # vibration
