/**
 * Centralized WebSocket connection configuration and resilient timing parameters.
 */

export const WEBSOCKET_CONFIG = {
  // Reconnect backoff schedule (ms) with exponential backoff progression
  reconnectScheduleMs: [250, 500, 1000, 2000, 4000, 8000] as const,
  maxReconnectAttempts: 10,

  // Duration in milliseconds before active stream without frames is flagged as STALE
  telemetryStaleAfterMs: 1500,

  // In-memory bounded circular telemetry buffer length for live charts & trends
  bufferCapacity: 300,

  // Maximum allowed payload size for validation guard
  maxMessageBytes: 65536,
} as const;

/**
 * Dynamically resolves the authoritative WebSocket URL.
 * Supports environment override via VITE_WS_URL or builds from window.location.
 * In local development (localhost / 127.0.0.1), connects to port 8000 (or VITE_WS_PORT).
 * In production, connects over same-origin host without port 8000 (e.g., wss://<host>/api/v1/ws/telemetry).
 */
export function getWebSocketUrl(): string {
  // 1. Environment variable override
  const envUrl = import.meta.env.VITE_WS_URL;
  if (envUrl && typeof envUrl === 'string' && envUrl.trim().length > 0) {
    return envUrl.trim();
  }

  // 2. Headless / SSR fallback
  if (typeof window === 'undefined') {
    return 'ws://localhost:8000/api/v1/ws/telemetry';
  }

  // 3. Browser runtime dynamic resolution
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const hostname = window.location.hostname || 'localhost';
  const isLocalhost =
    hostname === 'localhost' ||
    hostname === '127.0.0.1' ||
    hostname === '[::1]';

  if (isLocalhost) {
    const port = import.meta.env.VITE_WS_PORT || '8000';
    return `${protocol}//${hostname}:${port}/api/v1/ws/telemetry`;
  }

  // In production, connect through current browser host with no :8000
  const host = window.location.host || hostname;
  return `${protocol}//${host}/api/v1/ws/telemetry`;
}
