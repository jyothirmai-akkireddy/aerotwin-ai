"""Unit tests for TelemetryValidator rule enforcement."""

from app.domain.entities.telemetry import QualityStatus, TelemetryFrame, TelemetrySource
from app.domain.telemetry.validation import TelemetryValidator


def create_nominal_frame(seq: int = 1, timestamp: float = 1000.0) -> TelemetryFrame:
    """Helper to construct a valid nominal telemetry frame."""
    return TelemetryFrame(
        version="1.0.0",
        timestamp=timestamp,
        sequence_id=seq,
        source_type=TelemetrySource.SIMULATED,
        quality_flag=QualityStatus.VALID,
        rpm=2500.0,
        manifold_pressure=29.92,
        throttle_position=40.0,
        fuel_flow=15.0,
        fuel_pressure=3.2,
        injection_timing=22.0,
        cht=[95.0, 93.0, 91.0, 89.0],
        egt=[720.0, 715.0, 710.0, 705.0],
        coolant_temp=75.0,
        oil_temperature=85.0,
        oil_pressure=3.8,
        vibration_rms=1.1,
        battery_voltage=28.0,
        alternator_current=18.0,
        alternator_status="OK",
        altitude=1500.0,
        ambient_temp=12.0,
        true_airspeed=45.0,
    )


def test_nominal_frame_validation_passes():
    validator = TelemetryValidator(track_history=True)
    frame = create_nominal_frame()
    result = validator.validate(frame)
    assert result.is_valid
    assert result.quality == QualityStatus.VALID
    assert len(result.errors) == 0


def test_out_of_bounds_scalar_rejection():
    validator = TelemetryValidator(track_history=False)
    frame = create_nominal_frame()
    # Fuel pressure outside prototype range [0.4, 6.0]
    frame.fuel_pressure = 8.5
    result = validator.validate(frame)
    assert not result.is_valid
    assert result.quality == QualityStatus.INVALID
    assert any("fuel_pressure" in err for err in result.errors)


def test_out_of_bounds_cht_rejection():
    validator = TelemetryValidator(track_history=False)
    frame = create_nominal_frame()
    frame.cht[1] = 280.0  # CHT exceeds maximum thermal limit 250°C
    result = validator.validate(frame)
    assert not result.is_valid
    assert result.quality == QualityStatus.INVALID
    assert any("cht[1]" in err for err in result.errors)


def test_non_monotonic_timestamp_detection():
    validator = TelemetryValidator(track_history=True)
    frame1 = create_nominal_frame(seq=1, timestamp=100.1)
    frame2 = create_nominal_frame(seq=2, timestamp=100.0)  # Time went backwards

    res1 = validator.validate(frame1)
    assert res1.is_valid

    res2 = validator.validate(frame2)
    assert not res2.is_valid
    assert any("Non-monotonic timestamp" in err for err in res2.errors)


def test_sequence_id_gap_detection():
    validator = TelemetryValidator(track_history=True)
    frame1 = create_nominal_frame(seq=10, timestamp=100.0)
    frame2 = create_nominal_frame(seq=15, timestamp=100.1)  # Dropped 4 frames

    validator.validate(frame1)
    res2 = validator.validate(frame2)
    # Dropped frames generate warnings and degrade quality
    assert res2.is_valid  # Still physically valid
    assert res2.quality == QualityStatus.DEGRADED
    assert any("Dropped frames" in warn for warn in res2.warnings)


def test_unphysical_rpm_slew_rate():
    validator = TelemetryValidator(track_history=True)
    frame1 = create_nominal_frame(seq=1, timestamp=100.0)
    frame1.rpm = 2000.0

    frame2 = create_nominal_frame(seq=2, timestamp=100.1)
    frame2.rpm = 5800.0  # +3800 RPM in 0.1s = 38000 RPM/s (exceeds 3500 RPM/s)

    validator.validate(frame1)
    res2 = validator.validate(frame2)
    assert not res2.is_valid
    assert any("Unphysical RPM slew rate" in err for err in res2.errors)


def test_unphysical_cht_slew_rate():
    validator = TelemetryValidator(track_history=True)
    frame1 = create_nominal_frame(seq=1, timestamp=100.0)
    frame1.cht = [90.0, 90.0, 90.0, 90.0]

    frame2 = create_nominal_frame(seq=2, timestamp=100.1)
    frame2.cht = [90.0, 115.0, 90.0, 90.0]  # +25°C in 0.1s = 250°C/s (exceeds 15°C/s)

    validator.validate(frame1)
    res2 = validator.validate(frame2)
    assert not res2.is_valid
    assert any("Unphysical CHT rate" in err for err in res2.errors)


def test_impossible_physical_combination():
    validator = TelemetryValidator(track_history=False)
    frame = create_nominal_frame()
    frame.rpm = 4500.0
    frame.fuel_flow = 0.1  # High power RPM with zero fuel flow is physically impossible

    res = validator.validate(frame)
    assert not res.is_valid
    assert any("Impossible condition" in err for err in res.errors)
