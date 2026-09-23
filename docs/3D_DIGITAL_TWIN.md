# AeroTwin AI — 3D Digital Twin Visualizer Architecture & Technical Specification

**Project**: SIH26054 — AeroTwin AI  
**Document**: Architectural & Kinematics Specification for Subsystem 3D Digital Twin  
**Phase**: Phase 3  
**Status**: Completed & Verified  

---

## 1. System Overview & Clean Architecture Alignment

The 3D Digital Twin Subsystem (`frontend/src/features/twin`) provides an interactive, mathematically rigorous, hardware-accelerated 3D visualization of a generic 4-cylinder horizontally-opposed turbocharged aero-piston engine inspired by the Rotax 914/915 class.

In strict adherence to clean architecture principles:
1. **Kinematic Purity**: Kinematic equations and thermal interpolation routines are implemented as pure, zero-dependency mathematical functions (`kinematics.ts`, `thermal.ts`). They contain no Three.js or DOM side effects and are 100% unit-tested in isolation.
2. **Decoupled State Management**: The visualization state is governed by Zustand (`useTwinStore.ts`), which completely separates 3D rendering state (camera presets, active visualization mode, selected cylinder, visual playback multiplier) from the telemetry data payload.
3. **Phase Boundary Preservation**: In Phase 3, the visualization consumes telemetry snapshots synchronously via the `TwinDevAdapter` (invoking the Phase 2 REST API endpoint `/api/v1/simulation/step` or manual engineering controls). No real-time WebSockets, streaming workers, or fake AI predictions are introduced, preserving Phase 4 and Phase 6 isolation.

```
+-------------------------------------------------------------------------------+
|                             AeroTwin AI Frontend                              |
|                                                                               |
|  +------------------------+                     +--------------------------+  |
|  |   TwinDevAdapter       |                     |     TwinControls         |  |
|  | (Phase 2 REST Bridge / |                     | (Mode, Cam Presets,      |  |
|  |  Manual Telemetry Test)|                     |  Exploded Dist, Speed)   |  |
|  +-----------+------------+                     +------------+-------------+  |
|              |                                               |                |
|              v                                               v                |
|  +-------------------------------------------------------------------------+  |
|  |                         Zustand useTwinStore                            |  |
|  |  - engineState: EngineStateSnapshot                                      |  |
|  |  - mode: NORMAL | THERMAL | CUTAWAY | EXPLODED                          |  |
|  |  - cameraPreset: ISOMETRIC | FRONT | TOP | LEFT_BANK | RIGHT_BANK       |  |
|  |  - selectedCylinder: 1 | 2 | 3 | 4 | null                               |  |
|  |  - isRunning: boolean, visualSpeedMultiplier: number                    |  |
|  +--------------------+--------------------------------+-------------------+  |
|                       |                                |                      |
|                       v                                v                      |
|  +-----------------------------------+    +--------------------------------+  |
|  |             TwinHud               |    |          EngineScene           |  |
|  |  - Master Engine Status           |    |  - Three.js Canvas / R3F       |  |
|  |  - Telemetry Gauges (RPM, MAP, ..)|    |  - 3-Point Studio Lighting     |  |
|  |  - 4x CHT/EGT Cylinder Cards      |    |  - OrbitControls (Lerp Preset) |  |
|  |  - Prototype Legal Disclaimer     |    |  - WebGL Capability Fallback   |  |
|  +-----------------------------------+    +---------------+----------------+  |
|                                                           |                   |
|                                                           v                   |
|                                           +--------------------------------+  |
|                                           |          EngineModel           |  |
|                                           |  - CrankshaftAssembly          |  |
|                                           |  - PistonAssembly (x4)         |  |
|                                           |  - CylinderAssembly (x4)       |  |
|                                           |  - TurbochargerAssembly        |  |
|                                           |  - IntakeExhaustAssembly       |  |
|                                           |  - Kinematics & Thermal Hooks  |  |
|                                           +--------------------------------+  |
+-------------------------------------------------------------------------------+
```

---

## 2. Mathematical & Kinematic Formulations

### 2.1 Slider-Crank Kinematics Derivation

The piston reciprocates along the cylinder bore axis $X$. The exact position $x(\theta)$ measured from the crankshaft center of rotation to the wrist pin center is governed by:

$$x(\theta) = r \cos(\theta) + \sqrt{L^2 - r^2 \sin^2(\theta)}$$

Where:
- $r$: Crank throw radius ($r = \frac{\text{Stroke}}{2} = \frac{0.061\text{ m}}{2} = 0.0305\text{ m} = 0.28\text{ scene units}$)
- $L$: Connecting rod center-to-center length ($L = 0.110\text{ m} = 0.85\text{ scene units}$)
- $\theta$: Instantaneous crank angle for the specific cylinder throw ($\text{rad}$)

The connecting rod obliquity angle $\phi(\theta)$ relative to the cylinder bore axis satisfies:

$$\sin(\phi) = \frac{r}{L} \sin(\theta) \implies \phi(\theta) = \arcsin\left(\frac{r}{L} \sin(\theta)\right)$$

### 2.2 Boxer-4 Engine Phasing & Geometry

The engine features a horizontally-opposed 4-cylinder layout (two opposing banks separated by $180^\circ$ around the crank axis):

- **Bank 1 (Cylinders 1 & 3)**: Positioned on the positive $X$ side ($+X$). Piston displacement extends along $+X$.
- **Bank 2 (Cylinders 2 & 4)**: Positioned on the negative $X$ side ($-X$). Piston displacement extends along $-X$.

The standard firing order is **$1 - 4 - 2 - 3$**, resulting in individual cylinder crank pin offsets:

$$\theta_1 = \theta$$
$$\theta_4 = \theta + \pi$$
$$\theta_2 = \theta + \frac{3\pi}{2}$$
$$\theta_3 = \theta + \frac{\pi}{2}$$

### 2.3 Frame-Rate Independent Angular Integration

To ensure smooth visual motion regardless of GPU frame rate fluctuations ($30 - 144\text{ FPS}$), the crank angle $\theta$ is integrated over frame delta time $\Delta t$:

$$\omega = \text{RPM} \times \frac{2\pi}{60} \times s_{\text{multiplier}}$$

$$\theta(t + \Delta t) = \left(\theta(t) + \omega \cdot \Delta t\right) \pmod{2\pi}$$

Where $s_{\text{multiplier}} \in [0.05, 1.0]$ scales the visual rotation so fast aero-engine speeds ($5,500\text{ RPM} = 91.6\text{ rev/s}$) can be observed comfortably without stroboscopic aliasing.

---

## 3. Thermal Visualization Subsystem

Cylinder thermal states are continuously driven by scalar Cylinder Head Temperature (CHT) values ($T_{\text{CHT}, i} \in [50^\circ\text{C}, 180^\circ\text{C}]$).

### 3.1 Piecewise Linear Gradient Interpolation

Color evaluation uses 5 calibrated engineering color stops:

| Temperature ($^\circ\text{C}$) | State | Color Name | Hex Code | Three.js Vector3 $(R, G, B)$ |
| :---: | :---: | :---: | :---: | :---: |
| $\le 50$ | Cold / Ambient | Aero Sky Blue | `#00a8ff` | $(0.00, 0.66, 1.00)$ |
| $90$ | Optimal Operating | Emerald Green | `#00e676` | $(0.00, 0.90, 0.46)$ |
| $120$ | Warm Nominal | Amber Warning | `#ffea00` | $(1.00, 0.92, 0.00)$ |
| $150$ | Elevated Caution | Tangerine Orange | `#ff6d00` | $(1.00, 0.43, 0.00)$ |
| $\ge 180$ | Critical Limit | Radiant Crimson | `#d50000` | $(0.84, 0.00, 0.00)$ |

For any intermediate temperature $T \in [T_k, T_{k+1}]$:

$$t_{\text{norm}} = \frac{T - T_k}{T_{k+1} - T_k}, \quad C(T) = \text{lerp}\left(C_k, C_{k+1}, t_{\text{norm}}\right)$$

### 3.2 Dynamic Emissive Shading

To simulate radiant thermal emission under stress, the material's emissive intensity scales with temperatures exceeding $120^\circ\text{C}$:

$$I_{\text{emissive}} = \text{clamp}\left(\frac{T - 120}{180 - 120}, 0.0, 1.0\right) \times 0.9$$

---

## 4. Visualization Modes & Camera Controls

### 4.1 Four Rendering Modes

1. **`NORMAL`**: Full photorealistic PBR rendering with metallic cast aluminum and steel finishes.
2. **`THERMAL`**: Applies dynamic CHT color mapping to cylinder barrels, cooling fins, and cylinder heads, reflecting live temperature gradients.
3. **`CUTAWAY`**: Sets cylinder outer walls and heads to semi-transparent (`opacity: 0.35`, `transparent: true`), exposing the reciprocating piston crowns, wrist pins, and pivoting connecting rods in real-time.
4. **`EXPLODED`**: Translates sub-assemblies outward along their primary kinematic axes proportionally to an exploded distance factor $s \in [0.0, 1.5]$:
   - Bank 1 Cylinders: $+X$ translation
   - Bank 2 Cylinders: $-X$ translation
   - Turbocharger & Exhaust: $+Z$ translation
   - Intake Plenum: $+Y$ translation
   - Oil Sump: $-Y$ translation

### 4.2 Camera Presets with Spherical Lerp Transitions

The camera controller transitions between 5 engineering vantage points:

| Preset | Target Position $(X, Y, Z)$ | Look-At Target | Purpose |
| :--- | :--- | :--- | :--- |
| **`ISOMETRIC`** | $(2.8, 2.2, 2.8)$ | $(0, 0, 0)$ | Comprehensive 3/4 overview |
| **`FRONT`** | $(0.0, 0.4, 3.8)$ | $(0, 0, 0)$ | Propeller flange & bank symmetry |
| **`TOP`** | $(0.0, 4.2, 0.01)$ | $(0, 0, 0)$ | Intake plenum & runner alignment |
| **`LEFT_BANK`** | $(-3.4, 0.6, 0.0)$ | $(-0.8, 0, 0)$ | Bank 2 (Cylinders 2 & 4) inspection |
| **`RIGHT_BANK`**| $(3.4, 0.6, 0.0)$ | $(0.8, 0, 0)$ | Bank 1 (Cylinders 1 & 3) inspection |

---

## 5. Engineering HUD & Tactical Interface

The HUD overlays real-time telemetry meters directly on top of the 3D viewport:
- **Engine Identity Banner**: Highlights model class with strict disclaimer: `"Generic Turbocharged Aero-Piston Engine (Rotax 914/915 Class Inspired - Prototype Visualizer)"`.
- **Operating State Badge**: Displays engine operational mode (`COLD`, `IDLE`, `CRUISE`, `TAKEOFF`, `DESCENT`, `HOT_SHUTDOWN`).
- **Powertrain Telemetry Gauges**: Engine RPM, Manifold Absolute Pressure (MAP in bar), Oil Pressure (bar), Fuel Flow (L/h), and Vibration Intensity ($g$).
- **Per-Cylinder Telemetry Cards**: Live CHT ($^\circ\text{C}$), EGT ($^\circ\text{C}$), and cylinder-specific firing status for Cylinders 1 through 4. Interactive selection synchronizes with 3D mesh raycasting.

---

## 6. Phase 3 Development State Adapter (`TwinDevAdapter`)

To facilitate rigorous development and testing prior to Phase 4 WebSocket deployment:
- **Live Simulator Step**: Communicates with the Phase 2 FastAPI backend via `POST /api/v1/simulation/step` to fetch the next sequential engine snapshot.
- **Flight Scenario Injection**: One-click scenario switching (`CRUISE`, `TAKEOFF`, `DESCENT`, `OVERHEAT_WARNING`, `HIGH_VIBRATION`).
- **Interactive Engineering Sliders**: Manual real-time override for RPM ($0 - 6,000$), MAP ($0.5 - 1.6\text{ bar}$), and CHT ($50 - 200^\circ\text{C}$).

---

## 7. WebGL Capability Detection & Fallback Strategy

The application executes a lightweight WebGL context test (`src/features/twin/webgl.ts`):
```typescript
const canvas = document.createElement('canvas');
const gl = canvas.getContext('webgl2') || canvas.getContext('webgl');
```
If WebGL is disabled or unsupported in headless environments, the component renders `WebGLFallback.tsx`, presenting an accessible, structured tabular readout of all engine telemetry parameters without breaking the UI.

---

## 8. Assumption Register & Known Limitations

1. **Geometric Representation**: Visual components are high-fidelity procedural approximations. They are not certifiable CAD geometries and must not be used for manufacturing or physical clearance analysis.
2. **Thermal Conduction Model**: Surface temperature gradients are rendered per-cylinder based on lumped scalar CHT telemetry; 3D spatial finite-element heat conduction (FEA/CFD) is out of scope for Phase 3.
3. **Crankshaft Torsional Deflection**: The crankshaft is modeled as an infinitely rigid body; aero-elastic torsion and cyclic micro-deflection are not represented visually.
