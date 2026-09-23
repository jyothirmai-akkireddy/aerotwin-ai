"""Causal buffer management, feature extraction, and trend analysis for prognostics."""

from collections import deque

from app.domain.entities.telemetry import TelemetryFrame
from app.domain.ml.models import MLInferenceResult
from app.domain.physics.models import PhysicsTwinResult
from app.domain.prognostics.models import (
    PrognosticIndicator,
    SubsystemDegradation,
    TrendDirection,
)

PROGNOSTIC_FEATURE_SCHEMA_VERSION = "1.0.0"


class CausalTelemetryBuffer:
    """Fixed-capacity strictly causal sliding ring buffer preventing future temporal leakage."""

    def __init__(self, max_capacity: int = 300) -> None:
        self.max_capacity = max_capacity
        self._buffer: deque[dict[str, float]] = deque(maxlen=max_capacity)

    def append(self, entry: dict[str, float]) -> None:
        """Append an observation with O(1) time complexity."""
        self._buffer.append(entry)

    def get_history(self) -> list[dict[str, float]]:
        """Return history strictly in chronological order."""
        return list(self._buffer)

    @property
    def size(self) -> int:
        return len(self._buffer)

    def is_sufficient(self, min_frames: int = 30) -> bool:
        return len(self._buffer) >= min_frames

    def clear(self) -> None:
        self._buffer.clear()


class PrognosticFeatureExtractor:
    """Extracts causal degradation features, regression slopes, stress integrals, and indicators."""

    def __init__(self, epsilon_trend: float = 1.0e-4) -> None:
        self.epsilon_trend = epsilon_trend

    def compute_trend_slope(self, history: list[dict[str, float]]) -> tuple[float, TrendDirection]:
        """Compute ordinary least squares slope beta on Health Index over normalized time."""
        n = len(history)
        if n < 30:
            return 0.0, TrendDirection.UNKNOWN

        t0 = history[0]["timestamp"]
        times = [h["timestamp"] - t0 for h in history]
        his = [h["health_index"] for h in history]

        # Check that time span is non-zero
        total_time = times[-1] - times[0]
        if total_time <= 1e-6:
            return 0.0, TrendDirection.STABLE

        mean_t = sum(times) / n
        mean_hi = sum(his) / n

        num = sum((times[i] - mean_t) * (his[i] - mean_hi) for i in range(n))
        den = sum((times[i] - mean_t) ** 2 for i in range(n))

        if den <= 1e-12:
            return 0.0, TrendDirection.STABLE

        beta = num / den

        if beta < -self.epsilon_trend:
            direction = TrendDirection.DEGRADING
        elif beta > self.epsilon_trend:
            direction = TrendDirection.IMPROVING
        else:
            direction = TrendDirection.STABLE

        return round(beta, 6), direction

    def compute_stress_accumulators(
        self, history: list[dict[str, float]]
    ) -> tuple[float, float, float]:
        """Calculate cumulative mechanical, thermal, and load stress integrals."""
        if len(history) < 2:
            return 0.0, 0.0, 0.0

        cum_thermal_stress = 0.0
        cum_map_stress = 0.0
        cum_vib_stress = 0.0

        for i in range(1, len(history)):
            dt = max(0.0, history[i]["timestamp"] - history[i - 1]["timestamp"])
            # Thermal stress: excess CHT above nominal threshold (120 °C)
            cht = history[i].get("cht_mean", 95.0)
            if cht > 120.0:
                cum_thermal_stress += (cht - 120.0) * dt

            # High load MAP stress: excess manifold pressure above 35 inHg
            map_val = history[i].get("manifold_pressure", 29.5)
            if map_val > 35.0:
                cum_map_stress += (map_val - 35.0) * dt

            # Vibration stress: excess vibration above 2.0 g
            vib = history[i].get("vibration_rms", 1.15)
            if vib > 2.0:
                cum_vib_stress += (vib - 2.0) * dt

        return (
            round(cum_thermal_stress, 3),
            round(cum_map_stress, 3),
            round(cum_vib_stress, 3),
        )

    def extract_indicators(
        self,
        frame: TelemetryFrame,
        physics: PhysicsTwinResult | None,
        subsystems: SubsystemDegradation,
        trend_dir: TrendDirection,
    ) -> list[PrognosticIndicator]:
        """Extract key diagnostic telemetry indicators with deviation severity."""
        indicators: list[PrognosticIndicator] = []

        # 1. Oil Pressure
        exp_oil_p = (
            physics.expected_state.oil_pressure if physics and physics.expected_state else 3.8
        )
        oil_p_raw = abs(frame.oil_pressure - exp_oil_p)
        oil_p_norm = subsystems.lubrication.normalized_deviation
        sev_oil_p = "NORMAL"
        if oil_p_norm >= 3.0:
            sev_oil_p = "CRITICAL"
        elif oil_p_norm >= 2.0:
            sev_oil_p = "WARNING"
        elif oil_p_norm >= 1.0:
            sev_oil_p = "ADVISORY"

        indicators.append(
            PrognosticIndicator(
                name="oil_pressure",
                current_value=round(frame.oil_pressure, 2),
                baseline_value=round(exp_oil_p, 2),
                raw_deviation=round(oil_p_raw, 2),
                normalized_deviation=round(oil_p_norm, 2),
                unit="bar",
                severity=sev_oil_p,
                trend=trend_dir,
            )
        )

        # 2. Oil Temperature
        exp_oil_t = (
            physics.expected_state.oil_temperature if physics and physics.expected_state else 85.0
        )
        oil_t_raw = abs(frame.oil_temperature - exp_oil_t)
        sev_oil_t = "NORMAL"
        if frame.oil_temperature >= 120.0:
            sev_oil_t = "CRITICAL"
        elif frame.oil_temperature >= 105.0:
            sev_oil_t = "WARNING"
        elif frame.oil_temperature >= 95.0:
            sev_oil_t = "ADVISORY"

        indicators.append(
            PrognosticIndicator(
                name="oil_temperature",
                current_value=round(frame.oil_temperature, 1),
                baseline_value=round(exp_oil_t, 1),
                raw_deviation=round(oil_t_raw, 1),
                normalized_deviation=round(oil_t_raw / 3.0, 2),
                unit="°C",
                severity=sev_oil_t,
                trend=trend_dir,
            )
        )

        # 3. CHT Thermal Imbalance
        cht_spread = max(frame.cht) - min(frame.cht)
        sev_cht = "NORMAL"
        if cht_spread >= 30.0:
            sev_cht = "CRITICAL"
        elif cht_spread >= 20.0:
            sev_cht = "WARNING"
        elif cht_spread >= 12.0:
            sev_cht = "ADVISORY"

        indicators.append(
            PrognosticIndicator(
                name="cht_spread_imbalance",
                current_value=round(cht_spread, 1),
                baseline_value=5.5,
                raw_deviation=round(max(0.0, cht_spread - 5.5), 1),
                normalized_deviation=round(cht_spread / 8.0, 2),
                unit="°C",
                severity=sev_cht,
                trend=trend_dir,
            )
        )

        # 4. Vibration RMS
        exp_vib = (
            physics.expected_state.vibration_rms if physics and physics.expected_state else 1.15
        )
        vib_raw = abs(frame.vibration_rms - exp_vib)
        vib_norm = subsystems.rotational_vibration.normalized_deviation
        sev_vib = "NORMAL"
        if frame.vibration_rms >= 4.0:
            sev_vib = "CRITICAL"
        elif frame.vibration_rms >= 2.5:
            sev_vib = "WARNING"
        elif frame.vibration_rms >= 1.6:
            sev_vib = "ADVISORY"

        indicators.append(
            PrognosticIndicator(
                name="vibration_rms",
                current_value=round(frame.vibration_rms, 2),
                baseline_value=round(exp_vib, 2),
                raw_deviation=round(vib_raw, 2),
                normalized_deviation=round(vib_norm, 2),
                unit="g",
                severity=sev_vib,
                trend=trend_dir,
            )
        )

        return indicators

    def construct_feature_vector(
        self,
        health_index: float,
        beta_slope: float,
        subsystems: SubsystemDegradation,
        frame: TelemetryFrame,
        stress_accumulators: tuple[float, float, float],
        ml: MLInferenceResult | None,
    ) -> list[float]:
        """Construct deterministic 12-dimensional prognostic feature vector."""
        cum_thermal, cum_map, cum_vib = stress_accumulators
        cht_spread = max(frame.cht) - min(frame.cht)
        anom_score = ml.anomaly.score if ml and ml.anomaly else 0.0

        return [
            float(health_index),
            float(beta_slope),
            float(subsystems.lubrication.normalized_deviation),
            float(subsystems.thermal.normalized_deviation),
            float(subsystems.turbocharger.normalized_deviation),
            float(subsystems.rotational_vibration.normalized_deviation),
            float(cht_spread),
            float(frame.oil_temperature),
            float(frame.oil_pressure),
            float(cum_thermal),
            float(cum_map),
            float(anom_score),
        ]
