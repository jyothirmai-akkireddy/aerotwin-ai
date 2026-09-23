import { describe, it, expect, beforeEach } from 'vitest';
import { useTwinStore } from '../../../stores/useTwinStore';
import { TelemetryMessage } from '../../../services/websocket/types';
import { WEBSOCKET_CONFIG } from '../../../config/websocket';

describe('useTwinStore Realtime Telemetry Ingestion', () => {
  beforeEach(() => {
    useTwinStore.getState().resetToNominal();
    useTwinStore.getState().clearTelemetryBuffer();
  });

  const createMsg = (seq: number, rpm: number = 2400.0): TelemetryMessage => ({
    type: 'telemetry',
    version: '1.0.0',
    timestamp: 1000.0 + seq * 0.1,
    sequence_id: seq,
    server_time: 1000.0 + seq * 0.1,
    payload: {
      version: '1.0.0',
      timestamp: 1000.0 + seq * 0.1,
      sequence_id: seq,
      source_type: 'SIMULATED',
      quality_flag: 'VALID',
      rpm,
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
  });

  it('updates telemetry and tracks sequence ID from incoming message', () => {
    const store = useTwinStore.getState();
    const msg = createMsg(42, 3100.0);

    store.handleIncomingTelemetry(msg);

    const updated = useTwinStore.getState();
    expect(updated.telemetry.rpm).toBe(3100.0);
    expect(updated.telemetry.sequenceId).toBe(42);
    expect(updated.lastSequenceId).toBe(42);
    expect(updated.telemetryBuffer).toHaveLength(1);
  });

  it('enforces circular buffer capacity bound', () => {
    const store = useTwinStore.getState();
    const capacity = WEBSOCKET_CONFIG.bufferCapacity;

    // Ingest capacity + 20 frames
    for (let i = 1; i <= capacity + 20; i++) {
      store.handleIncomingTelemetry(createMsg(i, 2000.0 + i));
    }

    const updated = useTwinStore.getState();
    expect(updated.telemetryBuffer.length).toBe(capacity);
    // Oldest surviving frame should be i = 21
    expect(updated.telemetryBuffer[0].sequenceId).toBe(21);
    // Newest frame should be i = capacity + 20
    expect(updated.telemetryBuffer[capacity - 1].sequenceId).toBe(capacity + 20);
  });

  it('records sequence gaps and duplicate anomalies', () => {
    const store = useTwinStore.getState();

    // Gap: expected 10, got 14 (missed 4)
    store.recordSequenceAnomaly('GAP', 10, 14);
    expect(useTwinStore.getState().missedFramesCount).toBe(4);

    // Duplicate
    store.recordSequenceAnomaly('DUPLICATE', 15, 14);
    expect(useTwinStore.getState().duplicateFramesCount).toBe(1);
  });

  it('switches transport mode cleanly', () => {
    const store = useTwinStore.getState();
    expect(store.transportMode).toBe('WEBSOCKET');

    store.setTransportMode('MANUAL_DEV');
    expect(useTwinStore.getState().transportMode).toBe('MANUAL_DEV');

    store.setTransportMode('WEBSOCKET');
    expect(useTwinStore.getState().transportMode).toBe('WEBSOCKET');
  });
});
