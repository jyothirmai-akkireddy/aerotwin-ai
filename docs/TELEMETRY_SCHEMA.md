# AeroTwin AI — Telemetry Contract & Schema Specification

**Schema Identifier**: `aerotwin.telemetry.frame`  
**Current Version**: `v1.0.0`  
**Status**: PROTOTYPE / SPECIFIED  
**Target Engine**: Generic 4-Cylinder Turbocharged Horizontally-Opposed Aero-Piston Engine (inspired by Rotax 914/915 class; prototype assumptions, not an exact manufacturer model)  
**Nominal Rate**: 10 Hz (Architecture is rate-configurable to support varied rates)  

---

## 1. Overview & Architectural Role

In AeroTwin AI, telemetry data represents the raw or pre-filtered stream of physical state observations transmitted from the UAV over an RF datalink or simulated by the physics injection module.

The telemetry stream is processed in real time:
```
Raw Frame → Ingestion Validation → Physics Twin (Expected vs Actual) → Residual Vector → AI Diagnostics
```

> **IMPORTANT**: The schema limits and physical values defined below represent **prototype engineering assumptions** for a generic 4-cylinder aero-piston engine. They are NOT certified manufacturer specifications.

To avoid silent ingestion failures or data corruption propagating into the Digital Twin, every frame is rigorously validated at system ingress against the rules defined below.

---

## 2. Telemetry Frame Schema Definition (v1.0.0)

### 2.1 Metadata & Temporal Frame Fields

| Field Name | Type | Unit | Required | Valid Range | Prototype Assumption / Definition |
|---|---|---|---|---|---|
| `version` | string | - | Yes | `"1.0.0"` | Telemetry schema protocol version string. |
| `timestamp` | float / ISO-8601 | seconds (UTC epoch) | Yes | $> 0$, strictly monotonic | High-precision floating timestamp representing observation time. |
| `sequence_id` | integer | counter | Yes | $\ge 0$ | Monotonically increasing sequence packet counter to detect packet drops. |
| `source_type` | enum string | - | Yes | `SIMULATED`, `REPLAY`, `CAN_HARDWARE` | Data provenance tag to strictly guarantee ML honesty. |
| `quality_flag` | enum string | - | Yes | `GOOD`, `DEGRADED`, `CORRUPTED`, `INVALID` | Health status of the telemetry link. |

---

### 2.2 Propulsion & Powertrain Dynamics

| Field Name | Type | Unit | Required | Valid Range (Prototype Assumption) | Description |
|---|---|---|---|---|---|
| `rpm` | float | RPM | Yes | `0.0` to `6500.0` | Crankshaft rotational speed. Redline assumption: 5800 RPM continuous, 6500 max transient. |
| `manifold_pressure` | float | inHg | Yes | `10.0` to `45.0` | Turbocharger manifold absolute pressure (MAP). 29.92 inHg = ambient sea level standard. |
| `throttle_position` | float | % | Yes | `0.0` to `100.0` | Commanded throttle valve angle / servo actuator position. |
| `fuel_flow` | float | L/h | Yes | `0.0` to `60.0` | Instantaneous total volumetric fuel consumption rate. |
| `fuel_pressure` | float | bar | Yes | `1.0` to `5.5` | Electronic fuel injection rail differential pressure. |
| `injection_timing` | float | °BTDC | Yes | `5.0` to `40.0` | Spark / injection advance in degrees Before Top Dead Center. |

---

### 2.3 Thermal Management & Exhaust Dynamics

*Note: The baseline engine is a 4-cylinder boxer configuration (Cylinders 1, 2, 3, 4).*

| Field Name | Type | Unit | Required | Valid Range (Prototype Assumption) | Description |
|---|---|---|---|---|---|
| `cht` | array[float, 4] | °C | Yes | `-30.0` to `250.0` | Cylinder Head Temperatures for Cyl 1, 2, 3, 4. Normal operating range: 90–135 °C. |
| `egt` | array[float, 4] | °C | Yes | `100.0` to `980.0` | Exhaust Gas Temperatures for Cyl 1, 2, 3, 4. Normal operating range: 700–880 °C. |
| `coolant_temp` | float | °C | Yes | `-30.0` to `130.0` | Liquid coolant temperature at the cylinder jacket outlet. |
| `oil_temperature` | float | °C | Yes | `-20.0` to `160.0` | Lubricating oil temperature in the main engine sump/reservoir. |

---

### 2.4 Lubrication & Mechanical Vibration

| Field Name | Type | Unit | Required | Valid Range (Prototype Assumption) | Description |
|---|---|---|---|---|---|
| `oil_pressure` | float | bar | Yes | `0.0` to `10.0` | Main oil gallery pressure. Normal operating range: 2.0 to 5.0 bar; critical low threshold: 1.5 bar. |
| `vibration_rms` | float | g ($m/s^2$) | Yes | `0.0` to `15.0` | Tri-axial engine block high-frequency vibration RMS amplitude. Baseline normal: 0.5–2.5 g. |

---

### 2.5 Electrical & Avionics Subsystems

| Field Name | Type | Unit | Required | Valid Range (Prototype Assumption) | Description |
|---|---|---|---|---|---|
| `battery_voltage` | float | V | Yes | `9.0` to `32.0` | 24V/28V UAV bus system voltage. Nominal: 27.5–28.5 V. |
| `alternator_current`| float | A | Yes | `0.0` to `60.0` | Output current load of primary engine-driven alternator. |
| `alternator_status` | enum string | - | Yes | `OK`, `WARNING`, `FAULT` | Generator field excitation and diode rectifier health state. |

---

### 2.6 Ambient & Flight State Context

| Field Name | Type | Unit | Required | Valid Range (Prototype Assumption) | Description |
|---|---|---|---|---|---|
| `altitude` | float | m (ASL) | Yes | `-200.0` to `12000.0` | Pressure altitude of the UAV above mean sea level. |
| `ambient_temp` | float | °C | Yes | `-60.0` to `60.0` | Outside Air Temperature (OAT) affecting intercooler & cooling efficiency. |
| `true_airspeed` | float | m/s | Yes | `0.0` to `120.0` | True airspeed affecting ram air cooling through cowlings. |

---

## 3. Physical Boundary & Validation Rules

1. **Monotonicity**: Successive frames must have strictly increasing timestamps ($\Delta t > 0$).
2. **Rate of Change (Slew Rate Limits)**:
   - RPM cannot change faster than $3000\text{ RPM/sec}$ under physical propeller inertia.
   - CHT cannot physically jump more than $15^\circ\text{C/sec}$ due to metal thermal mass.
3. **Impossibility Matrix**:
   - If $\text{RPM} = 0$, $\text{Fuel Flow} = 0$, $\text{MAP} \approx \text{ambient pressure}$, and $\text{vibration} < 0.2\text{ g}$.
   - If $\text{Oil Pressure} < 0.5\text{ bar}$ while $\text{RPM} > 3000$, an immediate critical lubrication anomaly is flagged.
4. **Missing Values**:
   - If non-critical secondary fields (e.g., `alternator_current`) are missing, forward-fill interpolation (up to 3 frames) is applied with a `DEGRADED` quality tag.
   - If critical fields (`rpm`, `cht`, `oil_pressure`) are null or NaN, the frame is marked `INVALID` and rejected from physics twin updates.

---

## 4. Sample JSON Frame (v1.0.0)

```json
{
  "version": "1.0.0",
  "timestamp": 1774358400.100,
  "sequence_id": 4201,
  "source_type": "SIMULATED",
  "quality_flag": "GOOD",
  "rpm": 5200.0,
  "manifold_pressure": 35.4,
  "throttle_position": 85.0,
  "fuel_flow": 28.5,
  "fuel_pressure": 3.2,
  "injection_timing": 24.5,
  "cht": [118.2, 121.0, 117.8, 119.5],
  "egt": [810.4, 825.1, 808.6, 815.0],
  "coolant_temp": 88.5,
  "oil_temperature": 94.2,
  "oil_pressure": 3.8,
  "vibration_rms": 1.25,
  "battery_voltage": 28.2,
  "alternator_current": 22.0,
  "alternator_status": "OK",
  "altitude": 3500.0,
  "ambient_temp": 12.0,
  "true_airspeed": 48.0
}
```
