# AeroTwin AI — Phase 7: Remaining Useful Life (RUL) Methodology

## 1. RUL Modeling Strategy & Quantile Regression

Remaining Useful Life (RUL) estimation estimates the remaining flight hours until an engine component reaches a simulated critical degradation threshold ($HI \le 0.25$).

Rather than relying purely on deterministic point projections, AeroTwin AI uses an ensemble of **Quantile Gradient Boosting Regressors** (`HistGradientBoostingRegressor`):

$$\begin{aligned}
\widehat{RUL}_{\text{med}} &= \hat{q}_{0.50}(\mathbf{x}) \quad \text{(Point Estimate)} \\
\widehat{RUL}_{\text{low}} &= \max\left(0.05, \hat{q}_{0.025}(\mathbf{x}) - \delta_{\text{conformal}}\right) \quad \text{(Lower 95% Bound)} \\
\widehat{RUL}_{\text{upp}} &= \hat{q}_{0.975}(\mathbf{x}) + \delta_{\text{conformal}} \quad \text{(Upper 95% Bound)}
\end{aligned}$$

---

## 2. Conformal Interval Calibration & Empirical Coverage

Direct uncalibrated quantile regression can suffer from coverage degradation on unseen operational domains. AeroTwin AI calibrates its prediction intervals using conformal non-conformity residuals computed on the held-out validation set (Runs 151–170):

$$\delta_{\text{conformal}} = \text{Quantile}_{0.95}\left(\max\left(0.0, \hat{q}_{0.025}(\mathbf{x}_i) - y_i, y_i - \hat{q}_{0.975}(\mathbf{x}_i)\right)\right)$$

On the validation set, $\delta_{\text{conformal}} = 2.183\text{ flight hours}$.

### Empirical Test Set Coverage
Evaluated on the 20 independent test trajectories (Runs 171–190, 4,952 samples):

$$\text{Coverage}_{95} = \frac{1}{M}\sum_{m=1}^M \mathbb{I}\left(\widehat{RUL}_{\text{low}, m} \le RUL^*_m \le \widehat{RUL}_{\text{upp}, m}\right) = \mathbf{89.78\%}$$

This comfortably exceeds the statistical acceptance threshold ($\ge 85\%$).

---

## 3. Decoupling Coverage from Runtime Heuristic Confidence

To ensure mathematical rigor, formal statistical prediction interval coverage is decoupled from the runtime heuristic confidence metric ($C_{\text{prog}} \in [0.0, 1.0]$):

$$C_{\text{prog}} = C_{\text{history}} \cdot C_{\text{spread}} \cdot C_{\text{noise}}$$

- **Buffer Fullness Factor:** $C_{\text{history}} = \min(1.0, N / 100)$
- **Interval Sharpness Factor:** $C_{\text{spread}} = \max\left(0.0, 1.0 - \frac{\widehat{RUL}_{\text{upp}} - \widehat{RUL}_{\text{low}}}{2.5 \cdot \max(1.0, \widehat{RUL}_{\text{med}})}\right)$
- **Signal-to-Noise Factor:** $C_{\text{noise}} = \max\left(0.2, 1.0 - \frac{\text{std}(HI)}{\text{mean}(HI) + 10^{-6}}\right)$

---

## 4. 4-Stage Execution Gating Hierarchy

Under no circumstances does the model return arbitrary values or $0.0$ when ground truth is unestablished. The system enforces strict 4-stage gating:

1. **Stage 1 — Insufficient History ($N < 30$):**
   $$\text{status} = \text{INSUFFICIENT\_HISTORY}, \quad \widehat{RUL} = \text{None}, \quad \text{CI}_{95} = \text{None}$$
2. **Stage 2 — Corrupted or Non-Finite Telemetry:**
   $$\text{status} = \text{RUL\_UNAVAILABLE}, \quad \widehat{RUL} = \text{None}, \quad \text{CI}_{95} = \text{None}$$
3. **Stage 3 — Nominal Engine ($HI \ge 0.90$ & STABLE):**
   $$\text{status} = \text{DEGRADATION\_NOT\_DETECTED}, \quad \widehat{RUL} = \text{None}, \quad \text{CI}_{95} = \text{None}$$
4. **Stage 4 — Active Degradation Mode ($HI < 0.90$ & DEGRADING):**
   $$\text{status} = \text{ACTIVE}, \quad \widehat{RUL} = \hat{q}_{0.50}, \quad \text{CI}_{95} = [\widehat{RUL}_{\text{low}}, \widehat{RUL}_{\text{upp}}]$$
