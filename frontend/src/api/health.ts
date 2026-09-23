/**
 * Health and system diagnostics API methods.
 */

import { apiClient } from './client';
import { HealthResponse, ReadinessResponse, SystemInfoResponse } from './types';

export async function fetchHealth(): Promise<HealthResponse> {
  return apiClient.get<HealthResponse>('/api/v1/health');
}

export async function fetchReadiness(): Promise<ReadinessResponse> {
  return apiClient.get<ReadinessResponse>('/api/v1/ready');
}

export async function fetchSystemInfo(): Promise<SystemInfoResponse> {
  return apiClient.get<SystemInfoResponse>('/api/v1/info');
}
