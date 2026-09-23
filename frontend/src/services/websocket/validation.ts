/**
 * Type-safe runtime message validator for inbound WebSocket payloads.
 * Protects application state from malformed, truncated, or hostile network inputs.
 */

import {
  TelemetryFramePayload,
  TelemetryMessage,
  StatusMessage,
  ErrorMessage,
  HeartbeatMessage,
  WebSocketInboundMessage,
} from './types';

function isRecord(val: unknown): val is Record<string, unknown> {
  return typeof val === 'object' && val !== null && !Array.isArray(val);
}

export function isValidTelemetryPayload(p: unknown): p is TelemetryFramePayload {
  if (!isRecord(p)) return false;

  const validNumbers =
    typeof p.timestamp === 'number' &&
    typeof p.sequence_id === 'number' &&
    typeof p.rpm === 'number' &&
    typeof p.manifold_pressure === 'number' &&
    typeof p.throttle_position === 'number' &&
    typeof p.fuel_flow === 'number' &&
    typeof p.oil_pressure === 'number' &&
    typeof p.oil_temperature === 'number' &&
    typeof p.vibration_rms === 'number' &&
    typeof p.battery_voltage === 'number';

  if (!validNumbers) return false;

  const validCht =
    Array.isArray(p.cht) &&
    p.cht.length === 4 &&
    p.cht.every((v) => typeof v === 'number');

  const validEgt =
    Array.isArray(p.egt) &&
    p.egt.length === 4 &&
    p.egt.every((v) => typeof v === 'number');

  return validCht && validEgt;
}

export function parseWebSocketMessage(raw: unknown): WebSocketInboundMessage | null {
  if (!isRecord(raw)) return null;

  const type = raw.type;

  if (type === 'telemetry') {
    if (
      typeof raw.sequence_id === 'number' &&
      typeof raw.timestamp === 'number' &&
      isValidTelemetryPayload(raw.payload)
    ) {
      return raw as unknown as TelemetryMessage;
    }
    return null;
  }

  if (type === 'status') {
    const validStatuses = ['connected', 'running', 'paused', 'stopped', 'degraded', 'error'];
    if (
      typeof raw.status === 'string' &&
      validStatuses.includes(raw.status) &&
      typeof raw.message === 'string'
    ) {
      return raw as unknown as StatusMessage;
    }
    return null;
  }

  if (type === 'error') {
    if (typeof raw.code === 'string' && typeof raw.message === 'string') {
      return raw as unknown as ErrorMessage;
    }
    return null;
  }

  if (type === 'heartbeat') {
    if (typeof raw.server_time === 'number') {
      return raw as unknown as HeartbeatMessage;
    }
    return null;
  }

  return null;
}
