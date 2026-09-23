"""Enumerations for mission definitions, phase types, and transition curves.

PROTOTYPE DISCLAIMER:
These enums describe synthetic benchmark flight envelopes for research/prototyping.
They do not represent certified flight envelopes or OEM procedures.
"""

from enum import Enum


class MissionPhaseType(str, Enum):
    """Authoritative domain classification of flight phases."""

    PRE_START = "PRE_START"
    START = "START"
    TAXI = "TAXI"
    TAKEOFF = "TAKEOFF"
    CLIMB = "CLIMB"
    CRUISE = "CRUISE"
    HIGH_ALTITUDE_CRUISE = "HIGH_ALTITUDE_CRUISE"
    HIGH_POWER = "HIGH_POWER"
    THROTTLE_TRANSIENT = "THROTTLE_TRANSIENT"
    DESCENT = "DESCENT"
    APPROACH_LANDING = "APPROACH_LANDING"
    SHUTDOWN = "SHUTDOWN"


class ProfileTransitionType(str, Enum):
    """Mathematical transition mode for scalar control and environmental profiles."""

    CONSTANT = "CONSTANT"
    STEP = "STEP"
    LINEAR_RAMP = "LINEAR_RAMP"
    SMOOTH_RAMP = "SMOOTH_RAMP"


class ControlTargetParameter(str, Enum):
    """Whitelist of valid physical inputs to the engine simulator."""

    THROTTLE_PCT = "throttle_pct"
    ALTITUDE_M = "altitude_m"
    AMBIENT_TEMP_C = "ambient_temp_c"
    AIRSPEED_MS = "airspeed_ms"
