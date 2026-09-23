"""Simulation management and telemetry streaming API endpoints."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.api.dependencies import (
    get_engine_simulator,
    get_telemetry_repository,
    get_telemetry_source,
)
from app.domain.entities.telemetry import TelemetryFrame
from app.domain.simulation.faults import SensorFaultConfig
from app.domain.simulation.scenarios import STANDARD_SCENARIOS, ScenarioPhase
from app.infrastructure.persistence.telemetry_repository import SqliteTelemetryRepository
from app.infrastructure.simulation.engine_simulator import EngineSimulator
from app.infrastructure.telemetry.synthetic_source import SyntheticTelemetrySource

router = APIRouter(prefix="/api/v1/simulation", tags=["simulation"])


class SimulationConfigRequest(BaseModel):
    telemetry_rate_hz: int | None = Field(None, ge=1, le=100)


class StepInputRequest(BaseModel):
    phase_name: str = "MANUAL_STEP"
    target_throttle_pct: float = Field(0.0, ge=0.0, le=100.0)
    target_altitude_m: float = Field(0.0, ge=-200.0, le=12000.0)
    ambient_temp_c: float = Field(15.0, ge=-60.0, le=60.0)
    target_airspeed_ms: float = Field(0.0, ge=0.0, le=120.0)
    ignition_on: bool = True
    starter_engaged: bool = False


class BatchGenerationRequest(BaseModel):
    count: int = Field(default=10, ge=1, le=1000)
    scenario_name: str | None = None
    persist: bool = False


class ResetRequest(BaseModel):
    seed: int | None = None


@router.get("/config")
def get_simulation_config(
    simulator: EngineSimulator = Depends(get_engine_simulator),
) -> dict[str, Any]:
    """Retrieve active engine simulation parameters, rate, and scenario presets."""
    return {
        "engine_baseline": "Generic 4-cylinder horizontally-opposed turbocharged aero-piston engine inspired by the Rotax 914/915 class",
        "prototype_disclaimer": "All thermodynamic, mechanical, and aerodynamic parameters are simplified prototype simulation assumptions. Not certified aerospace OEM data.",
        "telemetry_rate_hz": simulator.rate_hz,
        "dt_seconds": simulator.dt,
        "sequence_id": simulator.sequence_id,
        "sim_time": round(simulator.state.sim_time, 4),
        "engine_state": simulator.state.operating_state.value,
        "active_faults_count": len(simulator.faults.fault_configs),
        "available_scenarios": list(STANDARD_SCENARIOS.keys()),
    }


@router.post("/step", response_model=TelemetryFrame)
def step_simulation(
    request: StepInputRequest | None = None,
    simulator: EngineSimulator = Depends(get_engine_simulator),
) -> TelemetryFrame:
    """Step the simulation by one discrete dt time interval and return the validated TelemetryFrame."""
    phase = None
    if request:
        phase = ScenarioPhase(
            phase_name=request.phase_name,
            duration_sec=simulator.dt,
            target_throttle_pct=request.target_throttle_pct,
            target_altitude_m=request.target_altitude_m,
            ambient_temp_c=request.ambient_temp_c,
            target_airspeed_ms=request.target_airspeed_ms,
            ignition_on=request.ignition_on,
            starter_engaged=request.starter_engaged,
        )
    return simulator.step(phase)


@router.post("/batch")
async def generate_batch(
    request: BatchGenerationRequest,
    source: SyntheticTelemetrySource = Depends(get_telemetry_source),
    repo: SqliteTelemetryRepository = Depends(get_telemetry_repository),
) -> dict[str, Any]:
    """Generate a batch of simulated telemetry frames, optionally persisting them."""
    phase = None
    if request.scenario_name:
        if request.scenario_name not in STANDARD_SCENARIOS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown scenario '{request.scenario_name}'. Available: {list(STANDARD_SCENARIOS.keys())}",
            )
        profile = STANDARD_SCENARIOS[request.scenario_name]
        frames = source.run_scenario(profile)
    else:
        frames = source.generate_batch(request.count, phase=phase)

    if request.persist and frames:
        await repo.save_batch(frames)

    return {
        "frames_generated": len(frames),
        "telemetry_rate_hz": source.simulator.rate_hz,
        "latest_sequence_id": frames[-1].sequence_id if frames else source.simulator.sequence_id,
        "sample_frame": frames[0] if frames else None,
    }


@router.post("/reset")
def reset_simulation(
    request: ResetRequest | None = None,
    simulator: EngineSimulator = Depends(get_engine_simulator),
) -> dict[str, Any]:
    """Reset the engine simulator to cold initial state with optional PRNG seed."""
    seed = request.seed if request else None
    simulator.reset(seed=seed)
    return {
        "status": "reset",
        "seed": seed,
        "sim_time": 0.0,
        "sequence_id": 0,
        "engine_state": simulator.state.operating_state.value,
    }


@router.get("/scenarios")
def list_scenarios() -> list[dict[str, Any]]:
    """List all available standard flight scenarios and their phases."""
    return [
        {
            "scenario_name": name,
            "description": p.description,
            "total_duration_sec": p.total_duration_sec,
            "phase_count": len(p.phases),
        }
        for name, p in STANDARD_SCENARIOS.items()
    ]


@router.get("/faults")
def list_faults(
    simulator: EngineSimulator = Depends(get_engine_simulator),
) -> list[dict[str, Any]]:
    """List currently configured sensor faults."""
    return [f.model_dump() for f in simulator.faults.fault_configs]


@router.post("/faults", status_code=status.HTTP_201_CREATED)
def inject_fault(
    fault: SensorFaultConfig,
    simulator: EngineSimulator = Depends(get_engine_simulator),
) -> dict[str, Any]:
    """Inject a reproducible sensor fault into the simulation stream."""
    simulator.faults.add_fault(fault)
    return {"status": "fault_injected", "fault": fault.model_dump()}


@router.delete("/faults")
def clear_faults(
    simulator: EngineSimulator = Depends(get_engine_simulator),
) -> dict[str, str]:
    """Clear all active sensor faults."""
    simulator.faults.clear()
    return {"status": "all_faults_cleared"}


@router.get("/records")
async def get_records(
    limit: int = Query(default=50, ge=1, le=500),
    repo: SqliteTelemetryRepository = Depends(get_telemetry_repository),
) -> list[TelemetryFrame]:
    """Retrieve recent persisted telemetry frames."""
    return await repo.get_recent_frames(limit=limit)
