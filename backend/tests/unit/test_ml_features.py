"""Unit tests for deterministic 24-feature extraction layer."""

import math

import numpy as np

from app.domain.entities.telemetry import QualityStatus, TelemetryFrame, TelemetrySource
from app.domain.ml.features import (
    FEATURE_NAMES,
    FEATURE_SCHEMA_VERSION,
    NOMINAL_BASELINES,
    FeatureExtractor,
)
from app.domain.physics.models import (
    ModelValidity,
    PhysicsExpectedState,
    PhysicsResidualSet,
    PhysicsTwinResult,
)


def _make_frame(**kwargs) -> TelemetryFrame:
    defaults = {
        "timestamp": 100.0,
        "sequence_id": 1,
        "source_type": TelemetrySource.SIMULATED,
        "quality_flag": QualityStatus.VALID,
        "rpm": 2400.0,
        "manifold_pressure": 29.5,
        "throttle_position": 45.0,
        "fuel_flow": 16.5,
        "fuel_pressure": 3.0,
        "injection_timing": 15.0,
        "cht": [95.0, 95.0, 95.0, 95.0],
        "egt": [720.0, 720.0, 720.0, 720.0],
        "coolant_temp": 82.0,
        "oil_temperature": 85.0,
        "oil_pressure": 3.8,
        "vibration_rms": 1.15,
        "battery_voltage": 28.2,
        "alternator_current": 20.0,
        "alternator_status": "OK",
        "altitude": 500.0,
        "ambient_temp": 20.0,
        "ambient_pressure": 29.92,
        "true_airspeed": 45.0,
    }
    defaults.update(kwargs)
    return TelemetryFrame(**defaults)


def _make_physics_result() -> PhysicsTwinResult:
    expected = PhysicsExpectedState(
        timestamp=100.0,
        sequence_id=1,
        rpm=2400.0,
        manifold_pressure=29.5,
        air_mass_flow=180.0,
        fuel_flow=16.5,
        cht=[95.0, 95.0, 95.0, 95.0],
        egt=[720.0, 720.0, 720.0, 720.0],
        coolant_temp=82.0,
        oil_temperature=85.0,
        oil_pressure=3.8,
        vibration_rms=1.15,
        validity=ModelValidity.VALID,
        confidence=0.98,
        model_version="1.0.0",
    )
    residuals = PhysicsResidualSet(
        timestamp=100.0,
        sequence_id=1,
        raw_residuals={
            "manifold_pressure": 0.5,
            "oil_pressure": -0.2,
        },
        normalized_residuals={
            "manifold_pressure": 1.11,
            "fuel_flow": 0.82,
            "oil_pressure": -0.91,
            "oil_temperature": 0.50,
            "vibration_rms": 0.35,
        },
        cht_max_imbalance_celsius=0.0,
        egt_max_imbalance_celsius=0.0,
        mean_absolute_normalized_residual=0.74,
        validity=ModelValidity.VALID,
        confidence=0.98,
    )
    return PhysicsTwinResult(expected_state=expected, residuals=residuals)


def test_feature_manifest_shape_and_version():
    """Verify exactly 24 features and schema version 1.0.0."""
    extractor = FeatureExtractor()
    assert extractor.feature_count == 24
    assert len(FEATURE_NAMES) == 24
    assert extractor.schema_version == "1.0.0"
    assert FEATURE_SCHEMA_VERSION == "1.0.0"


def test_feature_extraction_without_physics():
    """Verify deterministic fallback when Phase 5 Physics result is None."""
    extractor = FeatureExtractor()
    frame = _make_frame()
    features = extractor.extract(frame, physics=None)

    assert isinstance(features, np.ndarray)
    assert features.shape == (24,)
    assert features.dtype == np.float64

    # Raw telemetry channels
    assert features[0] == 2400.0  # rpm
    assert features[1] == 29.5  # map
    assert features[2] == 45.0  # throttle
    assert features[4] == 3.8  # oil_pressure
    assert features[8] == 28.2  # battery_voltage

    # Cylinder spreads
    assert features[10] == 95.0  # cht_mean
    assert features[11] == 0.0  # cht_spread
    assert features[12] == 720.0  # egt_mean
    assert features[13] == 0.0  # egt_spread

    # Residuals must default to 0.0 when physics is missing
    for idx in range(16, 24):
        assert features[idx] == 0.0, f"Residual feature {FEATURE_NAMES[idx]} should be 0.0"


def test_feature_extraction_with_physics():
    """Verify residual channels are mapped from PhysicsTwinResult."""
    extractor = FeatureExtractor()
    frame = _make_frame()
    physics = _make_physics_result()
    features = extractor.extract(frame, physics=physics)

    assert features.shape == (24,)
    assert features[16] == 0.5  # res_map_raw
    assert features[17] == 1.11  # res_map_norm
    assert features[18] == 0.82  # res_ff_norm
    assert features[19] == -0.2  # res_oil_p_raw
    assert features[20] == -0.91  # res_oil_p_norm
    assert features[21] == 0.50  # res_oil_t_norm
    assert features[22] == 0.35  # res_vib_norm
    assert features[23] == 0.74  # res_mean_abs_norm


def test_finiteness_and_nan_sanitization():
    """Verify all features are finite numbers and NaN values fall back safely."""
    extractor = FeatureExtractor()
    frame = TelemetryFrame.model_construct(
        timestamp=100.0,
        sequence_id=1,
        source_type=TelemetrySource.SIMULATED,
        quality_flag=QualityStatus.VALID,
        rpm=float("nan"),
        manifold_pressure=29.5,
        throttle_position=45.0,
        fuel_flow=16.5,
        fuel_pressure=3.0,
        injection_timing=15.0,
        cht=[95.0, 95.0, 95.0, 95.0],
        egt=[720.0, 720.0, 720.0, 720.0],
        coolant_temp=82.0,
        oil_temperature=85.0,
        oil_pressure=float("inf"),
        vibration_rms=1.15,
        battery_voltage=28.2,
        alternator_current=20.0,
        alternator_status="OK",
        altitude=500.0,
        ambient_temp=20.0,
        ambient_pressure=29.92,
        true_airspeed=45.0,
    )
    features = extractor.extract(frame, physics=None)

    for i, val in enumerate(features):
        assert math.isfinite(val), f"Feature {FEATURE_NAMES[i]} is not finite: {val}"

    # Sanitized NaN and Inf fall back to nominal
    assert features[0] == NOMINAL_BASELINES["rpm"]
    assert features[4] == NOMINAL_BASELINES["oil_pressure"]


def test_asymmetry_and_spread_derivation():
    """Verify CHT and EGT mean and spread calculations."""
    extractor = FeatureExtractor()
    frame = _make_frame(
        cht=[100.0, 90.0, 95.0, 95.0],
        egt=[740.0, 710.0, 720.0, 710.0],
    )
    features = extractor.extract(frame, physics=None)

    assert features[10] == 95.0  # cht_mean = (100+90+95+95)/4 = 95.0
    assert features[11] == 10.0  # cht_spread = 100 - 90 = 10.0
    assert features[14] == 5.0  # cht_cyl1_dev = 100 - 95 = 5.0

    assert features[12] == 720.0  # egt_mean = (740+710+720+710)/4 = 720.0
    assert features[13] == 30.0  # egt_spread = 740 - 710 = 30.0
    assert features[15] == 20.0  # egt_cyl1_dev = 740 - 720 = 20.0
