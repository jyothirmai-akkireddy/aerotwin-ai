"""Simulator throughput benchmarks.

NOTE ON PERFORMANCE TARGETS:
Sub-millisecond pipeline latency is designated strictly as a TARGET for the full
telemetry -> Digital Twin -> diagnostic inference pipeline in future phases.
In Phase 2, this benchmark measures generator throughput (samples/sec) and
per-sample generation time in simulation clock.
"""

import time

from app.domain.simulation.scenarios import SCENARIO_CRUISE
from app.infrastructure.simulation.engine_simulator import EngineSimulator


def test_simulator_generation_throughput():
    """Measure single-thread frame generation rate and per-sample compute time."""
    sim = EngineSimulator(telemetry_rate_hz=10)
    sample_count = 5000
    cruise_phase = SCENARIO_CRUISE.phases[0]

    # Warm-up (100 steps)
    for _ in range(100):
        sim.step(cruise_phase)

    # Benchmark loop
    t0 = time.perf_counter()
    for _ in range(sample_count):
        sim.step(cruise_phase)
    elapsed_sec = time.perf_counter() - t0

    throughput_hz = sample_count / elapsed_sec
    mean_us = (elapsed_sec / sample_count) * 1_000_000

    print(
        f"\n[BENCHMARK] Generated {sample_count} frames in {elapsed_sec:.4f}s: "
        f"{throughput_hz:.1f} samples/sec ({mean_us:.2f} µs/sample)"
    )

    # Simulator must comfortably generate at least 1,000 samples/sec (100x nominal 10 Hz rate)
    assert throughput_hz >= 1000.0, (
        f"Throughput {throughput_hz:.1f} samples/sec fell below 1000 threshold"
    )
