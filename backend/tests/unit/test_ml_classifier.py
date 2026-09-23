"""Unit tests for supervised fault classifier, confidence thresholding, and OOD gates."""

import os
import tempfile

import numpy as np
import pytest

from app.domain.ml.classifier import XGBoostFaultClassifier
from app.domain.ml.models import DecisionReason, FaultCategory


def test_uninitialized_classifier():
    """Verify safe fallback behavior when classifier is not fitted."""
    classifier = XGBoostFaultClassifier()
    assert not classifier.is_fitted

    dummy_feats = np.zeros(24, dtype=np.float64)
    res = classifier.predict(dummy_feats)

    assert res.fault_class == FaultCategory.UNKNOWN
    assert res.reason == DecisionReason.LOW_CONFIDENCE
    assert res.confidence == 0.0
    assert res.classifier_name == "XGBoostFaultClassifier"


def test_classifier_training_and_probability_normalization():
    """Verify trained classifier outputs normalized probabilities summing to 1.0."""
    rng = np.random.RandomState(42)
    # Generate synthetic 6-class dataset
    n_samples = 300
    X = rng.normal(size=(n_samples, 24))
    y = rng.randint(0, 6, size=n_samples)

    classifier = XGBoostFaultClassifier(confidence_threshold=0.60)
    classifier.fit(X, y, use_xgboost=False, random_state=42)  # Use HistGradient for quick unit test
    assert classifier.is_fitted

    sample = X[0]
    res = classifier.predict(sample, is_anom=False)

    assert isinstance(res.fault_class, FaultCategory)
    assert 0.0 <= res.confidence <= 1.0
    assert len(res.probabilities) == 6

    # Probabilities must sum to approximately 1.0
    prob_sum = sum(res.probabilities.values())
    assert pytest.approx(prob_sum, abs=0.01) == 1.0


def test_low_confidence_gate():
    """Verify candidate below confidence threshold returns UNKNOWN with LOW_CONFIDENCE reason."""
    classifier = XGBoostFaultClassifier(confidence_threshold=0.9999)  # Ultra-high threshold
    rng = np.random.RandomState(42)
    X = rng.normal(size=(100, 24))
    y = rng.randint(0, 6, size=100)
    classifier.fit(X, y, use_xgboost=False)

    sample = X[0]
    res = classifier.predict(sample, is_anom=False)

    assert res.fault_class == FaultCategory.UNKNOWN
    assert res.reason == DecisionReason.LOW_CONFIDENCE
    assert res.threshold_applied == 0.9999


def test_out_of_distribution_ood_gate():
    """Verify when is_anom=True but classifier predicts NORMAL, output is UNKNOWN (OOD)."""
    classifier = XGBoostFaultClassifier(confidence_threshold=0.50)
    # Train heavily on class 0 (NORMAL) so it always predicts NORMAL
    X = np.zeros((100, 24))
    y = np.zeros(100, dtype=int)
    classifier.fit(X, y, use_xgboost=False)

    sample = np.zeros(24)
    # Without anomaly flag: predicts NORMAL
    res_nom = classifier.predict(sample, is_anom=False)
    assert res_nom.fault_class == FaultCategory.NORMAL
    assert res_nom.reason == DecisionReason.NOMINAL_FLIGHT

    # With anomaly flag active: overrides to UNKNOWN (OOD)
    res_ood = classifier.predict(sample, is_anom=True)
    assert res_ood.fault_class == FaultCategory.UNKNOWN
    assert res_ood.reason == DecisionReason.OUT_OF_DISTRIBUTION


def test_classifier_persistence_roundtrip():
    """Verify save and load serialization preserves model state."""
    rng = np.random.RandomState(42)
    X = rng.normal(size=(100, 24))
    y = rng.randint(0, 6, size=100)

    classifier = XGBoostFaultClassifier(confidence_threshold=0.65)
    classifier.fit(X, y, use_xgboost=False, random_state=42)

    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = os.path.join(tmpdir, "classifier_test.joblib")
        classifier.save(filepath)
        assert os.path.exists(filepath)

        loaded = XGBoostFaultClassifier.load(filepath)
        assert loaded.is_fitted
        assert loaded.confidence_threshold == 0.65

        test_feat = rng.normal(size=(24,))
        orig_res = classifier.predict(test_feat)
        loaded_res = loaded.predict(test_feat)

        assert orig_res.fault_class == loaded_res.fault_class
        assert orig_res.reason == loaded_res.reason
        assert orig_res.confidence == loaded_res.confidence
