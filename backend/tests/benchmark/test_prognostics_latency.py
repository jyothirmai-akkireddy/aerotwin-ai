"""Prognostics pipeline latency benchmark evaluating >= 1,000 consecutive iterations."""

import time

import numpy as np

from app.application.services.ml_service import MLInferenceService
from app.application.services.physics_twin_service import PhysicsTwinService
from app.application.services.prognostics_service import PrognosticsService
from app.infrastructure.simulation.engine_simulator import EngineSimulator
from app.infrastructure.simulation.noise import DeterministicNoiseGenerator


def test_prognostics_pipeline_latency_benchmark():
    """Benchmark full prognostics pipeline across >= 1,000 consecutive frames.

    Target: Mean latency < 5.0 ms (acceptance criterion).
    """
    sim = EngineSimulator(
        noise_generator=DeterministicNoiseGenerator(seed=42),
        telemetry_rate_hz=10,
    )
    physics_service = PhysicsTwinService()
    ml_service = MLInferenceService()
    prognostics_service = PrognosticsService()

    # Warmup (100 frames)
    for _ in range(100):
        frame = sim.step()
        phys = physics_service.evaluate_frame(frame)
        ml = ml_service.evaluate(frame, phys)
        prognostics_service.evaluate(frame, phys, ml)

    iterations = 1000
    latencies = []
    hi_latencies = []
    trend_latencies = []
    rul_latencies = []

    for _ in range(iterations):
        frame = sim.step()
        phys = physics_service.evaluate_frame(frame)
        ml = ml_service.evaluate(frame, phys)

        t0 = time.perf_counter()
        res = prognostics_service.evaluate(frame, phys, ml)
        dt_ms = (time.perf_counter() - t0) * 1000.0

        latencies.append(dt_ms)
        hi_latencies.append(res.disaggregated_latencies.get("health_index_ms", 0.0))
        trend_latencies.append(res.disaggregated_latencies.get("trend_analysis_ms", 0.0))
        rul_latencies.append(res.disaggregated_latencies.get("rul_estimation_ms", 0.0))

    latencies_arr = np.array(latencies)
    mean_lat = float(np.mean(latencies_arr))
    p50_lat = float(np.percentile(latencies_arr, 50))
    p95_lat = float(np.percentile(latencies_arr, 95))
    p99_lat = float(np.percentile(latencies_arr, 99))
    max_lat = float(np.max(latencies_arr))

    mean_hi = float(np.mean(hi_latencies))
    mean_trend = float(np.mean(trend_latencies))
    mean_rul = float(np.mean(rul_latencies))

    print("\n=================================================================")
    print(f"PROGNOSTICS PIPELINE LATENCY BENCHMARK ({iterations} ITERATIONS)")
    print("=================================================================")
    print(f"Mean Total Pipeline Latency:       {mean_lat:.3f} ms (Target: < 5.0 ms)")
    print(f"Median (P50) Latency:              {p50_lat:.3f} ms")
    print(f"95th Percentile (P95) Latency:     {p95_lat:.3f} ms")
    print(f"99th Percentile (P99) Latency:     {p99_lat:.3f} ms")
    print(f"Maximum Latency:                   {max_lat:.3f} ms")
    print("-----------------------------------------------------------------")
    print("Disaggregated Breakdown (Means):")
    print(f"  Health Index & Subsystems:       {mean_hi:.3f} ms")
    print(f"  Causal Trend & Buffering:        {mean_trend:.3f} ms")
    print(f"  RUL Quantile Inference:          {mean_rul:.3f} ms")
    print("=================================================================")

    # Acceptance Criterion
    assert mean_lat < 5.0, f"Mean latency {mean_lat:.3f} ms exceeded 5.0 ms acceptance target!"
