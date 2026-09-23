# AeroTwin AI — Judge Demonstration & Presentation Guide
**SIH26054 — Digital Twin Engine Telemetry Platform**

> [!IMPORTANT]
> **PROTOTYPE RESEARCH DISCLAIMER**  
> AeroTwin AI is an engineering research prototype developed for SIH26054 based on a generic 4-cylinder horizontally-opposed turbocharged aero-piston engine (Rotax 914/915 iS class). All scenarios, flight logs, fault injections, degradation rates, and mission profiles represent synthetic benchmark models. Not certified for real-world flight operations or airworthiness sign-offs.

---

## 1. Executive Demonstration Philosophy

AeroTwin AI is designed to communicate one cohesive, undeniable engineering narrative to judges and technical evaluators:

```
TELEMETRY (10 Hz Ingestion)
    ↓
DIGITAL TWIN (Kinematic & Thermal 3D Model)
    ↓
PHYSICS RESIDUALS (Expected vs. Observed Deviations)
    ↓
AI ANOMALY & FAULT DETECTION (Isolation Forest + XGBoost)
    ↓
DEGRADATION TRACKING & PROGNOSTICS (Composite Health Index)
    ↓
REMAINING USEFUL LIFE (Causal OLS Extrapolation with 95% PI)
    ↓
MISSION SIMULATION & REPLAY (Deterministic UAV Flight Profiles)
    ↓
ACTIONABLE GROUND STATION COCKPIT
```

---

## 2. Pre-Demo Verification Checklist (60 Seconds)

Before presenting to judges, verify the system is in an optimal nominal state:

- [ ] **Backend Service:** Running on `http://localhost:8000`.
- [ ] **Frontend Application:** Running on `http://localhost:5173`.
- [ ] **API Health Probe:** `/api/v1/health` returns `{"status": "healthy"}`.
- [ ] **API Readiness Probe:** `/api/v1/ready` returns all 6 core components as `READY`.
- [ ] **WebSocket Stream:** Persistent header badge displays `CONNECTED` and `RATE: 10 Hz`.
- [ ] **Source Mode:** Persistent header badge displays `● LIVE`.
- [ ] **Engine Baseline:** Generic 4-Cylinder Turbo Boxer Aero-Piston.
- [ ] **Console Cleanliness:** Browser DevTools console shows zero unhandled errors.

---

## 3. The 10-Step Presentation Script (5 to 7 Minutes)

### Step 1: System Boot & Architecture Governance (30 Seconds)
- **Action:** Open `http://localhost:5173`. Point out the persistent status bar at the top.
- **Narrative:**
  > *"Judges, AeroTwin AI is a real-time digital twin platform for aero-piston engines in medium-altitude long-endurance (MALE) UAVs. Notice the persistent status bar: we are ingesting calibrated telemetry at 10 Hz over a low-latency RFC 8259 WebSocket connection with sub-5ms processing latency. The system strictly adheres to Clean Hexagonal Architecture where physics and ML domain models are 100% pure and decoupled from transports and databases."*

### Step 2: Executive Ground Station Cockpit (45 Seconds)
- **Action:** Navigate to **Ground Station** tab (`/`).
- **Narrative:**
  > *"This is our Level 2 Executive Engine Cockpit. In normal flight, judges can immediately answer the critical question: 'Is the engine healthy?' Here, the Composite Health Index reads 100.0%, degradation state is NOMINAL, and anomaly status is NOMINAL FLIGHT. Notice that Remaining Useful Life explicitly displays 'RUL UNAVAILABLE — Nominal baseline engine without active wear degradation.' We never fabricate '0 hours' or false RUL predictions when the engine is running nominally."*
- **Highlight:** Show the 9 real-time gauges (RPM, Manifold Pressure, CHT, EGT, Oil Pressure, Oil Temperature, Vibration, Fuel Flow at 0.72 kg/L density, Battery Voltage).

### Step 3: 3D Digital Twin & Kinematics (60 Seconds)
- **Action:** Click **3D Digital Twin** in the sidebar.
- **Narrative:**
  > *"Here is the Level 3 Digital Twin: a complete 3D boxer engine model featuring opposed cylinders, crankshaft rotation, piston reciprocation, and an active turbocharger assembly. Notice how the rotation speed dynamically scales with live telemetry RPM."*
- **Interactive Demonstrations:**
  1. Click **Isometric**, **Front**, **Top**, and **Left Bank** camera presets.
  2. Switch **Visualization Mode** to **THERMAL**: show how the vertex shaders map real-time Cylinder Head Temperatures (CHT) to a heat gradient (Blue $\to$ Cyan $\to$ Yellow $\to$ Red).
  3. Click Cylinder 2 or 3: show cylinder-specific telemetry isolation in the HUD.
  4. Toggle **Exploded View**: show internal piston rings and connecting rods smoothly displacing along their kinematic axes.

### Step 4: Physics Twin & Deviation Residuals (45 Seconds)
- **Action:** Scroll down to the **Physics-Informed Digital Twin** card below the 3D model.
- **Narrative:**
  > *"AeroTwin AI does not rely on naive black-box AI. Beneath the twin runs a physics-informed analytical model across 5 core subsystems: Thermal Heat Dissipation, Induction & Boost, Fuel Mass Fraction, Lubrication Hydraulics, and Rotational Vibration. Notice the observed vs expected columns: under normal flight, residuals hover near zero ($< 0.2\sigma$)."*

### Step 5: Synthetic Fault Injection (45 Seconds)
- **Action:** Scroll down to the **Twin Development Adapter** panel. Select the preset **OIL PRESSURE DRIFT (LEAK)** or **CYLINDER 2 MISFIRE**, and click **Inject Fault**.
- **Narrative:**
  > *"Let us introduce an in-flight anomaly. Notice the real-time reaction: within 100 milliseconds, oil pressure deviates from expected 4.2 bar down to 1.8 bar, while temperature begins an upward drift. The physics residual engine flags a $+3.8\sigma$ deviation."*

### Step 6: AI Anomaly Detection & XGBoost Diagnosis (60 Seconds)
- **Action:** Navigate to **AI Diagnostics & Prognostics** tab.
- **Narrative:**
  > *"Within 2 frames, the Level 4 AI Diagnostic Suite activates:
  > 1. The Isolation Forest anomaly severity score surges past the calibrated threshold ($\tau = 0.5402$) to 92.4%.
  > 2. The supervised XGBoost classifier identifies the failure pattern as LUBRICATION_LOSS with 96.8% confidence.
  > 3. Notice the feature attribution breakdown: the dominant driver is oil_pressure_residual (accounting for 68% of the anomaly score), followed by oil_temperature_residual. This gives the UAV operator immediate, explainable situational awareness rather than an opaque warning."*

### Step 7: Degradation Tracking & RUL Extrapolation (45 Seconds)
- **Action:** Point to the **Engine Degradation & Prognostics (RUL)** card.
- **Narrative:**
  > *"Now observe Level 5: Prognostics. As the fault persists, the causal FIFO buffer detects a negative health trend slope ($dH/dt = -0.00042\text{ /s}$). The Composite Health Index drops into MODERATE DEGRADATION. RUL activates dynamically, predicting 18.4 flight hours remaining with a 95% prediction interval of [14.2 – 22.6 hrs], driven by the Lubrication wear tier."*

### Step 8: Mission Simulation Center (45 Seconds)
- **Action:** Navigate to **Mission Sim & Replay** tab.
- **Narrative:**
  > *"AeroTwin AI includes a deterministic mission simulation engine capable of running complete UAV flight envelopes. Let's select `SURVEILLANCE_MISSION` (470 seconds across Taxi, Climb, Cruise, Loiter, Descent, Landing) with mathematical $S(\tau) = 3\tau^2 - 2\tau^3$ smooth cubic transitions. Clicking 'Simulate Mission' computes Riemann fuel flow integration, dynamic thermal loads, and exports a high-density Parquet dataset."*

### Step 9: Flight Replay Deck & Mode Switching (45 Seconds)
- **Action:** Select an exported log in the **Replay Scrubber Deck**. Switch source mode to **REPLAY**.
- **Narrative:**
  > *"Notice the header badge instantaneously transitions from LIVE to REPLAY. We can seek anywhere along the flight timeline, pause, resume, and run at strictly approved accelerated speeds (0.5x, 1x, 2x, 5x, 10x) or unpaced OFFLINE_BATCH. Crucially, downstream Physics, ML, and Prognostics evaluate identically regardless of playback pacing, verifying absolute data-time invariance."*

### Step 10: Safe Reset & Demo Recovery (30 Seconds)
- **Action:** Click **Reset Twin** in the persistent header.
- **Narrative:**
  > *"Finally, we trigger our Safe Demo Reset. This single action invokes our 6-step lifecycle reset: clearing simulator cold conditions, resetting physics transient thermal history, purging ML/prognostics causal buffers, resetting sequence tracking, and returning the UI to a pristine nominal state ready for the next evaluator."*

---

## 4. Emergency Recovery Procedures

If an unexpected condition occurs during a live presentation, execute these swift recovery protocols:

### Scenario A: Telemetry Stale or WebSocket Disconnected
1. Click the **Refresh** icon in the persistent header.
2. If stale indicator persists, click **Reset Twin**.
3. Verify backend terminal is active (`http://localhost:8000/api/v1/health`).

### Scenario B: Stuck in Replay Mode
1. In the header or cockpit, click **Reset Twin**.
2. Alternatively, in the Replay controls, click **LIVE STREAM** to force the source switch back to live simulation.

### Scenario C: WebGL Context Loss / Canvas Blank
1. Press `F5` to perform a clean browser refresh.
2. The UI automatically restores camera presets and nominal engine geometry.
