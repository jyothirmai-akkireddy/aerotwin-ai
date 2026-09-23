"""Telemetry validation layer enforcing structural, prototype range, and physical consistency rules.

PROTOTYPE DISCLAIMER:
Validation limits defined herein represent engineering prototype bounds for a generic
4-cylinder aero-piston engine inspired by the Rotax 914/915 class. They do NOT represent
certified aerospace operating limitations or manufacturer flight manuals.
"""

import math

from pydantic import BaseModel, Field

from app.domain.entities.telemetry import QualityStatus, TelemetryFrame


class TelemetryValidationResult(BaseModel):
    """Rich validation outcome detailing validity, quality classification, errors, and warnings."""

    is_valid: bool = True
    quality: QualityStatus = QualityStatus.VALID
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    field_checks: dict[str, bool] = Field(default_factory=dict)

    def add_error(self, message: str) -> None:
        self.errors.append(message)
        self.is_valid = False
        self.quality = QualityStatus.INVALID

    def add_warning(self, message: str) -> None:
        self.warnings.append(message)
        if self.quality == QualityStatus.VALID:
            self.quality = QualityStatus.DEGRADED


class TelemetryValidator:
    """Stateful validator checking individual telemetry frames and sequential continuity."""

    # Prototype boundary assumptions (Parameter: (min_valid, max_valid, unit, description))
    BOUNDS: dict[str, tuple[float, float]] = {
        "rpm": (0.0, 6500.0),  # 0 to transient redline
        "manifold_pressure": (8.0, 52.0),  # inHg (turbo boost / closed throttle range)
        "throttle_position": (0.0, 100.0),  # 0 - 100 percent
        "fuel_flow": (0.0, 60.0),  # L/h
        "fuel_pressure": (0.4, 6.0),  # bar (residual cold / operating rail pressure)
        "injection_timing": (0.0, 42.0),  # °BTDC (0 when stopped)
        "coolant_temp": (-30.0, 130.0),  # °C
        "oil_temperature": (-20.0, 160.0),  # °C
        "oil_pressure": (0.0, 10.0),  # bar
        "vibration_rms": (0.0, 15.0),  # g (m/s^2)
        "battery_voltage": (9.0, 32.0),  # V (24V/28V bus)
        "alternator_current": (0.0, 60.0),  # A
        "altitude": (-200.0, 12000.0),  # m ASL
        "ambient_temp": (-60.0, 60.0),  # °C
        "true_airspeed": (0.0, 120.0),  # m/s
    }

    # Cylinder bounds (°C)
    CHT_BOUNDS = (-30.0, 250.0)
    EGT_BOUNDS = (-50.0, 1000.0)

    # Max plausible rate of change (slew rate per second)
    MAX_RPM_SLEW_PER_SEC = 3500.0  # RPM/s (propeller and flywheel inertia)
    MAX_CHT_SLEW_PER_SEC = 15.0  # °C/s (cylinder head metal thermal inertia)

    def __init__(self, track_history: bool = True):
        self.track_history = track_history
        self._last_frame: TelemetryFrame | None = None

    def reset(self) -> None:
        """Reset sequence and temporal continuity tracking."""
        self._last_frame = None

    def validate(self, frame: TelemetryFrame) -> TelemetryValidationResult:
        """Validate a single telemetry frame against structural, boundary, and physical rules."""
        result = TelemetryValidationResult()

        # 1. Monotonicity & Timestamp Validity
        if not math.isfinite(frame.timestamp) or frame.timestamp <= 0.0:
            result.add_error(f"Timestamp {frame.timestamp} must be positive and finite.")
            return result

        if self.track_history and self._last_frame is not None:
            dt = frame.timestamp - self._last_frame.timestamp
            if dt <= 0.0:
                result.add_error(
                    f"Non-monotonic timestamp detected: current={frame.timestamp:.4f}, "
                    f"previous={self._last_frame.timestamp:.4f} (dt={dt:.4f}s)"
                )
            elif dt > 5.0:
                result.add_warning(f"Large telemetry gap detected: dt={dt:.2f}s")

            # Sequence ID check
            seq_diff = frame.sequence_id - self._last_frame.sequence_id
            if seq_diff <= 0:
                result.add_error(
                    f"Out-of-order or duplicate sequence ID: current={frame.sequence_id}, "
                    f"previous={self._last_frame.sequence_id}"
                )
            elif seq_diff > 1:
                result.add_warning(
                    f"Dropped frames detected: expected sequence {self._last_frame.sequence_id + 1}, "
                    f"received {frame.sequence_id} (dropped {seq_diff - 1} frames)"
                )

        # 2. Check Finiteness and Single-Channel Scalar Bounds
        for field_name, (min_val, max_val) in self.BOUNDS.items():
            val = getattr(frame, field_name, None)
            if val is None:
                result.add_error(f"Required field '{field_name}' is missing.")
                result.field_checks[field_name] = False
                continue

            if not isinstance(val, int | float) or not math.isfinite(val):
                result.add_error(f"Field '{field_name}' value {val} is not finite.")
                result.field_checks[field_name] = False
                continue

            if not (min_val <= val <= max_val):
                result.add_error(
                    f"Field '{field_name}' value {val} outside prototype range [{min_val}, {max_val}]."
                )
                result.field_checks[field_name] = False
            else:
                result.field_checks[field_name] = True

        # 3. Check Multi-Cylinder Temperatures (CHT & EGT)
        self._validate_cylinder_list(frame.cht, "cht", self.CHT_BOUNDS, result)
        self._validate_cylinder_list(frame.egt, "egt", self.EGT_BOUNDS, result)

        # 4. Slew Rate Checks (Temporal continuity)
        if self.track_history and self._last_frame is not None:
            dt = frame.timestamp - self._last_frame.timestamp
            if dt > 0.0:
                # RPM slew
                rpm_rate = abs(frame.rpm - self._last_frame.rpm) / dt
                if rpm_rate > self.MAX_RPM_SLEW_PER_SEC:
                    result.add_error(
                        f"Unphysical RPM slew rate: {rpm_rate:.1f} RPM/s exceeds limit {self.MAX_RPM_SLEW_PER_SEC}"
                    )

                # CHT slew (max across all 4 cylinders)
                for cyl_idx in range(4):
                    cht_rate = abs(frame.cht[cyl_idx] - self._last_frame.cht[cyl_idx]) / dt
                    if cht_rate > self.MAX_CHT_SLEW_PER_SEC:
                        result.add_error(
                            f"Unphysical CHT rate on Cylinder {cyl_idx + 1}: {cht_rate:.1f} °C/s "
                            f"exceeds thermal limit {self.MAX_CHT_SLEW_PER_SEC}"
                        )

        # 5. Impossible Physical Combinations (Physical Invariants)
        # Running at high power without fuel
        if frame.rpm > 3000.0 and frame.fuel_flow < 0.5:
            result.add_error(
                f"Impossible condition: High RPM ({frame.rpm:.0f}) with near-zero fuel flow ({frame.fuel_flow:.2f} L/h)"
            )

        # Engine running at high power with zero oil pressure (catastrophic failure or sensor disconnect)
        if frame.rpm > 2500.0 and frame.oil_pressure < 0.5:
            result.add_warning(
                f"Severe anomaly: High RPM ({frame.rpm:.0f}) with critically low oil pressure ({frame.oil_pressure:.2f} bar)"
            )

        # 6. Quality flag synchronization
        if not result.is_valid:
            result.quality = QualityStatus.INVALID
        elif len(result.warnings) > 0 and result.quality == QualityStatus.VALID:
            result.quality = QualityStatus.DEGRADED

        # Update last known frame if valid or for sequence continuity
        if self.track_history:
            self._last_frame = frame

        return result

    def _validate_cylinder_list(
        self,
        values: list[float],
        name: str,
        bounds: tuple[float, float],
        result: TelemetryValidationResult,
    ) -> None:
        min_val, max_val = bounds
        if not isinstance(values, list) or len(values) != 4:
            result.add_error(f"'{name}' must be an array of exactly 4 cylinder readings.")
            result.field_checks[name] = False
            return

        all_ok = True
        for idx, temp in enumerate(values):
            if not isinstance(temp, int | float) or not math.isfinite(temp):
                result.add_error(f"'{name}[{idx}]' value {temp} is not finite.")
                all_ok = False
            elif not (min_val <= temp <= max_val):
                result.add_error(
                    f"'{name}[{idx}]' value {temp}°C outside range [{min_val}, {max_val}]."
                )
                all_ok = False

        result.field_checks[name] = all_ok
