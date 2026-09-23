# AeroTwin AI — Final System Overview & Architecture Pipeline
**SIH26054 — Complete Digital Twin Technical Reference**

> [!IMPORTANT]
> **PROTOTYPE RESEARCH DISCLAIMER**  
> AeroTwin AI is an engineering research prototype developed for SIH26054 based on a generic 4-cylinder horizontally-opposed turbocharged aero-piston engine (Rotax 914/915 iS class). All scenarios, flight logs, fault injections, degradation rates, and mission profiles represent synthetic benchmark models. Not certified for flight operations.

---

## 1. End-to-End System Pipeline

The core strength of AeroTwin AI is its cohesive, multi-layered analytical pipeline. Rather than treating artificial intelligence as a disconnected black box, every stage builds deterministically upon physical foundations:

```
+-----------------------------------------------------------------------------------+
| 1. TELEMETRY INGESTION & NUMERICAL SAFETY GATE                                    |
| - 10 Hz ingestion, RFC 8259 JSON validation, monotonic sequence tracking        |
| - Rejection of NaN / Infinity / corrupt channels                                 |
+-----------------------------------------------------------------------------------+
                                         │
                                         ▼
+-----------------------------------------------------------------------------------+
| 2. 3D DIGITAL TWIN KINEMATIC & THERMAL SYNCHRONIZATION                            |
| - Opposed 4-cylinder kinematics (Crankshaft, Connecting Rods, Pistons)           |
| - Real-time RPM scaling, CHT vertex shader gradient mapping, exploded views      |
+-----------------------------------------------------------------------------------+
                                         │
                                         ▼
+-----------------------------------------------------------------------------------+
| 3. PHYSICS-INFORMED EXPECTED BEHAVIOR MODEL                                      |
| - 5 Analytical Subsystems: Thermal, Induction, Fuel, Lubrication, Vibration      |
| - Synthesis of Expected Values from current operating state                      |
| - Residual Vector Extraction: Δ = Observed - Expected                            |
+-----------------------------------------------------------------------------------+
                                         │
                                         ▼
+-----------------------------------------------------------------------------------+
| 4. AI ANOMALY DETECTION (Phase 6)                                                |
| - Unsupervised Multivariate Isolation Forest on residual vectors                 |
| - Anomaly Severity Score S ∈ [0.0, 1.0] with calibrated threshold τ = 0.5402       |
+-----------------------------------------------------------------------------------+
                                         │
                                         ▼
+-----------------------------------------------------------------------------------+
| 5. SUPERVISED FAULT CLASSIFICATION (Phase 6)                                     |
| - Gradient-boosted decision trees (XGBoost)                                      |
| - Classes: Normal, Misfire, Injector Clog, Lubrication Loss                      |
| - Softmax class probabilities and TreeSHAP causal feature attributions           |
+-----------------------------------------------------------------------------------+
                                         │
                                         ▼
+-----------------------------------------------------------------------------------+
| 6. PROGNOSTICS & MULTI-TIER DEGRADATION SCORING (Phase 7)                        |
| - 4 Degradation Tiers: Lubrication, Thermal, Vibration, Induction                |
| - Bounded Sigmoidal/Exponential Penalties                                        |
| - Composite Health Index: HI = 1.0 - Σ w_i * P_i ∈ [0.0, 1.0]                    |
+-----------------------------------------------------------------------------------+
                                         │
                                         ▼
+-----------------------------------------------------------------------------------+
| 7. REMAINING USEFUL LIFE (RUL) ESTIMATION (Phase 7)                              |
| - Causal sliding window FIFO buffer (30–300 frames)                              |
| - OLS Linear Trend Slope: dH/dt                                                  |
| - Extrapolation to Critical Degradation Threshold (HI = 0.70)                    |
| - 95% Empirical Prediction Interval: [RUL_low, RUL_high]                         |
| - Strict Invariant: "RUL UNAVAILABLE" on healthy engine (zero fabricated numbers)|
+-----------------------------------------------------------------------------------+
                                         │
                                         ▼
+-----------------------------------------------------------------------------------+
| 8. MISSION SIMULATION & MULTI-FORMAT FLIGHT REPLAY (Phase 8)                     |
| - 5 Deterministic Reference Missions with S(τ) = 3τ² - 2τ³ cubic transitions      |
| - Parquet / SQLite / CSV multi-format ingestion                                  |
| - Strict Speed Contract: 1.0x Realtime; 0.5x, 1x, 2x, 5x, 10x; unpaced Offline   |
| - Verified Data-Time Invariance across all downstream models                     |
+-----------------------------------------------------------------------------------+
                                         │
                                         ▼
+-----------------------------------------------------------------------------------+
| 9. OPERATOR GROUND STATION COCKPIT (Phase 10)                                    |
| - 6-Level Information Hierarchy                                                  |
| - Executive Health Summary, Real-Time 10 Hz Gauges, Subsystem Readiness Matrix   |
| - Safe Demo Reset & Instantaneous LIVE ↔ REPLAY Source Switching                 |
+-----------------------------------------------------------------------------------+
```

---

## 2. Engineering Classification: What is What

To maintain absolute scientific and technical honesty, the components of AeroTwin AI are categorized into their true functional boundaries:

### 2.1 What is Deterministic
- **Sequence Validation:** Frame sequence counter checking ($s_k = s_{k-1} + 1$), gap detection, and duplicate suppression.
- **Kinematic Assembly:** Mathematical relationship between crankshaft rotation angle $\theta$, connecting rod displacement, and piston stroke position.
- **Mission Profiles:** Mathematical phase scheduling ($S(\tau) = 3\tau^2 - 2\tau^3$ cubic ramps) and Riemann fuel consumption integration.
- **Playback Cursor:** Step calculations, scrubber timeline positions, and EOF detection.

### 2.2 What is Physics-Based
- **Thermal Heat Balance:** Cylinder Head Temperature (CHT) and Exhaust Gas Temperature (EGT) heat generation models as functions of engine load, ambient temperature, and airflow.
- **Induction & Boost:** Turbocharger manifold pressure ratio calculations based on throttle angle and RPM.
- **Fuel Hydraulics:** Fuel mass flow rate calculations using the prototype fuel density $\rho = 0.72\text{ kg/L}$.
- **Lubrication Hydraulics:** Oil pressure response curves across oil temperature viscosity shifts and engine speed.

### 2.3 What is Machine Learning-Based
- **Multivariate Isolation Forest:** Outlier scoring on the multi-dimensional physics residual vector.
- **XGBoost Fault Classifier:** Supervised multi-class gradient boosting model mapping residual signatures to fault categories.
- **TreeSHAP Explainability:** Game-theoretic Shapley value estimation attributing which sensor residuals drove the classification decision.

### 2.4 What is Synthetic / Prototype Benchmark
- **Engine Telemetry Source:** The real-time physics simulator generating calibrated Rotax 914/915 iS class telemetry frames.
- **Fault Injections:** Algorithmic bias and noise injections simulating sensor failure and mechanical drift.
- **Run-to-Failure Degradation Datasets:** Synthetic wear trajectories used to benchmark degradation and RUL models.
- **Model Evaluation Scores:** *"97.64% accuracy on the held-out synthetic benchmark test set"* and *"MAE 6.413 h on the synthetic run-to-failure benchmark"*.

### 2.5 Future Real-World Hardware Integration (Roadmap)
- **CAN Bus / ARINC 429 Ingestion:** Direct interface to real UAV engine control units (ECUs) and flight avionics busses.
- **OEM Engine Test Stand Calibration:** Dynamometer calibration curves for physical Rotax 914/915 iS or Lycoming/Continental aero-engines.
- **Edge Deployment:** Packaging into an DO-178C / DO-254 certifiable on-board embedded flight monitoring unit.

---

## 3. Clean Architecture Purity

AeroTwin AI is strictly structured under Clean Hexagonal Architecture:
- **Domain Layer (`backend/app/domain/`):** Pure Python entities and algorithms with zero imports from FastAPI, databases, WebSockets, or OS I/O. Verified 100% pure by AST boundary tests.
- **Application Layer (`backend/app/application/`):** Orchestrates telemetry flow, service resets, and source mode switching via Dependency Inversion.
- **Infrastructure Layer (`backend/app/infrastructure/`):** Concrete adapters for file loaders (Parquet, SQLite, CSV), broadcast channels, and repositories.
- **API / Interface Layer (`backend/app/api/`):** REST routers and RFC 8259 compliant WebSocket endpoints with Request-ID correlation and sanitized error DTOs.
