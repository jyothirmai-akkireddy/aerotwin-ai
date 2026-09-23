# AeroTwin AI — Physics Modeling Assumptions & Engineering Disclaimers

**Document Version**: 1.0.0  
**Phase**: Phase 5 — Physics-Informed Digital Twin  
**Reference Baseline**: Generic 4-Cylinder Turbocharged Aero-Piston Engine (MALE UAV Class)

---

## 1. Prototype Status & Disclaimer

> [!WARNING] PROTOTYPE APPROXIMATION NOTICE
> The analytical equations, coefficients, and thermal approximations implemented in the AeroTwin AI Physics-Informed Digital Twin are **prototype engineering approximations**. They are designed for real-time fault residual extraction, synthetic flight data benchmarking, and human-in-the-loop engineering visualization.
> 
> They are **NOT certified flight simulator aerodynamic models**, **NOT FAA/EASA-certified full authority digital engine control (FADEC) software**, and must not be used for actual aircraft primary flight control or direct airworthiness certification without empirical dyno-bench calibration and DO-178C software qualification.

---

## 2. Engine Architecture Baseline (Rotax 914/915 Comparison)

The analytical equations emulate the thermodynamic and mechanical characteristics of modern turbocharged 4-cylinder horizontally-opposed aero-piston engines (e.g. Rotax 914 UL / 915 iS class) commonly deployed in Medium Altitude Long Endurance (MALE) and tactical UAVs:

| Feature | Rotax 914 / 915 iS Reference | AeroTwin PIDT Analytical Model |
| :--- | :--- | :--- |
| **Displacement** | 1211 cc (914) / 1352 cc (915) | Configurable (Default: 1352 cc) |
| **Cylinder Layout** | 4-cylinder horizontally opposed (boxer) | 4-cylinder discrete thermal lumped balance |
| **Aspiration** | Turbocharged with wastegate | Naturally aspirated throttle + boost ratio schedule |
| **Cooling System** | Liquid-cooled heads, air-cooled cylinders | Convective ram air cooling + coolant jacket |
| **Rated Speed** | 5500 - 5800 RPM | 5500 RPM rated, 1400 RPM idle |
| **Nominal Cruise MAP** | 27 - 31 inHg | 29.5 inHg nominal |
| **Nominal Cruise CHT** | 90 - 110 °C | ~95 °C nominal |
| **Nominal Cruise EGT** | 700 - 750 °C | ~720 °C nominal |
| **Oil Pressure** | 2.0 - 5.0 bar | 2.0 - 5.0 bar positive-displacement curve |

---

## 3. Operational Validity Envelopes & Model Validity

Models do not silently clamp extreme values to artificially realistic numbers. Instead, mathematical expressions are evaluated faithfully, and an explicit `ModelValidity` enum is assigned:

| Validity State | Environmental / Operating Boundary | System Behavior |
| :--- | :--- | :--- |
| `VALID` | Altitude $\in [-500, 12000]\text{ m}$, $T_{\text{amb}} \in [-60, 65]^\circ\text{C}$, $\text{RPM} \ge 1000$ | Standard flight operation; confidence $\approx 0.98$. |
| `DEGRADED` | Engine starting, idle, shutdown, or transition ($\text{RPM} < 1000$) | Transient operations outside steady-state regime; confidence $\le 0.60$. |
| `OUT_OF_RANGE` | Atmospheric or physical variables exceed flight envelope | Physics sub-models flag out-of-envelope condition; confidence $\le 0.30$. |
| `INVALID` | Missing sensor data, corrupted quality flag, or non-finite (NaN/Inf) values | Safe zero output; confidence $0.0$; diagnostic event logged. |

### Non-Silent Clamping Policy
If an observed sensor reading exhibits a massive physical discrepancy (e.g., severe turbocharger leak or manifold rupture where MAP deviates by 25 inHg), the residual engine **preserves the true algebraic difference** ($r_{\text{raw}} = 25.0\text{ inHg}$) and normalized scale rather than artificially truncating the deviation. This ensures downstream anomaly detectors receive true signals without saturation.

---

## 4. Empirical Sigma ($\sigma$) Derivation & Reproducibility

Normalized residuals are defined as:
$$\bar{r} = \frac{y_{\text{obs}} - y_{\text{exp}}}{\sigma_y}$$

### Derivation Methodology
1. **Dataset Source**: Phase 2 verified steady-state cruise baseline flight recording (2,600 telemetry frames).
2. **Calculation**: The sample standard deviation of each sensor channel was calculated during constant-speed, constant-altitude cruise:
   $$\sigma = \sqrt{\frac{1}{N - 1} \sum_{i=1}^N (y_i - \bar{y})^2}$$
3. **Reproducible Baseline File**: Stored in JSON format at [`backend/app/infrastructure/physics/calibration_default.json`](file:///d:/sih/backend/app/infrastructure/physics/calibration_default.json).
4. **Division Guard**: If $\sigma_y \le 10^{-6}$ or non-finite, $\bar{r} = 0.0$ is returned to prevent numerical singularity.

### Diagnostic Feature Interpretation (Phase 5 vs Phase 6)
In Phase 5, normalized residuals are **engineering diagnostic features**, NOT ML anomaly classifications:
- $\bar{r} \in [-1.5, +1.5]\sigma$: Expected nominal sensor noise.
- $|\bar{r}| > 2.0\sigma$: Moderate physical divergence.
- $|\bar{r}| > 3.0\sigma$: Substantial physical discrepancy under investigation.
- ML thresholding, isolation forests, and fault classifiers belong strictly to Phase 6.
