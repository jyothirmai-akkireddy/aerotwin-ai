# AeroTwin AI — Phase 6: ML Training Pipeline & Dataset Generation

## 1. Run-Isolated Dataset Generation Protocol

To strictly prevent temporal autocorrelation leakage across sequential frames, datasets are partitioned at the **flight run and PRNG seed level**:

* **Training Set (`train_dataset.parquet`)**: Seed `42`, 5,300 rows across 6 flight scenarios.
* **Validation Set (`val_dataset.parquet`)**: Seed `101`, 5,300 rows across 6 flight scenarios.
* **Held-Out Test Set (`test_dataset.parquet`)**: Seed `202`, 5,300 rows across 6 flight scenarios.

### Fault Injection Profiles
1. **NORMAL**: Full flight profile (`SCENARIO_COMPLETE_FLIGHT`) spanning Taxi, Takeoff, Climb, Cruise, Descent, Approach, and Rollout (duration: 330.1 s).
2. **OIL_PRESSURE_BIAS**: Cruise profile with additive step bias (+2.0 bar after $t=60\text{ s}$).
3. **OIL_TEMP_DRIFT**: Cruise profile with linear drift (+1.2°C/s between $t=100\text{ s}$ and $t=130\text{ s}$).
4. **THROTTLE_STUCK**: Transient flight profile with throttle actuator pinned at 30% after $t=60\text{ s}$.
5. **SENSOR_DROPOUT**: Cruise profile with alternator/battery channel dropout (voltage drops to 0.0V after $t=60\text{ s}$).
6. **MAP_NOISE_SPIKE**: Takeoff profile with 4x variance amplification in manifold pressure after $t=30\text{ s}$.

---

## 2. Model Training Protocol

* **Script:** `backend/scripts/train_ml_models.py`
* **Artifact Locations:**
  - `models/anomaly/isolation_forest_v1.joblib`
  - `models/anomaly/metadata.json`
  - `models/classifier/fault_classifier_v1.joblib`
  - `models/classifier/metadata.json`

### Hyperparameters:
* **Isolation Forest:**
  - `n_estimators = 100`
  - `contamination = 0.03`
  - `random_state = 42`
  - `n_jobs = -1`
  - Calibrated decision threshold on Validation Normal Split: $\tau = 0.5402$ (Target FPR $\le 1.0\%$).
* **XGBoost Fault Classifier:**
  - `n_estimators = 100`
  - `max_depth = 4`
  - `learning_rate = 0.08`
  - `subsample = 0.8`
  - `colsample_bytree = 0.8`
  - `objective = "multi:softprob"`
  - `confidence_threshold = 0.60`
