import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { WebSocketClient } from '../WebSocketClient';
import { TelemetryMessage } from '../types';

class MockWebSocket {
  static instances: MockWebSocket[] = [];
  public url: string;
  public onopen: (() => void) | null = null;
  public onmessage: ((ev: MessageEvent) => void) | null = null;
  public onclose: (() => void) | null = null;
  public onerror: (() => void) | null = null;
  public readyState: number = 0; // CONNECTING
  public sentMessages: string[] = [];

  constructor(url: string) {
    this.url = url;
    MockWebSocket.instances.push(this);
    setTimeout(() => {
      this.readyState = 1; // OPEN
      this.onopen?.();
    }, 10);
  }

  public send(data: string): void {
    this.sentMessages.push(data);
  }

  public close(): void {
    this.readyState = 3; // CLOSED
    this.onclose?.();
  }

  public triggerMessage(data: string): void {
    this.onmessage?.(new MessageEvent('message', { data }));
  }
}

describe('WebSocketClient Service', () => {
  beforeEach(() => {
    MockWebSocket.instances = [];
    vi.stubGlobal('WebSocket', MockWebSocket);
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.clearAllTimers();
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it('transitions state from DISCONNECTED to CONNECTING to CONNECTED', () => {
    let observedState = '';
    const client = new WebSocketClient(
      {
        onStateChange: (state) => {
          observedState = state;
        },
      },
      'ws://localhost:8000/api/v1/ws/telemetry'
    );

    expect(client.getState()).toBe('DISCONNECTED');
    client.connect();
    expect(client.getState()).toBe('CONNECTING');

    // Advance timer to trigger mock onopen
    vi.advanceTimersByTime(20);
    expect(client.getState()).toBe('CONNECTED');
    expect(observedState).toBe('CONNECTED');

    client.disconnect();
    expect(client.getState()).toBe('DISCONNECTED');
  });

  it('parses valid incoming telemetry and notifies onTelemetry callback', () => {
    let receivedSeq = -1;
    let receivedFreshness = '';

    const client = new WebSocketClient(
      {
        onTelemetry: (msg) => {
          receivedSeq = msg.sequence_id;
        },
        onFreshnessChange: (freshness) => {
          receivedFreshness = freshness;
        },
      },
      'ws://localhost:8000/api/v1/ws/telemetry'
    );

    client.connect();
    vi.advanceTimersByTime(20);

    const mockWs = MockWebSocket.instances[0];
    const telemetryMsg: TelemetryMessage = {
      type: 'telemetry',
      version: '1.0.0',
      timestamp: 12345.6,
      sequence_id: 100,
      server_time: 12345.62,
      payload: {
        version: '1.0.0',
        timestamp: 12345.6,
        sequence_id: 100,
        source_type: 'SIMULATED',
        quality_flag: 'VALID',
        rpm: 2400.0,
        manifold_pressure: 29.5,
        throttle_position: 45.0,
        fuel_flow: 16.5,
        fuel_pressure: 3.2,
        injection_timing: 24.0,
        cht: [95.0, 92.5, 98.0, 94.0],
        egt: [720.0, 715.0, 730.0, 722.0],
        coolant_temp: 82.0,
        oil_temperature: 85.0,
        oil_pressure: 3.8,
        vibration_rms: 1.15,
        battery_voltage: 28.2,
        alternator_current: 18.5,
        alternator_status: 'OK',
        altitude: 1000.0,
        ambient_temp: 15.0,
        true_airspeed: 45.0,
      },
    };

    mockWs.triggerMessage(JSON.stringify(telemetryMsg));

    expect(receivedSeq).toBe(100);
    expect(receivedFreshness).toBe('LIVE');
    expect(client.getLastSequenceId()).toBe(100);
  });

  it('detects sequence gaps and duplicates', () => {
    const anomalies: { type: string; expected: number; actual: number }[] = [];

    const client = new WebSocketClient(
      {
        onSequenceAnomaly: (type, expected, actual) => {
          anomalies.push({ type, expected, actual });
        },
      },
      'ws://localhost:8000/api/v1/ws/telemetry'
    );

    client.connect();
    vi.advanceTimersByTime(20);
    const mockWs = MockWebSocket.instances[0];

    const makeMsg = (seq: number) =>
      JSON.stringify({
        type: 'telemetry',
        version: '1.0.0',
        timestamp: 100.0 + seq,
        sequence_id: seq,
        server_time: 100.0 + seq,
        payload: {
          version: '1.0.0',
          timestamp: 100.0 + seq,
          sequence_id: seq,
          source_type: 'SIMULATED',
          quality_flag: 'VALID',
          rpm: 2400.0,
          manifold_pressure: 29.5,
          throttle_position: 45.0,
          fuel_flow: 16.5,
          fuel_pressure: 3.2,
          injection_timing: 24.0,
          cht: [95.0, 95.0, 95.0, 95.0],
          egt: [700.0, 700.0, 700.0, 700.0],
          coolant_temp: 80.0,
          oil_temperature: 80.0,
          oil_pressure: 3.5,
          vibration_rms: 1.0,
          battery_voltage: 28.0,
          alternator_current: 18.0,
          alternator_status: 'OK',
          altitude: 1000.0,
          ambient_temp: 15.0,
          true_airspeed: 45.0,
        },
      });

    // Receive seq 10
    mockWs.triggerMessage(makeMsg(10));
    // Receive seq 13 (gap of 2 frames: missed 11 and 12)
    mockWs.triggerMessage(makeMsg(13));
    // Receive seq 13 again (duplicate)
    mockWs.triggerMessage(makeMsg(13));

    expect(anomalies).toHaveLength(2);
    expect(anomalies[0]).toEqual({ type: 'GAP', expected: 11, actual: 13 });
    expect(anomalies[1]).toEqual({ type: 'DUPLICATE', expected: 14, actual: 13 });
  });

  it('marks data as STALE when no telemetry is received within 1500ms', () => {
    let observedFreshness = '';
    const client = new WebSocketClient(
      {
        onFreshnessChange: (freshness) => {
          observedFreshness = freshness;
        },
      },
      'ws://localhost:8000/api/v1/ws/telemetry'
    );

    client.connect();
    vi.advanceTimersByTime(20);
    const mockWs = MockWebSocket.instances[0];

    // Trigger one frame
    mockWs.triggerMessage(
      JSON.stringify({
        type: 'telemetry',
        version: '1.0.0',
        timestamp: 100.0,
        sequence_id: 1,
        server_time: 100.0,
        payload: {
          version: '1.0.0',
          timestamp: 100.0,
          sequence_id: 1,
          source_type: 'SIMULATED',
          quality_flag: 'VALID',
          rpm: 2400.0,
          manifold_pressure: 29.5,
          throttle_position: 45.0,
          fuel_flow: 16.5,
          fuel_pressure: 3.2,
          injection_timing: 24.0,
          cht: [95.0, 95.0, 95.0, 95.0],
          egt: [700.0, 700.0, 700.0, 700.0],
          coolant_temp: 80.0,
          oil_temperature: 80.0,
          oil_pressure: 3.5,
          vibration_rms: 1.0,
          battery_voltage: 28.0,
          alternator_current: 18.0,
          alternator_status: 'OK',
          altitude: 1000.0,
          ambient_temp: 15.0,
          true_airspeed: 45.0,
        },
      })
    );

    expect(observedFreshness).toBe('LIVE');

    // Advance time by 1600ms without new frames
    vi.advanceTimersByTime(1600);

    expect(observedFreshness).toBe('STALE');
    expect(client.getFreshness()).toBe('STALE');
  });

  it('sends client commands properly formatted', () => {
    const client = new WebSocketClient({}, 'ws://localhost:8000/api/v1/ws/telemetry');
    client.connect();
    vi.advanceTimersByTime(20);
    const mockWs = MockWebSocket.instances[0];

    const success = client.sendCommand('pause', { reason: 'test' });
    expect(success).toBe(true);
    expect(mockWs.sentMessages).toHaveLength(1);
    const sent = JSON.parse(mockWs.sentMessages[0]);
    expect(sent.type).toBe('command');
    expect(sent.command).toBe('pause');
    expect(sent.params.reason).toBe('test');
  });
});
