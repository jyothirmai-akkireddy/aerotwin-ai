# AeroTwin AI — Architectural Decision Records (ADRs)

This document records the foundational architectural decisions established during Phase 0 for the AeroTwin AI platform (SIH26054).

---

## ADR-001: Modular Monolith vs. Microservices Architecture
- **Status**: ACCEPTED
- **Context**: AeroTwin AI requires high-frequency (10–50 Hz) telemetry ingestion, real-time physics residual calculation, ML inference, and WebSocket broadcasting to an interactive 3D ground station HMI.
- **Decision**: Adopt a **Modular Monolith** organized under Clean / Hexagonal Architecture (Ports and Adapters) rather than a distributed microservices architecture.
- **Consequences**:
  - *Pros*: Eliminates inter-service network hops between telemetry ingestion, physics twin, and ML diagnostics (targeting sub-millisecond pipeline latency once implemented); straightforward in-memory IPC; trivial local debugging; single cohesive test suite; simplified deployment without Kubernetes or Kafka overhead.
  - *Cons*: Must strictly enforce domain boundaries through package structure and linting to prevent accidental coupling.
  - *Future Evolution*: Core modules (e.g., Diagnostics or Simulation) can be extracted into standalone network services if multi-tenant fleet scaling demands it.

---

## ADR-002: Persistence Strategy — SQLite & Parquet Initially
- **Status**: ACCEPTED
- **Context**: High-frequency telemetry generates dense numerical time-series (10 samples/sec = 36,000 frames/hour). Relational metadata (missions, alerts, configuration, engine serials) requires structured queries.
- **Decision**: Use **SQLite** for relational configuration, mission state, and discrete fault events; use **Apache Parquet** for dense time-series telemetry dumps.
- **Consequences**:
  - *Pros*: Zero external database server administration; serverless and embedded; Parquet provides 10x columnar compression and instant NumPy/Pandas query speed; easily runs offline on ground station laptops.
  - *Cons*: SQLite concurrency is limited for high-write loads, mitigated by separating dense telemetry to append-only Parquet logs.
  - *Future Evolution*: The `ITelemetryRepository` port allows swapping SQLite with TimescaleDB / PostgreSQL without changing any domain logic.

---

## ADR-003: Telemetry Source — Simulated Telemetry Baseline
- **Status**: ACCEPTED
- **Context**: Real aerospace UAV telemetry is subject to defence ITAR/EAR restrictions, physical ground testing schedules, and hardware accessibility limitations.
- **Decision**: Establish a physics-guided synthetic telemetry generator and flight profile simulator as the primary data provider for development and demonstration, clearly labeled as `SYNTHETIC_SIMULATED_PROTOTYPE`.
- **Consequences**:
  - *Pros*: Unconstrained development velocity; reproducible edge-case fault scenarios (runaway CHT, injector clogging, oil starvation) without destroying real aerospace hardware.
  - *Cons*: Cannot claim aerospace certification or flight-qualified accuracy without physical engine dynamometer validation data.
  - *Mitigation*: Architecture defines `ITelemetryProvider` interface; CAN bus / FADEC adapters can be plugged in seamlessly when real engine data is available.

---

## ADR-004: Frontend Stack Selection (React 18 + Vite + TS + Tailwind + Zustand + R3F)
- **Status**: ACCEPTED
- **Context**: Ground station operators need a tactical, low-latency HMI with real-time gauges, time-series telemetry plots, and an interactive 3D kinematic engine twin displaying thermal gradients.
- **Decision**: Select React 18, TypeScript, Vite, Tailwind CSS, Zustand, Recharts, Three.js, and React Three Fiber (R3F).
- **Consequences**:
  - *Pros*: Vite provides instant HMR; Zustand offers atomic, zero-boilerplate high-frequency state updates without full React re-renders; R3F enables declarative WebGL rendering with GPU shaders; Recharts renders responsive time-series charts.
  - *Cons*: WebGL performance requires careful mesh budget and GPU shader memory management.

---

## ADR-005: Machine Learning & Explainability Stack (Isolation Forest + XGBoost + SHAP)
- **Status**: ACCEPTED
- **Context**: The system requires early anomaly detection for novel sensor deviations, supervised classification for known fault signatures (misfire, overheating, lubrication loss), and operator explainability.
- **Decision**: Use **Scikit-learn Isolation Forest** for unsupervised anomaly detection on residual vectors, **XGBoost** for multi-class fault classification, and **TreeSHAP** for feature importance attribution. Defer PyTorch until sequential deep learning is strictly justified.
- **Consequences**:
  - *Pros*: Low latency target (<5 ms inference time); proven tabular performance; exact and mathematically rigorous Shapley explanations; lightweight memory footprint.
  - *Cons*: SHAP computation on every 10 Hz frame is expensive; SHAP will be scheduled asynchronously or on anomaly triggers rather than on every tick.

---

## ADR-006: Physics-Informed Residual Analysis as Core Digital Twin Paradigm
- **Status**: ACCEPTED
- **Context**: Raw sensor data alone cannot distinguish between normal high-load states (e.g., high CHT during full-throttle takeoff climb) and abnormal failure states (e.g., cooling duct blockage during gentle cruise).
- **Decision**: Anchor the Digital Twin on **Physics-Informed Residuals** ($\vec{r} = \vec{y}_{\text{actual}} - \hat{y}_{\text{expected}}$), where expected state is computed by a 0D/1D thermodynamic-mechanical model of the engine.
- **Consequences**:
  - *Pros*: Drastically reduces false alarms; normalizes operating context (altitude, throttle, airspeed, OAT); ML models train on deviations from physical laws rather than raw sensor distributions.
  - *Cons*: Physics model requires realistic aerodynamic and thermodynamic equations.

---

## ADR-007: Python Version Baseline (Python 3.10.11)
- **Status**: ACCEPTED
- **Context**: The user environment has Python 3.10.11 pre-installed. Scientific ML libraries (SHAP, XGBoost, SciPy, NumPy) require stable C-extensions and pre-compiled wheels on Windows x64.
- **Decision**: Freeze Python 3.10.11 as the official runtime baseline for AeroTwin AI.
- **Consequences**:
  - *Pros*: Full pre-compiled wheel compatibility for NumPy 1.26, SciPy 1.14, XGBoost 2.1, and SHAP 0.45 without requiring MSVC build tools; matches the host machine exactly.
  - *Cons*: Cannot use Python 3.11/3.12-specific syntax additions (e.g., `ExceptionGroup` standard syntax), which is not a hindrance.

---

## ADR-008: Dependency Management & Virtualization Strategy
- **Status**: ACCEPTED
- **Context**: Global package installations risk package version drift and pollution across multiple projects on the host system.
- **Decision**: Strict project-local virtualization via `backend/.venv` for Python and `frontend/node_modules` for Node.js. Pinned dependency ranges in `requirements.txt` and `package.json`.
- **Consequences**:
  - *Pros*: 100% reproducible builds; zero global side-effects; isolated test execution.
  - *Cons*: Disk space overhead (~800 MB for Python scientific packages and node modules), well within the available 250 GB drive space.

---

## ADR-009: Engine Model Baseline — Generic Aero-Piston Twin Inspired by Rotax 914/915 Class
- **Status**: ACCEPTED
- **Context**: The MALE UAV digital twin requires a concrete aero-propulsion architecture to model manifold pressures, turbocharger dynamics, cylinder thermal balancing, and lubrication.
- **Decision**: Baseline the physics twin on a **generic 4-cylinder horizontally-opposed turbocharged aero-piston engine inspired by the Rotax 914/915 class**.
- **Important Restrictions**:
  - The model shall **NOT** be represented as an exact Rotax 914/915 simulation.
  - All engine, thermodynamic, and mechanical parameters must be documented as **explicit prototype assumptions**.
  - Zero claims of manufacturer-accurate specifications or certified performance are permitted unless independently sourced and verified.
- **Consequences**:
  - *Pros*: Provides realistic boxer-engine multi-cylinder thermal, boost, and lubrication dynamics representative of MALE UAVs without infringing proprietary OEM performance data or making unverified claims.
  - *Cons*: Model represents generalized aero-piston physical principles rather than a certified OEM-specific digital twin.

---

## ADR-010: Telemetry Frequency & Rate-Configurability
- **Status**: ACCEPTED
- **Context**: Real-time health monitoring requires adequate temporal resolution to observe engine transients (e.g., rapid throttle changes, sudden misfires), while remaining adaptable to diverse UAV datalinks and compute environments.
- **Decision**: Establish **10 Hz as the nominal simulation and streaming frequency**, while keeping the entire architecture **rate-configurable** via application settings (`telemetry_sample_rate_hz`, `simulation_dt_sec`).
- **Consequences**:
  - *Pros*: 10 Hz provides 100 ms resolution, optimal for ground-station HMI responsiveness and transient anomaly detection; rate configurability allows seamlessly scaling down to 1 Hz for constrained RF datalinks or scaling up for high-fidelity offline replays.
  - *Cons*: 10 Hz requires careful asynchronous worker separation so heavy tasks (SHAP, persistence) do not lag the streaming pipeline.

