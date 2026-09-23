"""Deterministic sensor fault injection definitions and application hooks."""

from enum import Enum

from pydantic import BaseModel, Field


class SensorFaultType(str, Enum):
    """Supported sensor fault modes for synthetic telemetry."""

    BIAS = "BIAS"  # Fixed constant offset added to reading
    DRIFT = "DRIFT"  # Linear ramp offset growing over time
    STUCK = "STUCK"  # Sensor freezes at fixed value
    DROPOUT = "DROPOUT"  # Sensor drops to 0.0 or NaN, marked INVALID
    NOISE_SPIKE = "NOISE_SPIKE"  # Bounded variance amplification


class EngineFaultType(str, Enum):
    """Extension points for future engine-level thermodynamic faults (Phase 4)."""

    NONE = "NONE"
    MISFIRE = "MISFIRE"
    INJECTOR_CLOG = "INJECTOR_CLOG"
    OIL_LEAK = "OIL_LEAK"
    COOLING_BLOCKAGE = "COOLING_BLOCKAGE"
    TURBO_WASTEGATE_STUCK = "TURBO_WASTEGATE_STUCK"


class SensorFaultConfig(BaseModel):
    """Specification of a reproducible sensor fault scenario."""

    target_channel: str = Field(
        ..., description="Target sensor name, e.g. 'oil_pressure' or 'cht_2'"
    )
    fault_type: SensorFaultType
    start_time_sec: float = Field(..., ge=0.0)
    end_time_sec: float | None = Field(default=None, description="None = persists indefinitely")
    magnitude: float = Field(
        default=0.0, description="Offset magnitude for bias, or frozen value for stuck"
    )
    drift_rate_per_sec: float = Field(default=0.0, description="Rate of drift per second")
    noise_multiplier: float = Field(default=3.0, ge=1.0, description="Noise factor for noise spike")

    def is_active(self, current_time: float) -> bool:
        """Return True if fault is active at given simulation time."""
        if current_time < self.start_time_sec:
            return False
        if self.end_time_sec is not None and current_time >= self.end_time_sec:
            return False
        return True


class FaultController:
    """Controller managing active sensor faults and modifying simulated outputs."""

    def __init__(self, fault_configs: list[SensorFaultConfig] | None = None):
        self.fault_configs = fault_configs or []

    def add_fault(self, fault: SensorFaultConfig) -> None:
        self.fault_configs.append(fault)

    def clear(self) -> None:
        self.fault_configs.clear()

    def apply_scalar_fault(
        self,
        channel_name: str,
        clean_value: float,
        sim_time: float,
        gaussian_noise: float = 0.0,
    ) -> tuple[float, bool]:
        """Apply active sensor faults to a scalar channel.

        Returns:
            tuple of (modified_value, is_fault_injected: bool)
        """
        modified_value = clean_value
        is_injected = False

        for fault in self.fault_configs:
            if fault.target_channel == channel_name and fault.is_active(sim_time):
                is_injected = True
                elapsed_fault_time = sim_time - fault.start_time_sec

                if fault.fault_type == SensorFaultType.BIAS:
                    modified_value += fault.magnitude
                elif fault.fault_type == SensorFaultType.DRIFT:
                    modified_value += fault.magnitude + (
                        fault.drift_rate_per_sec * elapsed_fault_time
                    )
                elif fault.fault_type == SensorFaultType.STUCK:
                    modified_value = fault.magnitude
                elif fault.fault_type == SensorFaultType.DROPOUT:
                    modified_value = 0.0
                elif fault.fault_type == SensorFaultType.NOISE_SPIKE:
                    modified_value += gaussian_noise * fault.noise_multiplier

        return modified_value, is_injected
