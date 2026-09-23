# AeroTwin AI — Phase 7: Degradation Model & Health Index Formulation

## 1. Mathematical Foundations & 3-Tier Representation

To prevent information loss through premature clipping, all subsystem degradation metrics implement a formal **3-tier representation**:

1. **Tier 1 — Raw Physical Deviation ($r_{\text{raw}}$):** Native dimensional difference between observed telemetry and expected physics state ($\text{bar}$, $^\circ\text{C}$, $\text{g}$, $\text{inHg}$).
2. **Tier 2 — Normalized Deviation ($z = |r_{\text{raw}}| / \sigma$):** Unbounded, dimensionless ratio relative to baseline calibration sigma ($\sigma$). Preserves full diagnostic depth and severity for advanced engineering analysis.
3. **Tier 3 — Bounded Degradation Penalty ($d_k \in [0.0, 1.0]$):** Monotonically clamped into $[0.0, 1.0]$ specifically for computing the composite Health Index:
   $$d_k = \max\left(0.0, \min\left(1.0, \frac{z_k}{3.0}\right)\right)$$

---

## 2. Subsystem Degradation Formulas

### 2.1 Lubrication Subsystem
$$\begin{aligned}
z_{\text{oil\_p}} &= \frac{|y_{\text{oil\_p}} - \hat{y}_{\text{oil\_p}}|}{\sigma_{\text{oil\_p}}}, \quad z_{\text{oil\_t}} = \frac{|y_{\text{oil\_t}} - \hat{y}_{\text{oil\_t}}|}{\sigma_{\text{oil\_t}}} \\
z_{\text{oil}} &= 0.60 \cdot z_{\text{oil\_p}} + 0.40 \cdot z_{\text{oil\_t}} \\
d_{\text{oil}} &= \text{clamp}(z_{\text{oil}} / 3.0, 0.0, 1.0) \\
HI_{\text{oil}} &= (1.0 - d_{\text{oil}}) \times 100\%
\end{aligned}$$

### 2.2 Thermal Balance Subsystem
$$\begin{aligned}
z_{\text{spread}} &= \frac{\max(\text{CHT}) - \min(\text{CHT})}{\sigma_{\text{cht\_spread}}}, \quad z_{\text{mean}} = \frac{|\overline{\text{CHT}} - \hat{y}_{\text{cht}}|}{\sigma_{\text{cht}}} \\
z_{\text{therm}} &= 0.50 \cdot z_{\text{spread}} + 0.50 \cdot z_{\text{mean}} \\
d_{\text{therm}} &= \text{clamp}(z_{\text{therm}} / 3.0, 0.0, 1.0) \\
HI_{\text{therm}} &= (1.0 - d_{\text{therm}}) \times 100\%
\end{aligned}$$

### 2.3 Turbocharger Induction Subsystem
$$\begin{aligned}
z_{\text{turbo}} &= \frac{|y_{\text{map}} - \hat{y}_{\text{map}}|}{\sigma_{\text{map}}} \\
d_{\text{turbo}} &= \text{clamp}(z_{\text{turbo}} / 3.0, 0.0, 1.0) \\
HI_{\text{turbo}} &= (1.0 - d_{\text{turbo}}) \times 100\%
\end{aligned}$$

### 2.4 Mechanical & Rotational Vibration Subsystem
$$\begin{aligned}
z_{\text{vib}} &= \frac{|y_{\text{vib}} - \hat{y}_{\text{vib}}|}{\sigma_{\text{vib}}} \\
d_{\text{vib}} &= \text{clamp}(z_{\text{vib}} / 3.0, 0.0, 1.0) \\
HI_{\text{vib}} &= (1.0 - d_{\text{vib}}) \times 100\%
\end{aligned}$$

---

## 3. Threshold-Gated Anomaly Penalty & Invariant Proof

### 3.1 Problem Definition
In unsupervised anomaly detection, the decision score $s_{\text{anom}}(t)$ hovers at positive baseline values ($\approx 0.30 - 0.45$) even on nominal frames. Directly adding $w_{\text{anom}} \cdot s_{\text{anom}}$ to the degradation penalty violates the fundamental invariant:
$$\text{If } r_k = 0 \; \forall k \implies HI \equiv 1.0$$

### 3.2 Mathematical Formulation
We define the anomaly penalty as a rectified, threshold-gated penalty using the calibrated operational threshold $\tau_{\text{anom}} = 0.5402$:

$$d_{\text{anom}}(t) = \begin{cases} 
0.0, & \text{if } s_{\text{anom}}(t) \le \tau_{\text{anom}} \text{ or } \text{anomaly\_flag} = \text{False} \\
\min\left(1.0, \frac{s_{\text{anom}}(t) - \tau_{\text{anom}}}{1.0 - \tau_{\text{anom}}}\right), & \text{if } s_{\text{anom}}(t) > \tau_{\text{anom}} \text{ and } \text{anomaly\_flag} = \text{True}
\end{cases}$$

### 3.3 Proof of Invariant
When all physics residuals are zero ($r_k \equiv 0$):
1. $z_k = 0 \implies d_k = 0$ for all physical subsystems.
2. By definition of nominal flight, $\text{anomaly\_flag} = \text{False}$ and $s_{\text{anom}} < \tau_{\text{anom}} \implies d_{\text{anom}} = 0.0$.
3. Total penalty:
   $$\sum_{k \in \mathcal{K}} w_k \cdot d_k = 0.25(0) + 0.25(0) + 0.20(0) + 0.15(0) + 0.15(0) = 0.0$$
4. Health Index:
   $$HI = 1.0 - 0.0 \equiv 1.0 \quad \blacksquare$$

---

## 4. Prototype Degradation State Mapping

| Prototype Degradation State | Health Index Interval | Operational Interpretation |
| :--- | :---: | :--- |
| `NOMINAL` | $[0.90, 1.00]$ | Normal engine health; negligible wear accumulation |
| `EARLY_DEGRADATION` | $[0.75, 0.90)$ | Initial thermal/hydraulic deviation; advisory monitoring |
| `MODERATE_DEGRADATION` | $[0.50, 0.75)$ | Noticeable performance or balance drop; maintenance planning |
| `SEVERE_DEGRADATION` | $[0.25, 0.50)$ | Pronounced degradation; mission duration restriction |
| `CRITICAL_SIMULATED_STATE` | $[0.00, 0.25)$ | Near simulated failure; abort/shutdown advisory |
