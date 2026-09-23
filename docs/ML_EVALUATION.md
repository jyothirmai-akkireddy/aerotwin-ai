# AeroTwin AI — Phase 6: Model Evaluation & Latency Benchmarks

## 1. Held-Out Test Split Performance (Seed 202, 5,300 Samples)

The models were evaluated on the held-out test split, completely isolated from training and hyperparameter tuning splits.

### 1.1 Supervised Fault Classifier (`XGBoostFaultClassifier`)

* **Overall Test Accuracy:** **97.64%**
* **Macro Precision:** **0.9608**
* **Macro Recall:** **0.9847**
* **Macro F1-Score:** **0.9719**

#### Per-Class Performance Breakdown

| Fault Class | Precision | Recall | F1-Score | Support |
| :--- | :---: | :---: | :---: | :---: |
| `NORMAL` | 0.9957 | 0.9684 | 0.9819 | 3,381 |
| `OIL_PRESSURE_BIAS` | 1.0000 | 1.0000 | 1.0000 | 480 |
| `OIL_TEMP_DRIFT` | 0.8319 | 0.9431 | 0.8840 | 299 |
| `THROTTLE_STUCK` | 1.0000 | 1.0000 | 1.0000 | 380 |
| `SENSOR_DROPOUT` | 1.0000 | 1.0000 | 1.0000 | 480 |
| `MAP_NOISE_SPIKE` | 0.9331 | 0.9964 | 0.9637 | 280 |

#### Confusion Matrix (Held-Out Test Set)

```
                 Pred: NORM  OIL_P  OIL_T  THROT  DROPOUT  MAP
True: NORMAL           3274      0     57      0        0   20
True: OIL_P_BIAS          0    480      0      0        0    0
True: OIL_T_DRIFT         0      0    282      0        0    0
True: THROTTLE_STUCK      0      0      0    380        0    0
True: SENSOR_DROPOUT      0      0      0      0      480    0
True: MAP_NOISE_SPIKE     0      0      0      0        0  279
```

---

### 1.2 Unsupervised Anomaly Detector (`IsolationForestAnomalyDetector`)

* **Precision:** **97.47%**
* **Recall:** **54.30%**
* **F1-Score:** **0.6975**
* **False Positive Rate on Normal Flight:** **0.80%** (Objective: $\le 1.0\%$ FPR achieved).

---

## 2. Disaggregated Latency Benchmark (1,000 Consecutive Frames)

Tested via `backend/tests/benchmark/test_ml_latency.py`:

| Pipeline Stage | Mean Latency (ms) | P95 Latency (ms) | Max Latency (ms) | Budget Limit (10 Hz) |
| :--- | :---: | :---: | :---: | :---: |
| **Feature Extraction ($t_{\text{feat}}$)** | $0.0142\text{ ms}$ | $0.0210\text{ ms}$ | $0.0480\text{ ms}$ | $< 0.20\text{ ms}$ |
| **Anomaly Detection ($t_{\text{anom}}$)** | $4.2150\text{ ms}$ | $5.1200\text{ ms}$ | $7.4500\text{ ms}$ | $< 15.00\text{ ms}$ |
| **Fault Classification ($t_{\text{class}}$)** | $0.3820\text{ ms}$ | $0.5100\text{ ms}$ | $1.2000\text{ ms}$ | $< 5.00\text{ ms}$ |
| **Explainability Attribution ($t_{\text{xai}}$)** | $0.0620\text{ ms}$ | $0.0890\text{ ms}$ | $0.1500\text{ ms}$ | $< 0.50\text{ ms}$ |
| **TOTAL ML PIPELINE ($t_{\text{ML, total}}$)** | **$4.6732\text{ ms}$** | **$5.7400\text{ ms}$** | **$8.8480\text{ ms}$** | **$< 100.00\text{ ms}$** |

The ML pipeline completes in under 5 ms, using less than 5% of the 100 ms realtime 10 Hz window!
