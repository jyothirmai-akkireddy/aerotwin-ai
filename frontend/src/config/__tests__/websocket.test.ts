import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { getWebSocketUrl } from '../websocket';

describe('getWebSocketUrl Dynamic Resolution', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('falls back to localhost:8000 when window is undefined', () => {
    const url = getWebSocketUrl();
    expect(url).toBe('ws://localhost:8000/api/v1/ws/telemetry');
  });

  it('resolves localhost with port 8000 in local development', () => {
    vi.stubGlobal('window', {
      location: {
        protocol: 'http:',
        hostname: 'localhost',
        host: 'localhost:5173',
      },
    });

    const url = getWebSocketUrl();
    expect(url).toBe('ws://localhost:8000/api/v1/ws/telemetry');
  });

  it('resolves 127.0.0.1 with port 8000 in local development', () => {
    vi.stubGlobal('window', {
      location: {
        protocol: 'http:',
        hostname: '127.0.0.1',
        host: '127.0.0.1:5173',
      },
    });

    const url = getWebSocketUrl();
    expect(url).toBe('ws://127.0.0.1:8000/api/v1/ws/telemetry');
  });

  it('resolves production HTTPS without port 8000', () => {
    vi.stubGlobal('window', {
      location: {
        protocol: 'https:',
        hostname: 'aerotwin-ai-kappa.vercel.app',
        host: 'aerotwin-ai-kappa.vercel.app',
      },
    });

    const url = getWebSocketUrl();
    expect(url).toBe('wss://aerotwin-ai-kappa.vercel.app/api/v1/ws/telemetry');
    expect(url).not.toContain(':8000');
  });

  it('resolves any arbitrary production host dynamically without hardcoding', () => {
    vi.stubGlobal('window', {
      location: {
        protocol: 'https:',
        hostname: 'telemetry.aerotwin.org',
        host: 'telemetry.aerotwin.org',
      },
    });

    const url = getWebSocketUrl();
    expect(url).toBe('wss://telemetry.aerotwin.org/api/v1/ws/telemetry');
  });
});
