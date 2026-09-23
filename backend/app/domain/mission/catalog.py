"""Predefined reference mission profiles for benchmark and regression testing.

PROTOTYPE DISCLAIMER:
These mission profiles are synthetic benchmark models representing approximate operating
conditions for a generic 4-cylinder turbocharged aero-piston engine (Rotax 914/915 iS class).
They do NOT represent certified flight operations or OEM performance data.
"""

from app.domain.mission.enums import MissionPhaseType
from app.domain.mission.models import MissionDefinition, MissionPhaseDefinition
from app.domain.mission.profiles import ProfileCurve

# ==============================================================================
# 1. SURVEILLANCE_MISSION (Standard Multi-Phase UAV Patrol)
# ==============================================================================
SURVEILLANCE_MISSION = MissionDefinition(
    mission_id="SURVEILLANCE_MISSION",
    name="Standard Surveillance Patrol [SYNTHETIC / PROTOTYPE SCENARIO]",
    description=(
        "SYNTHETIC / PROTOTYPE SCENARIO: Complete UAV patrol profile covering cold start, "
        "taxi, takeoff roll, initial climb to 3000m, loiter cruise, descent, and shutdown."
    ),
    initial_altitude_m=0.0,
    initial_ambient_temp_c=15.0,
    is_synthetic=True,
    phases=[
        MissionPhaseDefinition(
            phase_id="P1_PRE_START",
            phase_type=MissionPhaseType.PRE_START,
            duration_sec=3.0,
            throttle_profile=ProfileCurve.constant(0.0, 3.0),
            altitude_profile=ProfileCurve.constant(0.0, 3.0),
            airspeed_profile=ProfileCurve.constant(0.0, 3.0),
            ambient_temp_profile=ProfileCurve.constant(15.0, 3.0),
            ignition_on=False,
            starter_engaged=False,
            description="Pre-flight avionics check and engine cold state",
        ),
        MissionPhaseDefinition(
            phase_id="P2_START",
            phase_type=MissionPhaseType.START,
            duration_sec=3.0,
            throttle_profile=ProfileCurve.constant(10.0, 3.0),
            altitude_profile=ProfileCurve.constant(0.0, 3.0),
            airspeed_profile=ProfileCurve.constant(0.0, 3.0),
            ambient_temp_profile=ProfileCurve.constant(15.0, 3.0),
            ignition_on=True,
            starter_engaged=True,
            description="Starter engagement, ignition fire, and cranking",
        ),
        MissionPhaseDefinition(
            phase_id="P3_IDLE",
            phase_type=MissionPhaseType.START,
            duration_sec=10.0,
            throttle_profile=ProfileCurve.constant(5.0, 10.0),
            altitude_profile=ProfileCurve.constant(0.0, 10.0),
            airspeed_profile=ProfileCurve.constant(0.0, 10.0),
            ambient_temp_profile=ProfileCurve.constant(15.0, 10.0),
            ignition_on=True,
            starter_engaged=False,
            description="Ground idle warmup and oil circulation",
        ),
        MissionPhaseDefinition(
            phase_id="P4_TAXI",
            phase_type=MissionPhaseType.TAXI,
            duration_sec=15.0,
            throttle_profile=ProfileCurve.smooth(5.0, 18.0, 15.0),
            altitude_profile=ProfileCurve.constant(0.0, 15.0),
            airspeed_profile=ProfileCurve.smooth(0.0, 8.0, 15.0),
            ambient_temp_profile=ProfileCurve.constant(15.0, 15.0),
            ignition_on=True,
            starter_engaged=False,
            description="Low-power taxi to active runway",
        ),
        MissionPhaseDefinition(
            phase_id="P5_TAKEOFF",
            phase_type=MissionPhaseType.TAKEOFF,
            duration_sec=15.0,
            throttle_profile=ProfileCurve.smooth(18.0, 100.0, 15.0),
            altitude_profile=ProfileCurve.linear(0.0, 50.0, 15.0),
            airspeed_profile=ProfileCurve.smooth(8.0, 35.0, 15.0),
            ambient_temp_profile=ProfileCurve.constant(15.0, 15.0),
            ignition_on=True,
            starter_engaged=False,
            description="Maximum takeoff power rollout and initial rotation",
        ),
        MissionPhaseDefinition(
            phase_id="P6_CLIMB",
            phase_type=MissionPhaseType.CLIMB,
            duration_sec=40.0,
            throttle_profile=ProfileCurve.constant(90.0, 40.0),
            altitude_profile=ProfileCurve.smooth(50.0, 3000.0, 40.0),
            airspeed_profile=ProfileCurve.constant(42.0, 40.0),
            ambient_temp_profile=ProfileCurve.linear(15.0, -4.5, 40.0),
            ignition_on=True,
            starter_engaged=False,
            description="En-route climb to surveillance operating altitude",
        ),
        MissionPhaseDefinition(
            phase_id="P7_CRUISE",
            phase_type=MissionPhaseType.CRUISE,
            duration_sec=60.0,
            throttle_profile=ProfileCurve.constant(65.0, 60.0),
            altitude_profile=ProfileCurve.constant(3000.0, 60.0),
            airspeed_profile=ProfileCurve.constant(48.0, 60.0),
            ambient_temp_profile=ProfileCurve.constant(-4.5, 60.0),
            ignition_on=True,
            starter_engaged=False,
            description="Level endurance surveillance loiter at 3000m",
        ),
        MissionPhaseDefinition(
            phase_id="P8_DESCENT",
            phase_type=MissionPhaseType.DESCENT,
            duration_sec=30.0,
            throttle_profile=ProfileCurve.smooth(65.0, 25.0, 30.0),
            altitude_profile=ProfileCurve.smooth(3000.0, 100.0, 30.0),
            airspeed_profile=ProfileCurve.smooth(48.0, 35.0, 30.0),
            ambient_temp_profile=ProfileCurve.linear(-4.5, 14.0, 30.0),
            ignition_on=True,
            starter_engaged=False,
            description="Controlled descent to recovery pattern",
        ),
        MissionPhaseDefinition(
            phase_id="P9_LANDING",
            phase_type=MissionPhaseType.APPROACH_LANDING,
            duration_sec=15.0,
            throttle_profile=ProfileCurve.smooth(25.0, 5.0, 15.0),
            altitude_profile=ProfileCurve.smooth(100.0, 0.0, 15.0),
            airspeed_profile=ProfileCurve.smooth(35.0, 0.0, 15.0),
            ambient_temp_profile=ProfileCurve.constant(15.0, 15.0),
            ignition_on=True,
            starter_engaged=False,
            description="Approach flare, touchdown, and rollout",
        ),
        MissionPhaseDefinition(
            phase_id="P10_SHUTDOWN",
            phase_type=MissionPhaseType.SHUTDOWN,
            duration_sec=10.0,
            throttle_profile=ProfileCurve.constant(0.0, 10.0),
            altitude_profile=ProfileCurve.constant(0.0, 10.0),
            airspeed_profile=ProfileCurve.constant(0.0, 10.0),
            ambient_temp_profile=ProfileCurve.constant(15.0, 10.0),
            ignition_on=False,
            starter_engaged=False,
            description="Engine ignition cut and mechanical spin-down",
        ),
    ],
)

# ==============================================================================
# 2. RAPID_CLIMB_HOT_DAY (Extreme Thermal Stress Benchmark)
# ==============================================================================
RAPID_CLIMB_HOT_DAY = MissionDefinition(
    mission_id="RAPID_CLIMB_HOT_DAY",
    name="Rapid Climb Hot Day Stress Test [SYNTHETIC / PROTOTYPE SCENARIO]",
    description=(
        "SYNTHETIC / PROTOTYPE SCENARIO: High ambient temperature (35°C ISA+20) with maximum continuous "
        "power climb to 3500m to stress test cylinder head temperatures and cooling limits."
    ),
    initial_altitude_m=0.0,
    initial_ambient_temp_c=35.0,
    is_synthetic=True,
    phases=[
        MissionPhaseDefinition(
            phase_id="P1_WARMUP",
            phase_type=MissionPhaseType.START,
            duration_sec=15.0,
            throttle_profile=ProfileCurve.constant(8.0, 15.0),
            altitude_profile=ProfileCurve.constant(0.0, 15.0),
            airspeed_profile=ProfileCurve.constant(0.0, 15.0),
            ambient_temp_profile=ProfileCurve.constant(35.0, 15.0),
            ignition_on=True,
            starter_engaged=False,
            description="Hot-day ground idle stabilization",
        ),
        MissionPhaseDefinition(
            phase_id="P2_TAKEOFF",
            phase_type=MissionPhaseType.TAKEOFF,
            duration_sec=20.0,
            throttle_profile=ProfileCurve.smooth(8.0, 100.0, 20.0),
            altitude_profile=ProfileCurve.linear(0.0, 80.0, 20.0),
            airspeed_profile=ProfileCurve.smooth(0.0, 38.0, 20.0),
            ambient_temp_profile=ProfileCurve.constant(35.0, 20.0),
            ignition_on=True,
            starter_engaged=False,
            description="Maximum takeoff power in high ambient heat",
        ),
        MissionPhaseDefinition(
            phase_id="P3_MAX_CLIMB",
            phase_type=MissionPhaseType.HIGH_POWER,
            duration_sec=60.0,
            throttle_profile=ProfileCurve.constant(98.0, 60.0),
            altitude_profile=ProfileCurve.smooth(80.0, 3500.0, 60.0),
            airspeed_profile=ProfileCurve.constant(45.0, 60.0),
            ambient_temp_profile=ProfileCurve.linear(35.0, 12.0, 60.0),
            ignition_on=True,
            starter_engaged=False,
            description="Sustained 98% power climb testing thermal boundaries",
        ),
        MissionPhaseDefinition(
            phase_id="P4_LEVEL_OFF",
            phase_type=MissionPhaseType.CRUISE,
            duration_sec=30.0,
            throttle_profile=ProfileCurve.smooth(98.0, 60.0, 30.0),
            altitude_profile=ProfileCurve.constant(3500.0, 30.0),
            airspeed_profile=ProfileCurve.constant(50.0, 30.0),
            ambient_temp_profile=ProfileCurve.constant(12.0, 30.0),
            ignition_on=True,
            starter_engaged=False,
            description="Level-off to cruise and thermal stabilization",
        ),
    ],
)

# ==============================================================================
# 3. THROTTLE_DYNAMICS_BENCHMARK (Transient Lag & Inertia Test)
# ==============================================================================
THROTTLE_DYNAMICS_BENCHMARK = MissionDefinition(
    mission_id="THROTTLE_DYNAMICS_BENCHMARK",
    name="Throttle Dynamics Benchmark [SYNTHETIC / PROTOTYPE SCENARIO]",
    description=(
        "SYNTHETIC / PROTOTYPE SCENARIO: Rapid sequence of step and smooth-ramp throttle transients "
        "testing turbocharger manifold pressure lag, governor inertia, and AFR enrichment."
    ),
    initial_altitude_m=1500.0,
    initial_ambient_temp_c=5.0,
    is_synthetic=True,
    phases=[
        MissionPhaseDefinition(
            phase_id="P1_BASELINE_CRUISE",
            phase_type=MissionPhaseType.CRUISE,
            duration_sec=20.0,
            throttle_profile=ProfileCurve.constant(50.0, 20.0),
            altitude_profile=ProfileCurve.constant(1500.0, 20.0),
            airspeed_profile=ProfileCurve.constant(45.0, 20.0),
            ambient_temp_profile=ProfileCurve.constant(5.0, 20.0),
            ignition_on=True,
            starter_engaged=False,
            description="Stable intermediate cruise baseline",
        ),
        MissionPhaseDefinition(
            phase_id="P2_BURST_POWER",
            phase_type=MissionPhaseType.THROTTLE_TRANSIENT,
            duration_sec=15.0,
            throttle_profile=ProfileCurve.step(50.0, 95.0, step_time_sec=2.0, duration_sec=15.0),
            altitude_profile=ProfileCurve.constant(1500.0, 15.0),
            airspeed_profile=ProfileCurve.smooth(45.0, 55.0, 15.0),
            ambient_temp_profile=ProfileCurve.constant(5.0, 15.0),
            ignition_on=True,
            starter_engaged=False,
            description="Rapid step power burst to 95% throttle",
        ),
        MissionPhaseDefinition(
            phase_id="P3_RAPID_CHOP",
            phase_type=MissionPhaseType.THROTTLE_TRANSIENT,
            duration_sec=15.0,
            throttle_profile=ProfileCurve.step(95.0, 20.0, step_time_sec=1.0, duration_sec=15.0),
            altitude_profile=ProfileCurve.constant(1500.0, 15.0),
            airspeed_profile=ProfileCurve.smooth(55.0, 38.0, 15.0),
            ambient_temp_profile=ProfileCurve.constant(5.0, 15.0),
            ignition_on=True,
            starter_engaged=False,
            description="Rapid throttle chop from 95% to 20%",
        ),
        MissionPhaseDefinition(
            phase_id="P4_SMOOTH_RAMP_RECOVERY",
            phase_type=MissionPhaseType.THROTTLE_TRANSIENT,
            duration_sec=20.0,
            throttle_profile=ProfileCurve.smooth(20.0, 70.0, 20.0),
            altitude_profile=ProfileCurve.constant(1500.0, 20.0),
            airspeed_profile=ProfileCurve.smooth(38.0, 48.0, 20.0),
            ambient_temp_profile=ProfileCurve.constant(5.0, 20.0),
            ignition_on=True,
            starter_engaged=False,
            description="Smooth cubic Hermite ramp recovery to 70%",
        ),
    ],
)

# ==============================================================================
# 4. HIGH_ALTITUDE_FERRY (Turbo Boost Limit at Altitude)
# ==============================================================================
HIGH_ALTITUDE_FERRY = MissionDefinition(
    mission_id="HIGH_ALTITUDE_FERRY",
    name="High Altitude Ferry [SYNTHETIC / PROTOTYPE SCENARIO]",
    description=(
        "SYNTHETIC / PROTOTYPE SCENARIO: High-altitude endurance cruise at 4500m (-14°C ISA), "
        "evaluating turbocharger pressure ratio limits, wastegate headroom, and low density air cooling."
    ),
    initial_altitude_m=2000.0,
    initial_ambient_temp_c=2.0,
    is_synthetic=True,
    phases=[
        MissionPhaseDefinition(
            phase_id="P1_FERRY_CLIMB",
            phase_type=MissionPhaseType.CLIMB,
            duration_sec=40.0,
            throttle_profile=ProfileCurve.smooth(60.0, 85.0, 40.0),
            altitude_profile=ProfileCurve.smooth(2000.0, 4500.0, 40.0),
            airspeed_profile=ProfileCurve.constant(46.0, 40.0),
            ambient_temp_profile=ProfileCurve.linear(2.0, -14.2, 40.0),
            ignition_on=True,
            starter_engaged=False,
            description="Climb from 2000m to 4500m high-altitude cruise",
        ),
        MissionPhaseDefinition(
            phase_id="P2_HIGH_ALT_LOITER",
            phase_type=MissionPhaseType.HIGH_ALTITUDE_CRUISE,
            duration_sec=60.0,
            throttle_profile=ProfileCurve.constant(72.0, 60.0),
            altitude_profile=ProfileCurve.constant(4500.0, 60.0),
            airspeed_profile=ProfileCurve.constant(52.0, 60.0),
            ambient_temp_profile=ProfileCurve.constant(-14.2, 60.0),
            ignition_on=True,
            starter_engaged=False,
            description="Level high-altitude transit at 4500m with cold air",
        ),
    ],
)

# ==============================================================================
# 5. EMERGENCY_DESCENT (Steep Power Chop & Ram Air Cooling)
# ==============================================================================
EMERGENCY_DESCENT = MissionDefinition(
    mission_id="EMERGENCY_DESCENT",
    name="Emergency Rapid Descent [SYNTHETIC / PROTOTYPE SCENARIO]",
    description=(
        "SYNTHETIC / PROTOTYPE SCENARIO: Immediate power cut from cruise to idle with steep descent, "
        "testing thermal shock cooling and transient governor spin-down."
    ),
    initial_altitude_m=3500.0,
    initial_ambient_temp_c=-7.0,
    is_synthetic=True,
    phases=[
        MissionPhaseDefinition(
            phase_id="P1_CRUISE_BEFORE_DESCENT",
            phase_type=MissionPhaseType.CRUISE,
            duration_sec=15.0,
            throttle_profile=ProfileCurve.constant(65.0, 15.0),
            altitude_profile=ProfileCurve.constant(3500.0, 15.0),
            airspeed_profile=ProfileCurve.constant(48.0, 15.0),
            ambient_temp_profile=ProfileCurve.constant(-7.0, 15.0),
            ignition_on=True,
            starter_engaged=False,
            description="Initial cruise prior to emergency descent drill",
        ),
        MissionPhaseDefinition(
            phase_id="P2_RAPID_DESCENT",
            phase_type=MissionPhaseType.DESCENT,
            duration_sec=35.0,
            throttle_profile=ProfileCurve.step(65.0, 5.0, step_time_sec=1.0, duration_sec=35.0),
            altitude_profile=ProfileCurve.smooth(3500.0, 300.0, 35.0),
            airspeed_profile=ProfileCurve.smooth(48.0, 60.0, 35.0),
            ambient_temp_profile=ProfileCurve.linear(-7.0, 13.0, 35.0),
            ignition_on=True,
            starter_engaged=False,
            description="Rapid power chop to idle and high-speed steep descent",
        ),
        MissionPhaseDefinition(
            phase_id="P3_RECOVERY_LEVEL_OFF",
            phase_type=MissionPhaseType.CRUISE,
            duration_sec=20.0,
            throttle_profile=ProfileCurve.smooth(5.0, 45.0, 20.0),
            altitude_profile=ProfileCurve.constant(300.0, 20.0),
            airspeed_profile=ProfileCurve.smooth(60.0, 40.0, 20.0),
            ambient_temp_profile=ProfileCurve.constant(13.0, 20.0),
            ignition_on=True,
            starter_engaged=False,
            description="Low-altitude level-off and engine power recovery",
        ),
    ],
)

STANDARD_MISSIONS: dict[str, MissionDefinition] = {
    "SURVEILLANCE_MISSION": SURVEILLANCE_MISSION,
    "RAPID_CLIMB_HOT_DAY": RAPID_CLIMB_HOT_DAY,
    "THROTTLE_DYNAMICS_BENCHMARK": THROTTLE_DYNAMICS_BENCHMARK,
    "HIGH_ALTITUDE_FERRY": HIGH_ALTITUDE_FERRY,
    "EMERGENCY_DESCENT": EMERGENCY_DESCENT,
}


def get_predefined_mission(mission_id: str) -> MissionDefinition | None:
    """Retrieve standard predefined mission definition by case-insensitive identifier."""
    if not mission_id or not isinstance(mission_id, str):
        return None
    return STANDARD_MISSIONS.get(mission_id.strip().upper())
