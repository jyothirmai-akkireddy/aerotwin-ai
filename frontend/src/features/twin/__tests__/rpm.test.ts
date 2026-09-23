import { describe, it, expect } from 'vitest';
import { rpmToAngularVelocity, advanceCrankAngle } from '../kinematics';

describe('RPM and Crank Animation Logic', () => {
  it('converts 0 RPM to 0 rad/s', () => {
    expect(rpmToAngularVelocity(0)).toBe(0.0);
  });

  it('converts negative or non-finite RPM to 0 rad/s', () => {
    expect(rpmToAngularVelocity(-500)).toBe(0.0);
    expect(rpmToAngularVelocity(NaN)).toBe(0.0);
    expect(rpmToAngularVelocity(Infinity)).toBe(0.0);
  });

  it('converts idle RPM (1400 RPM) to accurate angular velocity', () => {
    // 1400 * 2 * PI / 60 = 146.607657... rad/s
    const omega = rpmToAngularVelocity(1400);
    expect(omega).toBeCloseTo(146.607657, 4);
  });

  it('converts cruise RPM (4800 RPM) to accurate angular velocity', () => {
    // 4800 * 2 * PI / 60 = 502.6548... rad/s (80 revs/sec)
    const omega = rpmToAngularVelocity(4800);
    expect(omega).toBeCloseTo(502.6548, 4);
  });

  it('converts redline RPM (5800 RPM) to accurate angular velocity', () => {
    // 5800 * 2 * PI / 60 = 607.374... rad/s (96.67 revs/sec)
    const omega = rpmToAngularVelocity(5800);
    expect(omega).toBeCloseTo(607.3746, 4);
  });

  it('advances crank angle in a frame-rate independent manner', () => {
    const rpm = 600; // 10 revs/sec = 20 * PI rad/s
    const omega = rpmToAngularVelocity(rpm);

    // Delta time = 0.016667s (60 FPS tick)
    const dt60 = 1.0 / 60.0;
    const angle60 = advanceCrankAngle(0.0, rpm, dt60, 1.0);
    expect(angle60).toBeCloseTo(omega * dt60, 5);

    // Delta time = 0.033333s (30 FPS tick)
    const dt30 = 1.0 / 30.0;
    const angle30 = advanceCrankAngle(0.0, rpm, dt30, 1.0);
    expect(angle30).toBeCloseTo(omega * dt30, 5);

    // 30 FPS tick advances twice as much as 60 FPS tick, ensuring visual speed consistency
    expect(angle30).toBeCloseTo(angle60 * 2.0, 5);
  });

  it('scales crank angle advance with visual multiplier', () => {
    const rpm = 600;
    const dt = 0.01;

    const angleFull = advanceCrankAngle(0.0, rpm, dt, 1.0);
    const angleHalf = advanceCrankAngle(0.0, rpm, dt, 0.5);
    const angleSlow = advanceCrankAngle(0.0, rpm, dt, 0.1);

    expect(angleHalf).toBeCloseTo(angleFull * 0.5, 6);
    expect(angleSlow).toBeCloseTo(angleFull * 0.1, 6);
  });

  it('wraps crank angle cleanly within [0, 2PI) range', () => {
    const rpm = 6000; // 100 revs/sec
    const dt = 1.0; // 1 full second = 100 complete revolutions
    const newAngle = advanceCrankAngle(0.5, rpm, dt, 1.0);

    expect(newAngle).toBeGreaterThanOrEqual(0.0);
    expect(newAngle).toBeLessThan(2.0 * Math.PI);
  });
});
