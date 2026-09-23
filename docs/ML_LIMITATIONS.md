# AeroTwin AI — Phase 6: Machine Learning Prototype Limitations

## 1. Prototype Scope Disclosure

AeroTwin AI is an engineering research prototype designed to demonstrate Digital Twin principles for aero-piston engines in Medium-Altitude Long-Endurance (MALE) UAV applications.

**The following limitations apply:**

1. **Synthetic Ground Truth:** All training, validation, and test datasets were synthetically generated using the Phase 2 deterministic engine simulator and Phase 5 analytical physics twin. While physics formulas follow thermodynamic and mechanical first-principles (Rotax 914/915 iS class), the models have not been fitted against dyno-bench hardware test cell logs or real flight data recorder (FDR) streams.
2. **No Aviation Certification:** Phase 6 does not claim FAA (DO-178C / DO-330 / AC 20-193), EASA, or DGCA airworthiness certification. The ML models are not certified for safety-critical flight operations or automated in-flight engine shutdown/override commands.
3. **Discrete Fault Archetypes:** Supervised fault classification is trained on 5 injected canonical failure modes (oil pressure bias, oil temperature drift, throttle actuator freeze, electrical/sensor dropout, and manifold pressure noise spikes). Novel failure modes, combined compound cascading failures, or unmodeled environmental regimes are mapped to `UNKNOWN` through the Out-Of-Distribution (OOD) and confidence gates.
4. **Research Prototype Notice:** All API payloads, diagnostics data models, and user interface panels prominently display:
   `"PROTOTYPE RESEARCH MODEL — NOT FOR CERTIFIED FLIGHT OPERATIONS"`
