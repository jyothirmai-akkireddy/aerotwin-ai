/**
 * Resilient, production-style WebSocket Client for AeroTwin AI.
 * Handles automatic exponential backoff reconnection, sequence gap detection,
 * stale telemetry tracking, and message parsing in total isolation from UI components.
 */

import { WEBSOCKET_CONFIG, getWebSocketUrl } from '../../config/websocket';
import {
  ConnectionState,
  TelemetryFreshness,
  TelemetryMessage,
  StatusMessage,
  ErrorMessage,
  ClientCommand,
  ClientPing,
} from './types';
import { parseWebSocketMessage } from './validation';

export interface WebSocketClientCallbacks {
  onTelemetry?: (msg: TelemetryMessage) => void;
  onStatus?: (msg: StatusMessage) => void;
  onError?: (msg: ErrorMessage) => void;
  onStateChange?: (state: ConnectionState) => void;
  onFreshnessChange?: (freshness: TelemetryFreshness) => void;
  onSequenceAnomaly?: (
    type: 'GAP' | 'DUPLICATE',
    expected: number,
    actual: number
  ) => void;
}

export class WebSocketClient {
  private ws: WebSocket | null = null;
  private url: string;
  private callbacks: WebSocketClientCallbacks;

  private state: ConnectionState = 'DISCONNECTED';
  private freshness: TelemetryFreshness = 'NO_DATA';
  private reconnectAttempt: number = 0;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private staleTimer: ReturnType<typeof setTimeout> | null = null;
  private lastSequenceId: number | null = null;
  private isManualDisconnect: boolean = false;

  constructor(callbacks: WebSocketClientCallbacks = {}, customUrl?: string) {
    this.callbacks = callbacks;
    this.url = customUrl || getWebSocketUrl();
  }

  public getState(): ConnectionState {
    return this.state;
  }

  public getFreshness(): TelemetryFreshness {
    return this.freshness;
  }

  public getLastSequenceId(): number | null {
    return this.lastSequenceId;
  }

  public setCallbacks(callbacks: WebSocketClientCallbacks): void {
    this.callbacks = { ...this.callbacks, ...callbacks };
  }

  public connect(): void {
    if (this.state === 'CONNECTED' || this.state === 'CONNECTING') {
      return;
    }

    this.isManualDisconnect = false;
    this.clearTimers();
    this.updateState(this.reconnectAttempt > 0 ? 'RECONNECTING' : 'CONNECTING');

    try {
      this.ws = new WebSocket(this.url);

      this.ws.onopen = () => {
        this.reconnectAttempt = 0;
        this.updateState('CONNECTED');
      };

      this.ws.onmessage = (event: MessageEvent) => {
        this.handleMessage(event.data);
      };

      this.ws.onerror = () => {
        this.updateState('ERROR');
      };

      this.ws.onclose = () => {
        this.handleClose();
      };
    } catch {
      this.updateState('ERROR');
      this.scheduleReconnect();
    }
  }

  public disconnect(): void {
    this.isManualDisconnect = true;
    this.clearTimers();

    if (this.ws) {
      try {
        this.ws.close();
      } catch {
        // Safe ignore
      }
      this.ws = null;
    }

    this.updateState('DISCONNECTED');
    this.updateFreshness('NO_DATA');
  }

  public sendCommand(
    command: ClientCommand['command'],
    params?: Record<string, unknown>
  ): boolean {
    if (!this.ws || this.state !== 'CONNECTED') {
      return false;
    }

    const payload: ClientCommand = {
      type: 'command',
      version: '1.0.0',
      command,
      params: params || {},
    };

    try {
      this.ws.send(JSON.stringify(payload));
      return true;
    } catch {
      return false;
    }
  }

  public sendPing(): boolean {
    if (!this.ws || this.state !== 'CONNECTED') {
      return false;
    }

    const payload: ClientPing = { type: 'ping' };
    try {
      this.ws.send(JSON.stringify(payload));
      return true;
    } catch {
      return false;
    }
  }

  private handleMessage(rawData: unknown): void {
    if (typeof rawData !== 'string') return;

    let parsedJson: unknown;
    try {
      parsedJson = JSON.parse(rawData);
    } catch {
      return;
    }

    const message = parseWebSocketMessage(parsedJson);
    if (!message) return;

    // Reset stale detection timer on every valid inbound frame
    this.resetStaleTimer();

    switch (message.type) {
      case 'telemetry':
        this.processTelemetry(message);
        break;
      case 'status':
        this.callbacks.onStatus?.(message);
        break;
      case 'error':
        this.callbacks.onError?.(message);
        break;
      case 'heartbeat':
        // Heartbeats confirm stream liveness; stale timer is already reset
        break;
    }
  }

  private processTelemetry(msg: TelemetryMessage): void {
    const seq = msg.sequence_id;

    // Sequence tracking and anomaly detection
    if (this.lastSequenceId !== null) {
      if (seq > this.lastSequenceId + 1) {
        this.callbacks.onSequenceAnomaly?.('GAP', this.lastSequenceId + 1, seq);
      } else if (seq <= this.lastSequenceId) {
        this.callbacks.onSequenceAnomaly?.('DUPLICATE', this.lastSequenceId + 1, seq);
      }
    }
    this.lastSequenceId = seq;

    // Mark live freshness
    this.updateFreshness('LIVE');

    // Notify telemetry callback
    this.callbacks.onTelemetry?.(msg);
  }

  private resetStaleTimer(): void {
    if (this.staleTimer) {
      clearTimeout(this.staleTimer);
    }

    this.staleTimer = setTimeout(() => {
      if (this.state === 'CONNECTED') {
        this.updateFreshness('STALE');
      }
    }, WEBSOCKET_CONFIG.telemetryStaleAfterMs);
  }

  private handleClose(): void {
    this.ws = null;
    this.clearTimers();

    if (this.isManualDisconnect) {
      this.updateState('DISCONNECTED');
      this.updateFreshness('NO_DATA');
    } else {
      this.scheduleReconnect();
    }
  }

  private scheduleReconnect(): void {
    if (this.reconnectAttempt >= WEBSOCKET_CONFIG.maxReconnectAttempts) {
      this.updateState('DISCONNECTED');
      this.updateFreshness('NO_DATA');
      return;
    }

    this.updateState('RECONNECTING');
    this.updateFreshness('NO_DATA');

    const schedule = WEBSOCKET_CONFIG.reconnectScheduleMs;
    const delay = schedule[Math.min(this.reconnectAttempt, schedule.length - 1)];
    this.reconnectAttempt++;

    this.reconnectTimer = setTimeout(() => {
      this.connect();
    }, delay);
  }

  private clearTimers(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.staleTimer) {
      clearTimeout(this.staleTimer);
      this.staleTimer = null;
    }
  }

  private updateState(newState: ConnectionState): void {
    if (this.state !== newState) {
      this.state = newState;
      this.callbacks.onStateChange?.(newState);
    }
  }

  private updateFreshness(newFreshness: TelemetryFreshness): void {
    if (this.freshness !== newFreshness) {
      this.freshness = newFreshness;
      this.callbacks.onFreshnessChange?.(newFreshness);
    }
  }
}
