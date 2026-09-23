"""Synthetic Benchmark Dataset Generation Script for Engine Prognostics (Phase 7).

IMPORTANT DISCLAIMER:
The degradation equations in this script constitute a synthetic benchmark generator
designed specifically to produce controlled, reproducible, stress-correlated
run-to-failure trajectories for algorithmic testing. They are NOT physical models
of metallurgical fatigue, tribological wear, or certified engine lifing for
Rotax or any real aero engine.

Splits:
- Train Split: Runs 101–150 (Seeds 10101–10150)
- Val Split:   Runs 151–170 (Seeds 10151–10170)
- Test Split:  Runs 171–190 (Seeds 10171–10190)
"""

import json
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.application.services.physics_twin_service import PhysicsTwinService
from app.domain.ml.models import (
    AnomalyInferenceResult,
    AnomalyStatus,
    DecisionReason,
    FaultCategory,
    FaultInferenceResult,
    MLInferenceResult,
)
from app.domain.prognostics.features import (
    PROGNOSTIC_FEATURE_SCHEMA_VERSION,
    CausalTelemetryBuffer,
    PrognosticFeatureExtractor,
)
from app.domain.prognostics.health_index import HealthIndexCalculator
from app.infrastructure.simulation.engine_simulator import EngineSimulator
from app.infrastructure.simulation.noise import DeterministicNoiseGenerator

OUTPUT_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../data/processed/prognostics")
)


def generate_benchmark_trajectory(
    run_id: int,
    seed: int,
    physics_service: PhysicsTwinService,
    hi_calc: HealthIndexCalculator,
    extractor: PrognosticFeatureExtractor,
) -> list[dict[str, float]]:
    """Simulate a single run-to-failure benchmark trajectory with seed isolation."""
    rng = np.random.default_rng(seed)

    # Benchmark parameterization
    nominal_duration_sec = rng.uniform(150.0, 300.0)
    exponent_k = rng.uniform(1.2, 1.8)
    initial_wear = rng.uniform(0.0, 0.05)

    # Primary simulated degradation axis for this run
    deg_mode = rng.choice(["oil_loss", "thermal_imbalance", "turbo_loss", "vibration_growth"])

    # Target simulated full flight life (5.0 to 40.0 hours)
    simulated_life_hours = rng.uniform(5.0, 40.0)

    # Initialize components
    noise_gen = DeterministicNoiseGenerator(seed=seed)
    sim = EngineSimulator(noise_generator=noise_gen, telemetry_rate_hz=10)
    buffer = CausalTelemetryBuffer(max_capacity=300)

    records: list[dict[str, float]] = []

    # Run discrete trajectory steps (sample at 2 Hz = 0.5s step to capture causal dynamics efficiently)
    step_dt = 0.5
    total_steps = int(nominal_duration_sec / step_dt)

    for step in range(total_steps):
        t_elapsed = step * step_dt
        tau = min(1.0, t_elapsed / nominal_duration_sec)

        # Benchmark wear equation: w(t) = w0 + alpha * tau + beta * tau^k
        wear = initial_wear + 0.3 * tau + 0.65 * (tau**exponent_k)
        wear = min(1.0, wear + rng.normal(0.0, 0.005))

        # Ground truth Remaining Useful Life in simulated flight hours
        remaining_fraction = max(0.0, 1.0 - wear)
        true_rul_hours = round(simulated_life_hours * remaining_fraction, 3)

        # Step underlying simulator to get baseline telemetry
        frame = sim.step()

        # Inject physical benchmark degradation matching the wear progression
        if deg_mode == "oil_loss":
            # Pressure drops by up to 2.2 bar, temperature rises by up to 28 °C
            frame.oil_pressure = max(0.5, frame.oil_pressure - 2.2 * wear)
            frame.oil_temperature = frame.oil_temperature + 28.0 * wear
        elif deg_mode == "thermal_imbalance":
            # Cylinder 3 runs hotter by up to 35 °C, expanding CHT spread
            c1, c2, c3, c4 = frame.cht
            frame.cht = (c1, c2, c3 + 35.0 * wear, c4)
        elif deg_mode == "turbo_loss":
            # Manifold pressure deficit up to 8 inHg
            frame.manifold_pressure = max(15.0, frame.manifold_pressure - 8.0 * wear)
        elif deg_mode == "vibration_growth":
            # Vibration increases by up to 3.5 g
            frame.vibration_rms = frame.vibration_rms + 3.5 * wear

        # Evaluate Phase 5 physics residuals
        physics_res = physics_service.evaluate_frame(frame)

        # Mock ML inference result matching anomaly severity
        anom_score = min(1.0, max(0.1, wear * 0.95 + rng.normal(0.0, 0.02)))
        anom_flag = anom_score > 0.5402
        ml_res = MLInferenceResult(
            timestamp=frame.timestamp,
            sequence_id=frame.sequence_id,
            anomaly=AnomalyInferenceResult(
                flag=anom_flag,
                status=AnomalyStatus.ANOMALOUS if anom_flag else AnomalyStatus.NORMAL,
                score=round(anom_score, 4),
                raw_score=round(anom_score - 0.5402, 4),
                confidence=0.92,
            ),
            fault=FaultInferenceResult(
                fault_class=FaultCategory.NORMAL,
                reason=DecisionReason.NOMINAL_FLIGHT,
                confidence=0.90,
            ),
            inference_latency_ms=3.5,
        )

        # Compute Health Index and 3-tier metrics
        hi, deg_state, subsystems, val_flag = hi_calc.calculate(frame, physics_res, ml_res)

        # Maintain causal buffer
        buffer_entry = {
            "timestamp": frame.timestamp,
            "health_index": hi,
            "rpm": frame.rpm,
            "manifold_pressure": frame.manifold_pressure,
            "oil_pressure": frame.oil_pressure,
            "oil_temperature": frame.oil_temperature,
            "cht_mean": sum(frame.cht) / len(frame.cht),
            "vibration_rms": frame.vibration_rms,
        }
        buffer.append(buffer_entry)

        # Only extract regression features when buffer has sufficient causal history (>= 30)
        if buffer.size >= 30:
            history = buffer.get_history()
            beta_slope, trend_dir = extractor.compute_trend_slope(history)
            stress_acc = extractor.compute_stress_accumulators(history)

            records.append(
                {
                    "run_id": run_id,
                    "seed": seed,
                    "step": step,
                    "timestamp": frame.timestamp,
                    "health_index": hi,
                    "beta_slope": beta_slope,
                    "subsystem_oil_norm": subsystems.lubrication.normalized_deviation,
                    "subsystem_therm_norm": subsystems.thermal.normalized_deviation,
                    "subsystem_turbo_norm": subsystems.turbocharger.normalized_deviation,
                    "subsystem_vib_norm": subsystems.rotational_vibration.normalized_deviation,
                    "cht_spread": max(frame.cht) - min(frame.cht),
                    "oil_temperature": frame.oil_temperature,
                    "oil_pressure": frame.oil_pressure,
                    "cum_thermal_stress": stress_acc[0],
                    "cum_map_stress": stress_acc[1],
                    "anom_score": anom_score,
                    "wear_benchmark": round(wear, 4),
                    "true_rul_hours": true_rul_hours,
                }
            )

        # Simulated failure termination condition
        if wear >= 1.0 or hi <= 0.25:
            break

    return records


def main() -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print("=================================================================")
    print("AeroTwin AI — Synthetic Prognostics Benchmark Dataset Generator")
    print("=================================================================")
    print("Target Directory:", OUTPUT_DIR)

    physics_service = PhysicsTwinService()
    hi_calc = HealthIndexCalculator()
    extractor = PrognosticFeatureExtractor()

    # Define isolated run IDs and seeds
    splits = {
        "train": [(run_id, 10000 + run_id) for run_id in range(101, 151)],  # 50 runs
        "val": [(run_id, 10000 + run_id) for run_id in range(151, 171)],  # 20 runs
        "test": [(run_id, 10000 + run_id) for run_id in range(171, 191)],  # 20 runs
    }

    manifest = {
        "generator_version": "1.0.0",
        "feature_schema_version": PROGNOSTIC_FEATURE_SCHEMA_VERSION,
        "disclaimer": (
            "SYNTHETIC BENCHMARK ONLY — NOT A PHYSICAL ENGINE-LIFE OR CERTIFIED LIFING MODEL"
        ),
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "splits": {},
    }

    for split_name, run_seed_list in splits.items():
        print(f"\nGenerating {split_name} split ({len(run_seed_list)} runs)...")
        all_records = []
        for run_id, seed in run_seed_list:
            recs = generate_benchmark_trajectory(
                run_id=run_id,
                seed=seed,
                physics_service=physics_service,
                hi_calc=hi_calc,
                extractor=extractor,
            )
            all_records.extend(recs)

        df = pd.DataFrame(all_records)
        output_parquet = os.path.join(OUTPUT_DIR, f"{split_name}_prognostics.parquet")
        df.to_parquet(output_parquet, index=False)
        print(
            f"Saved {output_parquet} ({len(df)} samples, {len(run_seed_list)} runs, {df['true_rul_hours'].mean():.2f} avg RUL hrs)"
        )

        manifest["splits"][split_name] = {
            "num_runs": len(run_seed_list),
            "num_samples": len(df),
            "mean_rul_hours": float(df["true_rul_hours"].mean()),
            "std_rul_hours": float(df["true_rul_hours"].std()),
            "runs": [r for r, _ in run_seed_list],
            "file": os.path.basename(output_parquet),
        }

    manifest_path = os.path.join(OUTPUT_DIR, "dataset_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print("\nDataset generation completed successfully.")
    print("Manifest saved to:", manifest_path)


if __name__ == "__main__":
    main()
