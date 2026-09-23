"""Unit tests for unsupervised Isolation Forest anomaly detection."""

import os
import tempfile

import numpy as np

from app.domain.ml.anomaly import IsolationForestAnomalyDetector
from app.domain.ml.models import AnomalyStatus


def test_uninitialized_anomaly_detector():
    """Verify safe fallback behavior when detector is not fitted."""
    detector = IsolationForestAnomalyDetector()
    assert not detector.is_fitted

    dummy_feats = np.zeros(24, dtype=np.float64)
    res = detector.predict(dummy_feats)

    assert not res.flag
    assert res.status == AnomalyStatus.NORMAL
    assert res.score == 0.0
    assert res.confidence == 0.50
    assert res.detector_name == "IsolationForest"


def test_monotonic_severity_and_calibration():
    """Verify monotonic severity scoring and threshold calibration."""
    rng = np.random.RandomState(42)
    # Generate 500 normal samples in 24D with nominal battery voltage
    X_train_norm = rng.normal(loc=0.0, scale=1.0, size=(500, 24))
    X_train_norm[:, 8] = 28.2
    X_val_norm = rng.normal(loc=0.0, scale=1.0, size=(200, 24))
    X_val_norm[:, 8] = 28.2

    detector = IsolationForestAnomalyDetector()
    detector.fit(X_train_norm, contamination=0.03, random_state=42)
    assert detector.is_fitted

    # Calibrate threshold for target FPR <= 5%
    thresh = detector.calibrate_threshold(X_val_norm, target_fpr=0.05)
    assert 0.0 <= thresh <= 1.0

    # Evaluate normal samples vs extreme outlier
    normal_sample = X_val_norm[0]
    res_normal = detector.predict(normal_sample)
    assert 0.0 <= res_normal.score <= 1.0
    assert 0.50 <= res_normal.confidence <= 1.00

    # Severe outlier: 20 sigma excursion
    outlier_sample = np.ones(24) * 20.0
    res_outlier = detector.predict(outlier_sample)
    assert res_outlier.score > res_normal.score
    assert res_outlier.flag
    assert res_outlier.status == AnomalyStatus.ANOMALOUS


def test_anomaly_persistence_roundtrip():
    """Verify save and load serialization preserves model parameters."""
    rng = np.random.RandomState(42)
    X = rng.normal(size=(200, 24))

    detector = IsolationForestAnomalyDetector(threshold=0.62)
    detector.fit(X, random_state=42)

    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = os.path.join(tmpdir, "anomaly_test.joblib")
        detector.save(filepath)
        assert os.path.exists(filepath)

        loaded = IsolationForestAnomalyDetector.load(filepath)
        assert loaded.is_fitted
        assert loaded.threshold == 0.62
        assert loaded.detector_name == "IsolationForest"

        test_feat = rng.normal(size=(24,))
        orig_res = detector.predict(test_feat)
        loaded_res = loaded.predict(test_feat)

        assert orig_res.score == loaded_res.score
        assert orig_res.flag == loaded_res.flag
        assert orig_res.confidence == loaded_res.confidence
