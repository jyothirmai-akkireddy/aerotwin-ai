"""Deterministic scalar profile curves for flight mission control and environment.

Provides CONSTANT, STEP, LINEAR_RAMP, and cubic SMOOTH_RAMP (Hermite smoothstep)
interpolations with strict C1 derivative continuity and zero overshoot.
"""

import math

from pydantic import BaseModel, Field, model_validator

from app.domain.mission.enums import ProfileTransitionType


class ProfileCurve(BaseModel):
    """Evaluation model for a continuous or step scalar profile over time."""

    transition_type: ProfileTransitionType = Field(default=ProfileTransitionType.CONSTANT)
    start_value: float = Field(..., description="Initial value at phase onset")
    end_value: float = Field(..., description="Target value at phase completion")
    duration_sec: float = Field(
        ..., gt=0.0, description="Total active duration of the phase/curve (seconds)"
    )
    step_time_sec: float = Field(
        default=0.0,
        ge=0.0,
        description="Elapsed seconds within phase at which STEP transition triggers",
    )

    @model_validator(mode="after")
    def validate_curve_parameters(self) -> "ProfileCurve":
        """Verify parameters are finite and step_time is within duration."""
        if not math.isfinite(self.start_value):
            raise ValueError("start_value must be a finite number")
        if not math.isfinite(self.end_value):
            raise ValueError("end_value must be a finite number")
        if not math.isfinite(self.duration_sec) or self.duration_sec <= 0.0:
            raise ValueError("duration_sec must be a positive finite number")
        if not math.isfinite(self.step_time_sec) or self.step_time_sec < 0.0:
            raise ValueError("step_time_sec must be non-negative and finite")
        if self.step_time_sec > self.duration_sec:
            raise ValueError(
                f"step_time_sec ({self.step_time_sec}) cannot exceed duration_sec ({self.duration_sec})"
            )
        return self

    def evaluate(self, elapsed_sec: float) -> float:
        """Evaluate the curve at elapsed_sec within the phase.

        Boundary handling:
            elapsed_sec <= 0.0 returns start_value
            elapsed_sec >= duration_sec returns end_value (except CONSTANT returns start_value)
        """
        if self.transition_type == ProfileTransitionType.CONSTANT:
            return self.start_value

        if self.transition_type == ProfileTransitionType.STEP:
            if elapsed_sec < self.step_time_sec:
                return self.start_value
            return self.end_value

        # Normalized progress parameter tau clamped strictly to [0.0, 1.0]
        tau = max(0.0, min(1.0, elapsed_sec / self.duration_sec))

        if self.transition_type == ProfileTransitionType.LINEAR_RAMP:
            return self.start_value + (self.end_value - self.start_value) * tau

        if self.transition_type == ProfileTransitionType.SMOOTH_RAMP:
            # Cubic Hermite Smoothstep: S(tau) = 3*tau^2 - 2*tau^3
            # Invariants: S(0) = 0, S(1) = 1, S'(0) = 0, S'(1) = 0
            s_tau = (3.0 * tau * tau) - (2.0 * tau * tau * tau)
            return self.start_value + (self.end_value - self.start_value) * s_tau

        return self.start_value

    @classmethod
    def constant(cls, value: float, duration_sec: float) -> "ProfileCurve":
        """Convenience factory for a constant value profile."""
        return cls(
            transition_type=ProfileTransitionType.CONSTANT,
            start_value=value,
            end_value=value,
            duration_sec=duration_sec,
        )

    @classmethod
    def linear(cls, start: float, end: float, duration_sec: float) -> "ProfileCurve":
        """Convenience factory for a linear ramp profile."""
        return cls(
            transition_type=ProfileTransitionType.LINEAR_RAMP,
            start_value=start,
            end_value=end,
            duration_sec=duration_sec,
        )

    @classmethod
    def smooth(cls, start: float, end: float, duration_sec: float) -> "ProfileCurve":
        """Convenience factory for a cubic Hermite smoothstep profile."""
        return cls(
            transition_type=ProfileTransitionType.SMOOTH_RAMP,
            start_value=start,
            end_value=end,
            duration_sec=duration_sec,
        )

    @classmethod
    def step(
        cls, start: float, end: float, step_time_sec: float, duration_sec: float
    ) -> "ProfileCurve":
        """Convenience factory for a step change profile."""
        return cls(
            transition_type=ProfileTransitionType.STEP,
            start_value=start,
            end_value=end,
            step_time_sec=step_time_sec,
            duration_sec=duration_sec,
        )
