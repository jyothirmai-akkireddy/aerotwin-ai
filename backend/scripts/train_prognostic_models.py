"""Model Training Script for Engine Prognostics and Remaining Useful Life (RUL).

Trains quantile gradient boosting regressors to predict:
1. Median point estimate (quantile=0.50)
2. Lower 95% prediction interval bound (quantile=0.025)
3. Upper 95% prediction interval bound (quantile=0.975)

Evaluates on the held-out test split:
- MAE, RMSE
- Formal Empirical 95% Prediction Interval Coverage (Acceptance: >= 85%)
- Mean Prediction Interval Width

Persists model bundle and metadata to `models/prognostics/`.
"""

import json
import os
import sys
import time

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, root_mean_squared_error

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

DATA_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../data/processed/prognostics")
)
MODELS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../models/prognostics"))

FEATURE_COLUMNS = [
    "health_index",
    "beta_slope",
    "subsystem_oil_norm",
    "subsystem_therm_norm",
    "subsystem_turbo_norm",
    "subsystem_vib_norm",
    "cht_spread",
    "oil_temperature",
    "oil_pressure",
    "cum_thermal_stress",
    "cum_map_stress",
    "anom_score",
]
TARGET_COLUMN = "true_rul_hours"


def main() -> None:
    os.makedirs(MODELS_DIR, exist_ok=True)
    print("=================================================================")
    print("AeroTwin AI — Prognostics & RUL Model Training Pipeline")
    print("=================================================================")
    print("Data Directory:  ", DATA_DIR)
    print("Models Directory:", MODELS_DIR)

    train_path = os.path.join(DATA_DIR, "train_prognostics.parquet")
    val_path = os.path.join(DATA_DIR, "val_prognostics.parquet")
    test_path = os.path.join(DATA_DIR, "test_prognostics.parquet")

    if not (os.path.exists(train_path) and os.path.exists(test_path)):
        print(
            f"Error: Required datasets not found in {DATA_DIR}. Run generate_prognostic_datasets.py first."
        )
        sys.exit(1)

    print("\nLoading datasets...")
    df_train = pd.read_parquet(train_path)
    df_val = pd.read_parquet(val_path)
    df_test = pd.read_parquet(test_path)

    print(f"Train samples: {len(df_train)} (Runs: {df_train['run_id'].nunique()})")
    print(f"Val samples:   {len(df_val)} (Runs: {df_val['run_id'].nunique()})")
    print(f"Test samples:  {len(df_test)} (Runs: {df_test['run_id'].nunique()})")

    X_train = df_train[FEATURE_COLUMNS].to_numpy()
    y_train = df_train[TARGET_COLUMN].to_numpy()

    X_val = df_val[FEATURE_COLUMNS].to_numpy()
    y_val = df_val[TARGET_COLUMN].to_numpy()

    X_test = df_test[FEATURE_COLUMNS].to_numpy()
    y_test = df_test[TARGET_COLUMN].to_numpy()

    print("\nTraining Quantile Gradient Boosting Regressors...")
    start_time = time.perf_counter()

    # 1. Median point estimate model (quantile=0.50)
    print("1. Fitting Median Regressor (q=0.50)...")
    model_med = HistGradientBoostingRegressor(
        loss="quantile",
        quantile=0.50,
        max_iter=150,
        max_depth=6,
        learning_rate=0.08,
        random_state=42,
    )
    model_med.fit(X_train, y_train)

    # 2. Lower bound model (quantile=0.025)
    print("2. Fitting Lower Bound Regressor (q=0.025)...")
    model_low = HistGradientBoostingRegressor(
        loss="quantile",
        quantile=0.025,
        max_iter=150,
        max_depth=6,
        learning_rate=0.08,
        random_state=42,
    )
    model_low.fit(X_train, y_train)

    # 3. Upper bound model (quantile=0.975)
    print("3. Fitting Upper Bound Regressor (q=0.975)...")
    model_upp = HistGradientBoostingRegressor(
        loss="quantile",
        quantile=0.975,
        max_iter=150,
        max_depth=6,
        learning_rate=0.08,
        random_state=42,
    )
    model_upp.fit(X_train, y_train)

    fit_duration = time.perf_counter() - start_time
    print(f"Training completed in {fit_duration:.2f} s")

    # Conformal Calibration on Validation Split to guarantee >= 85% empirical coverage
    print("\nCalibrating prediction intervals on Validation Split (Runs 151–170)...")
    val_pred_med = model_med.predict(X_val)
    val_pred_low = np.minimum(model_low.predict(X_val), val_pred_med)
    val_pred_upp = np.maximum(model_upp.predict(X_val), val_pred_med)

    # Compute validation non-conformity margin for 95% target
    val_errors_low = np.maximum(0.0, val_pred_low - y_val)
    val_errors_upp = np.maximum(0.0, y_val - val_pred_upp)
    val_max_errors = np.maximum(val_errors_low, val_errors_upp)

    # 95th percentile conformal correction margin
    conformal_margin = float(np.percentile(val_max_errors, 95.0))
    print(f"Computed Conformal Correction Margin delta: {conformal_margin:.3f} flight hours")

    # Evaluate on held-out test set
    print("\nEvaluating on independent Test Split (Runs 171–190)...")
    pred_med = model_med.predict(X_test)
    pred_low = np.maximum(0.0, model_low.predict(X_test) - conformal_margin)
    pred_upp = model_upp.predict(X_test) + conformal_margin

    # Ensure ordering sanity: low <= med <= upp
    pred_low = np.minimum(pred_low, pred_med)
    pred_upp = np.maximum(pred_upp, pred_med)

    mae = float(mean_absolute_error(y_test, pred_med))
    rmse = float(root_mean_squared_error(y_test, pred_med))

    # Empirical 95% Prediction Interval Coverage
    in_interval = (y_test >= pred_low) & (y_test <= pred_upp)
    empirical_coverage_95 = float(np.mean(in_interval))
    mean_interval_width = float(np.mean(pred_upp - pred_low))

    print("-----------------------------------------------------------------")
    print(f"Test MAE:                         {mae:.3f} flight hours")
    print(f"Test RMSE:                        {rmse:.3f} flight hours")
    print(
        f"Empirical 95% PI Coverage:        {empirical_coverage_95 * 100.0:.2f}% (Target: >= 85%)"
    )
    print(f"Mean Prediction Interval Width:   {mean_interval_width:.3f} flight hours")
    print("-----------------------------------------------------------------")

    if empirical_coverage_95 < 0.85:
        print("WARNING: Empirical coverage is below the 85% acceptance threshold!")
    else:
        print("PASS: Empirical coverage satisfies statistical acceptance threshold.")

    # Save model artifact bundle
    bundle_path = os.path.join(MODELS_DIR, "rul_estimator_v1.joblib")
    bundle = {
        "model_median": model_med,
        "model_lower": model_low,
        "model_upper": model_upp,
        "conformal_margin": conformal_margin,
        "is_fitted": True,
        "feature_names": FEATURE_COLUMNS,
    }
    joblib.dump(bundle, bundle_path)
    print(f"\nSaved RUL model bundle to {bundle_path}")

    # Save metadata JSON
    metadata = {
        "model_name": "HistGradientBoostingRULQuantileEstimator",
        "model_version": "1.0.0",
        "feature_schema_version": "1.0.0",
        "target": TARGET_COLUMN,
        "features": FEATURE_COLUMNS,
        "quantiles": [0.025, 0.50, 0.975],
        "test_metrics": {
            "mae_hours": round(mae, 4),
            "rmse_hours": round(rmse, 4),
            "empirical_95_coverage": round(empirical_coverage_95, 4),
            "mean_interval_width_hours": round(mean_interval_width, 4),
        },
        "training_metadata": {
            "train_samples": len(df_train),
            "train_runs": int(df_train["run_id"].nunique()),
            "fit_duration_seconds": round(fit_duration, 2),
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        },
        "disclaimer": (
            "PROTOTYPE RESEARCH MODEL — NOT FOR CERTIFIED FLIGHT OPERATIONS OR REAL-WORLD LIFING"
        ),
    }

    metadata_path = os.path.join(MODELS_DIR, "metadata.json")
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    print(f"Saved model metadata to {metadata_path}")


if __name__ == "__main__":
    main()
