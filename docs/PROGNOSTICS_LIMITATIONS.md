# AeroTwin AI — Phase 7: Prognostics Limitations & Non-Certified Disclaimers

## 1. Prototype Scope & Regulatory Status

> [!CAUTION]
> **NON-CERTIFIED PROTOTYPE DISCLAIMER**  
> AeroTwin AI is an engineering research prototype developed for educational and demonstration purposes. No models, residual calculations, Health Indices, trend predictions, or Remaining Useful Life (RUL) projections are approved by the FAA, EASA, DGCA, or any civil/military aviation airworthiness authority.
>
> They MUST NOT be used for flight dispatch decisions, in-flight emergency checklists, or real-world aircraft maintenance planning.

---

## 2. Technical Limitations & Operational Boundaries

1. **Synthetic Wear Dynamics:**  
   The underlying wear models are parameterized benchmark generators. They do not simulate micro-structural metallurgy, oil chemical additive depletion, microscopic bearing spalling, or thermal shock micro-cracking present in real operational engines.

2. **Discrete Scenario Assumptions:**  
   Simulated flights follow synthetic scenario profiles (Cruise, Climb, Takeoff, Descent). Sudden unmodeled catastrophic events (e.g., bird strikes, foreign object damage) do not follow gradual wear curves and may produce sudden abrupt changes.

3. **Causal Window Buffering:**  
   Trend slope and RUL projection require at least 30 consecutive frames (3 seconds at 10 Hz) of causal history. During cold start or post-reset, RUL is explicitly `INSUFFICIENT_HISTORY`.

4. **Nominal State Invariance:**  
   When the engine is running nominally ($HI \ge 0.90$), wear rate is negligible and RUL is explicitly gated to `DEGRADATION_NOT_DETECTED`. It will not display artificial 2,000-hour TBO countdowns.
