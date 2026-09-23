"""Simulation state tracking continuous physical state variables and state transitions."""

from enum import Enum

from pydantic import BaseModel, Field


class EngineOperatingState(str, Enum):
    """Engine operational state machine modes."""

    OFF = "OFF"
    STARTING = "STARTING"
    IDLE = "IDLE"
    ACCELERATING = "ACCELERATING"
    CRUISE = "CRUISE"
    HIGH_POWER = "HIGH_POWER"
    DECELERATING = "DECELERATING"
    SHUTDOWN = "SHUTDOWN"


class SimulationInternalState(BaseModel):
    """Continuous physical state variables before sensor dynamics and noise injection."""

    sim_time: float = 0.0
    operating_state: EngineOperatingState = EngineOperatingState.OFF
    throttle_pct: float = 0.0
    commanded_throttle_pct: float = 0.0

    # Powertrain dynamics
    rpm: float = 0.0
    target_rpm: float = 0.0
    manifold_pressure_inhg: float = 29.92
    fuel_flow_lph: float = 0.0
    fuel_pressure_bar: float = 3.0
    injection_timing_deg: float = 20.0

    # Thermal states (°C)
    cht_c: list[float] = Field(default_factory=lambda: [15.0, 15.0, 15.0, 15.0])
    egt_c: list[float] = Field(default_factory=lambda: [20.0, 20.0, 20.0, 20.0])
    coolant_temp_c: float = 15.0
    oil_temperature_c: float = 15.0
    oil_pressure_bar: float = 0.0

    # Mechanical & Electrical
    vibration_rms_g: float = 0.0
    battery_voltage_v: float = 24.5
    alternator_current_a: float = 0.0
    alternator_status: str = "OK"

    # Flight Environment
    altitude_m: float = 0.0
    ambient_temp_c: float = 15.0
    true_airspeed_ms: float = 0.0
