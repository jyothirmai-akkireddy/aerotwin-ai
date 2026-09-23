/**
 * Engine Degradation & Prognostics REST API client module.
 */

import { apiClient } from './client';
import {
  MLInferenceResultDto,
  PhysicsTwinResultDto,
  PrognosticResultDto,
  TelemetryFramePayload,
} from '../services/websocket/types';

export interface PrognosticsStatusDto {
  ready: boolean;
  model_fitted: boolean;
  feature_schema_version: string;
  buffer_size: number;
  buffer_capacity: number;
  evaluations_count: number;
  mean_pipeline_latency_ms: number;
  disclaimer: string;
  model_metadata?: Record<string, unknown>;
  last_result?: PrognosticResultDto;
}

export async function fetchPrognosticsStatus(): Promise<PrognosticsStatusDto> {
  return apiClient.get<PrognosticsStatusDto>('/api/v1/prognostics/status');
}

export async function fetchPrognosticsCurrent(): Promise<PrognosticResultDto | null> {
  return apiClient.get<PrognosticResultDto | null>('/api/v1/prognostics/current');
}

export async function evaluatePrognosticsFrame(
  frame: TelemetryFramePayload,
  physics?: PhysicsTwinResultDto,
  ml?: MLInferenceResultDto
): Promise<PrognosticResultDto> {
  return apiClient.post<PrognosticResultDto>('/api/v1/prognostics/evaluate', {
    frame,
    physics,
    ml,
  });
}
