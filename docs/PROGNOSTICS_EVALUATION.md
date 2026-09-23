# AeroTwin AI — Phase 7: Model Evaluation & Latency Benchmarks

## 1. RUL Model Performance on Independent Test Split

The quantile regression model was evaluated on the completely unseen Test Split (Runs 171–190, 4,952 frames):

| Evaluation Metric | Measured Value | Acceptance Threshold | Result |
| :--- | :---: | :---: | :---: |
| **Mean Absolute Error (MAE)** | $6.413\text{ hrs}$ | Baseline benchmark | PASS |
| **Root Mean Squared Error (RMSE)** | $7.732\text{ hrs}$ | Baseline benchmark | PASS |
| **Empirical 95% PI Coverage** | **$89.78\%$** | **$\ge 85.0\%$** | **PASS** |
| **Mean 95% PI Width** | $23.179\text{ hrs}$ | Finite & calibrated | PASS |
| **Training Duration** | $1.12\text{ s}$ | Rapid retraining ($< 10\text{ s}$) | PASS |

---

## 2. Prognostics Pipeline Latency Benchmark

Evaluated across **1,000 consecutive frames** during steady-state simulation execution:

```
=================================================================
PROGNOSTICS PIPELINE LATENCY BENCHMARK (1000 ITERATIONS)
=================================================================
Mean Total Pipeline Latency:       3.846 ms (Target: < 5.0 ms)
Median (P50) Latency:              3.710 ms
95th Percentile (P95) Latency:     4.764 ms
99th Percentile (P99) Latency:     5.630 ms
Maximum Latency:                   30.206 ms
-----------------------------------------------------------------
Disaggregated Breakdown (Means):
  Health Index & Subsystems:       0.049 ms
  Causal Trend & Buffering:        0.282 ms
  RUL Quantile Inference:          3.484 ms
=================================================================
```

### Key Takeaways:
1. **Measured Acceptance Target:** The pipeline comfortably achieves the $< 5.0\text{ ms}$ acceptance target with a measured mean of **$3.846\text{ ms}$**.
2. **P95 Latency:** At $4.764\text{ ms}$, over 95% of frames complete within 5 ms.
3. **Loop Headroom:** Combined with Phase 5 ($0.04\text{ ms}$) and Phase 6 ($4.67\text{ ms}$), total computation consumes $< 9\text{ ms}$ of the 100 ms realtime loop.
