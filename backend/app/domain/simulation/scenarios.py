"""Predefined and configurable engine operating scenarios and flight phases."""

from pydantic import BaseModel, Field


class ScenarioPhase(BaseModel):
    """A discrete temporal phase within an operating scenario."""

    phase_name: str
    duration_sec: float = Field(..., gt=0.0)
    target_throttle_pct: float = Field(..., ge=0.0, le=100.0)
    target_altitude_m: float = Field(default=0.0, ge=-200.0, le=12000.0)
    ambient_temp_c: float = Field(default=15.0, ge=-60.0, le=60.0)
    target_airspeed_ms: float = Field(default=0.0, ge=0.0, le=120.0)
    ignition_on: bool = True
    starter_engaged: bool = False


class ScenarioProfile(BaseModel):
    """Complete multi-phase simulation scenario."""

    scenario_name: str
    description: str
    phases: list[ScenarioPhase]

    @property
    def total_duration_sec(self) -> float:
        return sum(p.duration_sec for p in self.phases)


# ==============================================================================
# Standard Predefined Scenarios (Prototype Benchmarks)
# ==============================================================================

SCENARIO_ENGINE_START = ScenarioProfile(
    scenario_name="ENGINE_START",
    description="Engine cranking, ignition catch, and stabilization to ground idle",
    phases=[
        ScenarioPhase(
            phase_name="PRE_START",
            duration_sec=3.0,
            target_throttle_pct=0.0,
            ignition_on=False,
            starter_engaged=False,
        ),
        ScenarioPhase(
            phase_name="CRANKING",
            duration_sec=2.0,
            target_throttle_pct=10.0,
            ignition_on=True,
            starter_engaged=True,
        ),
        ScenarioPhase(
            phase_name="IDLE_STABILIZE",
            duration_sec=10.0,
            target_throttle_pct=5.0,
            ignition_on=True,
            starter_engaged=False,
        ),
    ],
)

SCENARIO_IDLE = ScenarioProfile(
    scenario_name="IDLE",
    description="Steady-state ground idle warm-up at standard sea-level temperature",
    phases=[
        ScenarioPhase(
            phase_name="GROUND_IDLE",
            duration_sec=30.0,
            target_throttle_pct=5.0,
            target_altitude_m=0.0,
            ambient_temp_c=15.0,
            target_airspeed_ms=0.0,
        )
    ],
)

SCENARIO_TAXI = ScenarioProfile(
    scenario_name="TAXI_LOW_POWER",
    description="Low power ground maneuvering and taxiing",
    phases=[
        ScenarioPhase(
            phase_name="TAXI_OUT",
            duration_sec=20.0,
            target_throttle_pct=18.0,
            target_altitude_m=0.0,
            ambient_temp_c=15.0,
            target_airspeed_ms=8.0,
        )
    ],
)

SCENARIO_TAKEOFF = ScenarioProfile(
    scenario_name="TAKEOFF_HIGH_POWER",
    description="Takeoff rollout and initial climb at maximum continuous power",
    phases=[
        ScenarioPhase(
            phase_name="TAKEOFF_ROLL",
            duration_sec=10.0,
            target_throttle_pct=100.0,
            target_altitude_m=10.0,
            target_airspeed_ms=25.0,
        ),
        ScenarioPhase(
            phase_name="INITIAL_CLIMB",
            duration_sec=30.0,
            target_throttle_pct=95.0,
            target_altitude_m=1000.0,
            target_airspeed_ms=40.0,
        ),
    ],
)

SCENARIO_CRUISE = ScenarioProfile(
    scenario_name="CRUISE",
    description="Steady level endurance cruise at altitude (65% power)",
    phases=[
        ScenarioPhase(
            phase_name="LEVEL_CRUISE",
            duration_sec=60.0,
            target_throttle_pct=65.0,
            target_altitude_m=3500.0,
            ambient_temp_c=-7.0,  # Standard lapse rate at 3500m
            target_airspeed_ms=50.0,
        )
    ],
)

SCENARIO_THROTTLE_TRANSIENTS = ScenarioProfile(
    scenario_name="THROTTLE_TRANSIENTS",
    description="Rapid throttle transitions testing turbo lag and governor inertia",
    phases=[
        ScenarioPhase(
            phase_name="BASE_CRUISE",
            duration_sec=15.0,
            target_throttle_pct=50.0,
            target_altitude_m=2000.0,
            target_airspeed_ms=45.0,
        ),
        ScenarioPhase(
            phase_name="BURST_POWER",
            duration_sec=10.0,
            target_throttle_pct=95.0,
            target_altitude_m=2000.0,
            target_airspeed_ms=52.0,
        ),
        ScenarioPhase(
            phase_name="RAPID_CHOP",
            duration_sec=10.0,
            target_throttle_pct=20.0,
            target_altitude_m=2000.0,
            target_airspeed_ms=40.0,
        ),
        ScenarioPhase(
            phase_name="RECOVERY",
            duration_sec=15.0,
            target_throttle_pct=60.0,
            target_altitude_m=2000.0,
            target_airspeed_ms=46.0,
        ),
    ],
)

SCENARIO_DECELERATION = ScenarioProfile(
    scenario_name="DECELERATION",
    description="Power reduction, descent, and deceleration",
    phases=[
        ScenarioPhase(
            phase_name="DESCENT_LOW_POWER",
            duration_sec=25.0,
            target_throttle_pct=25.0,
            target_altitude_m=500.0,
            target_airspeed_ms=35.0,
        )
    ],
)

SCENARIO_SHUTDOWN = ScenarioProfile(
    scenario_name="ENGINE_SHUTDOWN",
    description="Cool-down idle, ignition cut, and mechanical spin-down",
    phases=[
        ScenarioPhase(
            phase_name="COOL_DOWN_IDLE",
            duration_sec=15.0,
            target_throttle_pct=5.0,
            target_altitude_m=0.0,
            ignition_on=True,
            target_airspeed_ms=0.0,
        ),
        ScenarioPhase(
            phase_name="IGNITION_CUT",
            duration_sec=5.0,
            target_throttle_pct=0.0,
            ignition_on=False,
            target_airspeed_ms=0.0,
        ),
    ],
)

# Combined full mission flight profile for integration and benchmark testing
SCENARIO_COMPLETE_FLIGHT = ScenarioProfile(
    scenario_name="COMPLETE_FLIGHT_PROFILE",
    description="Full mission cycle: Start -> Idle -> Taxi -> Takeoff -> Cruise -> Transient -> Descent -> Shutdown",
    phases=[
        *SCENARIO_ENGINE_START.phases,
        *SCENARIO_IDLE.phases,
        *SCENARIO_TAXI.phases,
        *SCENARIO_TAKEOFF.phases,
        *SCENARIO_CRUISE.phases,
        *SCENARIO_THROTTLE_TRANSIENTS.phases,
        *SCENARIO_DECELERATION.phases,
        *SCENARIO_SHUTDOWN.phases,
    ],
)

STANDARD_SCENARIOS: dict[str, ScenarioProfile] = {
    "ENGINE_START": SCENARIO_ENGINE_START,
    "IDLE": SCENARIO_IDLE,
    "TAXI": SCENARIO_TAXI,
    "TAKEOFF": SCENARIO_TAKEOFF,
    "CRUISE": SCENARIO_CRUISE,
    "THROTTLE_TRANSIENTS": SCENARIO_THROTTLE_TRANSIENTS,
    "DECELERATION": SCENARIO_DECELERATION,
    "ENGINE_SHUTDOWN": SCENARIO_SHUTDOWN,
    "COMPLETE_FLIGHT_PROFILE": SCENARIO_COMPLETE_FLIGHT,
}


def get_scenario(name: str) -> ScenarioProfile | None:
    """Retrieve a standard scenario profile by name in a case-insensitive manner.

    Args:
        name: Scenario identifier (e.g. 'CRUISE', 'cruise', 'idle', 'TAKEOFF').

    Returns:
        The matching ScenarioProfile if found, or None if invalid or unknown.
    """
    if not name or not isinstance(name, str):
        return None
    normalized = name.strip().upper()
    return STANDARD_SCENARIOS.get(normalized)
