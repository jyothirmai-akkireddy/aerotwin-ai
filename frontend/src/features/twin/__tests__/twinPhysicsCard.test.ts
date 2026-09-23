import { describe, it, expect, beforeEach } from 'vitest';
import { useTwinStore } from '../../../stores/useTwinStore';
import {
  PhysicsTwinResultDto,
  TelemetryMessage,
} from '../../../services/websocket/types';

describe('Physics Twin Store & Diagnostics', () => {
  beforeEach(() => {
    useTwinStore.getState().resetToNominal();
  });

  const mockPhysicsResult: PhysicsTwinResultDto = {
    expected_state: {
      timestamp: 100.0,
      sequence_id: 1,
      rpm: 2400.0,
      manifold_pressure: 29.5,
      air_mass_flow: 180.0,
      fuel_flow: 16.5,
      cht: [95.0, 94.0, 96.0, 95.0],
      egt: [720.0, 715.0, 725.0, 720.0],
      coolant_temp: 82.0,
      oil_temperature: 85.0,
      oil_pressure: 3.8,
      vibration_rms: 1.1,
      validity: 'VALID',
      confidence: 0.98,
      model_version: '1.0.0',
    },
    residuals: {
      timestamp: 100.0,
      sequence_id: 1,
      raw_residuals: {
        manifold_pressure: 0.5,
        fuel_flow: 0.3,
        cht: [1.0, -1.0, 2.0, 0.0],
        egt: [5.0, -5.0, 10.0, 0.0],
        oil_pressure: 0.1,
        oil_temperature: -2.0,
        vibration_rms: 0.05,
      },
      normalized_residuals: {
        manifold_pressure: 0.5 / 0.65,
        fuel_flow: 0.3 / 0.55,
        cht: [1.0 / 3.5, -1.0 / 3.5, 2.0 / 3.5, 0.0],
        egt: [5.0 / 14.2, -5.0 / 14.2, 10.0 / 14.2, 0.0],
        oil_pressure: 0.1 / 0.28,
        oil_temperature: -2.0 / 2.8,
        vibration_rms: 0.05 / 0.22,
      },
      cht_max_imbalance_celsius: 3.0,
      egt_max_imbalance_celsius: 15.0,
      mean_absolute_normalized_residual: 0.45,
      validity: 'VALID',
      confidence: 0.98,
    },
    diagnostics: {
      compute_time_ms: 0.038,
    },
  };

  it('updates physicsResult via setPhysicsResult', () => {
    const store = useTwinStore.getState();
    expect(store.physicsResult).toBeNull();

    store.setPhysicsResult(mockPhysicsResult);
    expect(useTwinStore.getState().physicsResult).toEqual(mockPhysicsResult);
    expect(useTwinStore.getState().physicsResult?.expected_state.validity).toBe('VALID');
    expect(useTwinStore.getState().physicsResult?.residuals.mean_absolute_normalized_residual).toBe(0.45);
  });

  it('ingests physicsResult attached to incoming TelemetryMessage', () => {
    const store = useTwinStore.getState();

    const msg: TelemetryMessage = {
      type: 'telemetry',
      version: '1.0.0',
      timestamp: 100.1,
      sequence_id: 2,
      server_time: 100.1,
      payload: {
        version: '1.0.0',
        timestamp: 100.1,
        sequence_id: 2,
        source_type: 'SIMULATED',
        quality_flag: 'VALID',
        rpm: 2400.0,
        manifold_pressure: 30.0,
        throttle_position: 50.0,
        fuel_flow: 16.8,
        fuel_pressure: 3.2,
        injection_timing: 24.0,
        cht: [96.0, 93.0, 98.0, 95.0],
        egt: [725.0, 710.0, 735.0, 720.0],
        coolant_temp: 83.0,
        oil_temperature: 84.0,
        oil_pressure: 3.9,
        vibration_rms: 1.15,
        battery_voltage: 28.2,
        alternator_current: 18.0,
        alternator_status: 'OK',
        altitude: 1000.0,
        ambient_temp: 15.0,
        true_airspeed: 45.0,
      },
      physics: mockPhysicsResult,
    };

    store.handleIncomingTelemetry(msg);

    const updated = useTwinStore.getState();
    expect(updated.physicsResult).not.toBeNull();
    expect(updated.physicsResult?.expected_state.sequence_id).toBe(1);
    expect(updated.physicsResult?.residuals.cht_max_imbalance_celsius).toBe(3.0);
  });

  it('clears physicsResult when store is resetToNominal', () => {
    const store = useTwinStore.getState();
    store.setPhysicsResult(mockPhysicsResult);
    expect(useTwinStore.getState().physicsResult).not.toBeNull();

    store.resetToNominal();
    expect(useTwinStore.getState().physicsResult).toBeNull();
  });
});
