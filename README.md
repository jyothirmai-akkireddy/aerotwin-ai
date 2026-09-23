# AeroTwin AI — MALE UAV Engine Digital Twin Platform
**SIH26054 | Generic 4-Cylinder Boxer Turbocharged Aero-Piston Engine**

[![Architecture](https://img.shields.io/badge/Architecture-Clean%20Hexagonal-blue.svg)](docs/ARCHITECTURE.md)
[![Status](https://img.shields.io/badge/Status-Phase%2010%20Release%20Ready-emerald.svg)](docs/PHASE_10_REPORT.md)
[![Python](https://img.shields.io/badge/Python-3.10.11-brightgreen.svg)](#)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.4-blue.svg)](#)
[![Tests](https://img.shields.io/badge/Tests-243%20Backend%20%7C%2074%20Frontend%20PASS-success.svg)](#)

> [!IMPORTANT]
> **PROTOTYPE RESEARCH DISCLAIMER**  
> AeroTwin AI is an engineering research prototype developed for SIH26054 based on a generic 4-cylinder horizontally-opposed turbocharged aero-piston engine (Rotax 914/915 iS class). All scenarios, flight logs, fault injections, degradation rates, and mission profiles represent synthetic benchmark models. Not certified by FAA, EASA, DGCA, or any airworthiness authority for physical flight operations or maintenance sign-offs.

---

## 1. System Overview

AeroTwin AI is a real-time Digital Twin and Ground Station Cockpit designed for Medium-Altitude Long-Endurance (MALE) UAV aero-piston engines. The platform bridges physical principles and machine learning:

```
Telemetry (10 Hz Ingestion)
          ↓
3D Digital Twin (Kinematics & Thermal Vertex Shaders)
          ↓
Physics Residuals (Observed vs. Expected Across 5 Subsystems)
          ↓
AI Anomaly Scoring (Multivariate Isolation Forest, τ = 0.5402)
          ↓
Fault Classification (XGBoost + Softmax + TreeSHAP Attribution)
          ↓
Degradation & Health Index (4-Tier Multi-Subsystem Penalty Scoring)
          ↓
Remaining Useful Life (Causal Linear OLS with 95% Prediction Interval)
          ↓
Mission Simulation & Replay (5 Reference Profiles, Scrubber Deck, Unpaced Batch)
          ↓
Executive Ground Station Cockpit & Telemetry Gauges
```

---

## 2. Key Capabilities by Phase

- **Phase 0–1 (Foundation):** Clean Hexagonal Architecture, 100% pure domain models verified by AST boundary tests, RFC 8259 JSON contracts.
- **Phase 2–4 (Telemetry & Transport):** 10 Hz telemetry streaming, non-blocking async WebSocket broadcaster, sub-5ms serialization latency, bounded client backpressure queues.
- **Phase 3 (3D Digital Twin):** Three.js / React Three Fiber interactive 3D boxer engine with dynamic RPM kinematics, CHT heat gradient vertex shaders, exploded cutaway view, and camera presets.
- **Phase 5 (Physics Twin):** 5-subsystem analytical model (Thermal, Induction, Fuel Hydraulics at 0.72 kg/L, Lubrication, Vibration) outputting normalized residual deviations.
- **Phase 6 (AI Diagnostics):** Isolation Forest anomaly scoring ($\tau = 0.5402$), XGBoost multi-class fault classification (Normal, Misfire, Injector Clog, Lubrication Loss), and TreeSHAP explainability.
- **Phase 7 (Prognostics & RUL):** Multi-tier degradation scoring ($HI \in [0, 1]$), causal OLS trend slopes, RUL estimation with empirical 95% prediction intervals, and strict `"RUL UNAVAILABLE"` gating on nominal engines.
- **Phase 8 (Mission Sim & Replay):** 5 benchmark UAV missions (`SURVEILLANCE_MISSION`, `RAPID_CLIMB_HOT_DAY`, `THROTTLE_DYNAMICS_BENCHMARK`, `HIGH_ALTITUDE_FERRY`, `EMERGENCY_DESCENT`), multi-format Parquet/SQLite/CSV replay, and strict playback speeds (`1.0x` realtime; `0.5x, 1x, 2x, 5x, 10x` accelerated; unpaced `OFFLINE_BATCH`).
- **Phase 9 (Integration & QA):** Continuous 5-minute soak verification ($> 3,000$ frames, bounded memory, zero frame drops), security auditing (path traversal defenses, input sanitization), and multi-client scalability (1–50 clients).
- **Phase 10 (Demo Hardening & Release):** 6-level dashboard hierarchy, Executive Ground Station Cockpit, deep-dive AI Diagnostics view, safe 6-step lifecycle demo reset, and comprehensive documentation suite.

---

## 3. Quick Start (Single-Command Demo)

To launch the full AeroTwin AI platform on Windows:

```powershell
.\scripts\start_demo.ps1
```

Access Points:
- **Cockpit UI:** [http://localhost:5173](http://localhost:5173)
- **Backend API:** [http://localhost:8000](http://localhost:8000)
- **Interactive REST Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Subsystem Readiness:** [http://localhost:8000/api/v1/ready](http://localhost:8000/api/v1/ready)

---

## 4. Manual Startup

### Backend:
```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### Frontend:
```powershell
cd frontend
npm install
npm run dev
```

---

## 5. Verification & Testing

```powershell
# Backend tests (243 passed)
cd backend
.\.venv\Scripts\pytest -v

# Static analysis & formatting
.\.venv\Scripts\ruff check .
.\.venv\Scripts\ruff format --check .

# Frontend tests (74 passed)
cd ../frontend
npm test -- --run

# Frontend lint & build
npm run lint
npm run build
```

---

## 6. Documentation Directory

- [Judge Presentation & Demo Guide](docs/DEMO_GUIDE.md) — 10-step judge walkthrough script and recovery protocols.
- [Setup & Installation Guide](docs/SETUP_GUIDE.md) — Clean-room prerequisites, environment variables, and startup.
- [Troubleshooting & Recovery](docs/TROUBLESHOOTING.md) — Operational diagnostics, port conflicts, and emergency recovery.
- [Final System Overview](docs/FINAL_SYSTEM_OVERVIEW.md) — End-to-end analytical pipeline and engineering vs synthetic boundaries.
- [Phase 10 Sign-Off Report](docs/PHASE_10_REPORT.md) — Comprehensive 17-section release report.
- [Integration Testing Protocol](docs/INTEGRATION_TESTING.md) — End-to-end integration and source switching stress test results.
- [Security Review](docs/SECURITY_REVIEW.md) — Static AST audit, path traversal defenses, and secrets hygiene.
- [Performance Benchmark](docs/PERFORMANCE_BENCHMARK.md) — Disaggregated latencies and multi-client scalability.
- [Reliability & Soak Testing](docs/RELIABILITY_TESTING.md) — 5-minute continuous soak telemetry and memory stability.
- [System Architecture](docs/ARCHITECTURE.md) — Clean Hexagonal architecture and component specifications.

---

## 7. Version Control & Git Constitution

In strict accordance with project governance, all modifications remain uncommitted in the working tree (`0 git commits`). Inspection via `git status` verifies complete adherence.
