"""Benchmark measuring actual per-frame execution latency for the Physics Twin."""

import time

from app.application.services.physics_twin_service import PhysicsTwinService
from app.infrastructure.simulation.engine_simulator import EngineSimulator


def test_physics_evaluation_latency_benchmark():
    """Benchmark per-frame analytical physics compute time across 1,000 frames.

    Performance Target: < 1.0 ms average latency per frame.
    Measures and logs actual mean, P95, and maximum evaluation times.
    """
    simulator = EngineSimulator()
    service = PhysicsTwinService()

    # Pre-generate 1,000 frames to isolate physics compute from simulation compute
    frames = [simulator.step() for _ in range(1000)]

    latencies_ms: list[float] = []

    # Warmup
    for f in frames[:20]:
        service.evaluate_frame(f)

    # Benchmark loop
    for f in frames[20:]:
        t0 = time.perf_counter()
        service.evaluate_frame(f)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        latencies_ms.append(elapsed_ms)

    latencies_ms.sort()
    avg_latency = sum(latencies_ms) / len(latencies_ms)
    p95_latency = latencies_ms[int(0.95 * len(latencies_ms))]
    max_latency = max(latencies_ms)

    print(
        f"\n[PHYSICS BENCHMARK] Evaluated {len(latencies_ms)} frames:"
        f"\n  - Target:       < 1.000 ms"
        f"\n  - Measured Avg: {avg_latency:.4f} ms"
        f"\n  - Measured P95: {p95_latency:.4f} ms"
        f"\n  - Measured Max: {max_latency:.4f} ms"
    )

    # Invariant: Performance target < 1.0 ms
    assert avg_latency < 1.0, f"Average latency {avg_latency:.4f} ms exceeded 1.0 ms target"
    assert p95_latency < 2.0, f"P95 latency {p95_latency:.4f} ms exceeded 2.0 ms limit"
