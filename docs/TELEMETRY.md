# AeroTwin AI — Telemetry Specification & Quality System

**Document Version:** 1.0.0  
**Phase Status:** Phase 2 Complete  
**Engine Baseline:** Generic 4-cylinder horizontally-opposed turbocharged aero-piston engine inspired by the Rotax 914/915 class  
**Nominal Sampling Rate:** 10 Hz (Configurable via `TELEMETRY_RATE_HZ`)  

---

## 1. Overview & Data Philosophy

AeroTwin AI consumes, processes, and persists high-frequency engine sensor telemetry.
In aerospace and MALE UAV operations, sensor data cannot simply be assumed correct. It is subject to electrical bus noise, thermal drifts, sensor fouling, and ADC dropouts.

The telemetry system is architected around three non-negotiable principles:
1. **Physical Integrity & Bounds Enforcement:** Every measurement is checked against plausible aerospace operational limits.
2. **Quality Status Awareness:** Telemetry samples are annotated with a rigorous `QualityStatus` enum (`VALID`, `GOOD`, `DEGRADED`, `INVALID`, `MISSING`) so downstream Digital Twin physics engines and AI models never train or infer on corrupted data without explicit awareness.
3. **Temporal Monotonicity & Continuity:** Clock timestamps must be strictly monotonic, and sequence IDs are audited for gaps and out-of-order delivery.

---

## 2. Telemetry Frame Schema (`TelemetryFrame` v1.0.0)

A single telemetry observation is encapsulated by the `TelemetryFrame` domain entity (`app/domain/entities/telemetry.py`).

| Channel | Type | Unit | Nominal Range | Valid Sensor Bounds | Description |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `version` | string | — | `"1.0.0"` | Constant | Schema contract version |
| `timestamp` | float | s | Epoch | $> 0.0$, finite | UTC epoch seconds (or simulation time) |
| `sequence_id` | integer | — | $\ge 0$ | Monotonic +1 | Sequential frame counter |
| `source_type` | enum | — | `SIMULATED` | `SIMULATED`, `REPLAY`, `CAN_HARDWARE` | Telemetry origin adapter |
| `quality_flag` | enum | — | `VALID` | `VALID`, `GOOD`, `DEGRADED`, `INVALID`, `MISSING` | Frame data quality indicator |
| `rpm` | float | RPM | 1400 – 5800 | 0.0 – 6500.0 | Crankshaft rotational speed |
| `manifold_pressure` | float | inHg | 25.0 – 40.0 | 8.0 – 52.0 | Turbocharged manifold absolute pressure |
| `throttle_position`| float | % | 0.0 – 100.0 | 0.0 – 100.0 | Commanded throttle angle percentage |
| `fuel_flow` | float | L/h | 5.0 – 35.0 | 0.0 – 60.0 | Instantaneous fuel flow rate |
| `fuel_pressure` | float | bar | 2.8 – 3.4 | 0.4 – 6.0 | Fuel rail differential pressure |
| `injection_timing` | float | °BTDC | 15.0 – 32.0 | 0.0 – 42.0 | Ignition advance / spark timing |
| `cht` (4 cylinders)| list[float]| °C | 75.0 – 115.0 | -30.0 – 250.0 | Cylinder head temperatures (Cylinders 1–4) |
| `egt` (4 cylinders)| list[float]| °C | 680.0 – 820.0| -50.0 – 1000.0| Exhaust gas temperatures (Cylinders 1–4) |
| `coolant_temp` | float | °C | 60.0 – 85.0 | -30.0 – 130.0 | Cylinder jacket coolant temperature |
| `oil_temperature` | float | °C | 75.0 – 110.0 | -20.0 – 160.0 | Engine sump oil temperature |
| `oil_pressure` | float | bar | 2.0 – 4.5 | 0.0 – 10.0 | Main gallery lubrication oil pressure |
| `vibration_rms` | float | g | 0.5 – 2.2 | 0.0 – 15.0 | Tri-axial engine block vibration RMS |
| `battery_voltage` | float | V | 27.5 – 28.5 | 9.0 – 32.0 | 28V avionics bus system voltage |
| `alternator_current`| float | A | 10.0 – 35.0 | 0.0 – 60.0 | Alternator electrical load |
| `alternator_status` | string| — | `"OK"` | `"OK"`, `"WARNING"`, `"FAULT"` | Internal alternator regulator health |
| `altitude` | float | m ASL | 0.0 – 3500.0 | -200.0 – 12000.0 | Barometric pressure altitude |
| `ambient_temp` | float | °C | -20.0 – 35.0 | -60.0 – 60.0 | Outside air temperature (OAT) |
| `true_airspeed` | float | m/s | 0.0 – 65.0 | 0.0 – 120.0 | True airspeed (TAS) |

---

## 3. Multi-Cylinder Convention

AeroTwin AI models a 4-cylinder horizontally-opposed configuration:
- `cht[0]`: Cylinder 1 (Front Left)
- `cht[1]`: Cylinder 2 (Front Right)
- `cht[2]`: Cylinder 3 (Rear Left)
- `cht[3]`: Cylinder 4 (Rear Right)

In horizontally opposed aircraft installations, rear cylinders typically experience lower direct ram air cooling than front cylinders. Under nominal conditions, the simulator accounts for this geometry by introducing a physical thermal delta ($\Delta T \approx 2\text{--}6^\circ\text{C}$ across cylinder banks).

---

## 4. Telemetry Validation Rules

The `TelemetryValidator` (`app/domain/telemetry/validation.py`) executes five distinct validation phases on every frame:

1. **Temporal & Continuity Checks:**
   - Monotonic timestamps ($t_{k} > t_{k-1}$). Reverse timestamps flag `INVALID`.
   - Sequence ID continuity ($seq_{k} - seq_{k-1} = 1$). Dropped frames produce a warning and mark quality `DEGRADED`.
   - Large temporal gap ($dt > 5.0\text{ s}$) produces a warning.

2. **Finiteness & Single-Channel Bounds:**
   - Every scalar channel must be finite (not `NaN`, `+Inf`, or `-Inf`).
   - Must fall within aerospace prototype bounds. Out-of-bounds channels produce errors and mark the frame `INVALID`.

3. **Multi-Cylinder Temperature Array Checks:**
   - Both `cht` and `egt` must contain exactly 4 readings.
   - Every reading must be finite and within operational bounds (`[-30, 250]` for CHT, `[-50, 1000]` for EGT).

4. **Slew Rate Checks (Temporal Derivatives):**
   - Maximum RPM rate of change: $3,500\text{ RPM/s}$ (flywheel and propeller inertia limit).
   - Maximum CHT rate of change: $15.0^\circ\text{C/s}$ (thermal mass inertia limit).
   - Excessive slew rates indicate unphysical step glitches or sensor noise spikes.

5. **Impossible Physical Combinations (Physical Invariants):**
   - High power without fuel: $\text{RPM} > 3,000$ and $\text{Fuel Flow} < 0.5\text{ L/h}$ is rejected as physically impossible.
   - High power without lubrication: $\text{RPM} > 2,500$ and $\text{Oil Pressure} < 0.5\text{ bar}$ generates a high-severity warning (`DEGRADED`).

---

## 5. Sensor Fault Injection Model

The simulation engine includes a deterministic sensor fault injection subsystem (`app/domain/simulation/faults.py`) to generate realistic degradation for AI testing:

- **`BIAS`:** Constant additive offset ($y(t) = x(t) + M$) during active window $[t_{start}, t_{end}]$.
- **`DRIFT`:** Linearly growing offset ($y(t) = x(t) + R \cdot (t - t_{start})$).
- **`STUCK`:** Freezes sensor reading at a fixed constant value $M$ regardless of physical changes.
- **`DROPOUT`:** Sensor output drops to $0.0$ or disconnected state, triggering validator `INVALID` rejection.
- **`NOISE_SPIKE`:** Amplifies measurement white noise by a multiplicative factor $K_{noise}$.

---

## 6. Rate-Configurability

The nominal telemetry generation and streaming rate is **10 Hz** ($dt = 0.1\text{ s}$).
However, all physics calculations, lags, slew rate limiters, and time steps are parameterized by $dt = 1.0 / \text{rate\_hz}$.

The rate can be overridden at runtime via:
- Environment variable: `AEROTWIN_TELEMETRY__RATE_HZ=20`
- Simulator initialization: `EngineSimulator(telemetry_rate_hz=20)`
- Tested configurations: 1 Hz, 5 Hz, 10 Hz, 20 Hz, 50 Hz.
