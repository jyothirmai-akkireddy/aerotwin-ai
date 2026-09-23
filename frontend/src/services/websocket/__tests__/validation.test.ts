import { describe, it, expect } from 'vitest';
import { parseWebSocketMessage, isValidTelemetryPayload } from '../validation';

describe('WebSocket Message Validation', () => {
  const validPayload = {
    version: '1.0.0',
    timestamp: 1700000000.5,
    sequence_id: 10,
    source_type: 'SIMULATED',
    quality_flag: 'VALID',
    rpm: 2450.0,
    manifold_pressure: 29.8,
    throttle_position: 48.0,
    fuel_flow: 16.8,
    fuel_pressure: 3.3,
    injection_timing: 24.5,
    cht: [96.0, 94.0, 99.0, 95.0] as [number, number, number, number],
    egt: [722.0, 718.0, 732.0, 725.0] as [number, number, number, number],
    coolant_temp: 83.0,
    oil_temperature: 86.0,
    oil_pressure: 3.9,
    vibration_rms: 1.18,
    battery_voltage: 28.1,
    alternator_current: 19.0,
    alternator_status: 'OK',
    altitude: 1050.0,
    ambient_temp: 14.5,
    true_airspeed: 46.0,
  };

  it('validates a correct TelemetryMessage', () => {
    const msg = {
      type: 'telemetry',
      version: '1.0.0',
      timestamp: 1700000000.5,
      sequence_id: 10,
      server_time: 1700000000.52,
      payload: validPayload,
    };

    const parsed = parseWebSocketMessage(msg);
    expect(parsed).not.toBeNull();
    expect(parsed?.type).toBe('telemetry');
  });

  it('rejects a telemetry message with incomplete CHT array', () => {
    const badPayload = {
      ...validPayload,
      cht: [96.0, 94.0, 99.0], // Only 3 cylinders
    };
    expect(isValidTelemetryPayload(badPayload)).toBe(false);

    const msg = {
      type: 'telemetry',
      version: '1.0.0',
      timestamp: 1000.0,
      sequence_id: 1,
      payload: badPayload,
    };
    expect(parseWebSocketMessage(msg)).toBeNull();
  });

  it('rejects a telemetry message with non-numeric RPM', () => {
    const badPayload = {
      ...validPayload,
      rpm: 'TWO_THOUSAND',
    };
    expect(isValidTelemetryPayload(badPayload)).toBe(false);
  });

  it('validates a valid StatusMessage', () => {
    const statusMsg = {
      type: 'status',
      version: '1.0.0',
      status: 'running',
      message: 'Active stream',
      server_time: 123456.0,
    };

    const parsed = parseWebSocketMessage(statusMsg);
    expect(parsed).not.toBeNull();
    expect(parsed?.type).toBe('status');
  });

  it('rejects a status message with invalid status value', () => {
    const badStatus = {
      type: 'status',
      version: '1.0.0',
      status: 'HACKED',
      message: 'Bad status',
    };
    expect(parseWebSocketMessage(badStatus)).toBeNull();
  });

  it('validates an ErrorMessage', () => {
    const errMsg = {
      type: 'error',
      version: '1.0.0',
      code: 'INVALID_JSON',
      message: 'Syntax error',
    };
    const parsed = parseWebSocketMessage(errMsg);
    expect(parsed).not.toBeNull();
    expect(parsed?.type).toBe('error');
  });

  it('validates a HeartbeatMessage', () => {
    const hbMsg = {
      type: 'heartbeat',
      version: '1.0.0',
      server_time: 1700000000.0,
    };
    const parsed = parseWebSocketMessage(hbMsg);
    expect(parsed).not.toBeNull();
    expect(parsed?.type).toBe('heartbeat');
  });
});
