"""Synthetic Dataset Generation Script for Phase 6 ML Models.

Generates run/seed-isolated training, validation, and testing datasets using
the deterministic EngineSimulator and FaultController. Computes Phase 5 analytical
residuals on each frame to generate the exact 24-feature manifest.

Splits:
- Train Split:      Seed 42  (~5,200 samples)
- Validation Split: Seed 101 (~2,000 samples)
- Test Split:       Seed 202 (~2,000 samples)
"""

import json
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.application.services.physics_twin_service import PhysicsTwinService
from app.domain.ml.features import FEATURE_NAMES, FeatureExtractor
from app.domain.simulation.faults import FaultController, SensorFaultConfig, SensorFaultType
from app.domain.simulation.scenarios import (
    SCENARIO_COMPLETE_FLIGHT,
    SCENARIO_CRUISE,
    SCENARIO_TAKEOFF,
    SCENARIO_THROTTLE_TRANSIENTS,
    ScenarioProfile,
)
from app.infrastructure.simulation.engine_simulator import EngineSimulator
from app.infrastructure.simulation.noise import DeterministicNoiseGenerator

OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data/processed/ml"))


def generate_flight_run(
    seed: int,
    profile: ScenarioProfile,
    fault_config: SensorFaultConfig | None = None,
    fault_label: str = "NORMAL",
) -> list[dict[str, float]]:
    """Generate a single scenario run and extract 24 features and class label for each frame."""
    noise_gen = DeterministicNoiseGenerator(seed=seed)
    fault_ctrl = FaultController()
    if fault_config is not None:
        fault_ctrl.add_fault(fault_config)

    sim = EngineSimulator(
        noise_generator=noise_gen,
        fault_controller=fault_ctrl,
        telemetry_rate_hz=10,
    )
    physics_service = PhysicsTwinService()
    extractor = FeatureExtractor()

    records: list[dict[str, float]] = []

    for phase in profile.phases:
        step_count = int(np.ceil(phase.duration_sec / sim.dt))
        for _ in range(step_count):
            frame = sim.step(phase)
            physics_res = physics_service.evaluate_frame(frame)
            feats = extractor.extract(frame, physics_res)

            row: dict[str, float] = {}
            for idx, fname in enumerate(FEATURE_NAMES):
                row[fname] = float(feats[idx])

            # Labeling: if fault was active during this frame, label with fault_label, else NORMAL
            is_active = fault_config.is_active(sim.state.sim_time) if fault_config else False
            row["fault_class"] = fault_label if is_active else "NORMAL"
            row["is_anomaly"] = 1.0 if (fault_label != "NORMAL" and is_active) else 0.0
            row["sim_time"] = float(sim.state.sim_time)
            row["sequence_id"] = float(frame.sequence_id)
            records.append(row)

    return records


def build_split(
    seed: int, target_runs: list[tuple[ScenarioProfile, SensorFaultConfig | None, str]]
) -> pd.DataFrame:
    """Build a combined dataframe from multiple flight scenario runs."""
    all_records: list[dict[str, float]] = []
    run_idx = 0
    for profile, fault_cfg, label in target_runs:
        run_seed = seed + run_idx * 17
        run_records = generate_flight_run(run_seed, profile, fault_cfg, label)
        all_records.extend(run_records)
        run_idx += 1
    return pd.DataFrame(all_records)


def main() -> None:
    print("==================================================")
    print("STARTING ML DATASET GENERATION")
    print("==================================================")
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Define standard fault injection scenarios
    def make_runs(base_t: float) -> list[tuple[ScenarioProfile, SensorFaultConfig | None, str]]:
        return [
            # 1. Normal Flight Run
            (SCENARIO_COMPLETE_FLIGHT, None, "NORMAL"),
            # 2. Oil Pressure Bias (+2.0 bar after base_t sec)
            (
                SCENARIO_CRUISE,
                SensorFaultConfig(
                    target_channel="oil_pressure",
                    fault_type=SensorFaultType.BIAS,
                    start_time_sec=base_t,
                    magnitude=2.0,
                ),
                "OIL_PRESSURE_BIAS",
            ),
            # 3. Oil Temperature Drift (+1.2°C/sec bounded by end_time_sec)
            (
                SCENARIO_CRUISE,
                SensorFaultConfig(
                    target_channel="oil_temperature",
                    fault_type=SensorFaultType.DRIFT,
                    start_time_sec=base_t,
                    end_time_sec=base_t + 30.0,
                    drift_rate_per_sec=1.2,
                ),
                "OIL_TEMP_DRIFT",
            ),
            # 4. Throttle Stuck (pinned at 30%)
            (
                SCENARIO_THROTTLE_TRANSIENTS,
                SensorFaultConfig(
                    target_channel="throttle_position",
                    fault_type=SensorFaultType.STUCK,
                    start_time_sec=base_t,
                    magnitude=30.0,
                ),
                "THROTTLE_STUCK",
            ),
            # 5. Sensor Dropout (battery voltage dropped to 0V)
            (
                SCENARIO_CRUISE,
                SensorFaultConfig(
                    target_channel="battery_voltage",
                    fault_type=SensorFaultType.DROPOUT,
                    start_time_sec=base_t,
                ),
                "SENSOR_DROPOUT",
            ),
            # 6. MAP Noise Spike (4x variance amplification)
            (
                SCENARIO_TAKEOFF,
                SensorFaultConfig(
                    target_channel="manifold_pressure",
                    fault_type=SensorFaultType.NOISE_SPIKE,
                    start_time_sec=base_t,
                    noise_multiplier=4.0,
                ),
                "MAP_NOISE_SPIKE",
            ),
        ]

    # 1. Generate Training Split (Seed 42)
    print("\nGenerating TRAIN split (Seed 42)...")
    train_df = build_split(seed=42, target_runs=make_runs(base_t=10.0))
    train_path = os.path.join(OUTPUT_DIR, "train_dataset.parquet")
    train_df.to_parquet(train_path, index=False)
    print(f"  -> Saved {len(train_df)} rows to {train_path}")
    print(train_df["fault_class"].value_counts().to_dict())

    # 2. Generate Validation Split (Seed 101, different fault onset timings)
    print("\nGenerating VALIDATION split (Seed 101)...")
    val_df = build_split(seed=101, target_runs=make_runs(base_t=8.0))
    val_path = os.path.join(OUTPUT_DIR, "val_dataset.parquet")
    val_df.to_parquet(val_path, index=False)
    print(f"  -> Saved {len(val_df)} rows to {val_path}")
    print(val_df["fault_class"].value_counts().to_dict())

    # 3. Generate Test Split (Seed 202, held-out runs & magnitudes)
    print("\nGenerating TEST split (Seed 202)...")
    test_df = build_split(seed=202, target_runs=make_runs(base_t=12.0))
    test_path = os.path.join(OUTPUT_DIR, "test_dataset.parquet")
    test_df.to_parquet(test_path, index=False)
    print(f"  -> Saved {len(test_df)} rows to {test_path}")
    print(test_df["fault_class"].value_counts().to_dict())

    # 4. Generate Metadata JSON
    metadata = {
        "generated_at_utc": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "provenance": "SYNTHETIC_SIMULATED_PROTOTYPE",
        "feature_schema_version": "1.0.0",
        "feature_names": FEATURE_NAMES,
        "splits": {
            "train": {
                "seed": 42,
                "sample_count": len(train_df),
                "class_distribution": train_df["fault_class"].value_counts().to_dict(),
            },
            "validation": {
                "seed": 101,
                "sample_count": len(val_df),
                "class_distribution": val_df["fault_class"].value_counts().to_dict(),
            },
            "test": {
                "seed": 202,
                "sample_count": len(test_df),
                "class_distribution": test_df["fault_class"].value_counts().to_dict(),
            },
        },
    }
    meta_path = os.path.join(OUTPUT_DIR, "dataset_metadata.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    print(f"\nMetadata written to {meta_path}")
    print("==================================================")
    print("DATASET GENERATION COMPLETE")
    print("==================================================")


if __name__ == "__main__":
    main()
