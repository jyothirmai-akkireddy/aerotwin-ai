import { describe, it, expect } from 'vitest';
import {
  calculatePistonDisplacement,
  calculateRodAngle,
  calculateAllPistonDisplacements,
  DEFAULT_KINEMATICS,
} from '../kinematics';

describe('Engine Kinematics', () => {
  const { crankRadius: r, connectingRodLength: L } = DEFAULT_KINEMATICS;

  it('calculates Top Dead Center (TDC) displacement at theta = 0', () => {
    const disp = calculatePistonDisplacement(0.0, r, L);
    // At TDC, x = r + L
    expect(disp).toBeCloseTo(r + L, 6);
  });

  it('calculates Bottom Dead Center (BDC) displacement at theta = PI', () => {
    const disp = calculatePistonDisplacement(Math.PI, r, L);
    // At BDC, x = L - r
    expect(disp).toBeCloseTo(L - r, 6);
  });

  it('verifies total piston stroke travel equals exactly 2 * crankRadius', () => {
    const tdc = calculatePistonDisplacement(0.0, r, L);
    const bdc = calculatePistonDisplacement(Math.PI, r, L);
    const stroke = tdc - bdc;
    expect(stroke).toBeCloseTo(2 * r, 6);
  });

  it('calculates mid-stroke displacement at theta = PI/2 and 3PI/2', () => {
    const disp1 = calculatePistonDisplacement(Math.PI / 2, r, L);
    const disp2 = calculatePistonDisplacement((3 * Math.PI) / 2, r, L);

    // At 90° and 270°, x = sqrt(L^2 - r^2)
    const expected = Math.sqrt(L * L - r * r);
    expect(disp1).toBeCloseTo(expected, 6);
    expect(disp2).toBeCloseTo(expected, 6);
  });

  it('asserts piston displacement is strictly bounded within [L - r, L + r]', () => {
    const minBound = L - r;
    const maxBound = L + r;

    // Test across a full 360 degree revolution with fine 5-degree increments
    for (let deg = 0; deg <= 360; deg += 5) {
      const theta = (deg * Math.PI) / 180.0;
      const x = calculatePistonDisplacement(theta, r, L);
      expect(Number.isFinite(x)).toBe(true);
      expect(x).toBeGreaterThanOrEqual(minBound - 1e-7);
      expect(x).toBeLessThanOrEqual(maxBound + 1e-7);
    }
  });

  it('calculates connecting rod tilt angle correctly', () => {
    // At TDC (0) and BDC (PI), rod angle is zero
    expect(calculateRodAngle(0, r, L)).toBeCloseTo(0.0, 6);
    expect(calculateRodAngle(Math.PI, r, L)).toBeCloseTo(0.0, 6);

    // At 90 degrees, sin(phi) = r / L
    const maxAngle = Math.asin(r / L);
    expect(calculateRodAngle(Math.PI / 2, r, L)).toBeCloseTo(maxAngle, 6);
    expect(calculateRodAngle((3 * Math.PI) / 2, r, L)).toBeCloseTo(-maxAngle, 6);
  });

  it('supports multiple rod and crank dimension configurations', () => {
    // Custom long-rod configuration (e.g. r = 40mm, L = 160mm)
    const r2 = 0.04;
    const L2 = 0.16;
    const tdc2 = calculatePistonDisplacement(0.0, r2, L2);
    const bdc2 = calculatePistonDisplacement(Math.PI, r2, L2);

    expect(tdc2).toBeCloseTo(0.2, 6);
    expect(bdc2).toBeCloseTo(0.12, 6);
    expect(tdc2 - bdc2).toBeCloseTo(0.08, 6);
  });

  it('throws error when invalid geometry (L <= r) is supplied', () => {
    expect(() => calculatePistonDisplacement(0.0, 0.1, 0.05)).toThrowError(
      /Invalid crank-slider geometry/
    );
  });

  it('computes 4-cylinder displacement array with appropriate phase offsets', () => {
    const displacements = calculateAllPistonDisplacements(0.0);
    expect(displacements).toHaveLength(4);

    // Cylinder 1 is at theta = 0 (TDC)
    expect(displacements[0]).toBeCloseTo(r + L, 6);
    // Cylinder 2 has phase offset PI -> at BDC
    expect(displacements[1]).toBeCloseTo(L - r, 6);
    // Cylinder 3 has phase offset PI -> at BDC
    expect(displacements[2]).toBeCloseTo(L - r, 6);
    // Cylinder 4 has phase offset 0 -> at TDC
    expect(displacements[3]).toBeCloseTo(r + L, 6);
  });
});
