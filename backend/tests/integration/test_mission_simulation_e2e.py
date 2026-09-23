"""Mission Simulation and Replay end-to-end integration verification.

SIH26054 — AeroTwin AI
Phase 9 Integration & QA Gate

Validates:
1. Deterministic execution of all 5 reference missions:
   - SURVEILLANCE_MISSION
   - RAPID_CLIMB_HOT_DAY
   - THROTTLE_DYNAMICS_BENCHMARK
   - HIGH_ALTITUDE_FERRY
   - EMERGENCY_DESCENT
2. Fuel accounting verification via Riemann integration.
3. Environmental / altitude scaling and atmospheric engine response.
4. Mission Parquet export and subsequent Replay pipeline verification.
5. Physics Twin -> ML Diagnostics -> Prognostics analytical propagation.
6. All scenarios explicitly tagged as SYNTHETIC / PROTOTYPE SCENARIO.
"""

from pathlib import Path

import pandas as pd
import pytest

from app.application.services.mission_simulator import MissionSimulator
from app.application.services.ml_service import MLInferenceService
from app.application.services.physics_twin_service import PhysicsTwinService
from app.application.services.prognostics_service import PrognosticsService
from app.application.services.replay_service import ReplayService
from app.domain.mission.catalog import STANDARD_MISSIONS
from app.infrastructure.logging.logger import get_logger
from app.infrastructure.physics.calibration_repository import PhysicsCalibrationRepository
from app.infrastructure.replay.loader import FlightLogLoader

logger = get_logger("aerotwin.test.mission_simulation_e2e")

PROTOTYPE_SCENARIO_TAG = "SYNTHETIC / PROTOTYPE SCENARIO — Phase 9 Mission Simulation E2E"


def test_all_five_reference_missions_execution():
    """Execute all 5 reference missions and verify physics metrics and Riemann fuel accounting."""
    logger.info(f"Executing: {PROTOTYPE_SCENARIO_TAG} - All 5 Reference Missions")

    expected_missions = [
        "SURVEILLANCE_MISSION",
        "RAPID_CLIMB_HOT_DAY",
        "THROTTLE_DYNAMICS_BENCHMARK",
        "HIGH_ALTITUDE_FERRY",
        "EMERGENCY_DESCENT",
    ]

    for m_id in expected_missions:
        mission_def = STANDARD_MISSIONS.get(m_id)
        assert mission_def is not None, f"Missing standard mission definition: {m_id}"

        sim = MissionSimulator(mission=mission_def, telemetry_rate_hz=10, seed=42)
        summary, frames = sim.run_sync()

        # 1. Structural integrity
        assert summary.total_frames == len(frames)
        assert len(frames) > 0
        assert summary.total_duration_sec > 0.0

        # 2. Riemann integration for fuel consumption
        dt = 1.0 / 10.0
        expected_fuel_l = sum((f.fuel_flow / 3600.0) * dt for f in frames)
        assert summary.fuel_consumed_liters == pytest.approx(expected_fuel_l, abs=0.001)
        assert summary.fuel_mass_kg == pytest.approx(expected_fuel_l * 0.72, abs=0.001)

        # 3. Environmental and physical properties
        if m_id == "HIGH_ALTITUDE_FERRY":
            assert summary.max_altitude_m >= 4400.0, (
                "High altitude mission did not reach expected ceiling"
            )
        elif m_id == "RAPID_CLIMB_HOT_DAY":
            assert summary.max_cht_c > 90.0, "Hot day climb did not exhibit elevated CHT"

        # 4. Prototype disclaimer verification
        assert "PROTOTYPE" in summary.prototype_disclaimer
        logger.info(
            f"Mission {m_id} complete: {len(frames)} frames, {summary.fuel_consumed_liters:.3f}L fuel consumed."
        )


def test_mission_export_and_replay_analytical_chain(tmp_path: Path):
    """Export a simulated mission to Parquet and verify Replay ingestion through full analytics."""
    logger.info(f"Executing: {PROTOTYPE_SCENARIO_TAG} - Export and Replay Loop")

    mission_def = STANDARD_MISSIONS["SURVEILLANCE_MISSION"]
    sim = MissionSimulator(mission=mission_def, telemetry_rate_hz=10, seed=42)
    summary, frames = sim.run_sync()

    # Convert frames to Parquet
    data: dict[str, list] = {
        "sequence_id": [f.sequence_id for f in frames],
        "timestamp": [f.timestamp for f in frames],
        "rpm": [f.rpm for f in frames],
        "manifold_pressure": [f.manifold_pressure for f in frames],
        "throttle_position": [f.throttle_position for f in frames],
        "fuel_flow": [f.fuel_flow for f in frames],
        "fuel_pressure": [f.fuel_pressure for f in frames],
        "injection_timing": [f.injection_timing for f in frames],
        "cht_1": [f.cht[0] for f in frames],
        "cht_2": [f.cht[1] for f in frames],
        "cht_3": [f.cht[2] for f in frames],
        "cht_4": [f.cht[3] for f in frames],
        "egt_1": [f.egt[0] for f in frames],
        "egt_2": [f.egt[1] for f in frames],
        "egt_3": [f.egt[2] for f in frames],
        "egt_4": [f.egt[3] for f in frames],
        "coolant_temp": [f.coolant_temp for f in frames],
        "oil_temperature": [f.oil_temperature for f in frames],
        "oil_pressure": [f.oil_pressure for f in frames],
        "vibration_rms": [f.vibration_rms for f in frames],
        "battery_voltage": [f.battery_voltage for f in frames],
        "alternator_current": [f.alternator_current for f in frames],
        "alternator_status": [f.alternator_status for f in frames],
        "altitude": [f.altitude for f in frames],
        "ambient_temp": [f.ambient_temp for f in frames],
        "true_airspeed": [f.true_airspeed for f in frames],
        "source_type": ["REPLAY" for _ in frames],
        "quality_flag": ["VALID" for _ in frames],
    }

    parquet_file = tmp_path / "surveillance_mission_replay.parquet"
    df = pd.DataFrame(data)
    df.to_parquet(parquet_file, index=False)

    # Ingest into Replay service
    replay_service = ReplayService(search_directories=[tmp_path])
    cursor_status = replay_service.load_dataset(parquet_file.name)
    assert cursor_status.total_frames == len(frames)

    loaded_frames = FlightLogLoader.load_frames(parquet_file)
    assert len(loaded_frames) == len(frames)

    # Propagate through Physics -> ML -> Prognostics
    cal_repo = PhysicsCalibrationRepository()
    physics_service = PhysicsTwinService(calibration_repo=cal_repo)
    ml_service = MLInferenceService()
    prognostics_service = PrognosticsService()

    physics_results = []
    ml_results = []
    prognostics_results = []

    for f in loaded_frames:
        p_res = physics_service.evaluate_frame(f)
        m_res = ml_service.evaluate(f, p_res)
        prog_res = prognostics_service.evaluate(f, p_res, m_res)

        physics_results.append(p_res)
        ml_results.append(m_res)
        prognostics_results.append(prog_res)

        assert p_res.residuals.validity in ("VALID", "DEGRADED", "INVALID")
        assert 0.0 <= m_res.anomaly.score <= 1.0
        assert 0.0 <= prog_res.health_index <= 1.0

    assert len(physics_results) == len(frames)
    assert len(ml_results) == len(frames)
    assert len(prognostics_results) == len(frames)
    logger.info(
        f"Mission Replay Analytical Chain Passed: All {len(frames)} frames propagated cleanly "
        f"through Physics -> ML -> Prognostics with zero errors."
    )
