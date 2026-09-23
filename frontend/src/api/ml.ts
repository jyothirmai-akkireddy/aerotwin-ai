/**
 * Machine Learning Diagnostics API client module.
 * Provides REST calls for status, models metadata, features manifest, and evaluation.
 */

import { apiClient } from './client';
import {
  MLInferenceResultDto,
  PhysicsTwinResultDto,
  TelemetryFramePayload,
} from '../services/websocket/types';

export interface MLStatusDto {
  evaluation_count: number;
  anomaly_count: number;
  anomaly_rate_pct: number;
  fault_breakdown: Record<string, number>;
  status: 'READY' | 'DEGRADED';
  average_latencies_ms: {
    feature_extraction: number;
    anomaly_detection: number;
    fault_classification: number;
    explainability: number;
    total_pipeline: number;
  };
}

export interface MLModelsMetadataDto {
  feature_schema_version: string;
  anomaly_detector: {
    name: string;
    version: string;
    threshold: number;
    fitted: boolean;
    metadata?: Record<string, unknown>;
  };
  fault_classifier: {
    name: string;
    version: string;
    confidence_threshold: number;
    fitted: boolean;
    metadata?: Record<string, unknown>;
  };
  provenance: string;
  prototype_notice: string;
}

export interface MLFeaturesManifestDto {
  schema_version: string;
  feature_count: number;
  features: string[];
  nominal_baselines: Record<string, number>;
}

export async function fetchMLStatus(): Promise<MLStatusDto> {
  return apiClient.get<MLStatusDto>('/api/v1/ml/status');
}

export async function fetchMLModels(): Promise<MLModelsMetadataDto> {
  return apiClient.get<MLModelsMetadataDto>('/api/v1/ml/models');
}

export async function fetchMLFeatures(): Promise<MLFeaturesManifestDto> {
  return apiClient.get<MLFeaturesManifestDto>('/api/v1/ml/features');
}

export async function fetchMLCurrent(): Promise<MLInferenceResultDto | null> {
  return apiClient.get<MLInferenceResultDto | null>('/api/v1/ml/current');
}

export async function evaluateMLFrame(
  frame: TelemetryFramePayload,
  physics?: PhysicsTwinResultDto | null
): Promise<MLInferenceResultDto> {
  return apiClient.post<MLInferenceResultDto>('/api/v1/ml/evaluate', {
    frame,
    physics,
  });
}
