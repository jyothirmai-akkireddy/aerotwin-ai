"""Model Training and Persistence Pipeline for Phase 6 ML Models.

Trains:
1. Unsupervised IsolationForest anomaly detector on normal flight profiles.
2. Supervised XGBoost/HistGradient multi-class fault classifier on 6 target classes.
3. Evaluates models on held-out test split (Seed 202) with macro & per-class metrics.
4. Persists joblib bundles and metadata JSON into models/anomaly/ and models/classifier/.
"""

import json
import os
import sys
import time

import numpy as np
import pandas as pd
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.domain.ml.anomaly import IsolationForestAnomalyDetector
from app.domain.ml.classifier import CLASS_NAMES, XGBoostFaultClassifier
from app.domain.ml.features import FEATURE_NAMES

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data/processed/ml"))
MODELS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../models"))


def train_and_evaluate() -> None:
    print("==================================================")
    print("STARTING ML MODEL TRAINING & EVALUATION PIPELINE")
    print("==================================================")

    # 1. Load Parquet Datasets
    train_path = os.path.join(DATA_DIR, "train_dataset.parquet")
    val_path = os.path.join(DATA_DIR, "val_dataset.parquet")
    test_path = os.path.join(DATA_DIR, "test_dataset.parquet")

    train_df = pd.read_parquet(train_path)
    val_df = pd.read_parquet(val_path)
    test_df = pd.read_parquet(test_path)

    print(f"Loaded Train: {train_df.shape}, Val: {val_df.shape}, Test: {test_df.shape}")

    X_train = train_df[FEATURE_NAMES].values
    X_val = val_df[FEATURE_NAMES].values
    X_test = test_df[FEATURE_NAMES].values

    y_train_str = train_df["fault_class"].values
    y_val_str = val_df["fault_class"].values
    y_test_str = test_df["fault_class"].values

    is_anom_test = test_df["is_anomaly"].values

    # Mapping class names to integers
    class_to_idx = {name: idx for idx, name in enumerate(CLASS_NAMES)}
    y_train_idx = np.array([class_to_idx[c] for c in y_train_str])

    # -------------------------------------------------------------
    # 2. Train Anomaly Detector (Isolation Forest on NORMAL flight)
    # -------------------------------------------------------------
    print("\n--- 1. Training Anomaly Detector (Isolation Forest) ---")
    normal_mask_train = y_train_str == "NORMAL"
    X_train_normal = X_train[normal_mask_train]
    print(f"Training on {len(X_train_normal)} normal flight samples...")

    t0_anom = time.perf_counter()
    anomaly_detector = IsolationForestAnomalyDetector()
    anomaly_detector.fit(X_train_normal, contamination=0.03, random_state=42)
    t_train_anom = time.perf_counter() - t0_anom
    print(f"Fitted Isolation Forest in {t_train_anom:.3f} s")

    # Calibrate threshold on validation normal split for FPR <= 1.0%
    normal_mask_val = y_val_str == "NORMAL"
    X_val_normal = X_val[normal_mask_val]
    calibrated_thresh = anomaly_detector.calibrate_threshold(X_val_normal, target_fpr=0.01)
    print(f"Calibrated Anomaly Threshold (FPR <= 1%): {calibrated_thresh:.4f}")

    # Evaluate Anomaly Detector on Test Split
    test_anom_preds = [anomaly_detector.predict(X_test[i]).flag for i in range(len(X_test))]
    anom_prec = precision_score(is_anom_test, test_anom_preds, zero_division=0)
    anom_rec = recall_score(is_anom_test, test_anom_preds, zero_division=0)
    anom_f1 = f1_score(is_anom_test, test_anom_preds, zero_division=0)

    # False positive rate on normal test samples
    normal_mask_test = is_anom_test == 0.0
    test_anom_preds_arr = np.array(test_anom_preds)
    test_fpr = np.mean(test_anom_preds_arr[normal_mask_test])

    print(
        f"[Anomaly Test Metrics] Precision: {anom_prec:.4f} | Recall: {anom_rec:.4f} | F1: {anom_f1:.4f} | FPR: {test_fpr:.4f}"
    )

    # -------------------------------------------------------------
    # 3. Train Fault Classifier (XGBoost / HistGradient)
    # -------------------------------------------------------------
    print("\n--- 2. Training Supervised Fault Classifier ---")
    t0_class = time.perf_counter()
    fault_classifier = XGBoostFaultClassifier(confidence_threshold=0.60)
    fault_classifier.fit(X_train, y_train_idx, use_xgboost=True, random_state=42)
    t_train_class = time.perf_counter() - t0_class
    print(f"Fitted {fault_classifier.classifier_name} in {t_train_class:.3f} s")

    # Evaluate Classifier on Test Split
    test_class_preds: list[str] = []
    for i in range(len(X_test)):
        is_anom = test_anom_preds[i]
        res = fault_classifier.predict(X_test[i], is_anom=is_anom)
        test_class_preds.append(res.fault_class.value)

    # Metrics on known classes
    cls_report = classification_report(
        y_test_str, test_class_preds, labels=CLASS_NAMES, output_dict=True, zero_division=0
    )
    macro_f1 = cls_report["macro avg"]["f1-score"]
    macro_prec = cls_report["macro avg"]["precision"]
    macro_rec = cls_report["macro avg"]["recall"]
    from sklearn.metrics import accuracy_score

    accuracy = float(accuracy_score(y_test_str, test_class_preds))

    print(
        f"[Classifier Test Metrics] Accuracy: {accuracy:.4f} | Macro Prec: {macro_prec:.4f} | Macro Rec: {macro_rec:.4f} | Macro F1: {macro_f1:.4f}"
    )
    cm = confusion_matrix(y_test_str, test_class_preds, labels=CLASS_NAMES)
    print("Confusion Matrix:\n", cm)

    # -------------------------------------------------------------
    # 4. Save Trained Models & Metadata
    # -------------------------------------------------------------
    anom_dir = os.path.join(MODELS_DIR, "anomaly")
    class_dir = os.path.join(MODELS_DIR, "classifier")
    os.makedirs(anom_dir, exist_ok=True)
    os.makedirs(class_dir, exist_ok=True)

    anom_model_path = os.path.join(anom_dir, "isolation_forest_v1.joblib")
    anomaly_detector.save(anom_model_path)
    print(f"\nSaved anomaly detector to: {anom_model_path}")

    anom_meta = {
        "model_version": anomaly_detector.model_version,
        "detector_name": anomaly_detector.detector_name,
        "feature_schema_version": "1.0.0",
        "threshold": round(anomaly_detector.threshold, 4),
        "score_min": round(anomaly_detector.score_min, 4),
        "score_max": round(anomaly_detector.score_max, 4),
        "trained_at_utc": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "provenance": "SYNTHETIC_SIMULATED_PROTOTYPE",
        "training_samples": int(len(X_train_normal)),
        "test_metrics": {
            "precision": round(float(anom_prec), 4),
            "recall": round(float(anom_rec), 4),
            "f1": round(float(anom_f1), 4),
            "false_positive_rate": round(float(test_fpr), 4),
        },
    }
    with open(os.path.join(anom_dir, "metadata.json"), "w", encoding="utf-8") as f:
        json.dump(anom_meta, f, indent=2)

    class_model_path = os.path.join(class_dir, "fault_classifier_v1.joblib")
    fault_classifier.save(class_model_path)
    print(f"Saved fault classifier to: {class_model_path}")

    class_meta = {
        "model_version": fault_classifier.model_version,
        "classifier_name": fault_classifier.classifier_name,
        "feature_schema_version": "1.0.0",
        "confidence_threshold": fault_classifier.confidence_threshold,
        "class_names": CLASS_NAMES,
        "trained_at_utc": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "provenance": "SYNTHETIC_SIMULATED_PROTOTYPE",
        "training_samples": int(len(X_train)),
        "test_metrics": {
            "accuracy": round(float(accuracy), 4),
            "macro_precision": round(float(macro_prec), 4),
            "macro_recall": round(float(macro_rec), 4),
            "macro_f1": round(float(macro_f1), 4),
            "per_class": {
                name: {
                    "precision": round(float(cls_report[name]["precision"]), 4),
                    "recall": round(float(cls_report[name]["recall"]), 4),
                    "f1": round(float(cls_report[name]["f1-score"]), 4),
                    "support": int(cls_report[name]["support"]),
                }
                for name in CLASS_NAMES
            },
        },
    }
    with open(os.path.join(class_dir, "metadata.json"), "w", encoding="utf-8") as f:
        json.dump(class_meta, f, indent=2)

    print("==================================================")
    print("TRAINING & PERSISTENCE COMPLETE")
    print("==================================================")


if __name__ == "__main__":
    train_and_evaluate()
