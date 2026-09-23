"""Benchmark measuring disaggregated per-frame execution latency for ML inference pipeline."""

import numpy as np

from app.application.services.ml_service import MLInferenceService
from app.application.services.physics_twin_service import PhysicsTwinService
from app.infrastructure.simulation.engine_simulator import EngineSimulator


def test_ml_pipeline_disaggregated_latency_benchmark():
    """Benchmark per-frame ML inference across 1,000 consecutive simulated frames.

    Disaggregates:
    - t_feat: Feature extraction (24D deterministic mapping)
    - t_anom: Unsupervised Isolation Forest anomaly scoring
    - t_class: Supervised multi-class fault classification (XGBoost)
    - t_xai: Explainability and top-4 attribution engine
    - t_total: End-to-end ML inference latency

    Budget: < 100.0 ms (10 Hz publication tick). Target: < 20.0 ms.
    """
    simulator = EngineSimulator()
    physics_service = PhysicsTwinService()
    ml_service = MLInferenceService()

    assert ml_service.is_ready, "MLInferenceService models must be loaded for benchmark"

    # Pre-generate 1,000 frames and physics states
    frames_with_physics = []
    for _ in range(1000):
        frame = simulator.step()
        phys = physics_service.evaluate_frame(frame)
        frames_with_physics.append((frame, phys))

    # Warmup
    for f, p in frames_with_physics[:25]:
        ml_service.evaluate(f, p)

    t_feat_list: list[float] = []
    t_anom_list: list[float] = []
    t_class_list: list[float] = []
    t_xai_list: list[float] = []
    t_total_list: list[float] = []

    for f, p in frames_with_physics[25:]:
        res = ml_service.evaluate(f, p)
        disagg = res.disaggregated_latencies
        t_feat_list.append(disagg.get("feature_extraction_ms", 0.0))
        t_anom_list.append(disagg.get("anomaly_detection_ms", 0.0))
        t_class_list.append(disagg.get("fault_classification_ms", 0.0))
        t_xai_list.append(disagg.get("explainability_ms", 0.0))
        t_total_list.append(res.inference_latency_ms)

    def stats(vals: list[float]) -> tuple[float, float, float]:
        arr = sorted(vals)
        mean_v = float(np.mean(arr))
        p95_v = float(np.percentile(arr, 95))
        max_v = float(np.max(arr))
        return mean_v, p95_v, max_v

    mean_feat, p95_feat, max_feat = stats(t_feat_list)
    mean_anom, p95_anom, max_anom = stats(t_anom_list)
    mean_class, p95_class, max_class = stats(t_class_list)
    mean_xai, p95_xai, max_xai = stats(t_xai_list)
    mean_tot, p95_tot, max_tot = stats(t_total_list)

    print(
        f"\n========================================================"
        f"\n[PHASE 6 ML DISAGGREGATED LATENCY BENCHMARK]"
        f"\nEvaluated {len(t_total_list)} frames (10 Hz budget = 100.0 ms):"
        f"\n  - Feature Extraction (t_feat): Mean={mean_feat:.4f} ms, P95={p95_feat:.4f} ms, Max={max_feat:.4f} ms"
        f"\n  - Anomaly Detection (t_anom):  Mean={mean_anom:.4f} ms, P95={p95_anom:.4f} ms, Max={max_anom:.4f} ms"
        f"\n  - Fault Classify (t_class):    Mean={mean_class:.4f} ms, P95={p95_class:.4f} ms, Max={max_class:.4f} ms"
        f"\n  - Explainability XAI (t_xai):  Mean={mean_xai:.4f} ms, P95={p95_xai:.4f} ms, Max={max_xai:.4f} ms"
        f"\n  ------------------------------------------------------"
        f"\n  - TOTAL PIPELINE (t_ML,total): Mean={mean_tot:.4f} ms, P95={p95_tot:.4f} ms, Max={max_tot:.4f} ms"
        f"\n========================================================"
    )

    # Invariants:
    # 1. Total average pipeline latency must be < 25 ms (well within 100 ms tick)
    assert mean_tot < 25.0, (
        f"Average ML pipeline latency {mean_tot:.3f} ms exceeded 25.0 ms threshold"
    )
    # 2. P95 total latency must be < 50 ms
    assert p95_tot < 50.0, f"P95 ML pipeline latency {p95_tot:.3f} ms exceeded 50.0 ms threshold"
    # 3. Feature extraction must be < 0.2 ms
    assert mean_feat < 0.2, f"Feature extraction {mean_feat:.3f} ms exceeded 0.2 ms threshold"
    # 4. Explainability must be < 0.5 ms
    assert mean_xai < 0.5, f"Explainability {mean_xai:.3f} ms exceeded 0.5 ms threshold"
