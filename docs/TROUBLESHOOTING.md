# AeroTwin AI — Troubleshooting & Incident Recovery Guide
**SIH26054 — Operational Diagnostics, Defect Mitigation, and Fast-Recovery Workflows**

> [!IMPORTANT]
> **PROTOTYPE RESEARCH DISCLAIMER**  
> AeroTwin AI is an engineering research prototype developed for SIH26054 based on a generic 4-cylinder horizontally-opposed turbocharged aero-piston engine (Rotax 914/915 iS class). All telemetry logs, degradation baselines, and fault scenarios represent synthetic engineering models.

---

## 1. Fast Presentation Recovery (Under 10 Seconds)

If any unexpected UI state, freeze, or anomalous telemetry behavior occurs during an active evaluation:

1. **Trigger Safe Demo Reset:**
   - Click the **Reset Twin** button in the persistent top header (or on the Ground Station overview).
   - This invokes the backend 6-step lifecycle reset (`realtime_service.reset()`), clearing physics thermal history, zeroing prognostics wear buffers, resetting the PRNG seed, and resetting client store states.
2. **If Stream Remains Stale:**
   - Press `F5` in the browser. The frontend reconnects automatically to the backend WebSocket within 250 ms.
3. **If Backend Has Terminated:**
   - Relaunch via `.\scripts\start_demo.ps1` or run `uvicorn app.main:app --port 8000` in the backend terminal.

---

## 2. Common Operational Issues & Mitigations

### 2.1 Port Conflicts (Port 8000 or 5173 Already in Use)
**Symptom:** Backend fails to bind (`[Errno 10048] error while attempting to bind on address ('127.0.0.1', 8000)`).  
**Cause:** A zombie Python process or previous uvicorn instance is holding port 8000.  
**Resolution:**
```powershell
# Find and terminate process on port 8000 (Windows PowerShell):
Get-Process -Id (Get-NetTCPConnection -LocalPort 8000).OwningProcess | Stop-Process -Force

# Find and terminate process on port 5173:
Get-Process -Id (Get-NetTCPConnection -LocalPort 5173).OwningProcess | Stop-Process -Force
```

### 2.2 WebSocket Connection Drops / Status "DISCONNECTED"
**Symptom:** Status pill indicates `DISCONNECTED` or `STALE`, charts stop scrolling.  
**Cause:** Backend was restarted or network interface experienced an IP route reset.  
**Resolution:**
- The frontend `WebSocketClient` features exponential backoff reconnection (`initial_delay_ms=500`, `max_delay_ms=5000`, `jitter_factor=0.2`).
- To force an immediate reconnection, click the **Refresh** icon in the header.
- Verify backend is alive:
  ```powershell
  curl http://localhost:8000/api/v1/health
  ```

### 2.3 WebGL Context Loss / Black 3D Canvas
**Symptom:** The 3D Digital Twin viewport renders black or displays `"WebGL context lost"`.  
**Cause:** Operating system GPU power throttling, sleep state resume, or driver crash.  
**Resolution:**
- AeroTwin AI implements an automatic `WebGLFallback` component wrapped in a React `ErrorBoundary`.
- Click the **"Restore 3D Scene"** button rendered by the fallback overlay.
- If persistent, hardware acceleration can be verified in Chrome/Edge via `chrome://gpu`.

### 2.4 Replay Speed Contract Rejection (HTTP 400)
**Symptom:** REST endpoint `/api/v1/replay/control` returns `400 Bad Request`.  
**Cause:** Attempting to set an unauthorized speed (such as `0.25x` or `"MAX"`).  
**Resolution:**
- The approved Phase 8/9 speed contract strictly permits:
  - `REALTIME`: `1.0x`
  - `ACCELERATED`: strictly `0.5x, 1.0x, 2.0x, 5.0x, 10.0x`
  - `OFFLINE_BATCH`: unpaced unbuffered execution
- Use only the approved speed buttons in the UI scrubber deck.

### 2.5 RUL Displays "RUL UNAVAILABLE"
**Symptom:** The operator expects an RUL number, but the card displays `"RUL UNAVAILABLE"`.  
**Cause:** This is an intentional engineering invariant, not a bug! In nominal flight, health degradation has not been detected ($HI \ge 0.90$ with zero negative wear trend). Fabricating an RUL number on a healthy engine is mathematically ungrounded.  
**Resolution:**
- Introduce an active fault scenario (e.g., `OIL_PRESSURE_BIAS` or `OIL_TEMP_DRIFT`) via the Twin Dev Adapter or Mission Sim.
- Once degradation initiates ($dH/dt < -0.0001\text{ /s}$), RUL will dynamically activate with a bounded 95% prediction interval.

---

## 3. Diagnostic & Inspection Commands

### 3.1 Inspecting Active Telemetry Payloads
```powershell
# Query current live telemetry snapshot via REST:
curl http://localhost:8000/api/v1/simulation/state

# Query active physics residuals:
curl http://localhost:8000/api/v1/physics/current

# Query active ML diagnostic inference:
curl http://localhost:8000/api/v1/ml/current

# Query active prognostics and degradation status:
curl http://localhost:8000/api/v1/prognostics/current
```

### 3.2 Checking Subsystem Readiness
```powershell
curl http://localhost:8000/api/v1/ready
```
Expected output:
```json
{
  "status": "ready",
  "components": {
    "engine_simulator": "READY",
    "physics_twin": "READY",
    "ml_diagnostics": "READY",
    "prognostics": "READY",
    "mission_simulator": "READY",
    "flight_replay": "READY"
  }
}
```

---

## 4. Log Inspection & Debugging

- **Backend Log Output:** Formatted with timestamps, module names, log levels, and request correlation IDs (`request_id`). Check terminal stdout.
- **Frontend Log Output:** Open browser Developer Tools (`F12`), navigate to the **Console** tab. Look for WebSocket frame sequence IDs and client events.
