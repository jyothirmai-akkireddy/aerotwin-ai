# AeroTwin AI — Physics & Mission Simulation Specification

**Document Reference**: `AEROTWIN-SIM-001`  
**Classification**: Simulation Engine Design  
**Status**: APPROVED BASELINE  

---

## 1. Simulation Mission Profiles

To stress-test the Digital Twin across varied operational envelopes, the simulation engine supports five distinct MALE UAV mission scenarios:

1. **Standard Surveillance Flight**:
   - Engine start → Taxi → Takeoff climb (100% throttle, 5800 RPM) to 3500 m ASL → Level cruise (65% throttle, 4800 RPM) for 60 minutes → Descent → Landing rollout.
2. **High-Altitude Loiter (6000 m - 9000 m ASL)**:
   - Low ambient temperature (-35 °C to -50 °C), low air density requiring high turbocharger boost ratio ($MAP / P_{\text{ambient}} > 2.5$) and elevated turbine temperatures.
3. **Hot Weather & High Thermal Stress**:
   - High ambient OAT ($+45^\circ\text{C}$), reduced cooling air mass flow through cowlings, challenging CHT and oil radiator thermal equilibrium.
4. **Rapid Throttle Dynamics & Transients**:
   - Abrupt maneuvers with step changes in throttle position (30% $\leftrightarrow$ 100%), testing governor response, turbo lag, and fuel rail pressure damping.
5. **Endurance Degradation Flight**:
   - Long-duration cruise simulating cumulative friction wear, oil viscosity breakdown, and thermal drift over simulated tens of hours.

---

## 2. Controlled Fault Injection Scenarios

Fault injection is governed by the `FaultInjectionMatrix` and can be toggled dynamically during simulation runs:

| Fault Code | Failure Mode | Simulated Physical Manifestation | Diagnostic Expected Signature |
|---|---|---|---|
| `FAULT_MISFIRE_CYL_X` | Spark / Ignition Failure in Cylinder X | Rapid drop in CHT & EGT for Cylinder X; unburnt fuel causes slight EGT rise downstream; RPM drops; vibration increases. | Negative CHT/EGT residual on Cyl X; high vibration residual. |
| `FAULT_INJECTOR_CLOG` | Partially Clogged Fuel Injector | Lean mixture in affected cylinder; localized EGT spike; reduced fuel flow. | Positive EGT residual; negative fuel flow residual. |
| `FAULT_OIL_PRESSURE_LOSS` | Oil Pump Relief Valve Malfunction / Leak | Sharp decrease in oil pressure below 2.0 bar; gradual oil temperature rise due to boundary lubrication friction. | Large negative oil pressure residual; delayed positive oil temp residual. |
| `FAULT_COOLING_BAFFLE_BLOCK`| Cowling Air Baffle Blockage | Exponential rise in CHT across Cylinders 1 & 3; coolant temperature increases; EGT remains normal. | High positive CHT residuals with nominal EGT residuals. |
| `FAULT_SENSOR_DRIFT_CHT` | Thermocouple Sensor Calibration Drift | Linear artificial offset added to single CHT channel without accompanying physical change in coolant or EGT. | Single-channel CHT residual without thermodynamic cross-channel correlation. |

*Note: The Ground Station UI will visibly display a banner: `SIMULATION ACTIVE: FAULT INJECTED [Fault Code]` to ensure complete operational transparency.*
