# AeroTwin AI — Phase 7: Prognostics Data & Benchmark Specification

## 1. Characterization as a Synthetic Benchmark Dataset Generator

> [!WARNING]
> The degradation trajectories utilized in Phase 7 are **synthetic benchmark data**, designed specifically to generate controlled, reproducible, stress-correlated run-to-failure flights for algorithmic testing. They are **NOT** physical models of metallurgical fatigue, tribological wear, or certified lifing schedules for Rotax or any real aero-engine.

---

## 2. Dataset Partitioning & Run Isolation

Data was generated using `backend/scripts/generate_prognostic_datasets.py` with complete run and seed isolation:

| Split Name | Run IDs | Seed Interval | Sample Count | Mean RUL (Hours) | File Path |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Train** | 101–150 | 10101–10150 | 12,348 | $15.02\text{ hrs}$ | `data/processed/prognostics/train_prognostics.parquet` |
| **Validation** | 151–170 | 10151–10170 | 4,760 | $14.57\text{ hrs}$ | `data/processed/prognostics/val_prognostics.parquet` |
| **Test** | 171–190 | 10171–10190 | 4,952 | $12.14\text{ hrs}$ | `data/processed/prognostics/test_prognostics.parquet` |

---

## 3. 12-Feature Schema (`PROGNOSTIC_FEATURE_SCHEMA_VERSION = "1.0.0"`)

| Index | Feature Name | Source | Physical Description |
| :---: | :--- | :---: | :--- |
| `0` | `health_index` | Calculated | Composite Health Index in $[0.0, 1.0]$ |
| `1` | `beta_slope` | Causal Buffer | OLS regression slope of Health Index over time ($\text{s}^{-1}$) |
| `2` | `subsystem_oil_norm` | Subsystem | Lubrication normalized deviation ($z_{\text{oil}}$) |
| `3` | `subsystem_therm_norm` | Subsystem | Thermal balance normalized deviation ($z_{\text{therm}}$) |
| `4` | `subsystem_turbo_norm` | Subsystem | Turbocharger MAP deficit normalized deviation ($z_{\text{turbo}}$) |
| `5` | `subsystem_vib_norm` | Subsystem | Mechanical vibration normalized deviation ($z_{\text{vib}}$) |
| `6` | `cht_spread` | Telemetry | Peak-to-peak cylinder head temperature spread (°C) |
| `7` | `oil_temperature` | Telemetry | Engine oil temperature (°C) |
| `8` | `oil_pressure` | Telemetry | Engine oil pressure (bar) |
| `9` | `cum_thermal_stress` | Stress Integral | Cumulative exposure to CHT $> 120^\circ\text{C}$ ($\text{K}\cdot\text{s}$) |
| `10` | `cum_map_stress` | Stress Integral | Cumulative exposure to MAP $> 35\text{ inHg}$ ($\text{inHg}\cdot\text{s}$) |
| `11` | `anom_score` | Phase 6 ML | AI anomaly detection score from Isolation Forest ($s_{\text{anom}}$) |
