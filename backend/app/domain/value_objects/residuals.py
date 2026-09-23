"""ResidualVector value object representing deviations between actual and expected twin states."""

from pydantic import BaseModel, Field


class ResidualVector(BaseModel):
    """Vector of deviations (actual - expected) computed by the physics twin."""

    timestamp: float = Field(..., description="Timestamp of observation")
    rpm_residual: float = Field(default=0.0, description="Actual RPM - Expected RPM")
    map_residual: float = Field(default=0.0, description="Actual MAP - Expected MAP (inHg)")
    fuel_flow_residual: float = Field(default=0.0, description="Actual FF - Expected FF (L/h)")
    cht_residuals: list[float] = Field(
        default_factory=lambda: [0.0, 0.0, 0.0, 0.0],
        min_length=4,
        max_length=4,
        description="CHT residuals for Cylinders 1-4 (°C)",
    )
    egt_residuals: list[float] = Field(
        default_factory=lambda: [0.0, 0.0, 0.0, 0.0],
        min_length=4,
        max_length=4,
        description="EGT residuals for Cylinders 1-4 (°C)",
    )
    oil_pressure_residual: float = Field(default=0.0, description="Oil pressure residual (bar)")
    oil_temperature_residual: float = Field(default=0.0, description="Oil temp residual (°C)")
    vibration_residual: float = Field(default=0.0, description="Vibration RMS residual (g)")

    def to_feature_array(self) -> list[float]:
        """Flatten residuals into a 14-dimensional feature vector for ML inference."""
        return [
            self.rpm_residual,
            self.map_residual,
            self.fuel_flow_residual,
            *self.cht_residuals,
            *self.egt_residuals,
            self.oil_pressure_residual,
            self.oil_temperature_residual,
            self.vibration_residual,
        ]
