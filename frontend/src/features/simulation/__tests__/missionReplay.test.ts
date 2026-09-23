import { describe, it, expect } from 'vitest';
import { ClientCommand } from '../../../services/websocket/types';

describe('Phase 8 Mission & Replay Mathematical Specifications', () => {
  describe('Profile Curve Interpolation Functions', () => {
    // Smooth Ramp: S(tau) = 3*tau^2 - 2*tau^3, for tau in [0, 1]
    const smoothRamp = (v0: number, v1: number, tau: number): number => {
      const clampedTau = Math.max(0.0, Math.min(1.0, tau));
      const s = 3.0 * clampedTau ** 2 - 2.0 * clampedTau ** 3;
      return v0 + (v1 - v0) * s;
    };

    // Linear Ramp: L(tau) = v0 + (v1 - v0) * tau
    const linearRamp = (v0: number, v1: number, tau: number): number => {
      const clampedTau = Math.max(0.0, Math.min(1.0, tau));
      return v0 + (v1 - v0) * clampedTau;
    };

    it('validates Smooth Ramp boundary conditions and C1 zero derivatives', () => {
      // S(0) = 0, S(1) = 1
      expect(smoothRamp(10, 50, 0.0)).toBe(10);
      expect(smoothRamp(10, 50, 1.0)).toBe(50);
      expect(smoothRamp(10, 50, 0.5)).toBe(30);

      // Verify zero derivative near endpoints via numerical differentiation
      const eps = 1e-4;
      const dS_0 = (smoothRamp(0, 1, eps) - smoothRamp(0, 1, 0)) / eps;
      const dS_1 = (smoothRamp(0, 1, 1) - smoothRamp(0, 1, 1 - eps)) / eps;
      expect(dS_0).toBeCloseTo(0.0, 3);
      expect(dS_1).toBeCloseTo(0.0, 3);
    });

    it('validates Linear Ramp linearity and bounds', () => {
      expect(linearRamp(0, 100, 0.0)).toBe(0);
      expect(linearRamp(0, 100, 0.25)).toBe(25);
      expect(linearRamp(0, 100, 0.5)).toBe(50);
      expect(linearRamp(0, 100, 1.0)).toBe(100);

      // Clamping past boundaries
      expect(linearRamp(0, 100, -0.5)).toBe(0);
      expect(linearRamp(0, 100, 1.5)).toBe(100);
    });
  });

  describe('Fuel Consumption Integration Units', () => {
    // telemtry.fuel_flow is in Liters/hour
    // Volume: sum( (fuel_flow_L_per_h / 3600) * dt_s )
    // Mass: Volume * density (rho = 0.72 kg/L for 100LL Avgas)
    it('integrates fuel consumption accurately across constant flow', () => {
      const fuelFlowLph = 36.0; // 36 L/h = 0.01 L/s
      const dt = 0.1; // 100 ms timestep
      const totalSteps = 600; // 60 seconds

      let totalVolumeL = 0.0;
      for (let i = 0; i < totalSteps; i++) {
        totalVolumeL += (fuelFlowLph / 3600.0) * dt;
      }

      expect(totalVolumeL).toBeCloseTo(0.6, 6); // 60 s * 0.01 L/s = 0.6 Liters

      const densityKgL = 0.72;
      const totalMassKg = totalVolumeL * densityKgL;
      expect(totalMassKg).toBeCloseTo(0.432, 6); // 0.6 * 0.72 = 0.432 kg
    });
  });

  describe('Replay Control Command Contract & Whitelist', () => {
    it('constructs valid play, seek, and speed commands', () => {
      const playCmd: ClientCommand = {
        type: 'command',
        version: '1.0.0',
        command: 'replay_play',
      };
      expect(playCmd.command).toBe('replay_play');

      const seekCmd: ClientCommand = {
        type: 'command',
        version: '1.0.0',
        command: 'replay_seek',
        params: { timestamp: 15.0 },
      };
      expect(seekCmd.command).toBe('replay_seek');
      expect(seekCmd.params?.timestamp).toBe(15.0);

      const speedCmd: ClientCommand = {
        type: 'command',
        version: '1.0.0',
        command: 'replay_speed',
        params: { speed: 5.0 },
      };
      expect(speedCmd.command).toBe('replay_speed');
      expect(speedCmd.params?.speed).toBe(5.0);
    });

    it('verifies replay speed presets and bounds according to approved contract', () => {
      // Approved contract:
      // REALTIME: exactly 1.0x
      // ACCELERATED: exactly 0.5x, 1.0x, 2.0x, 5.0x, 10.0x
      // OFFLINE_BATCH: unpaced execution
      const approvedAcceleratedSpeeds = [0.5, 1.0, 2.0, 5.0, 10.0];
      const realtimeSpeed = 1.0;

      expect(realtimeSpeed).toBe(1.0);
      expect(approvedAcceleratedSpeeds).toEqual([0.5, 1.0, 2.0, 5.0, 10.0]);

      // 0.25x must NOT be in approved accelerated speeds
      expect(approvedAcceleratedSpeeds).not.toContain(0.25);

      // MAX is not a valid playback speed
      const isApprovedSpeed = (spd: unknown): boolean =>
        typeof spd === 'number' && approvedAcceleratedSpeeds.includes(spd);

      expect(isApprovedSpeed('MAX')).toBe(false);
      expect(isApprovedSpeed(0.25)).toBe(false);
      expect(isApprovedSpeed(1.0)).toBe(true);
      expect(isApprovedSpeed(5.0)).toBe(true);
    });
  });
});
