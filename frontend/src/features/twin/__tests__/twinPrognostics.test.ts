import { describe, it, expect, beforeEach } from 'vitest';
import { useTwinStore } from '../../../stores/useTwinStore';
import {
  PrognosticResultDto,
  TelemetryMessage,
} from '../../../services/websocket/types';

describe('Engine Prognostics & RUL Store Ingestion', () => {
  beforeEach(() => {
    useTwinStore.getState().resetToNominal();
    useTwinStore.getState().setPrognosticsResult(null);
  });

  const mockPrognosticResult: PrognosticResultDto = {
    timestamp: 100.0,
    sequence_id: 1,
    feature_schema_version: '1.0.0',
    health_index: 0.725,
    degradation_state: 'MODERATE_DEGRADATION',
    trend_direction: 'DEGRADING',
    trend_slope_per_sec: -0.00045,
    subsystems: {
      lubrication: {
        raw_deviation: 1.25,
        normalized_deviation: 3.12,
        bounded_penalty: 1.0,
        unit: 'bar/°C',
      },
      thermal: {
        raw_deviation: 12.5,
        normalized_deviation: 1.56,
        bounded_penalty: 0.52,
        unit: '°C',
      },
      turbocharger: {
        raw_deviation: 0.8,
        normalized_deviation: 0.8,
        bounded_penalty: 0.267,
        unit: 'inHg',
      },
      rotational_vibration: {
        raw_deviation: 0.2,
        normalized_deviation: 0.8,
        bounded_penalty: 0.267,
        unit: 'g',
      },
      anomaly_penalty: 0.25,
      lubrication_health_pct: 0.0,
      thermal_health_pct: 48.0,
      turbocharger_health_pct: 73.3,
      rotational_health_pct: 73.3,
      limiting_subsystem: 'lubrication',
    },
    rul: {
      status: 'ACTIVE',
      estimated_remaining_flight_hours: 14.2,
      confidence_interval_95: [11.8, 16.5],
      confidence: 0.88,
      limiting_subsystem: 'lubrication',
      degradation_rate_per_hour: 1.62,
      reason: 'Active simulated degradation detected on lubrication; RUL projected',
    },
    indicators: [
      {
        name: 'oil_pressure',
        current_value: 2.55,
        baseline_value: 3.8,
        raw_deviation: 1.25,
        normalized_deviation: 3.12,
        unit: 'bar',
        severity: 'CRITICAL',
        trend: 'DEGRADING',
      },
    ],
    pipeline_latency_ms: 3.85,
    disaggregated_latencies: {
      health_index_ms: 0.05,
      trend_analysis_ms: 0.28,
      rul_estimation_ms: 3.52,
    },
    validity: 'VALID',
    prototype_notice: 'PROTOTYPE RESEARCH MODEL — NOT FOR CERTIFIED FLIGHT OPERATIONS',
  };

  it('initializes with null prognosticsResult', () => {
    const state = useTwinStore.getState();
    expect(state.prognosticsResult).toBeNull();
  });

  it('updates prognosticsResult via explicit setter', () => {
    useTwinStore.getState().setPrognosticsResult(mockPrognosticResult);
    const state = useTwinStore.getState();
    expect(state.prognosticsResult).toEqual(mockPrognosticResult);
    expect(state.prognosticsResult?.health_index).toBe(0.725);
    expect(state.prognosticsResult?.rul.status).toBe('ACTIVE');
    expect(state.prognosticsResult?.rul.estimated_remaining_flight_hours).toBe(14.2);
    expect(state.prognosticsResult?.subsystems.lubrication.raw_deviation).toBe(1.25);
  });

  it('ingests prognostics result automatically via handleIncomingTelemetry', () => {
    const msg: TelemetryMessage = {
      type: 'telemetry',
      version: '1.0.0',
      timestamp: 100.0,
      sequence_id: 1,
      server_time: 100.05,
      payload: {
        version: '1.0.0',
        timestamp: 100.0,
        sequence_id: 1,
        source_type: 'SIMULATED',
        quality_flag: 'VALID',
        rpm: 2400.0,
        manifold_pressure: 29.5,
        throttle_position: 45.0,
        fuel_flow: 16.5,
        fuel_pressure: 3.0,
        injection_timing: 15.0,
        cht: [95.0, 92.5, 98.0, 94.0],
        egt: [720.0, 715.0, 730.0, 722.0],
        coolant_temp: 82.0,
        oil_temperature: 85.0,
        oil_pressure: 3.8,
        vibration_rms: 1.15,
        battery_voltage: 28.2,
        alternator_current: 14.0,
        alternator_status: 'OK',
        altitude: 1500.0,
        ambient_temp: 15.0,
        true_airspeed: 45.0,
      },
      prognostics: mockPrognosticResult,
    };

    useTwinStore.getState().handleIncomingTelemetry(msg);

    const state = useTwinStore.getState();
    expect(state.prognosticsResult).not.toBeNull();
    expect(state.prognosticsResult?.health_index).toBe(0.725);
    expect(state.prognosticsResult?.rul.status).toBe('ACTIVE');
    expect(state.prognosticsResult?.subsystems.limiting_subsystem).toBe('lubrication');
  });
});
