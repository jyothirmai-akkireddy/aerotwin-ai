# AeroTwin AI — Phase 6: Deterministic 24-Feature Manifest

## Schema Specification: `FEATURE_SCHEMA_VERSION = "1.0.0"`

The feature extraction layer (`FeatureExtractor`) deterministically constructs a 24-dimensional feature vector $\mathbf{x} \in \mathbb{R}^{24}$ from each incoming `TelemetryFrame` and accompanying Phase 5 `PhysicsTwinResult`.

| Index | Feature Name | Physical Unit | Data Source | Exact Mathematical Definition / Derivation | Valid Range | Nominal Baseline |
| :---: | :--- | :---: | :--- | :--- | :---: | :---: |
| `0` | `rpm` | RPM | Telemetry | $y_{\text{rpm}}$ | $[0.0, 6500.0]$ | $2400.0$ |
| `1` | `manifold_pressure` | inHg | Telemetry | $y_{\text{map}}$ | $[10.0, 45.0]$ | $29.5$ |
| `2` | `throttle_position` | % | Telemetry | $y_{\text{throttle}}$ | $[0.0, 100.0]$ | $45.0$ |
| `3` | `fuel_flow` | L/h | Telemetry | $y_{\text{ff}}$ | $[0.0, 50.0]$ | $16.5$ |
| `4` | `oil_pressure` | bar | Telemetry | $y_{\text{oil\_p}}$ | $[0.0, 7.0]$ | $3.8$ |
| `5` | `oil_temperature` | °C | Telemetry | $y_{\text{oil\_t}}$ | $[-20.0, 140.0]$ | $85.0$ |
| `6` | `coolant_temp` | °C | Telemetry | $y_{\text{coolant}}$ | $[-20.0, 130.0]$ | $82.0$ |
| `7` | `vibration_rms` | g | Telemetry | $y_{\text{vib}}$ | $[0.0, 10.0]$ | $1.15$ |
| `8` | `battery_voltage` | V | Telemetry | $y_{\text{v\_bat}}$ | $[0.0, 36.0]$ | $28.2$ |
| `9` | `true_airspeed` | m/s | Telemetry | $y_{\text{tas}}$ | $[0.0, 120.0]$ | $45.0$ |
| `10` | `cht_mean` | °C | Derived | $\frac{1}{4}\sum_{i=1}^4 y_{\text{cht}, i}$ | $[0.0, 200.0]$ | $94.9$ |
| `11` | `cht_spread` | °C | Derived | $\max_i(y_{\text{cht}, i}) - \min_i(y_{\text{cht}, i})$ | $[0.0, 80.0]$ | $5.5$ |
| `12` | `egt_mean` | °C | Derived | $\frac{1}{4}\sum_{i=1}^4 y_{\text{egt}, i}$ | $[0.0, 950.0]$ | $721.8$ |
| `13` | `egt_spread` | °C | Derived | $\max_i(y_{\text{egt}, i}) - \min_i(y_{\text{egt}, i})$ | $[0.0, 200.0]$ | $15.0$ |
| `14` | `cht_cyl1_dev` | °C | Derived | $y_{\text{cht}, 1} - \text{cht\_mean}$ | $[-50.0, 50.0]$ | $0.1$ |
| `15` | `egt_cyl1_dev` | °C | Derived | $y_{\text{egt}, 1} - \text{egt\_mean}$ | $[-100.0, 100.0]$ | $-1.8$ |
| `16` | `res_map_raw` | inHg | Phase 5 Residual | $y_{\text{map}} - \hat{y}_{\text{map}}$ | $[-20.0, 20.0]$ | $0.0$ |
| `17` | `res_map_norm` | $\sigma$ | Phase 5 Residual | $(y_{\text{map}} - \hat{y}_{\text{map}}) / \sigma_{\text{map}}$ ($\sigma_{\text{map}}=0.45\text{ inHg}$) | $[-15.0, 15.0]$ | $0.0$ |
| `18` | `res_ff_norm` | $\sigma$ | Phase 5 Residual | $(y_{\text{ff}} - \hat{y}_{\text{ff}}) / \sigma_{\text{ff}}$ ($\sigma_{\text{ff}}=0.85\text{ L/h}$) | $[-15.0, 15.0]$ | $0.0$ |
| `19` | `res_oil_p_raw` | bar | Phase 5 Residual | $y_{\text{oil\_p}} - \hat{y}_{\text{oil\_p}}$ | $[-5.0, 5.0]$ | $0.0$ |
| `20` | `res_oil_p_norm` | $\sigma$ | Phase 5 Residual | $(y_{\text{oil\_p}} - \hat{y}_{\text{oil\_p}}) / \sigma_{\text{oil\_p}}$ ($\sigma_{\text{oil\_p}}=0.22\text{ bar}$) | $[-15.0, 15.0]$ | $0.0$ |
| `21` | `res_oil_t_norm` | $\sigma$ | Phase 5 Residual | $(y_{\text{oil\_t}} - \hat{y}_{\text{oil\_t}}) / \sigma_{\text{oil\_t}}$ ($\sigma_{\text{oil\_t}}=2.10^\circ\text{C}$) | $[-15.0, 15.0]$ | $0.0$ |
| `22` | `res_vib_norm` | $\sigma$ | Phase 5 Residual | $(y_{\text{vib}} - \hat{y}_{\text{vib}}) / \sigma_{\text{vib}}$ ($\sigma_{\text{vib}}=0.08\text{ g}$) | $[-15.0, 15.0]$ | $0.0$ |
| `23` | `res_mean_abs_norm` | $\sigma$ | Phase 5 Residual | $\frac{1}{K}\sum_{k=1}^K \|z_k\|$ (Mean Absolute Normalized Residual) | $[0.0, 20.0]$ | $0.0$ |

---

## Architectural Invariants & Safety Guarantees

1. **Causal Time Invariant:** Features depend strictly on the instantaneous frame $t$ and causal internal simulator states (zero forward temporal leakage).
2. **Missing Physics Handling:** If Phase 5 `PhysicsTwinResult` is absent (e.g., initial tick), all residual features (`16`–`23`) deterministically default to `0.0`, ensuring safe execution.
3. **Finiteness Invariant:** If any telemetry input is non-finite (`NaN`, `+Inf`, `-Inf`), the feature extractor safely falls back to nominal baselines.
