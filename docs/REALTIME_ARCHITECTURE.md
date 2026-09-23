# AeroTwin AI — Realtime Transport Architecture & Decoupling Guide

**Subsystem**: Realtime Telemetry Synchronization & Ground Station Pipeline  
**Phase**: Phase 4  
**Status**: APPROVED & IMPLEMENTED  

---

## 1. Architectural Pipeline Overview

The AeroTwin AI real-time architecture connects the deterministic domain engine simulator with the interactive 3D Digital Twin and tactical HUD via a clean, layered pipeline:

```
[ Domain EngineSimulator ]  (Zero network knowledge, deterministic dt)
           │
           ▼
[ ITelemetrySource Port ]  (SyntheticTelemetrySource / Future CAN Adapter)
           │
           ▼
[ RealtimeTelemetryService ]  (Application Service: rate pacing, async loop, validation)
           │
           ▼
[ WebSocketBroadcastManager ]  (Infrastructure: bounded queues, client fan-out, backpressure)
           │
      WebSocket (v1.0.0 JSON Protocol @ 10 Hz)
           │
           ▼
[ WebSocketClient.ts ]  (Frontend Service: reconnect backoff, sequence gap detection, stale tracking)
           │
           ▼
[ Message Validator ]  (Type-safe runtime boundary guard)
           │
           ▼
[ Zustand useTwinStore ]  (Application state, bounded 300-frame ring buffer)
      ┌────┴────┐
      ▼         ▼
  [ TwinHud ]  [ EngineScene (3D Twin) ]
```

---

## 2. Decoupling Rationale: Why the Simulator is NOT Coupled to WebSockets

A common architectural anti-pattern in prototype digital twins is directly embedding socket emission inside the physics loop:

```python
# ANTI-PATTERN (STRICTLY FORBIDDEN IN AEROTWIN AI)
class BadEngineSimulator:
    def step(self):
        # calculate physics...
        websocket.send_json(self.state)  # VIOLATION: Couples physics to transport!
```

In AeroTwin AI, the `EngineSimulator` remains **100% network-agnostic and deterministic**:
1. **Network Independence**: The simulator can be executed in offline batch simulations, headless machine learning training pipelines, or unit tests without an active HTTP/WebSocket server or event loop.
2. **Timing Determinism**: Network jitter, slow TCP windowing, or lagging browser clients cannot stall or distort the differential equations governing engine thermodynamics and rotational mechanics.
3. **Pluggable Transports**: In future phases (e.g. Phase 8 mission replay or physical UAV test benches), the telemetry stream can be piped through CAN bus drivers, ZeroMQ, or Kafka without modifying a single line of simulator code.
4. **Clean Architecture Adherence**: Domain entities (`TelemetryFrame`, `EngineState`) and domain logic (`EngineSimulator`, `TelemetryValidator`) never import FastAPI, Starlette, or WebSockets.

---

## 3. Asynchronous Loop & Rate Control

The `RealtimeTelemetryService` coordinates frame publication using high-resolution monotonic time (`time.perf_counter()`):

$$\Delta t_{\text{target}} = \frac{1}{\text{rate\_hz}} = \frac{1}{10} = 0.100\text{ s}$$

$$\text{sleep\_time} = \max\left(0.0, \Delta t_{\text{target}} - (\tau_{\text{end}} - \tau_{\text{start}})\right)$$

This compensation dynamically absorbs small computational delays in frame generation or validation, guaranteeing jitter-free 10 Hz delivery without CPU-spinning busy waits.

---

## 4. Broadcast Fan-Out & Backpressure Strategy

### 4.1 Single Simulator, Multiple Viewers
AeroTwin AI executes a **single authoritative engine simulation**. Multiple connected ground station operators (flight engineers, telemetry analysts, maintenance supervisors) all observe the exact same authoritative flight sequence:

$$\text{Simulator} \longrightarrow \text{BroadcastManager} \longrightarrow \{\text{Client}_1, \text{Client}_2, \dots, \text{Client}_n\}$$

### 4.2 Bounded Queues & Latest-Value Eviction
- Unbounded queues cause catastrophic memory leaks when a client throttles or pauses background tabs.
- AeroTwin AI assigns an isolated bounded queue (`maxsize=100`) to every client session.
- If a client queue becomes full, the **latest-value drop policy** evicts the oldest pending frame (`queue.get_nowait()`) and enqueues the fresh frame. Stale historical frames are discarded; live telemetry remains immediate.

---

## 5. Frontend Decoupling: Pure Service Layer to Zustand State

1. **`WebSocketClient.ts`**: Pure TypeScript service class that contains zero React hooks, JSX, or DOM dependencies.
2. **State Store Ingestion**: Incoming validated messages enter `useTwinStore.handleIncomingTelemetry(msg)`, which:
   - Updates active scalar meters (RPM, MAP, oil pressure, fuel flow, vibration).
   - Maps 4-cylinder CHT and EGT arrays directly to the thermal shader inputs.
   - Pushes snapshots to a bounded 300-sample history buffer for live telemetry trending.
   - Updates sequence ID and evaluates transmission continuity.
3. **3D Twin Rendering**: The React Three Fiber scene components (`CrankshaftAssembly`, `PistonAssembly`, `CylinderAssembly`) consume state from Zustand; they have zero direct awareness of WebSocket networking.
