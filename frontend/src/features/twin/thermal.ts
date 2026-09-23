/**
 * Continuous thermal color mapping for engine 3D visualization.
 *
 * PROTOTYPE DISCLAIMER:
 * This module performs visual thermal mapping based on scalar cylinder head temperatures (CHT).
 * It represents a SIMULATED THERMAL VISUALIZATION for engineering situational awareness,
 * NOT a certified CFD (Computational Fluid Dynamics) thermal distribution.
 */

import * as THREE from 'three';

export interface ThermalConfig {
  /** Lower temperature threshold (°C) mapped to cold color */
  minTempC: number;
  /** Upper temperature threshold (°C) mapped to peak hot color */
  maxTempC: number;
}

export const DEFAULT_THERMAL_CONFIG: ThermalConfig = {
  minTempC: 30.0, // Ambient / cold engine baseline (°C)
  maxTempC: 150.0, // Upper operational threshold before warning/redline (°C)
};

/**
 * Normalized color stops for continuous thermal gradient:
 * - 0.00: Cold ambient (#0ea5e9 / Sky blue)
 * - 0.25: Warm idle (#10b981 / Emerald green)
 * - 0.55: Nominal cruise (#f59e0b / Amber)
 * - 0.80: Elevated power (#ea580c / Hot orange)
 * - 1.00: Overheat redline (#ef4444 / Crimson red)
 */
const THERMAL_STOPS = [
  { stop: 0.0, color: new THREE.Color('#0ea5e9') },
  { stop: 0.25, color: new THREE.Color('#10b981') },
  { stop: 0.55, color: new THREE.Color('#f59e0b') },
  { stop: 0.8, color: new THREE.Color('#ea580c') },
  { stop: 1.0, color: new THREE.Color('#ef4444') },
];

/**
 * Normalize an operational temperature to [0.0, 1.0] with clamping.
 */
export function normalizeTemperature(
  tempC: number,
  config: ThermalConfig = DEFAULT_THERMAL_CONFIG
): number {
  if (!Number.isFinite(tempC)) {
    return 0.0;
  }
  const range = config.maxTempC - config.minTempC;
  if (range <= 0) {
    return 0.5;
  }
  const normalized = (tempC - config.minTempC) / range;
  return Math.max(0.0, Math.min(1.0, normalized));
}

/**
 * Convert a cylinder head temperature (°C) into a continuous interpolated Three.js Color.
 */
export function getThermalColor(
  tempC: number,
  config: ThermalConfig = DEFAULT_THERMAL_CONFIG
): THREE.Color {
  const t = normalizeTemperature(tempC, config);

  // Find surrounding color stops
  for (let i = 0; i < THERMAL_STOPS.length - 1; i++) {
    const s1 = THERMAL_STOPS[i];
    const s2 = THERMAL_STOPS[i + 1];

    if (t >= s1.stop && t <= s2.stop) {
      const segmentRatio = (t - s1.stop) / (s2.stop - s1.stop);
      const result = s1.color.clone();
      result.lerp(s2.color, segmentRatio);
      return result;
    }
  }

  return THERMAL_STOPS[THERMAL_STOPS.length - 1].color.clone();
}

/**
 * Calculate dynamic emissive intensity and color for glowing thermal highlights.
 */
export function getThermalEmissive(
  tempC: number,
  config: ThermalConfig = DEFAULT_THERMAL_CONFIG
): { color: THREE.Color; intensity: number } {
  const t = normalizeTemperature(tempC, config);
  const color = getThermalColor(tempC, config);

  // Emissive increases progressively beyond 50% thermal range
  const intensity = t > 0.5 ? (t - 0.5) * 1.6 : 0.05;
  return { color, intensity };
}

/**
 * Determine high-level thermal status badge based on CHT value.
 */
export function getThermalStatus(tempC: number): {
  status: 'COLD' | 'OPTIMAL' | 'ELEVATED' | 'OVERHEAT';
  label: string;
  colorClass: string;
} {
  if (!Number.isFinite(tempC) || tempC < 50.0) {
    return { status: 'COLD', label: 'COLD', colorClass: 'text-sky-400 bg-sky-950/40 border-sky-800' };
  }
  if (tempC <= 115.0) {
    return { status: 'OPTIMAL', label: 'OPTIMAL', colorClass: 'text-emerald-400 bg-emerald-950/40 border-emerald-800' };
  }
  if (tempC <= 135.0) {
    return { status: 'ELEVATED', label: 'ELEVATED', colorClass: 'text-amber-400 bg-amber-950/40 border-amber-800' };
  }
  return { status: 'OVERHEAT', label: 'OVERHEAT', colorClass: 'text-red-400 bg-red-950/40 border-red-800' };
}
