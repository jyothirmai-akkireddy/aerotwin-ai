/**
 * Type-safe definitions for the AeroTwin AI WebSocket Protocol v1.0.0.
 */

export type ConnectionState =
  | 'DISCONNECTED'
  | 'CONNECTING'
  | 'CONNECTED'
  | 'RECONNECTING'
  | 'ERROR';

export type TelemetryFreshness = 'LIVE' | 'STALE' | 'NO_DATA';

export type TransportMode = 'WEBSOCKET' | 'MANUAL_DEV';

export interface TelemetryFramePayload {
  version: string;
  timestamp: number;
  sequence_id: number;
  source_type: string;
  quality_flag: string;
  rpm: number;
  manifold_pressure: number;
  throttle_position: number;
  fuel_flow: number;
  fuel_pressure: number;
  injection_timing: number;
  cht: [number, number, number, number];
  egt: [number, number, number, number];
  coolant_temp: number;
  oil_temperature: number;
  oil_pressure: number;
  vibration_rms: number;
  battery_voltage: number;
  alternator_current: number;
  alternator_status: string;
  altitude: number;
  ambient_temp: number;
  true_airspeed: number;
}

export type ModelValidityDto = 'VALID' | 'DEGRADED' | 'OUT_OF_RANGE' | 'INVALID';

export interface PhysicsExpectedStateDto {
  timestamp: number;
  sequence_id: number;
  rpm: number;
  manifold_pressure: number;
  air_mass_flow: number;
  fuel_flow: number;
  cht: [number, number, number, number];
  egt: [number, number, number, number];
  coolant_temp: number;
  oil_temperature: number;
  oil_pressure: number;
  vibration_rms: number;
  validity: ModelValidityDto;
  confidence: number;
  model_version: string;
}

export interface PhysicsResidualSetDto {
  timestamp: number;
  sequence_id: number;
  raw_residuals: Record<string, number | number[]>;
  normalized_residuals: Record<string, number | number[]>;
  cht_max_imbalance_celsius: number;
  egt_max_imbalance_celsius: number;
  mean_absolute_normalized_residual: number;
  validity: ModelValidityDto;
  confidence: number;
}

export interface PhysicsTwinResultDto {
  expected_state: PhysicsExpectedStateDto;
  residuals: PhysicsResidualSetDto;
  diagnostics?: Record<string, unknown>;
}

export type AnomalyStatusDto = 'NORMAL' | 'ANOMALOUS';

export type FaultCategoryDto =
  | 'NORMAL'
  | 'OIL_PRESSURE_BIAS'
  | 'OIL_TEMP_DRIFT'
  | 'THROTTLE_STUCK'
  | 'SENSOR_DROPOUT'
  | 'MAP_NOISE_SPIKE'
  | 'UNKNOWN';

export type DecisionReasonDto =
  | 'CONFIDENT_MATCH'
  | 'NOMINAL_FLIGHT'
  | 'LOW_CONFIDENCE'
  | 'OUT_OF_DISTRIBUTION';

export interface FeatureContributionDto {
  feature_name: string;
  contribution_weight: number;
  direction: 'ELEVATED' | 'DEPRESSED' | 'IRREGULAR';
}

export interface AnomalyInferenceDto {
  flag: boolean;
  status: AnomalyStatusDto;
  score: number;
  raw_score: number;
  threshold: number;
  confidence: number;
  detector_name: string;
  model_version: string;
}

export interface FaultInferenceDto {
  fault_class: FaultCategoryDto;
  reason: DecisionReasonDto;
  confidence: number;
  probabilities: Record<string, number>;
  threshold_applied: number;
  classifier_name: string;
  model_version: string;
}

export interface MLInferenceResultDto {
  timestamp: number;
  sequence_id: number;
  feature_schema_version: string;
  anomaly: AnomalyInferenceDto;
  fault: FaultInferenceDto;
  top_contributions: FeatureContributionDto[];
  inference_latency_ms: number;
  disaggregated_latencies?: Record<string, number>;
  validity: 'VALID' | 'DEGRADED' | 'INVALID';
  prototype_notice: string;
}

export type DegradationStateDto =
  | 'NOMINAL'
  | 'EARLY_DEGRADATION'
  | 'MODERATE_DEGRADATION'
  | 'SEVERE_DEGRADATION'
  | 'CRITICAL_SIMULATED_STATE';

export type TrendDirectionDto = 'IMPROVING' | 'STABLE' | 'DEGRADING' | 'UNKNOWN';

export type RULStatusDto =
  | 'ACTIVE'
  | 'INSUFFICIENT_HISTORY'
  | 'RUL_UNAVAILABLE'
  | 'DEGRADATION_NOT_DETECTED';

export interface SubsystemDegradationMetricDto {
  raw_deviation: number;
  normalized_deviation: number;
  bounded_penalty: number;
  unit: string;
}

export interface SubsystemDegradationDto {
  lubrication: SubsystemDegradationMetricDto;
  thermal: SubsystemDegradationMetricDto;
  turbocharger: SubsystemDegradationMetricDto;
  rotational_vibration: SubsystemDegradationMetricDto;
  anomaly_penalty: number;
  lubrication_health_pct: number;
  thermal_health_pct: number;
  turbocharger_health_pct: number;
  rotational_health_pct: number;
  limiting_subsystem: string;
}

export interface RULEstimateDto {
  status: RULStatusDto;
  estimated_remaining_flight_hours: number | null;
  confidence_interval_95: [number, number] | null;
  confidence: number;
  limiting_subsystem: string;
  degradation_rate_per_hour: number | null;
  reason: string;
}

export interface PrognosticIndicatorDto {
  name: string;
  current_value: number;
  baseline_value: number;
  raw_deviation: number;
  normalized_deviation: number;
  unit: string;
  severity: 'NORMAL' | 'ADVISORY' | 'WARNING' | 'CRITICAL';
  trend: TrendDirectionDto;
}

export interface PrognosticResultDto {
  timestamp: number;
  sequence_id: number;
  feature_schema_version: string;
  health_index: number;
  degradation_state: DegradationStateDto;
  trend_direction: TrendDirectionDto;
  trend_slope_per_sec: number;
  subsystems: SubsystemDegradationDto;
  rul: RULEstimateDto;
  indicators: PrognosticIndicatorDto[];
  pipeline_latency_ms: number;
  disaggregated_latencies?: Record<string, number>;
  validity: 'VALID' | 'DEGRADED' | 'INVALID';
  prototype_notice: string;
}

export type PlaybackStateDto = 'IDLE' | 'PLAYING' | 'PAUSED' | 'COMPLETED' | 'STOPPED';

export type ReplayExecutionModeDto = 'REALTIME' | 'ACCELERATED' | 'OFFLINE_BATCH';

export const APPROVED_ACCELERATED_SPEEDS = [0.5, 1.0, 2.0, 5.0, 10.0] as const;
export type ApprovedAcceleratedSpeed = (typeof APPROVED_ACCELERATED_SPEEDS)[number];

export interface ReplayCursorStatusDto {
  playback_state: PlaybackStateDto;
  execution_mode: ReplayExecutionModeDto;
  current_index: number;
  total_frames: number;
  data_timestamp: number;
  start_timestamp: number;
  end_timestamp: number;
  elapsed_sim_time_sec: number;
  total_sim_time_sec: number;
  progress_pct: number;
  playback_speed: number;
  source_filename?: string | null;
  is_looping: boolean;
}

export interface ReplayDatasetMetadataDto {
  filename: string;
  format: 'PARQUET' | 'SQLITE' | 'CSV';
  size_bytes: number;
  total_frames: number;
  start_timestamp: number;
  end_timestamp: number;
  duration_sec: number;
  nominal_rate_hz: number;
}

export interface MissionTelemetryContextDto {
  mission_id: string;
  mission_name: string;
  current_phase_id: string;
  current_phase_type: string;
  phase_elapsed_sec: number;
  phase_duration_sec: number;
  mission_elapsed_sec: number;
  total_duration_sec: number;
  mission_progress_pct: number;
}

export interface TelemetryMessage {
  type: 'telemetry';
  version: string;
  timestamp: number;
  sequence_id: number;
  server_time: number;
  source_mode?: 'LIVE' | 'REPLAY';
  payload: TelemetryFramePayload;
  physics?: PhysicsTwinResultDto;
  ml?: MLInferenceResultDto;
  prognostics?: PrognosticResultDto;
  mission?: MissionTelemetryContextDto;
  replay?: ReplayCursorStatusDto;
}

export interface StatusMessage {
  type: 'status';
  version: string;
  status: 'connected' | 'running' | 'paused' | 'stopped' | 'degraded' | 'error';
  message: string;
  server_time: number;
}

export interface ErrorMessage {
  type: 'error';
  version: string;
  code: string;
  message: string;
  server_time?: number;
}

export interface HeartbeatMessage {
  type: 'heartbeat';
  version: string;
  server_time: number;
}

export type WebSocketInboundMessage =
  | TelemetryMessage
  | StatusMessage
  | ErrorMessage
  | HeartbeatMessage;

export interface ClientCommand {
  type: 'command';
  version: '1.0.0';
  command:
    | 'start'
    | 'pause'
    | 'resume'
    | 'reset'
    | 'set_scenario'
    | 'set_rate'
    | 'replay_play'
    | 'replay_pause'
    | 'replay_resume'
    | 'replay_seek'
    | 'replay_speed'
    | 'replay_mode'
    | 'replay_reset'
    | 'set_source';
  params?: Record<string, unknown>;
}

export interface ClientPing {
  type: 'ping';
}
