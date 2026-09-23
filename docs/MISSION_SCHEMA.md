# AeroTwin AI — Mission Specification Schema
**JSON Schema Specifications, Validation Constraints, and Payload Definitions**

**Document ID:** AT-SPEC-MISSION-SCHEMA-001  
**Project:** SIH26054 — AeroTwin AI  
**Subsystem:** Phase 8 — Mission Simulation + Flight Replay + Scenario Playback  
**Baseline Engine:** Generic 4-cylinder horizontally-opposed turbocharged aero-piston engine (Rotax 914/915 iS class)  
**Status:** IMPLEMENTED & VERIFIED  

---

> [!IMPORTANT]
> **PROTOTYPE RESEARCH DISCLAIMER**  
> The mission schemas specified herein define simulation input structures for research prototypes. Field values and atmospheric constraints do not represent certified flight plans or FAA/EASA-approved operational profiles.

---

## 1. Mission Schema Overview

AeroTwin AI missions are defined as structured declarative schemas comprising:
1. **Metadata:** Unique ID, human-readable name, description, tags, scenario labels.
2. **Phase Definitions:** Sequential ordered flight phases (`MissionPhaseDefinition`), each specifying duration and profile curves.
3. **Control Events:** Time-stamped discrete control perturbations (`MissionControlEvent`).
4. **Fault Events:** Time-stamped sensor/actuator fault injections (`MissionFaultEvent`).

---

## 2. Complete JSON Schema Specification

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "MissionDefinition",
  "description": "Complete specification for a simulated UAV engine mission profile.",
  "type": "object",
  "required": ["mission_id", "name", "phases"],
  "properties": {
    "mission_id": {
      "type": "string",
      "description": "Unique alphanumeric identifier (e.g., 'SURVEILLANCE_MISSION').",
      "pattern": "^[A-Za-z0-9_-]+$"
    },
    "name": {
      "type": "string",
      "description": "Human-readable mission title."
    },
    "description": {
      "type": "string",
      "description": "Detailed operational summary and objectives."
    },
    "scenario_label": {
      "type": "string",
      "default": "SYNTHETIC / PROTOTYPE SCENARIO",
      "description": "Mandatory prototype disclaimer banner."
    },
    "phases": {
      "type": "array",
      "description": "Ordered list of mission phases.",
      "minItems": 1,
      "items": {
        "$ref": "#/$defs/MissionPhaseDefinition"
      }
    },
    "control_events": {
      "type": "array",
      "description": "Optional discrete control perturbations.",
      "items": {
        "$ref": "#/$defs/MissionControlEvent"
      }
    },
    "fault_events": {
      "type": "array",
      "description": "Optional discrete fault injection events.",
      "items": {
        "$ref": "#/$defs/MissionFaultEvent"
      }
    }
  },
  "$defs": {
    "MissionPhaseDefinition": {
      "type": "object",
      "required": ["phase_name", "phase_type", "duration_s", "target_throttle_pct"],
      "properties": {
        "phase_name": {
          "type": "string",
          "description": "Identifier for the phase (e.g., 'CLIMB_STAGE_1')."
        },
        "phase_type": {
          "type": "string",
          "enum": ["IDLE", "TAXI", "TAKEOFF", "CLIMB", "CRUISE", "LOITER", "DESCENT", "APPROACH", "LANDING", "BENCHMARK_STEP", "CUSTOM"]
        },
        "duration_s": {
          "type": "number",
          "minimum": 1.0,
          "maximum": 86400.0,
          "description": "Phase duration in seconds."
        },
        "target_throttle_pct": {
          "type": "number",
          "minimum": 0.0,
          "maximum": 115.0,
          "description": "Target throttle setting in percent (115% represents 5-min takeoff boost)."
        },
        "transition_type": {
          "type": "string",
          "enum": ["CONSTANT", "STEP", "LINEAR_RAMP", "SMOOTH_RAMP"],
          "default": "SMOOTH_RAMP",
          "description": "Interpolation function applied across the phase."
        },
        "target_altitude_m": {
          "type": "number",
          "minimum": -50.0,
          "maximum": 12000.0,
          "default": 0.0,
          "description": "Target geometric altitude in meters ASL."
        },
        "target_ambient_temp_c": {
          "type": "number",
          "minimum": -60.0,
          "maximum": 60.0,
          "default": 15.0,
          "description": "Target ambient temperature in degrees Celsius."
        },
        "target_airspeed_mps": {
          "type": "number",
          "minimum": 0.0,
          "maximum": 150.0,
          "default": 0.0,
          "description": "Target true airspeed in meters per second."
        }
      }
    },
    "MissionControlEvent": {
      "type": "object",
      "required": ["start_time_s", "duration_s", "target_parameter", "value"],
      "properties": {
        "start_time_s": {
          "type": "number",
          "minimum": 0.0
        },
        "duration_s": {
          "type": "number",
          "minimum": 0.1
        },
        "target_parameter": {
          "type": "string",
          "enum": ["THROTTLE_PCT", "ALTITUDE_M", "AIRSPEED_MPS", "AMBIENT_TEMP_C"]
        },
        "value": {
          "type": "number"
        },
        "is_override": {
          "type": "boolean",
          "default": false,
          "description": "True replaces target value; False adds delta value."
        }
      }
    },
    "MissionFaultEvent": {
      "type": "object",
      "required": ["start_time_s", "duration_s", "fault_type", "target_sensor"],
      "properties": {
        "start_time_s": {
          "type": "number",
          "minimum": 0.0
        },
        "duration_s": {
          "type": "number",
          "minimum": 0.1
        },
        "fault_type": {
          "type": "string",
          "enum": ["DRIFT", "STUCK", "SPIKE", "NOISE_BURST"]
        },
        "target_sensor": {
          "type": "string",
          "enum": ["RPM", "MANIFOLD_PRESSURE", "CHT", "EGT", "OIL_PRESSURE", "OIL_TEMPERATURE", "FUEL_FLOW", "FUEL_PRESSURE", "VIBRATION"]
        },
        "severity": {
          "type": "number",
          "minimum": 0.0,
          "maximum": 1.0,
          "default": 0.5
        },
        "parameters": {
          "type": "object",
          "description": "Specific parameters (e.g. drift_rate, stuck_value, spike_magnitude)."
        }
      }
    }
  }
}
```

---

## 3. Example Mission Payload

```json
{
  "mission_id": "RAPID_CLIMB_HOT_DAY",
  "name": "Hot-Day High-Rate Climb Benchmark",
  "description": "Evaluates cylinder head thermal saturation during high-rate climb under elevated ISA+23C ambient temperatures.",
  "scenario_label": "SYNTHETIC / PROTOTYPE SCENARIO",
  "phases": [
    {
      "phase_name": "GROUND_IDLE_PREWARM",
      "phase_type": "IDLE",
      "duration_s": 30.0,
      "target_throttle_pct": 20.0,
      "transition_type": "CONSTANT",
      "target_altitude_m": 100.0,
      "target_ambient_temp_c": 38.0,
      "target_airspeed_mps": 0.0
    },
    {
      "phase_name": "FULL_POWER_CLIMB",
      "phase_type": "CLIMB",
      "duration_s": 90.0,
      "target_throttle_pct": 100.0,
      "transition_type": "SMOOTH_RAMP",
      "target_altitude_m": 3000.0,
      "target_ambient_temp_c": 22.0,
      "target_airspeed_mps": 45.0
    },
    {
      "phase_name": "TOP_OF_CLIMB_CRUISE",
      "phase_type": "CRUISE",
      "duration_s": 60.0,
      "target_throttle_pct": 75.0,
      "transition_type": "LINEAR_RAMP",
      "target_altitude_m": 3000.0,
      "target_ambient_temp_c": 22.0,
      "target_airspeed_mps": 55.0
    }
  ],
  "control_events": [],
  "fault_events": []
}
```
