"""Mission simulation domain package."""

from app.domain.mission.catalog import (
    EMERGENCY_DESCENT,
    HIGH_ALTITUDE_FERRY,
    RAPID_CLIMB_HOT_DAY,
    STANDARD_MISSIONS,
    SURVEILLANCE_MISSION,
    THROTTLE_DYNAMICS_BENCHMARK,
    get_predefined_mission,
)
from app.domain.mission.enums import (
    ControlTargetParameter,
    MissionPhaseType,
    ProfileTransitionType,
)
from app.domain.mission.events import MissionControlEvent, MissionFaultEvent
from app.domain.mission.models import (
    MissionDefinition,
    MissionPhaseDefinition,
    MissionSimulationSummary,
    MissionTelemetryContext,
    PhaseSummary,
)
from app.domain.mission.profiles import ProfileCurve

__all__ = [
    "ControlTargetParameter",
    "EMERGENCY_DESCENT",
    "HIGH_ALTITUDE_FERRY",
    "MissionControlEvent",
    "MissionDefinition",
    "MissionFaultEvent",
    "MissionPhaseDefinition",
    "MissionPhaseType",
    "MissionSimulationSummary",
    "MissionTelemetryContext",
    "PhaseSummary",
    "ProfileCurve",
    "ProfileTransitionType",
    "RAPID_CLIMB_HOT_DAY",
    "STANDARD_MISSIONS",
    "SURVEILLANCE_MISSION",
    "THROTTLE_DYNAMICS_BENCHMARK",
    "get_predefined_mission",
]
