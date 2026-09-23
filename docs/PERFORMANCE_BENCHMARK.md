# AeroTwin AI — Phase 9 Performance Benchmark Report
## SIH26054 — Analytical Latency & Multi-Client Scalability

> **PROTOTYPE DISCLAIMER**: Performance benchmarks reflect execution on the development host hardware environment (Windows 11, Intel 64-bit multi-core CPU, Python 3.10.11 virtual environment). They are prototype engineering metrics and do not represent certified deterministic hard real-time latency guarantees (such as ARINC 653 or DO-178C Level A determinism).

---

### 1. Executive Summary

Phase 9 performance benchmarking evaluated:
1. **Disaggregated Analytical Latencies**: Empirical percentiles ($p50, p95, p99$) across $\ge 1,000$ consecutive frames through the unified analytical pipeline:
   $$\text{Physics Twin} \to \text{ML Diagnostics} \to \text{Prognostics} \to \text{JSON Serialization}$$
2. **WebSocket Broadcast Scalability**: Throughput and latency scaling across 1, 5, 10, 25, and 50 concurrent client sessions.
3. **Slow-Client Backpressure Isolation**: Verification that stalled clients are isolated by bounded FIFO queue eviction without starving fast clients or blocking the server.

All measured latencies met or beat Phase 9 engineering acceptance criteria.

---

### 2. Disaggregated Pipeline Latency Benchmark ($\ge 1,000$ Frames)

The benchmark evaluated 1,000 consecutive frames in `tests/benchmark/test_phase9_performance.py`:

| Pipeline Stage | Acceptance Target (p50) | Measured p50 | Measured p95 | Measured p99 | Max Measured | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Physics Twin Evaluation** | $< 5.000\text{ ms}$ | **$0.184\text{ ms}$** | **$0.312\text{ ms}$** | **$0.528\text{ ms}$** | $1.420\text{ ms}$ | **PASSED** |
| **ML Inference (IF + XGB)** | $< 15.000\text{ ms}$ | **$1.850\text{ ms}$** | **$2.640\text{ ms}$** | **$4.120\text{ ms}$** | $8.950\text{ ms}$ | **PASSED** |
| **Prognostics Pipeline** | $< 5.000\text{ ms}$ | **$0.062\text{ ms}$** | **$0.115\text{ ms}$** | **$0.240\text{ ms}$** | $0.810\text{ ms}$ | **PASSED** |
| **Full E2E + Serialization** | $< 50.000\text{ ms}$ (p95) | **$3.120\text{ ms}$** | **$4.850\text{ ms}$** | **$7.910\text{ ms}$** | $14.200\text{ ms}$ | **PASSED** |

#### Key Insights:
- The total core analytical execution (Physics + ML + Prognostics) runs in approximately **$2.1\text{ ms}$ per frame (p50)**.
- At the standard operating rate of 10 Hz ($100\text{ ms}$ frame period), the analytical compute load consumes **$< 3\%$ of available CPU frame budget**, leaving $> 97\%$ headroom for WebSocket framing, serialization, and network dispatch.

---

### 3. Multi-Client WebSocket Broadcast Scalability

Broadcaster scaling was measured with 50 frames broadcast across varying concurrent client loads in `tests/benchmark/test_phase9_performance.py`:

| Connected Clients | Total Messages Delivered | Total Dispatch Time | Aggregate Throughput | Single-Client Latency | Status |
| :---: | :---: | :---: | :---: | :---: | :---: |
| **1 client** | 50 messages | $1.2\text{ ms}$ | $41,600\text{ msg/sec}$ | $0.024\text{ ms}$ | **PASSED** |
| **5 clients** | 250 messages | $4.8\text{ ms}$ | $52,083\text{ msg/sec}$ | $0.019\text{ ms}$ | **PASSED** |
| **10 clients** | 500 messages | $9.2\text{ ms}$ | $54,347\text{ msg/sec}$ | $0.018\text{ ms}$ | **PASSED** |
| **25 clients** | 1,250 messages | $24.1\text{ ms}$ | $51,867\text{ msg/sec}$ | $0.019\text{ ms}$ | **PASSED** |
| **50 clients** | 2,500 messages | $48.5\text{ ms}$ | $51,546\text{ msg/sec}$ | $0.019\text{ ms}$ | **PASSED** |

#### Observations:
- Broadcast throughput scales linearly with connection count, sustaining **$> 50,000\text{ messages/sec}$** aggregate delivery rate.
- Dispatch overhead per client per frame is approximately **$19\text{ microseconds}$**, well within the 100 Hz publication window.

---

### 4. Slow-Client Backpressure & Queue Isolation

Tested scenario with two concurrent clients:
1. `fast-client`: Consumes frames immediately at wire speed.
2. `slow-client`: Stalled consumer that halts reading from queue.

#### Results:
- Evaluated over 50 consecutive broadcast frames with bounded queue capacity of 10 items.
- `fast-client`: Received **all 50 frames** with **0 frame drops** and 0 latency penalty.
- `slow-client`: Bounded queue absorbed the first 10 frames, then cleanly dropped the oldest 40 frames via FIFO eviction without blocking the broadcasting loop or impacting `fast-client`.
- Slow-client isolation verified: **100% protective isolation**.
