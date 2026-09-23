/**
 * Physics Twin API client module.
 * Provides REST calls for expected state, residuals, diagnostics, and calibration.
 */

import { apiClient } from './client';
import {
  PhysicsCalibrationParametersDto,
  PhysicsResidualSetDto,
  PhysicsTwinResultDto,
  PhysicsStatusDto,
} from './types';
import { TelemetryFramePayload } from '../services/websocket/types';

export async function fetchPhysicsStatus(): Promise<PhysicsStatusDto> {
  return apiClient.get<PhysicsStatusDto>('/api/v1/physics/status');
}

export async function fetchPhysicsCurrent(): Promise<PhysicsTwinResultDto> {
  return apiClient.get<PhysicsTwinResultDto>('/api/v1/physics/current');
}

export async function fetchPhysicsResiduals(): Promise<PhysicsResidualSetDto> {
  return apiClient.get<PhysicsResidualSetDto>('/api/v1/physics/residuals');
}

export async function fetchPhysicsCalibration(): Promise<PhysicsCalibrationParametersDto> {
  return apiClient.get<PhysicsCalibrationParametersDto>('/api/v1/physics/calibration');
}

export async function updatePhysicsCalibration(
  params: PhysicsCalibrationParametersDto
): Promise<PhysicsCalibrationParametersDto> {
  return apiClient.post<PhysicsCalibrationParametersDto>('/api/v1/physics/calibration', params);
}

export async function evaluatePhysicsFrame(
  frame: TelemetryFramePayload
): Promise<PhysicsTwinResultDto> {
  return apiClient.post<PhysicsTwinResultDto>('/api/v1/physics/evaluate', frame);
}
