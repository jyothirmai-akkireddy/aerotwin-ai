"""Script generating a representative complete flight telemetry dataset for Phase 2."""

# ruff: noqa: E402
import json
import sys
from pathlib import Path

# Ensure backend root is on sys.path
backend_root = Path(__file__).resolve().parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from app.domain.simulation.scenarios import SCENARIO_COMPLETE_FLIGHT
from app.domain.telemetry.statistics import compute_telemetry_statistics
from app.infrastructure.persistence.telemetry_repository import SqliteTelemetryRepository
from app.infrastructure.simulation.engine_simulator import EngineSimulator
from app.infrastructure.simulation.noise import DeterministicNoiseGenerator


def generate_representative_flight(
    seed: int = 42,
    rate_hz: int = 10,
    output_parquet: Path = backend_root.parent
    / "data"
    / "processed"
    / "representative_flight_sample.parquet",
    output_json: Path = backend_root.parent / "data" / "processed" / "flight_summary.json",
) -> None:
    """Generate deterministic flight profile dataset and summary metrics."""
    print(f"Generating flight dataset with seed={seed}, rate={rate_hz} Hz...")

    noise = DeterministicNoiseGenerator(seed=seed)
    simulator = EngineSimulator(
        noise_generator=noise,
        telemetry_rate_hz=rate_hz,
    )

    frames = simulator.run_scenario(SCENARIO_COMPLETE_FLIGHT)
    print(
        f"Generated {len(frames)} telemetry frames ({len(frames) / rate_hz:.1f} simulated flight seconds)."
    )

    # Save to Parquet
    SqliteTelemetryRepository.export_frames_to_parquet(frames, output_parquet)
    print(
        f"Exported Parquet dataset to: {output_parquet} ({output_parquet.stat().st_size / 1024:.1f} KB)"
    )

    # Compute validation & quality statistics
    stats = compute_telemetry_statistics(frames, expected_rate_hz=rate_hz)

    summary_dict = {
        "scenario": SCENARIO_COMPLETE_FLIGHT.scenario_name,
        "description": SCENARIO_COMPLETE_FLIGHT.description,
        "seed": seed,
        "sample_count": stats.total_samples,
        "quality_distribution": {
            "valid": stats.valid_samples,
            "degraded": stats.degraded_samples,
            "invalid": stats.invalid_samples,
            "missing": stats.missing_samples,
            "valid_ratio": stats.quality_ratio_valid,
        },
        "timing": {
            "expected_rate_hz": stats.timing.expected_rate_hz,
            "observed_mean_dt_sec": stats.timing.observed_mean_dt_sec,
            "min_dt_sec": stats.timing.min_dt_sec,
            "max_dt_sec": stats.timing.max_dt_sec,
            "jitter_std_sec": stats.timing.jitter_std_sec,
            "dropped_sequence_count": stats.timing.dropped_sequence_count,
            "out_of_order_count": stats.timing.out_of_order_count,
        },
        "channels": {
            ch: {
                "mean": metric.mean,
                "std_dev": metric.std_dev,
                "min": metric.min_value,
                "max": metric.max_value,
            }
            for ch, metric in stats.channels.items()
        },
    }

    output_json.parent.mkdir(parents=True, exist_ok=True)
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(summary_dict, f, indent=2)
    print(f"Exported statistical summary to: {output_json}")


if __name__ == "__main__":
    generate_representative_flight()
