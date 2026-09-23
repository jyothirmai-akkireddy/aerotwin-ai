# AeroTwin AI — Phase 3 Completion Report: 3D Digital Twin Visualizer

**Project**: SIH26054 — AeroTwin AI  
**Phase**: Phase 3 — 3D Digital Twin  
**Status**: COMPLETED & VERIFIED  
**Date**: September 22, 2026  
**Lead Architect & Reviewer**: Lead Software Architect / Senior Full-Stack Engineer  

---

## 1. Executive Summary

Phase 3 of the AeroTwin AI project has successfully delivered the complete interactive **3D Digital Twin Visualizer** for the aero-piston engine monitoring platform.

The visualizer renders a generic 4-cylinder horizontally-opposed turbocharged aero-piston engine inspired by the Rotax 914/915 class. The engine is rendered in hardware-accelerated WebGL using Three.js and React Three Fiber (`@react-three/fiber`), driven by frame-rate-independent slider-crank kinematics, dynamic CHT thermal shader mapping, multiple operational visualization modes (`NORMAL`, `THERMAL`, `CUTAWAY`, `EXPLODED`), and an engineering HUD.

All Phase 3 goals were achieved in strict compliance with the project constitution, clean architecture boundaries, and roadmap constraints. **No Phase 4 (WebSockets/real-time streaming), Phase 5 (physics twin), Phase 6 (AI anomaly detection), or Phase 7 (RUL/SHAP) features were implemented.**

---

## 2. Phase 0/1/2 Compliance & Continuity

1. **Engine Baseline Compliance**: The model is explicitly designated as a *"Generic 4-cylinder horizontally-opposed turbocharged aero-piston engine inspired by the Rotax 914/915 class"*. All UI headers, documentation, and source code contain explicit prototype disclaimers disclaiming OEM certified CAD equivalence.
2. **Domain Boundary Decoupling**: Kinematic formulas (`kinematics.ts`) and thermal interpolation functions (`thermal.ts`) are pure TypeScript mathematical routines completely isolated from rendering libraries and external networks.
3. **Backend System Integrity**: All 80 Phase 2 backend tests (`pytest`) pass with zero regressions. The Phase 2 simulator REST endpoints remain fully operational and serve as the data source for the Phase 3 development state adapter.
4. **Zero Phase Bleed**: Phase 4 (WebSockets, Socket.IO, SSE), Phase 5 (thermodynamic residuals), Phase 6 (anomaly detection/XGBoost), and Phase 7 (predictive maintenance) have not been touched or prematurely implemented.

---

## 3. 3D Engine Visualization Architecture

The visualization pipeline is structured into clear modular components:

```
frontend/src/features/twin/
├── kinematics.ts              # Pure math: exact slider-crank kinematics & angular integration
├── thermal.ts                 # Pure math: 5-stop CHT thermal color gradient & emissive scaling
├── webgl.ts                   # WebGL capability detection utility
├── DigitalTwin3DView.tsx      # Main layout view containing Canvas, HUD, and Dev Controls
├── components/
│   ├── EngineScene.tsx        # Three.js Canvas container, studio 3-point lighting, ground grid
│   ├── CameraController.tsx   # OrbitControls with smooth spherical lerp preset transitions
│   ├── EngineModel.tsx        # Master assembly coordinating rotating crank, pistons, accessories
│   ├── CrankshaftAssembly.tsx # Crankshaft main journals, 4 offset throws, propeller hub
│   ├── PistonAssembly.tsx     # 4 reciprocating pistons, wrist pins, and pivoting connecting rods
│   ├── CylinderAssembly.tsx   # 4 cylinder sleeves, 6 cooling fins per cylinder, spark plugs
│   ├── TurbochargerAssembly.tsx# Compressor volute scroll, turbine housing, spinning impeller
│   ├── IntakeExhaustAssembly.tsx# Intake plenum, throttle plate, 4 runners, exhaust headers
│   ├── TwinHud.tsx            # Tactical engineering HUD overlay with gauges and cylinder cards
│   ├── TwinControls.tsx       # Mode toggles, camera presets, speed multiplier, exploded slider
│   ├── TwinDevAdapter.tsx     # Step Simulator button (REST), flight scenarios, manual test sliders
│   └── WebGLFallback.tsx      # Accessible tabular fallback for non-WebGL environments
└── __tests__/
    ├── kinematics.test.ts     # 9 unit tests for slider-crank math and angular limits
    ├── thermal.test.ts        # 8 unit tests for color stop interpolation and emissive bounds
    ├── twinStore.test.ts      # 6 unit tests for Zustand store mode and camera transitions
    ├── webgl.test.ts          # 2 unit tests for WebGL detection and canvas mocking
    └── rpm.test.ts            # 8 unit tests for speed multiplier scaling and angular wrap
```

---

## 4. Mathematical & Kinematic Formulations

### 4.1 Exact Slider-Crank Reciprocating Displacement

For each cylinder $i \in \{1, 2, 3, 4\}$, the displacement of the piston wrist pin center $x_i(\theta)$ from the crankshaft axis is calculated using the exact closed-form slider-crank equation:

$$x_i(\theta) = r \cos(\theta_i) + \sqrt{L^2 - r^2 \sin^2(\theta_i)}$$

Where:
- Crank throw radius $r = 0.28\text{ units}$ (derived from physical stroke $61.0\text{ mm}$)
- Connecting rod length $L = 0.85\text{ units}$ (derived from physical rod center-to-center $110.0\text{ mm}$)
- Rod-to-crank ratio $\lambda = \frac{r}{L} \approx 0.329 < 1.0$ (ensuring strictly real roots under the radical)

### 4.2 Connecting Rod Obliquity

The angular deflection $\phi_i(\theta)$ of each connecting rod oscillates as the crank rotates:

$$\phi_i(\theta) = \arcsin\left(\frac{r}{L} \sin(\theta_i)\right)$$

### 4.3 Boxer-4 Phasing & Cylinder Offsets

The horizontal boxer-4 engine has opposed cylinder banks:
- **Bank 1 (Cylinders 1 & 3)**: Displaces in $+X$
- **Bank 2 (Cylinders 2 & 4)**: Displaces in $-X$

With firing order **$1 - 4 - 2 - 3$**, the individual crank pin phase angles are:
$$\theta_1 = \theta, \quad \theta_4 = \theta + \pi, \quad \theta_2 = \theta + \frac{3\pi}{2}, \quad \theta_3 = \theta + \frac{\pi}{2}$$

### 4.4 Frame-Rate Independent Crank Integration

$$\Delta \theta = \left(\text{RPM} \times \frac{2\pi}{60} \times s_{\text{multiplier}}\right) \times \Delta t$$
$$\theta_{k+1} = (\theta_k + \Delta \theta) \pmod{2\pi}$$

Where $\Delta t$ is the frame delta provided by `useFrame((_, delta) => ...)`.

---

## 5. Visualization Modes & Interaction Mechanics

| Mode | Visual Behavior | Primary Engineering Utility |
| :--- | :--- | :--- |
| **`NORMAL`** | Metallic PBR shading (`roughness: 0.25`, `metalness: 0.85`) | Baseline structural and assembly inspection |
| **`THERMAL`** | Dynamic continuous CHT heatmap on barrels and heads | Live detection of hot spots, cylinder imbalance, and overheating |
| **`CUTAWAY`** | Cylinder walls switch to `opacity: 0.35`, revealing internal components | Inspection of piston stroke, wrist pin pivot, and rod angularity |
| **`EXPLODED`** | Components displace radially outward proportional to distance slider | Detailed component hierarchy analysis and subsystem identification |

### Camera Controller & Presets

The viewport utilizes `OrbitControls` augmented with smooth spherical lerp transitions (`t = 0.05` per frame) across 5 standard engineering vantage points:
1. **`ISOMETRIC`**: Overview vantage at $(2.8, 2.2, 2.8)$
2. **`FRONT`**: Propeller hub and bank symmetry at $(0.0, 0.4, 3.8)$
3. **`TOP`**: Manifold and cylinder bore alignment at $(0.0, 4.2, 0.01)$
4. **`LEFT_BANK`**: Direct view of Bank 2 (Cylinders 2 & 4) at $(-3.4, 0.6, 0.0)$
5. **`RIGHT_BANK`**: Direct view of Bank 1 (Cylinders 1 & 3) at $(3.4, 0.6, 0.0)$

---

## 6. Thermal Mapping Subsystem

The thermal mapping pipeline evaluates scalar Cylinder Head Temperature telemetry ($T_{\text{CHT}} \in [50^\circ\text{C}, 180^\circ\text{C}]$) through a 5-stop continuous linear color gradient:
- $T \le 50^\circ\text{C}$: Sky Blue (`#00a8ff`) — Cold / Pre-flight ambient
- $T = 90^\circ\text{C}$: Emerald Green (`#00e676`) — Normal operating temperature
- $T = 120^\circ\text{C}$: Amber Yellow (`#ffea00`) — Elevated nominal threshold
- $T = 150^\circ\text{C}$: Bright Orange (`#ff6d00`) — High thermal warning
- $T \ge 180^\circ\text{C}$: Crimson Red (`#d50000`) — Critical thermal limit

For temperatures exceeding $120^\circ\text{C}$, the material activates an emissive glow channel scaled up to $0.90$ intensity, providing immediate visual warning of cylinder thermal distress.

---

## 7. Engineering HUD & Telemetry Interface

The HUD overlays real-time telemetry meters directly on top of the 3D viewport:
- **Engine Identity Banner**: Highlights model class with strict disclaimer: `"Generic Turbocharged Aero-Piston Engine (Rotax 914/915 Class Inspired - Prototype Visualizer)"`.
- **Operating State Badge**: Displays engine operational mode (`COLD`, `IDLE`, `CRUISE`, `TAKEOFF`, `DESCENT`, `HOT_SHUTDOWN`).
- **Powertrain Telemetry Gauges**: Engine RPM, Manifold Absolute Pressure (MAP in bar), Oil Pressure (bar), Fuel Flow (L/h), and Vibration Intensity ($g$).
- **Per-Cylinder Telemetry Cards**: Live CHT ($^\circ\text{C}$), EGT ($^\circ\text{C}$), and cylinder-specific firing status for Cylinders 1 through 4. Interactive selection synchronizes with 3D mesh raycasting.

---

## 8. Phase 3 Development State Adapter (`TwinDevAdapter`)

To facilitate rigorous development and testing prior to Phase 4 WebSocket deployment:
- **Live Simulator Step**: Communicates with the Phase 2 FastAPI backend via `POST /api/v1/simulation/step` to fetch the next sequential engine snapshot.
- **Flight Scenario Injection**: One-click scenario switching (`CRUISE`, `TAKEOFF`, `DESCENT`, `OVERHEAT_WARNING`, `HIGH_VIBRATION`).
- **Interactive Engineering Sliders**: Manual real-time override for RPM ($0 - 6,000$), MAP ($0.5 - 1.6\text{ bar}$), and CHT ($50 - 200^\circ\text{C}$).

---

## 9. WebGL Detection & Fallback Strategy

The application executes a lightweight WebGL context test (`src/features/twin/webgl.ts`):
```typescript
const canvas = document.createElement('canvas');
const gl = canvas.getContext('webgl2') || canvas.getContext('webgl');
```
If WebGL is disabled or unsupported in headless environments, the component renders `WebGLFallback.tsx`, presenting an accessible, structured tabular readout of all engine telemetry parameters without breaking the UI.

---

## 10. Verification & Test Results

### 10.1 Automated Test Suites

| Component | Test Suite | Tests Passed | Status |
| :--- | :--- | :---: | :---: |
| **Frontend Kinematics** | `src/features/twin/__tests__/kinematics.test.ts` | 9 / 9 | **PASS** |
| **Frontend Thermal Shader** | `src/features/twin/__tests__/thermal.test.ts` | 8 / 8 | **PASS** |
| **Frontend RPM & Multipliers** | `src/features/twin/__tests__/rpm.test.ts` | 8 / 8 | **PASS** |
| **Frontend Zustand Twin Store** | `src/features/twin/__tests__/twinStore.test.ts` | 6 / 6 | **PASS** |
| **Frontend WebGL Fallback** | `src/features/twin/__tests__/webgl.test.ts` | 2 / 2 | **PASS** |
| **Frontend Base Shell** | `src/App.test.ts`, `useAppStore.test.ts`, `client.test.ts` | 7 / 7 | **PASS** |
| **Frontend Total** | **Vitest 1.6.1** | **40 / 40** | **PASS** |
| **Backend Total** | **Pytest 8.4.2** | **80 / 80** | **PASS** |

### 10.2 Static Analysis & Quality Gate

- **TypeScript Compilation**: `tsc -b` completed with **0 errors**.
- **ESLint Compliance**: `eslint . --ext ts,tsx --max-warnings 0` completed with **0 errors and 0 warnings**.
- **Vite Production Build**: `vite build` completed successfully, producing an optimized production bundle (`dist/index.html` 0.60 kB, CSS 27.08 kB, JS 1,062.48 kB).
- **Backend Quality**: `ruff check backend/` passed with **All checks passed**.

---

## 11. Assumption Register & Traceability

1. **Procedural Geometry**: All 3D meshes are constructed from Three.js parametric buffer primitives (zero third-party unlicensed CAD).
2. **Kinematic Purity**: Piston stroke equations neglect crankshaft torsional flexure and pin offset friction, which is standard for diagnostic kinematic rendering.
3. **Thermal Model**: Dynamic thermal surface rendering uses lumped-parameter CHT values without full 3D CFD/FEM heat transfer modeling (appropriate for digital twin HUD).
4. **No Premature Phase Bleed**: All streaming, physics twin residuals, and AI models remain strictly reserved for subsequent phases.

---

## 12. Next Phase Readiness & Gate Sign-off

With the completion and verification of Phase 3, the AeroTwin AI platform now possesses:
1. A robust mathematical kinematics core for 4-cylinder aero-piston engines.
2. A complete hardware-accelerated 3D visualizer with 4 distinct analytical modes and 5 camera angles.
3. Full integration with the Phase 2 simulation REST API for step-by-step state ingestion.
4. Total test coverage (40 frontend unit tests + 80 backend tests).

**Phase 3 is complete and ready for formal review.** Execution is halted in accordance with Phase Control rules. Phase 4 will commence only upon explicit authorization.
