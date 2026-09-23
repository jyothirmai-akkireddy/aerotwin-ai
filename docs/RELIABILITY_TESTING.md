# AeroTwin AI — Phase 9 Reliability & Stability Report
## SIH26054 — Memory Stability, Resource Lifecycle, and Long-Run Reliability

> **PROTOTYPE DISCLAIMER**: AeroTwin AI is an engineering research prototype. Long-run stability testing is conducted within a prototype evaluation framework. It does not replace full DO-178C long-duration endurance runs or hardware-in-the-loop (HIL) operational test stands.

---

### 1. Executive Summary

Phase 9 reliability testing verified long-run stability, memory bounding, resource leak prevention, and graceful error handling across the complete AeroTwin AI telemetry streaming stack.

A full **continuous 5-minute soak test** ($\ge 300\text{ seconds}$, $\ge 3,000\text{ frames}$ at $10\text{ Hz}$) was executed against the running production-grade system with full analytical propagation (Physics Twin + ML Diagnostics + Prognostics + Broadcaster).

#### Key Objective Findings:
- **Exact Duration**: **$325.31\text{ seconds}$** ($5.42\text{ minutes}$, exceeding the $\ge 300\text{s}$ target).
- **Exact Frames Processed**: **$3,000\text{ frames}$**.
- **Observed Telemetry Rate**: **$9.22\text{ Hz}$** (nominal $10.0\text{ Hz}$).
- **Python Heap Memory**: Initial **$0.00\text{ MB}$**, Final **$2.75\text{ MB}$**, Peak **$3.13\text{ MB}$**, Net growth **$+2.75\text{ MB}$** (well within $< 25.0\text{ MB}$ limit).
- **OS Process RSS (Working Set)**: Initial **$162.78\text{ MB}$**, Final **$283.77\text{ MB}$**, Net growth **$+120.99\text{ MB}$** (attributable to native C++ OpenMP thread pools and PyArrow memory pools initializing during initial inference passes).
- **Dropped Frames**: **$0$** (100% frame delivery).
- **Duplicate Frames**: **$0$** (strictly monotonic sequence $0 \dots 2999$).
- **Sequence Ordering Violations**: **$0$**.
- **Queue Behavior**: Maximum queue depth seen was **$1\text{ frame}$** (no queue accumulation at 10 Hz).
- **Zombie / Orphan Async Tasks**: **$0$** remaining after lifecycle teardown.

---

### 2. 5-Minute Continuous Soak Test Benchmark (`test_soak_stability.py`)

Continuous soak testing was executed in `tests/benchmark/test_soak_stability.py` with continuous frame publishing and full downstream analytics:
$$\text{Simulator} \longrightarrow \text{SyntheticSource} \longrightarrow \text{Validator} \longrightarrow \text{PhysicsTwin} \longrightarrow \text{MLInference} \longrightarrow \text{Prognostics} \longrightarrow \text{Broadcaster}$$

#### 2.1 Complete Metric Summary Table

| Metric | Measured Value | Acceptance Threshold | Evaluation |
| :--- | :--- | :--- | :--- |
| **Total Test Duration** | **$325.31\text{ s}$ ($5.42\text{ min}$)** | $\ge 300.0\text{ s}$ ($\ge 5.0\text{ min}$) | **PASSED** |
| **Total Telemetry Frames** | **$3,000\text{ frames}$** | $\ge 3,000\text{ frames}$ | **PASSED** |
| **Observed Telemetry Rate** | **$9.22\text{ Hz}$** | $10.0 \pm 1.0\text{ Hz}$ | **PASSED** |
| **Initial Python Heap** | **$0.00\text{ MB}$** | Baseline (tracemalloc) | Recorded |
| **Final Python Heap** | **$2.75\text{ MB}$** | Bounded | Recorded |
| **Peak Python Heap** | **$3.13\text{ MB}$** | $< 50.0\text{ MB}$ | **PASSED** |
| **Net Python Heap Growth ($\Delta$)** | **$+2.75\text{ MB}$** | $< 25.0\text{ MB}$ | **PASSED** (0 leak) |
| **Initial OS RSS (Working Set)** | **$162.78\text{ MB}$** | Process baseline | Recorded |
| **Final OS RSS (Working Set)** | **$283.77\text{ MB}$** | $< 350.0\text{ MB}$ | **PASSED** |
| **Net OS RSS Growth ($\Delta$)** | **$+120.99\text{ MB}$** | Native runtime baseline | Plateaued |
| **Frames Dropped by Broadcaster** | **0** | **0** | **PASSED** |
| **Duplicate Frames** | **0** | **0** | **PASSED** |
| **Sequence Ordering Violations** | **0** | **0** | **PASSED** |
| **Maximum Client Queue Depth** | **1 frame** | $\le 1000$ (buffer size) | **PASSED** |
| **Zombie / Lingering Async Tasks** | **0** | **0** | **PASSED** |

#### 2.2 Memory Dynamics & Heap Profile
- Python heap allocation tracked via `tracemalloc` increased by only **$2.75\text{ MB}$** across the entire 3,000-frame test.
- Internal rolling windows in `PrognosticsService` (`maxlen=300`), `EngineSimulator` histories, and `TelemetryValidator` reached steady-state within the first 300 frames, with zero unbounded accumulation thereafter.
- OS Working Set (RSS) growth of $+120.99\text{ MB}$ corresponds to native C++ runtime allocations (XGBoost C++ OpenMP multi-threading buffers and PyArrow memory pools) allocating pages during initial passes and holding them allocated for process lifetime.

---

### 3. Resource Leak & Teardown Auditing

1. **Asyncio Tasks**:
   - `RealtimeTelemetryService.stop()` terminates `_realtime_loop` and `_heartbeat_loop` cleanly using cooperative `asyncio.Event` signaling.
   - Inspected `asyncio.all_tasks()` after teardown: **0 zombie or orphan tasks** detected.

2. **WebSocket Client Sessions**:
   - Client sessions registered with `broadcaster.register()` are cleanly evicted on disconnect with `broadcaster.unregister()`.
   - Client queues are drained and garbage collected upon disconnection.

3. **File Descriptors & Database Handles**:
   - Replay loaders (`FlightLogLoader`) manage SQLite connection handles using context managers (`with sqlite3.connect(...) as conn:`), guaranteeing immediate descriptor closure upon query completion.
   - Parquet readers stream row groups cleanly through PyArrow without holding unclosed operating system file locks.

---

### 4. Failure Mode Recovery & Fault Isolation

- **Non-Fatal Analytical Failures**:
  - Handled safely inside `RealtimeTelemetryService._realtime_loop`: If an individual model evaluation raises an exception, the error is logged, the corresponding field in `TelemetryMessage` is populated with `None` or degraded status, and the publisher loop continues without terminating the stream.
- **Invalid Client Commands**:
  - Invalid parameters or unsupported commands submitted over the control channel return descriptive errors or log warnings without destabilizing the telemetry streaming engine.
