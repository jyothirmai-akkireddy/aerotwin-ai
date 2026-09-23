import { describe, it, expect } from 'vitest';
import { ApiError } from './client';
import { ApiErrorResponse } from './types';

describe('API Client & Error Handling', () => {
  it('constructs ApiError with status, error_code, and request_id', () => {
    const errorPayload: ApiErrorResponse = {
      status: 'error',
      error_code: 'INVARIANT_VIOLATION',
      message: 'Physical bounds check failed',
      request_id: 'req-uuid-12345',
      timestamp: 1774358400,
      details: { field: 'rpm' },
    };

    const err = new ApiError(422, errorPayload);
    expect(err.name).toBe('ApiError');
    expect(err.status).toBe(422);
    expect(err.code).toBe('INVARIANT_VIOLATION');
    expect(err.requestId).toBe('req-uuid-12345');
    expect(err.message).toBe('Physical bounds check failed');
    expect(err.details).toEqual({ field: 'rpm' });
  });

  it('provides default error message if error payload is empty', () => {
    const err = new ApiError(500, {
      status: 'error',
      error_code: 'INTERNAL_ERROR',
      message: '',
      timestamp: 1774358400,
    });
    expect(err.message).toBe('API request failed');
  });

  describe('resolveApiUrl', () => {
    it('preserves absolute URLs starting with http:// or https://', async () => {
      const { resolveApiUrl } = await import('./client');
      expect(resolveApiUrl('https://api.external.com/telemetry')).toBe('https://api.external.com/telemetry');
      expect(resolveApiUrl('http://localhost:8000/api/v1/health')).toBe('http://localhost:8000/api/v1/health');
    });

    it('resolves relative paths with leading slash', async () => {
      const { resolveApiUrl, getApiBaseUrl } = await import('./client');
      const base = getApiBaseUrl();
      expect(resolveApiUrl('/api/v1/missions/predefined')).toBe(`${base}/api/v1/missions/predefined`);
      expect(resolveApiUrl('api/v1/missions/predefined')).toBe(`${base}/api/v1/missions/predefined`);
    });
  });
});
