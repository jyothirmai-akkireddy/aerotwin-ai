"""Regression tests for P2 defect fix: ScenarioProfile -> ScenarioPhase type boundary,
case-normalization, and WebSocket set_scenario command handling.
"""

import pytest

from app.application.services.realtime_service import RealtimeTelemetryService
from app.domain.simulation.scenarios import (
    SCENARIO_CRUISE,
    SCENARIO_TAKEOFF,
    STANDARD_SCENARIOS,
    ScenarioPhase,
    get_scenario,
)
from app.infrastructure.telemetry.synthetic_source import SyntheticTelemetrySource
from app.infrastructure.websocket.broadcaster import WebSocketBroadcastManager
from app.infrastructure.websocket.protocol import CommandMessage


# ==============================================================================
# TEST 1: Valid uppercase scenario
# ==============================================================================
def test_valid_uppercase_scenario_resolution():
    """Verify set_scenario('CRUISE') resolves to ScenarioPhase and steps simulator without AttributeError."""
    source = SyntheticTelemetrySource()
    assert source.current_phase is None

    success = source.set_scenario("CRUISE")
    assert success is True
    assert isinstance(source.current_phase, ScenarioPhase)
    assert source.current_phase.phase_name == "LEVEL_CRUISE"
    assert source.current_phase.target_throttle_pct == 65.0

    # Step simulator; must succeed without AttributeError
    frame = source.simulator.step(phase=source.current_phase)
    assert frame is not None
    assert frame.throttle_position >= 0.0


# ==============================================================================
# TEST 2: Lowercase scenario (case normalization)
# ==============================================================================
def test_case_insensitive_scenario_resolution():
    """Verify lowercase and mixed-case scenario inputs resolve identically to uppercase."""
    source = SyntheticTelemetrySource()

    # Lowercase 'cruise'
    success_lower = source.set_scenario("cruise")
    assert success_lower is True
    assert isinstance(source.current_phase, ScenarioPhase)
    assert source.current_phase.phase_name == "LEVEL_CRUISE"

    # Mixed-case 'Idle '
    success_mixed = source.set_scenario("  Idle ")
    assert success_mixed is True
    assert isinstance(source.current_phase, ScenarioPhase)
    assert source.current_phase.phase_name == "GROUND_IDLE"

    # get_scenario helper directly
    assert get_scenario("takeoff") == STANDARD_SCENARIOS["TAKEOFF"]
    assert get_scenario("CRUISE") == STANDARD_SCENARIOS["CRUISE"]
    assert get_scenario("idle") == STANDARD_SCENARIOS["IDLE"]


# ==============================================================================
# TEST 3: Invalid scenario input
# ==============================================================================
def test_invalid_scenario_handling():
    """Verify invalid scenario names fail safely without simulator corruption or uncaught exceptions."""
    source = SyntheticTelemetrySource()
    initial_phase = source.current_phase

    # Invalid scenario name
    success = source.set_scenario("NOT_A_REAL_SCENARIO")
    assert success is False
    assert source.current_phase == initial_phase

    # Empty string and non-string inputs
    assert get_scenario("") is None
    assert get_scenario("   ") is None
    assert get_scenario(None) is None  # type: ignore[arg-type]

    # Simulator continues to step normally
    frame = source.simulator.step()
    assert frame is not None


# ==============================================================================
# TEST 4: ScenarioProfile -> ScenarioPhase type boundary guard
# ==============================================================================
def test_scenario_profile_type_boundary_guard():
    """Explicitly verify that passing a ScenarioProfile directly to set_phase raises TypeError."""
    source = SyntheticTelemetrySource()

    # Attempting to pass a ScenarioProfile instead of ScenarioPhase must be rejected
    with pytest.raises(TypeError) as exc_info:
        source.set_phase(SCENARIO_CRUISE)  # type: ignore[arg-type]

    assert "Expected ScenarioPhase or None, got ScenarioProfile" in str(exc_info.value)

    # Passing a valid ScenarioPhase or None must succeed
    valid_phase = SCENARIO_CRUISE.phases[0]
    source.set_phase(valid_phase)
    assert source.current_phase == valid_phase

    source.set_phase(None)
    assert source.current_phase is None


# ==============================================================================
# TEST 5: Existing scenario progression behavior
# ==============================================================================
def test_existing_multi_phase_scenario_progression():
    """Verify that multi-phase scenario execution via run_scenario is preserved and intact."""
    source = SyntheticTelemetrySource()

    # SCENARIO_TAKEOFF has 2 phases: TAKEOFF_ROLL (10s) and INITIAL_CLIMB (30s)
    assert len(SCENARIO_TAKEOFF.phases) == 2
    total_expected_duration = SCENARIO_TAKEOFF.total_duration_sec
    assert total_expected_duration == 40.0

    # Execute full scenario
    frames = source.run_scenario(SCENARIO_TAKEOFF)
    dt = source.simulator.dt
    expected_frames = int(round(total_expected_duration / dt))
    assert len(frames) == expected_frames

    # Sequence IDs must be strictly monotonic
    for i in range(1, len(frames)):
        assert frames[i].sequence_id == frames[i - 1].sequence_id + 1

    # First portion corresponds to TAKEOFF_ROLL (100% throttle), second to INITIAL_CLIMB (95% throttle)
    first_phase_steps = int(round(SCENARIO_TAKEOFF.phases[0].duration_sec / dt))
    assert frames[first_phase_steps - 1].throttle_position >= 99.0


# ==============================================================================
# TEST 6: RealtimeTelemetryService set_scenario command integration
# ==============================================================================
@pytest.mark.asyncio
async def test_realtime_service_set_scenario_integration():
    """Verify RealtimeTelemetryService.execute_command successfully updates scenario."""
    source = SyntheticTelemetrySource()
    broadcaster = WebSocketBroadcastManager(max_clients=5, queue_size=10)
    service = RealtimeTelemetryService(
        telemetry_source=source,
        broadcaster=broadcaster,
        rate_hz=50,
    )

    # Execute uppercase command
    await service.execute_command("set_scenario", {"scenario": "CRUISE"})
    assert source.current_phase is not None
    assert source.current_phase.phase_name == "LEVEL_CRUISE"

    # Execute lowercase command with phase_name param
    await service.execute_command("set_scenario", {"phase_name": "idle"})
    assert source.current_phase is not None
    assert source.current_phase.phase_name == "GROUND_IDLE"

    # Execute invalid scenario command; must log warning without crashing
    await service.execute_command("set_scenario", {"scenario": "INVALID_UNKNOWN"})
    assert source.current_phase.phase_name == "GROUND_IDLE"  # Preserved unchanged


# ==============================================================================
# TEST 7: CommandMessage root-level parameter extraction & pipeline stepping
# ==============================================================================
def test_command_message_root_parameter_extraction():
    """Verify CommandMessage normalizes root-level 'scenario' and 'rate_hz' into params."""
    # Root level 'scenario'
    msg1 = CommandMessage.model_validate(
        {"type": "command", "command": "set_scenario", "scenario": "CRUISE"}
    )
    assert msg1.command == "set_scenario"
    assert msg1.params == {"scenario": "CRUISE"}

    # Lowercase root level 'scenario'
    msg2 = CommandMessage.model_validate(
        {"type": "command", "command": "set_scenario", "scenario": "idle"}
    )
    assert msg2.command == "set_scenario"
    assert msg2.params == {"scenario": "idle"}

    # Nested params
    msg3 = CommandMessage.model_validate(
        {"type": "command", "command": "set_scenario", "params": {"scenario": "TAKEOFF"}}
    )
    assert msg3.command == "set_scenario"
    assert msg3.params == {"scenario": "TAKEOFF"}


@pytest.mark.asyncio
async def test_realtime_service_scenario_telemetry_continuation():
    """Verify that after set_scenario, the simulator continues stepping and sequence IDs advance."""
    source = SyntheticTelemetrySource()
    broadcaster = WebSocketBroadcastManager(max_clients=5, queue_size=10)
    service = RealtimeTelemetryService(
        telemetry_source=source,
        broadcaster=broadcaster,
        rate_hz=50,
    )

    frame1 = await source.get_next_frame()
    seq1 = frame1.sequence_id

    # Switch scenario
    await service.execute_command("set_scenario", {"scenario": "CRUISE"})

    # Produce subsequent frames
    frame2 = await source.get_next_frame()
    seq2 = frame2.sequence_id

    assert seq2 == seq1 + 1
    assert frame2.throttle_position >= 0.0
