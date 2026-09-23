/**
 * Pure kinematic functions for a generic 4-cylinder horizontally-opposed aero-piston engine.
 *
 * PROTOTYPE ASSUMPTION DISCLAIMER:
 * Dimensions and kinematic relationships are simplified geometric approximations
 * inspired by the 4-cylinder horizontally-opposed turbocharged aero-piston engine class
 * (e.g. Rotax 914/915 class: ~61mm stroke, ~84mm bore).
 * They represent prototype visualization kinematics, not certified OEM CAD dimensions.
 */

export interface EngineKinematicDimensions {
  /** Crank radius (m) — Half of total piston stroke (e.g., 0.0305m for 61mm stroke) */
  crankRadius: number;
  /** Connecting rod center-to-center length (m) */
  connectingRodLength: number;
  /** Cylinder bore radius (m) */
  cylinderBoreRadius: number;
  /** Cylinder bank X offset from engine centerline (m) */
  bankOffset: number;
}

/**
 * Standard prototype dimensions for generic 4-cylinder aero-piston visual model.
 * Marked: PROTOTYPE ASSUMPTION.
 */
export const DEFAULT_KINEMATICS: EngineKinematicDimensions = {
  crankRadius: 0.0305, // 30.5 mm crank radius -> 61 mm stroke
  connectingRodLength: 0.112, // 112 mm rod length (rod-to-stroke ratio ~ 1.84)
  cylinderBoreRadius: 0.042, // 42 mm radius -> 84 mm bore (~1352 cc total displacement)
  bankOffset: 0.085, // 85 mm cylinder bank base offset from crank centerline
};

/**
 * Cylinder crank throw angular offsets (radians) for horizontally-opposed flat-4 engine.
 *
 * Cylinder layout:
 * - Cylinder 1: Left Bank Front (X < 0, Z > 0)
 * - Cylinder 2: Right Bank Front (X > 0, Z > 0)
 * - Cylinder 3: Left Bank Rear (X < 0, Z < 0)
 * - Cylinder 4: Right Bank Rear (X > 0, Z < 0)
 *
 * In a standard flat-4 boxer crank, opposed cylinders share 180° throws so pistons
 * move outward/inward symmetrically, providing primary balance.
 *
 * PROTOTYPE ASSUMPTION:
 * Phasing offsets: Cyl 1 = 0, Cyl 2 = π, Cyl 3 = π, Cyl 4 = 0.
 */
export const CYLINDER_PHASE_OFFSETS: [number, number, number, number] = [
  0.0,
  Math.PI,
  Math.PI,
  0.0,
];

/**
 * Convert engine RPM to physical angular velocity in radians per second.
 *
 * @param rpm Rotational speed (revolutions / minute)
 * @returns Angular velocity (radians / second)
 */
export function rpmToAngularVelocity(rpm: number): number {
  if (rpm <= 0.0 || !Number.isFinite(rpm)) {
    return 0.0;
  }
  return (rpm * 2.0 * Math.PI) / 60.0;
}

/**
 * Advance crank angle in a frame-rate independent manner.
 *
 * @param currentAngleRad Current crank angle (radians)
 * @param rpm Engine rotational speed
 * @param deltaSec Time delta since last animation frame (seconds)
 * @param visualMultiplier Scaling factor for visualization speed (e.g. 0.1 for slow-motion)
 * @returns New crank angle normalized to [0, 2π)
 */
export function advanceCrankAngle(
  currentAngleRad: number,
  rpm: number,
  deltaSec: number,
  visualMultiplier: number = 1.0
): number {
  if (!Number.isFinite(currentAngleRad) || !Number.isFinite(deltaSec) || deltaSec <= 0) {
    return currentAngleRad;
  }
  const omega = rpmToAngularVelocity(rpm);
  const deltaAngle = omega * deltaSec * visualMultiplier;
  const newAngle = (currentAngleRad + deltaAngle) % (2.0 * Math.PI);
  return newAngle >= 0 ? newAngle : newAngle + 2.0 * Math.PI;
}

/**
 * Calculate instantaneous piston displacement from crankshaft axis along the cylinder bore axis
 * using the exact crank-slider kinematic equation:
 *
 *   x(θ) = r * cos(θ) + sqrt(L² - r² * sin²(θ))
 *
 * where:
 *   r = crank throw radius
 *   L = connecting rod length
 *   θ = instantaneous crank angle
 *
 * At Top Dead Center (TDC, θ = 0):   x = r + L
 * At Bottom Dead Center (BDC, θ = π): x = -r + L = L - r
 * Total stroke travel = (r + L) - (L - r) = 2r
 *
 * @param thetaRad Instantaneous crank angle in radians
 * @param r Crank throw radius (m)
 * @param L Connecting rod length (m)
 * @returns Distance of piston gudgeon pin from crank center (m)
 */
export function calculatePistonDisplacement(
  thetaRad: number,
  r: number = DEFAULT_KINEMATICS.crankRadius,
  L: number = DEFAULT_KINEMATICS.connectingRodLength
): number {
  if (L <= r || r <= 0) {
    throw new Error(`Invalid crank-slider geometry: L (${L}) must be greater than r (${r}) > 0`);
  }
  const sinTheta = Math.sin(thetaRad);
  const cosTheta = Math.cos(thetaRad);
  const discriminant = L * L - r * r * sinTheta * sinTheta;

  // Due to L > r, discriminant is strictly positive
  const sqrtVal = Math.sqrt(Math.max(0.0, discriminant));
  return r * cosTheta + sqrtVal;
}

/**
 * Calculate instantaneous connecting rod swing angle (radians) relative to cylinder axis.
 *
 *   sin(φ) = (r / L) * sin(θ)
 *   φ = arcsin((r / L) * sin(θ))
 *
 * @param thetaRad Crank angle in radians
 * @param r Crank throw radius
 * @param L Connecting rod length
 * @returns Connecting rod tilt angle (radians)
 */
export function calculateRodAngle(
  thetaRad: number,
  r: number = DEFAULT_KINEMATICS.crankRadius,
  L: number = DEFAULT_KINEMATICS.connectingRodLength
): number {
  if (L <= r || r <= 0) {
    return 0.0;
  }
  const ratio = (r / L) * Math.sin(thetaRad);
  const clampedRatio = Math.max(-1.0, Math.min(1.0, ratio));
  return Math.asin(clampedRatio);
}

/**
 * Calculate piston displacement for all 4 cylinders at a given crank angle.
 *
 * @param baseAngleRad Base crankshaft angle (radians)
 * @param dimensions Kinematic dimensions
 * @returns Array of 4 piston displacements [Cyl1, Cyl2, Cyl3, Cyl4]
 */
export function calculateAllPistonDisplacements(
  baseAngleRad: number,
  dimensions: EngineKinematicDimensions = DEFAULT_KINEMATICS
): [number, number, number, number] {
  return [
    calculatePistonDisplacement(baseAngleRad + CYLINDER_PHASE_OFFSETS[0], dimensions.crankRadius, dimensions.connectingRodLength),
    calculatePistonDisplacement(baseAngleRad + CYLINDER_PHASE_OFFSETS[1], dimensions.crankRadius, dimensions.connectingRodLength),
    calculatePistonDisplacement(baseAngleRad + CYLINDER_PHASE_OFFSETS[2], dimensions.crankRadius, dimensions.connectingRodLength),
    calculatePistonDisplacement(baseAngleRad + CYLINDER_PHASE_OFFSETS[3], dimensions.crankRadius, dimensions.connectingRodLength),
  ];
}
