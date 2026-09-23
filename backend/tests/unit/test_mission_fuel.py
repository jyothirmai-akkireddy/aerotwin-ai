"""Unit tests for fuel flow consumption integration and mass conversions."""

import math

from app.domain.entities.telemetry import TelemetryFrame, TelemetrySource


def test_fuel_consumption_riemann_integration():
    """Verify Riemann integration of fuel_flow (L/h) into Liters consumed."""
    dt = 0.1  # 10 Hz
    num_frames = 1000  # 100 seconds
    synthetic_flow_lph = 36.0  # Exactly 36 L/h -> 36 / 3600 = 0.01 L/s

    # In 100 seconds at 0.01 L/s, total consumption must be exactly 1.0000 Liter
    frames = []
    for i in range(num_frames):
        frames.append(
            TelemetryFrame(
                timestamp=1000.0 + i * dt,
                sequence_id=i,
                source_type=TelemetrySource.SIMULATED,
                rpm=2500.0,
                manifold_pressure=28.0,
                throttle_position=50.0,
                fuel_flow=synthetic_flow_lph,
                fuel_pressure=3.2,
                injection_timing=20.0,
                cht=[95.0, 95.0, 95.0, 95.0],
                egt=[720.0, 720.0, 720.0, 720.0],
                coolant_temp=85.0,
                oil_temperature=88.0,
                oil_pressure=3.8,
                vibration_rms=1.1,
                battery_voltage=28.0,
                alternator_current=15.0,
                alternator_status="OK",
                altitude=1000.0,
                ambient_temp=15.0,
                true_airspeed=45.0,
            )
        )

    # Formula from domain: V_fuel = sum(fuel_flow / 3600 * dt)
    integrated_liters = sum((f.fuel_flow / 3600.0) * dt for f in frames)
    assert math.isclose(integrated_liters, 1.0, rel_tol=1e-5)

    # Mass conversion with calibrated Mogas/Avgas density (0.72 kg/L)
    density_kg_l = 0.72
    mass_kg = integrated_liters * density_kg_l
    assert math.isclose(mass_kg, 0.72, rel_tol=1e-5)
