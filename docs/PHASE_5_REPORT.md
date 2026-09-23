# AeroTwin AI — Phase 5 Completion Report: Physics-Informed Digital Twin & Residual Engine

**Project**: SIH26054 — AeroTwin AI  
**Phase**: Phase 5 — Physics-Informed Digital Twin (PIDT) & Residual Engine  
**Status**: COMPLETED & VERIFIED  
**Date**: September 23, 2026  
**Lead Architect & Reviewer**: Lead Software Architect / Senior Systems Engineer  

---

## 1. Executive Summary

Phase 5 of AeroTwin AI has successfully delivered a first-principles **Physics-Informed Digital Twin (PIDT)** and real-time **Residual Engine** for the generic turbocharged aero-piston engine baseline (Rotax 914/915 iS class). 

The PIDT estimates nominal expected engine states in real time, generates directional raw physical residuals and empirical $\sigma$-normalized diagnostic features, assesses model validity without silent value clamping, and streams these analytical insights to both the frontend 3D Digital Twin HUD and REST consumers.

All Phase 5 requirements have been implemented and verified in strict accordance with the approved implementation plan. **Zero Phase 6 (ML anomaly detection, XGBoost), Phase 7 (RUL/SHAP), or Phase 8 (mission replay) capabilities were implemented.**

---

## 2. Implemented Subsystems & Components

### 2.1 Physics Domain Sub-Models (`backend/app/domain/physics/`)
- [`induction.py`](file:///d:/sih/backend/app/domain/physics/induction.py): Induction pressure model combining ICAO Standard Atmosphere (ISA) barometric tropospheric lapse, throttled intake manifold absolute pressure, non-linear turbocharger boost schedule, and speed-density air mass induction ($V_d = 1352\text{ cc}$).
- [`fuel.py`](file:///d:/sih/backend/app/domain/physics/fuel.py): Speed-density fuel delivery model accounting for stoichiometric cruise ($\text{AFR} = 14.7$), full-throttle knock power enrichment ($\text{AFR} \to 12.6$), and rich idle sustaining flow.
- [`thermal.py`](file:///d:/sih/backend/app/domain/physics/thermal.py): 4-cylinder discrete lumped-parameter heat balance model with discrete exponential recurrence ($T_{t+\Delta t} = T_{\text{ss}} + (T_t - T_{\text{ss}})e^{-\Delta t / \tau}$), ram air convective cooling ($V_{\text{tas}}$), coolant jacket dynamics, and cylinder geometric thermal biases.
- [`exhaust.py`](file:///d:/sih/backend/app/domain/physics/exhaust.py): Exhaust enthalpy release model with spark timing advance/retard offset and thermocouple lag ($\tau = 1.2\text{ s}$).
- [`lubrication.py`](file:///d:/sih/backend/app/domain/physics/lubrication.py): Positive-displacement oil pump curve with oil temperature-dependent viscosity bearing clearance leakage and sump thermal inertia ($\tau = 35.0\text{ s}$).
- [`vibration.py`](file:///d:/sih/backend/app/domain/physics/vibration.py): Rotational harmonic baseline vibration model with $\omega^2$ mechanical unbalance and MAP cylinder pressure pulse loading.
- [`residual_engine.py`](file:///d:/sih/backend/app/domain/physics/residual_engine.py): Residual generation engine computing directional raw residuals ($y_{\text{obs}} - y_{\text{exp}}$), empirical $\sigma$-normalized residuals ($\bar{r} = \Delta y / \sigma$), 4-cylinder CHT/EGT spread imbalance, and mean absolute normalized residual.

### 2.2 Numerical Safety & Non-Silent Clamping
- **Directional Invariant Guarantee**:
  - $y_{\text{obs}} = y_{\text{exp}} \implies r = 0.0$
  - $y_{\text{obs}} > y_{\text{exp}} \implies r > 0.0$
  - $y_{\text{obs}} < y_{\text{exp}} \implies r < 0.0$
- **Zero Sigma Division Guard**: Guaranteed no divide-by-zero errors when $\sigma \le 10^{-6}$ or non-finite.
- **Validity Propagation**: Explicit `ModelValidity` enum (`VALID`, `DEGRADED`, `OUT_OF_RANGE`, `INVALID`) and confidence scores. No silent clamping or truncation of large physical discrepancies.

### 2.3 Calibration Repository (`backend/app/infrastructure/physics/`)
- [`calibration_default.json`](file:///d:/sih/backend/app/infrastructure/physics/calibration_default.json): Empirical baseline $\sigma$ scales and thermal time constants derived from Phase 2 steady-state flight recording.
- [`calibration_repository.py`](file:///d:/sih/backend/app/infrastructure/physics/calibration_repository.py): In-memory and file persistence repository with atomic reload support.

### 2.4 REST API & Realtime WebSocket Transport
- [`backend/app/api/routes/physics.py`](file:///d:/sih/backend/app/api/routes/physics.py):
  - `GET /api/v1/physics/status` (operational diagnostics and average latency)
  - `GET /api/v1/physics/current` (latest expected state and residuals)
  - `GET /api/v1/physics/residuals` (latest residual set)
  - `GET /api/v1/physics/calibration` (active engine calibration constants)
  - `POST /api/v1/physics/calibration` (runtime calibration parameter updates)
  - `POST /api/v1/physics/evaluate` (on-demand evaluation of arbitrary telemetry frames)
- [`backend/app/application/services/realtime_service.py`](file:///d:/sih/backend/app/application/services/realtime_service.py): Evaluates physics model per frame and attaches `physics` payload to `TelemetryMessage`.

### 2.5 Frontend Visualization & Diagnostic HUD
- [`frontend/src/features/twin/components/TwinPhysicsCard.tsx`](file:///d:/sih/frontend/src/features/twin/components/TwinPhysicsCard.tsx):
  - Expected vs Observed live comparison table across MAP, Fuel Flow, CHT, EGT, Coolant, Oil Pressure, Oil Temp, Vibration.
  - Graphical horizontal deviation bars showing standardized score relative to $\pm 1.5\sigma$ and $\pm 3.0\sigma$ bounds.
  - 4-cylinder thermal balance breakdown and maximum cylinder spread metrics.
  - Model validity badge and confidence score.
  - Prototype approximation notice.
- [`frontend/src/features/twin/DigitalTwin3DView.tsx`](file:///d:/sih/frontend/src/features/twin/DigitalTwin3DView.tsx): Embedded `TwinPhysicsCard` into 3D view.
- [`frontend/src/stores/useTwinStore.ts`](file:///d:/sih/frontend/src/stores/useTwinStore.ts): State management for `physicsResult` and seamless WebSocket ingestion.

---

## 3. Empirical Performance Benchmark Verification

A dedicated latency benchmark test ([`tests/benchmark/test_physics_latency.py`](file:///d:/sih/backend/tests/benchmark/test_physics_latency.py)) evaluated 980 consecutive flight frames:

```
[PHYSICS BENCHMARK] Evaluated 980 frames:
  - Target:       < 1.000 ms
  - Measured Avg: 0.0375 ms
  - Measured P95: 0.0600 ms
  - Measured Max: 0.2328 ms
```

The measured execution latency of **0.0375 ms** (~38 microseconds per frame) surpasses the $< 1.0\text{ ms}$ performance target with $>25\times$ margin, confirming that real-time evaluation consumes less than 0.04% of the 100 ms (10 Hz) telemetry interval.

---

## 4. Test Verification Summary

### Backend Test Suite
- Total Tests: **124 passing** (0 failures, 0 errors, 1 benign deprecation warning)
- Unit Tests: All sub-models, numerical safety, directional invariants, division guards.
- Integration Tests: All `/api/v1/physics/*` endpoints and health readiness.
- Benchmarks: Physics latency benchmark, simulator benchmark, real-time fan-out throughput.
- Code Quality: `ruff check` (0 errors), `ruff format` (100% compliant).

### Frontend Test Suite
- Total Tests: **59 passing** (12 test suites, 0 failures)
- Store Tests: Ingestion of physics payloads, reset actions, state updates.
- TypeScript: `tsc -b` passed with 0 errors.
- ESLint: `eslint` passed with 0 warnings, 0 errors.
- Production Build: `vite build` completed cleanly in 4.75s.

---

## 5. Phase 5 Completion Acceptance Checklist

- [x] First-principles low-order analytical physics models implemented for induction, fuel, 4-cylinder lumped heat balance, exhaust enthalpy, positive-displacement lubrication, and vibration.
- [x] Expected-state estimation generates physical states for all primary telemetry channels.
- [x] Residual engine generates raw residuals and empirical $\sigma$-normalized features.
- [x] Directionality invariants guaranteed ($y_{\text{obs}} == y_{\text{exp}} \implies r == 0$, $y_{\text{obs}} > y_{\text{exp}} \implies r > 0$).
- [x] Numerical safety verified (zero sigma guard, NaN/Inf handling, non-silent clamping, `ModelValidity`).
- [x] Empirical $\sigma$ source documented and reproducible from flight data.
- [x] REST API endpoints `/api/v1/physics/*` active and documented.
- [x] Real-time WebSocket transport attaches physics payload without blocking.
- [x] Frontend `TwinPhysicsCard.tsx` renders Expected vs Observed comparisons, deviation bars, and thermal balance.
- [x] Zero new external dependencies installed.
- [x] Measured latency benchmarks verified ($0.0375\text{ ms} < 1.000\text{ ms}$).
- [x] Comprehensive documentation authored (`PHYSICS_TWIN.md`, `PHYSICS_MODELS.md`, `PHYSICS_ASSUMPTIONS.md`, `PHASE_5_REPORT.md`).
- [x] Clean architectural boundaries preserved; Phase 6 features NOT touched.
