# AeroTwin AI — WebSocket Telemetry Protocol Specification (v1.0.0)

**Document**: Protocol Specification & Contract Definition  
**Subsystem**: Realtime Transport & Ground Station Synchronization  
**Phase**: Phase 4  
**Status**: APPROVED & IMPLEMENTED  

---

## 1. Protocol Overview & Endpoint

AeroTwin AI utilizes a structured, versioned WebSocket transport layer to synchronize real-time engine telemetry between the deterministic physics simulation and the interactive ground station 3D digital twin.

- **Primary WebSocket Endpoint**: `/api/v1/ws/telemetry`
- **Transport Scheme**: Standard WebSocket (`ws://` / `wss://`)
- **Default Port**: `8000` (configurable via `AppSettings.server.port`)
- **Protocol Version**: `1.0.0`
- **Serialization Format**: UTF-8 JSON (no binary framing in Phase 4)
- **Maximum Frame Rate**: 10 Hz nominal (rate-configurable between 1 and 100 Hz)
- **Maximum Payload Size**: 65,536 bytes (64 KB)

---

## 2. Inbound & Outbound Message Types

The protocol implements a discriminated union pattern driven by the `"type"` field:

```
                      +-----------------------------+
                      |     WebSocket Envelope      |
                      |  type: telemetry | status   |
                      |        error | heartbeat    |
                      |        command | ping       |
                      +--------------+--------------+
                                     |
         +---------------------------+---------------------------+
         |                           |                           |
         v                           v                           v
+------------------+        +------------------+        +------------------+
| TelemetryMessage |        |  StatusMessage   |        |   ErrorMessage   |
| (10 Hz Stream)   |        | (Session State)  |        | (Safe Errors)    |
+------------------+        +------------------+        +------------------+
```

---

## 3. Telemetry Message (`type: "telemetry"`)

Published continuously by the server at the nominal rate of 10 Hz ($\Delta t = 100\text{ ms}$).

### 3.1 JSON Schema
```json
{
  "type": "telemetry",
  "version": "1.0.0",
  "timestamp": 1774390000.123,
  "sequence_id": 1042,
  "server_time": 1774390000.125,
  "payload": {
    "version": "1.0.0",
    "timestamp": 1774390000.123,
    "sequence_id": 1042,
    "source_type": "SIMULATED",
    "quality_flag": "VALID",
    "rpm": 2400.0,
    "manifold_pressure": 29.5,
    "throttle_position": 45.0,
    "fuel_flow": 16.5,
    "fuel_pressure": 3.2,
    "injection_timing": 24.0,
    "cht": [95.0, 92.5, 98.0, 94.0],
    "egt": [720.0, 715.0, 730.0, 722.0],
    "coolant_temp": 82.0,
    "oil_temperature": 85.0,
    "oil_pressure": 3.8,
    "vibration_rms": 1.15,
    "battery_voltage": 28.2,
    "alternator_current": 18.5,
    "alternator_status": "OK",
    "altitude": 1000.0,
    "ambient_temp": 15.0,
    "true_airspeed": 45.0
  }
}
```

### 3.2 Field Definitions & Physical Units
- `timestamp` ($s$): Authoritative simulation epoch timestamp.
- `sequence_id` ($\mathbb{N}$): Monotonically increasing sequential frame counter.
- `server_time` ($s$): Server wall-clock UTC epoch timestamp when the frame was broadcast.
- `payload`: Complete domain `TelemetryFrame` preserving Phase 2 schemas without renaming.

---

## 4. Status Message (`type: "status"`)

Sent upon connection establishment, operational mode transitions, or command execution.

### 4.1 Schema
```json
{
  "type": "status",
  "version": "1.0.0",
  "status": "connected",
  "message": "AeroTwin AI Realtime Stream v1.0.0. Session ID: client-a1b2c3d4",
  "server_time": 1774390000.125
}
```

### 4.2 Supported Status Values
- `connected`: Handshake accepted and client session active.
- `running`: Simulation loop active and emitting telemetry.
- `paused`: Simulation loop paused; state preserved in memory.
- `stopped`: Stream terminated or engine shut down.
- `degraded`: Telemetry validation flagged sensor faults or quality degradation.
- `error`: Non-fatal operational anomaly.

---

## 5. Error Message (`type: "error"`)

Sent when a client request violates validation or transport rules. Internal stack traces, file paths, and environment secrets are never exposed.

### 5.1 Schema
```json
{
  "type": "error",
  "version": "1.0.0",
  "code": "INVALID_JSON",
  "message": "Malformed JSON syntax received",
  "server_time": 1774390000.125
}
```

### 5.2 Error Codes
- `CLIENT_LIMIT_EXCEEDED`: Active client limit reached ($50$).
- `OVERSIZED_MESSAGE`: Inbound payload exceeded $65,536\text{ bytes}$.
- `INVALID_JSON`: Inbound payload could not be parsed as JSON.
- `INVALID_COMMAND`: Command name or parameter dictionary failed validation.
- `UNKNOWN_MESSAGE_TYPE`: Unrecognized `"type"` discriminator.

---

## 6. Simulation Command Protocol (`type: "command"`)

Allows the ground station operator to control the authoritative backend simulation.

### 6.1 Schema
```json
{
  "type": "command",
  "version": "1.0.0",
  "command": "pause",
  "params": {}
}
```

### 6.2 Supported Commands & Parameters
| Command | Allowed Parameters | Action |
| :--- | :--- | :--- |
| `start` | None | Starts or resumes the telemetry publication loop |
| `pause` | None | Temporarily freezes frame emission; keeps state intact |
| `resume`| None | Resumes frame emission from current state |
| `reset` | None | Resets engine simulation state to cold/nominal defaults |
| `set_scenario` | `phase_name`: String (`"TAKEOFF_CLIMB"`, `"STANDARD_SURVEILLANCE"`, etc.) | Switches flight scenario profile |
| `set_rate` | `rate_hz`: Integer ($1 - 100$) | Dynamically updates streaming frequency |

---

## 7. Sequence Numbers & Anomaly Semantics

Every telemetry message carries a strictly monotonic integer `sequence_id`:
1. **Nominal Delivery**: $seq_k = seq_{k-1} + 1$.
2. **Gap Detection**: If $seq_k > seq_{k-1} + 1$, the client identifies a transmission gap:
   $$\text{Missed Frames} = seq_k - (seq_{k-1} + 1)$$
   The frontend records the gap counter and updates telemetry without fabricating missing data.
3. **Duplicate Detection**: If $seq_k \le seq_{k-1}$, the message is flagged as duplicate or out-of-order and safely discarded.

---

## 8. Timestamp Semantics

To prevent clock skew anomalies:
- **Simulation Time** (`timestamp`): Authoritative virtual flight time generated by `EngineSimulator.time`. Used for physics calculations, kinematics, and frame intervals.
- **Server Wall-Clock Time** (`server_time`): UTC epoch time generated at the instant of network transmission.
- **Client Receipt Time**: Local browser time recorded upon frame arrival.
- **Transport Latency**: Evaluated as $t_{\text{client}} - server\_time$ only when clocks are synchronized (labeled **localhost transport latency** in local development).

---

## 9. Backpressure & Client Isolation Strategy

- Each client connection is assigned an isolated, bounded queue (`asyncio.Queue(maxsize=100)`).
- **Latest-Value Drop Policy**: If a slow frontend client fails to read frames at 10 Hz and fills its 100-frame buffer, the broadcaster automatically discards the oldest unconsumed frame (`queue.get_nowait()`) and queues the newest frame.
- **Client Fault Isolation**: An exception or connection termination in one client never halts the publication loop or degrades delivery to other connected clients.

---

## 10. Client Reconnection & Stale Data Lifecycle

### 10.1 Exponential Backoff
When disconnected involuntarily, the frontend initiates reconnection with exponential backoff:
$$T_{\text{retry}} = [250\text{ ms}, 500\text{ ms}, 1000\text{ ms}, 2000\text{ ms}, 4000\text{ ms}, 8000\text{ ms}]$$
Clamped at a maximum of 10 attempts before entering terminal `DISCONNECTED` state.

### 10.2 Stale Data Evaluation
If the connection is `CONNECTED` but no telemetry frame is received within **1,500 ms** (15 frame intervals):
- Telemetry freshness transitions from `LIVE` to `STALE`.
- The HUD displays the amber `STALE` indicator.
- Last-known sensor values are preserved; **no synthetic replacement telemetry is fabricated**.

---

## 11. Security & Pre-Production Status

> [!WARNING]
> **Authentication Disclosure**:  
> In compliance with Phase 4 scope, **WebSocket authentication (JWT / OAuth2 / API Keys) is NOT implemented in prototype Phase 4** and is formally scheduled as a pre-production requirement.  
> The endpoint enforces strict origin validation (`CORSMiddleware`), connection limits ($50$), message size ceilings ($64\text{ KB}$), and safe error sanitization.
