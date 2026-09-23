# AeroTwin AI — Physics Models Reference Manual

**Document Version**: 1.0.0  
**Phase**: Phase 5 — Physics-Informed Digital Twin  
**Target Engine**: Generic Turbocharged 4-Stroke Aero-Piston Engine (Rotax 914/915 iS Baseline)

---

## 1. Introduction

The AeroTwin AI Physics-Informed Digital Twin implements six low-order analytical domain models. Each model balances mathematical rigor, numerical determinism, and real-time execution capability ($< 1.0\text{ ms}$ budget).

All models are low-order engineering approximations developed for real-time fault residual generation; they are **PROTOTYPE APPROXIMATIONS** and are not certified flight simulator or FAA/EASA flight control algorithms.

---

## 2. Model 1: Induction & Turbocharger Pressure Model

**Implementation**: [`app.domain.physics.induction.InductionPressureModel`](file:///d:/sih/backend/app/domain/physics/induction.py)

### 2.1 Environmental Boundary Conditions (Troposphere Lapse)
Ambient static barometric pressure $p_{\text{amb}}$ is calculated using the ICAO Standard Atmosphere (ISA) barometric lapse formula for the troposphere ($h \le 11,000\text{ m}$):
$$T_{\text{local}} = \max\left(180.0, T_0 - L \cdot h\right)$$
$$p_{\text{amb}}(h) = p_0 \cdot \left(\frac{T_{\text{local}}}{T_0}\right)^{\frac{g_0 \cdot M}{R \cdot L}}$$
- $T_0 = 288.15\text{ K}$ (15°C sea level)
- $p_0 = 29.921\text{ inHg}$ (1013.25 hPa)
- $L = 0.0065\text{ K/m}$
- Exponent: $\frac{g_0 M}{R L} \approx 5.2559$

### 2.2 Manifold Absolute Pressure (MAP)
1. **Throttled Naturally Aspirated Base Pressure**:
   $$p_{\text{na}} = p_{\text{amb}} \cdot \left(k_{\text{closed}} + (1 - k_{\text{closed}}) \cdot \alpha_{\text{norm}}\right)$$
   Where $k_{\text{closed}} = 0.35$ represents closed-throttle idle manifold vacuum fraction, and $\alpha_{\text{norm}} \in [0.0, 1.0]$ is throttle position.
2. **Turbocharger Pressure Ratio Boost Schedule**:
   $$\text{PR}_{\text{turbo}} = 1.0 + \left(\frac{\text{RPM} - n_{\text{spool}}}{n_{\text{rated}} - n_{\text{spool}}}\right)^{1.2} \cdot \alpha_{\text{norm}} \cdot (\text{PR}_{\text{max}} - 1.0)$$
   Where $n_{\text{spool}} = 2200\text{ RPM}$, $n_{\text{rated}} = 5500\text{ RPM}$, and $\text{PR}_{\text{max}} = 1.45$.
3. **Expected MAP**:
   $$p_{\text{map\_exp}} = \min\left(46.0\text{ inHg}, p_{\text{na}} \cdot \text{PR}_{\text{turbo}}\right)$$

### 2.3 Speed-Density Air Mass Induction
$$\rho_{\text{manifold}} = \frac{p_{\text{map\_exp}} \cdot 3386.39}{R_{\text{spec}} \cdot T_{\text{manifold}}}$$
$$\dot{m}_{\text{air}} = \left(\frac{V_d \cdot \text{RPM}}{120}\right) \cdot \rho_{\text{manifold}} \cdot \eta_v \cdot 3600 \quad [\text{kg/h}]$$
- $V_d = 1352\text{ cc} = 1.352 \times 10^{-3}\text{ m}^3$
- $R_{\text{spec}} = 287.05\text{ J/(kg K)}$
- Volumetric efficiency: $\eta_v = 0.82 + 0.08 \cdot \frac{\text{RPM}}{n_{\text{rated}}}$

---

## 3. Model 2: Fuel Delivery & Stoichiometric Demand

**Implementation**: [`app.domain.physics.fuel.FuelDeliveryModel`](file:///d:/sih/backend/app/domain/physics/fuel.py)

### 3.1 Air-Fuel Ratio (AFR) Regimes
- **Full Throttle Power Enrichment** ($\alpha > 75\%$):
  $$\text{AFR} = 14.7 - (14.7 - 12.6) \cdot \frac{\alpha - 75}{25}$$
- **Idle Enriched Mixture** ($\text{RPM} < n_{\text{idle}}$):
  $$\text{AFR} = 13.5$$
- **Cruise Operating Point**:
  $$\text{AFR} = 14.7 \text{ (Stoichiometric)}$$

### 3.2 Volumetric Fuel Flow Rate
$$\dot{m}_{\text{fuel}} = \frac{\dot{m}_{\text{air}}}{\text{AFR}} \quad [\text{kg/h}]$$
$$\dot{V}_{\text{fuel}} = \frac{\dot{m}_{\text{fuel}}}{\rho_{\text{fuel}}} \quad [\text{L/h}]$$
- $\rho_{\text{fuel}} = 0.72\text{ kg/L}$ (Aviation gasoline / Mogas)
- Sustaining idle floor: $\dot{V}_{\text{fuel}} \ge 1.8\text{ L/h}$ when $\text{RPM} > 600$.

---

## 4. Model 3: 4-Cylinder Thermal Balance & Coolant Model

**Implementation**: [`app.domain.physics.thermal.ThermalCylinderModel`](file:///d:/sih/backend/app/domain/physics/thermal.py)

### 4.1 First-Principles Heat Balance
$$\dot{Q}_{\text{in}} - \dot{Q}_{\text{out}} = m \cdot c_p \cdot \frac{dT}{dt}$$

### 4.2 Steady-State Equilibrium & Ram Air Convection
- Heat generation from combustion: $\Delta T_{\text{heat}} = 75.0 \cdot \left(\frac{\dot{V}_{\text{fuel}}}{16.0}\right)$
- Ram air cooling enhancement: $k_{\text{cool}} = 1.0 + 0.40 \cdot \left(\frac{V_{\text{tas}}}{50}\right)^{0.8}$
- Individual cylinder geometric equilibrium:
  $$T_{\text{ss}, i} = T_{\text{amb}} + \left(\frac{\Delta T_{\text{heat}}}{k_{\text{cool}}}\right) \cdot \beta_{\text{cht}, i}$$
  Geometric bias factors: $\vec{\beta}_{\text{cht}} = [1.00, 0.98, 1.03, 0.99]$ (rear cylinders run slightly warmer).

### 4.3 Discrete Exponential Recurrence
Using analytical integration over discrete time step $\Delta t$:
$$T_i(t + \Delta t) = T_{\text{ss}, i} + \left(T_i(t) - T_{\text{ss}, i}\right) \cdot e^{-\Delta t / \tau_{\text{cht}}}$$
- $\tau_{\text{cht}} = 14.0\text{ s}$
- Coolant jacket temperature dynamics: $\tau_{\text{coolant}} = 16.0\text{ s}$, equilibrium scaled by 0.85 (liquid jacket heat capacity).

---

## 5. Model 4: Exhaust Gas Energy Model (EGT)

**Implementation**: [`app.domain.physics.exhaust.ExhaustEnergyModel`](file:///d:/sih/backend/app/domain/physics/exhaust.py)

### 5.1 Enthalpy Release & Spark Timing Offset
Exhaust enthalpy scales with manifold charge density and fuel flow:
$$T_{\text{egt\_ss}, i} = \left(550.0 + 220.0 \cdot \frac{p_{\text{map}}}{29.92} \sqrt{\frac{\dot{V}_{\text{fuel}}}{16.0}} - 4.5 \cdot (\theta_{\text{inj}} - 24^\circ)\right) \cdot \beta_{\text{egt}, i}$$
- Retarded ignition timing increases exhaust gas temperature due to delayed heat release into the exhaust stroke.
- $\vec{\beta}_{\text{egt}} = [1.00, 0.99, 1.02, 1.00]$
- Fast thermocouple exponential lag: $\tau_{\text{egt}} = 1.2\text{ s}$.

---

## 6. Model 5: Hydrodynamic Lubrication & Oil Temperature

**Implementation**: [`app.domain.physics.lubrication.LubricationOilModel`](file:///d:/sih/backend/app/domain/physics/lubrication.py)

### 6.1 Positive Displacement Oil Pump Delivery
$$p_{\text{pump}} = 2.0 + 3.0 \cdot \left(\frac{\text{RPM} - n_{\text{idle}}}{n_{\text{rated}} - n_{\text{idle}}}\right) \quad [\text{bar}]$$

### 6.2 Viscosity & Bearing Clearance Leakage
Oil viscosity decreases exponentially with temperature, increasing side clearance leakage and lowering gallery pressure:
$$p_{\text{oil\_exp}} = \max\left(0.5, \min\left(5.0, p_{\text{pump}} - 0.020 \cdot (T_{\text{oil}} - 85^\circ\text{C})\right)\right)$$

### 6.3 Sump Thermal Inertia
$$T_{\text{oil\_ss}} = T_{\text{amb}} + 55.0 \cdot \frac{\text{RPM}}{n_{\text{rated}}}$$
$$T_{\text{oil}}(t + \Delta t) = T_{\text{oil\_ss}} + \left(T_{\text{oil}}(t) - T_{\text{oil\_ss}}\right) \cdot e^{-\Delta t / \tau_{\text{oil}}}$$
- Large sump thermal inertia: $\tau_{\text{oil}} = 35.0\text{ s}$.

---

## 7. Model 6: Rotational Harmonic Vibration Baseline

**Implementation**: [`app.domain.physics.vibration.VibrationBaselineModel`](file:///d:/sih/backend/app/domain/physics/vibration.py)

### 7.1 Unbalance & Combustion Cylinder Pulse Loading
Rotational mechanical unbalance scales quadratically with engine rotational speed ($\omega^2$), while combustion cylinder gas pressure pulses scale with manifold absolute pressure:
$$\text{RMS}_{\text{exp}} = 0.35 + 0.75 \cdot \left(\frac{\text{RPM}}{n_{\text{rated}}}\right)^2 + 0.35 \cdot \left(\frac{p_{\text{map}}}{29.92}\right) \quad [\text{g}]$$
- Valid envelope: $\text{RMS} \in [0.1, 10.0]\text{ g}$.
- Idle floor: $0.05\text{ g}$ when engine is stopped.
