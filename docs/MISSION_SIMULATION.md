# AeroTwin AI — Mission Simulation Subsystem
**Domain Architecture, Profile Curve Mathematics, Event Scheduling, and Fuel Integration**

**Document ID:** AT-DOC-MISSION-SIM-001  
**Project:** SIH26054 — AeroTwin AI  
**Subsystem:** Phase 8 — Mission Simulation + Flight Replay + Scenario Playback  
**Baseline Engine:** Generic 4-cylinder horizontally-opposed turbocharged aero-piston engine (Rotax 914/915 iS class)  
**Status:** IMPLEMENTED & VERIFIED  

---

> [!IMPORTANT]
> **PROTOTYPE RESEARCH DISCLAIMER**  
> All mission simulation profiles, dynamic transitions, atmospheric schedules, and injected faults described herein are synthetic engineering benchmarks generated for digital twin validation, software-in-the-loop (SITL) testing, and control algorithm evaluation. They do NOT represent certified flight profiles, OEM operational limitations, or airworthiness-approved flight procedures (FAA / EASA / DGCA).

---

## 1. Subsystem Architecture

The Mission Simulation Subsystem is engineered according to Clean Architecture boundaries:

```
+---------------------------------------------------------------------------------+
|                                 APPLICATION LAYER                               |
|   MissionService                 MissionSimulator                               |
|   - Predefined catalog           - Dynamic profile interpolation                |
|   - Export to Parquet/JSON       - Control & fault event scheduler              |
|   - Simulation runner            - Riemann fuel integration                     |
+---------------------------------------------------------------------------------+
                                      | calls
                                      v
+---------------------------------------------------------------------------------+
|                                  DOMAIN LAYER                                   |
|   app.domain.mission                                                            |
|   - enums: MissionPhaseType, ProfileTransitionType, ControlTargetParameter     |
|   - profiles: ProfileCurve (Constant, Step, Linear, Smooth Ramp)               |
|   - events: MissionControlEvent, MissionFaultEvent                             |
|   - models: MissionDefinition, MissionPhaseDefinition, SimulationSummary        |
|   - catalog: Predefined reference missions (Surveillance, Climb, Benchmark...)  |
+---------------------------------------------------------------------------------+
                                      | drives
                                      v
+---------------------------------------------------------------------------------+
|                                  PHYSICS CORE                                   |
|   EngineSimulator (Phase 1–2)                                                   |
|   - step(ScenarioPhase) -> TelemetryFrame at 10 Hz                              |
+---------------------------------------------------------------------------------+
```

The domain models are completely isolated from web frameworks, network I/O, database systems, and serialization formats, verified by automated AST inspection (`test_architecture_boundaries.py`).

---

## 2. Profile Curve Mathematics

Each mission phase specifies duration ($T_p$) and independent target parameters:
- `throttle_pct` ($\%$)
- `altitude_m` ($\text{m}$)
- `ambient_temp_c` ($^\circ\text{C}$)
- `airspeed_mps` ($\text{m/s}$)

Parameter dynamics across a phase are governed by `ProfileCurve` transition types evaluated against normalized phase time:

$$\tau = \frac{t - t_{\text{start}}}{T_p} \in [0.0, 1.0]$$

### 2.1 Profile Transition Functions

1. **CONSTANT:**
   $$v(\tau) = v_0 \quad \forall \, \tau \in [0.0, 1.0]$$

2. **STEP:**
   $$v(\tau) = \begin{cases} v_0, & \tau \le 0 \\ v_1, & \tau > 0 \end{cases}$$

3. **LINEAR_RAMP:**
   $$v(\tau) = v_0 + (v_1 - v_0) \cdot \tau$$

4. **SMOOTH_RAMP (Cubic Hermite Smootherstep):**
   To prevent discontinuous derivative impulses in the thermodynamic and mechanical ODE integrators of `EngineSimulator`, smooth ramp interpolation implements a cubic smoothstep polynomial $S(\tau)$:

   $$S(\tau) = 3\tau^2 - 2\tau^3$$

   $$v(\tau) = v_0 + (v_1 - v_0) \cdot S(\tau)$$

   **Mathematical Properties:**
   - Boundary Values: $S(0) = 0$, $S(1) = 1$
   - Boundary Derivatives: $S'(\tau) = 6\tau - 6\tau^2 \implies S'(0) = 0$, $S'(1) = 0$
   - $C^1$ Continuity: Zero jerk at phase entry and exit, preventing unphysical pressure spikes in the manifold and turbocharger models.

---

## 3. Dynamic Control & Fault Perturbations

In addition to base profile curves, missions support discrete time-bounded events:

### 3.1 MissionControlEvent
Applies targeted control perturbations over $[t_{\text{start}}, t_{\text{start}} + \text{duration}]$:
- Targets: `THROTTLE_PCT`, `ALTITUDE_M`, `AIRSPEED_MPS`, `AMBIENT_TEMP_C`.
- Modes:
  - Additive: $v_{\text{active}}(t) = v_{\text{curve}}(t) + \Delta v$
  - Overriding: $v_{\text{active}}(t) = v_{\text{override}}$

### 3.2 MissionFaultEvent
Injects sensor and subsystem anomalies mapped directly to Phase 2 `SensorFaultConfig`:
- Fault Types: `DRIFT`, `STUCK`, `SPIKE`, `NOISE_BURST`.
- Targets: All physical telemetry channels (`RPM`, `MAP`, `CHT`, `EGT`, `OIL_PRESS`, etc.).
- Active windows are evaluated per simulation step; when $t \in [t_{\text{start}}, t_{\text{start}} + \text{duration}]$, the corresponding `SensorFaultConfig` is passed into `EngineSimulator.step()`.

---

## 4. Fuel Flow Integration Semantics

To prevent unit ambiguity between volume flow rate and mass consumption:

1. **Telemetry Schema Invariant:**
   `TelemetryFrame.fuel_flow` is strictly in **Liters per hour ($L/\text{h}$)**.

2. **Discrete Riemann Volume Integration:**
   Given discrete simulation timestep $\Delta t = 0.1\text{ s}$ (10 Hz):

   $$V_{\text{fuel}} = \sum_{k=1}^{N} \frac{\text{fuel\_flow}_k}{3600.0} \cdot \Delta t \quad [\text{Liters}]$$

3. **Fuel Mass Calculation:**
   Using nominal aviation gasoline (100LL Avgas) density $\rho_{\text{fuel}} = 0.72\text{ kg/L}$:

   $$m_{\text{fuel}} = V_{\text{fuel}} \cdot \rho_{\text{fuel}} \quad [\text{kg}]$$

The integration is verified in automated unit tests (`test_mission_fuel.py`) across steady-state and dynamic throttle trajectories with zero drift.

---

## 5. Reference Benchmark Mission Catalog

The system provides 5 predefined synthetic benchmark missions (`app/domain/mission/catalog.py`):

| Mission ID | Mission Name | Duration | Phases | Injected Events | Purpose |
|:---|:---|:---:|:---:|:---:|:---|
| `SURVEILLANCE_MISSION` | Standard Tactical Surveillance | 470 s | 5 (Idle, Climb, Recon, Ingress, Descent) | EGT Drift at $t=180\text{s}$ | Long-duration endurance and thermal equilibrium validation |
| `RAPID_CLIMB_HOT_DAY` | Hot-Day High-Rate Climb | 180 s | 3 (Ground Idle, Rapid Climb, High Cruise) | None | High ambient temp ($38^\circ\text{C}$), CHT redline margin stress |
| `THROTTLE_DYNAMICS_BENCHMARK` | Step & Ramp Dynamic Response | 170 s | 4 (Idle, Linear Ramp, High Power, Step Drop) | Throttle Gust Perturbation | Governor transient tracking and turbocharger lag response |
| `HIGH_ALTITUDE_FERRY` | High Altitude Cruise Benchmark | 420 s | 4 (Climb, FL120 Cruise, Step Cruise, Descent) | Boost Pressure Fluctuation | Turbocharger wastegate control and low-density cooling ($4000\text{ m}$) |
| `EMERGENCY_DESCENT` | Rapid Emergency Descent | 160 s | 3 (Cruising, Power-Off Dive, Level-Off) | Oil Pressure Sensor Glitch | Thermal shock, rapid CHT drop, low-idle oil pressure limits |

All catalog missions are labeled `"SYNTHETIC / PROTOTYPE SCENARIO"`.

---

## 6. Bitwise Determinism & Verification

The mission simulation engine guarantees exact repeatability:
- Given an identical `MissionDefinition` and initial simulator state, two independent simulation runs produce bitwise identical telemetry streams:

$$\max_{k, i} |x_{1}(k, i) - x_{2}(k, i)| < 10^{-6}$$

Verified by `test_mission_determinism.py` across all scalar fields and 4-cylinder CHT/EGT temperature arrays.
