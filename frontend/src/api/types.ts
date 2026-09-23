/**
 * Frontend API DTO and contract interfaces mirroring backend schemas.
 */

export interface HealthResponse {
  status: string;
  version: string;
  environment: string;
  timestamp: number;
  uptime_seconds: number;
}

export interface ReadinessResponse {
  status: 'ready' | 'not_ready' | 'degraded';
  components: Record<string, string>;
  telemetry_rate_hz: number;
  timestamp: number;
}

export interface SystemInfoResponse {
  name: string;
  version: string;
  description: string;
  environment: string;
  engine_baseline: string;
  telemetry_rate_hz: number;
  dt_seconds: number;
}

export interface ApiErrorResponse {
  status: string;
  error_code: string;
  message: string;
  request_id?: string;
  timestamp: number;
  details?: Record<string, unknown>;
}

export type {
  ModelValidityDto,
  PhysicsExpectedStateDto,
  PhysicsResidualSetDto,
  PhysicsTwinResultDto,
} from '../services/websocket/types';

export interface PhysicsStatusDto {
  evaluation_count: number;
  average_compute_time_ms: number;
  invalid_frame_count: number;
  out_of_range_count: number;
  calibration_version: string;
  model_status: string;
}

export interface PhysicsCalibrationParametersDto {
  version: string;
  engine_displacement_cc: number;
  idle_rpm: number;
  rated_rpm: number;
  spool_rpm: number;
  max_boost_pr: number;
  tau_cht_seconds: number;
  tau_egt_seconds: number;
  tau_oil_seconds: number;
  tau_coolant_seconds: number;
  cht_cylinder_bias: [number, number, number, number];
  egt_cylinder_bias: [number, number, number, number];
  sigma_scales: Record<string, number>;
}
