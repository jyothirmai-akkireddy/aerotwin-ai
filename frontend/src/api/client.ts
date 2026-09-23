/**
 * Centralized API client abstraction.
 * Enforces typed requests, timeout handling, correlation IDs, and normalized error responses.
 */

import { ApiErrorResponse } from './types';

export class ApiError extends Error {
  public readonly status: number;
  public readonly code: string;
  public readonly requestId?: string;
  public readonly details?: Record<string, unknown>;

  constructor(status: number, errorData: ApiErrorResponse) {
    super(errorData.message || 'API request failed');
    this.name = 'ApiError';
    this.status = status;
    this.code = errorData.error_code || 'UNKNOWN_ERROR';
    this.requestId = errorData.request_id;
    this.details = errorData.details;
  }
}

export interface RequestOptions extends RequestInit {
  timeoutMs?: number;
}

const DEFAULT_TIMEOUT_MS = 8000;
const BASE_URL = (import.meta.env.VITE_API_BASE_URL as string) || '';

export async function request<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
  const { timeoutMs = DEFAULT_TIMEOUT_MS, headers, ...restOptions } = options;

  const url = endpoint.startsWith('http') ? endpoint : `${BASE_URL}${endpoint}`;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  const requestHeaders = new Headers(headers);
  if (!requestHeaders.has('Accept')) {
    requestHeaders.set('Accept', 'application/json');
  }
  if (!requestHeaders.has('Content-Type') && restOptions.body) {
    requestHeaders.set('Content-Type', 'application/json');
  }

  try {
    const response = await fetch(url, {
      ...restOptions,
      headers: requestHeaders,
      signal: controller.signal,
    });

    const contentType = response.headers.get('content-type') || '';
    const isJson = contentType.includes('application/json');
    const responseData = isJson ? await response.json() : await response.text();

    if (!response.ok) {
      const errorPayload: ApiErrorResponse = isJson
        ? (responseData as ApiErrorResponse)
        : {
            status: 'error',
            error_code: `HTTP_${response.status}`,
            message: String(responseData) || response.statusText,
            timestamp: Date.now() / 1000,
          };
      throw new ApiError(response.status, errorPayload);
    }

    return responseData as T;
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    if ((error as Error).name === 'AbortError') {
      throw new ApiError(408, {
        status: 'error',
        error_code: 'REQUEST_TIMEOUT',
        message: `Request timed out after ${timeoutMs}ms`,
        timestamp: Date.now() / 1000,
      });
    }
    throw new ApiError(0, {
      status: 'error',
      error_code: 'NETWORK_ERROR',
      message: (error as Error).message || 'Network communication failed',
      timestamp: Date.now() / 1000,
    });
  } finally {
    clearTimeout(timeoutId);
  }
}

export const apiClient = {
  get: <T>(endpoint: string, options?: RequestOptions) =>
    request<T>(endpoint, { ...options, method: 'GET' }),
  post: <T>(endpoint: string, body?: unknown, options?: RequestOptions) =>
    request<T>(endpoint, {
      ...options,
      method: 'POST',
      body: body ? JSON.stringify(body) : undefined,
    }),
};
