import { describe, it, expect, beforeEach } from 'vitest';
import { useTwinStore } from '../../../stores/useTwinStore';
import {
  MLInferenceResultDto,
  TelemetryMessage,
} from '../../../services/websocket/types';

describe('ML Diagnostics Store & Ingestion', () => {
  beforeEach(() => {
    useTwinStore.getState().resetToNominal();
  });

  const mockMLResult: MLInferenceResultDto = {
    timestamp: 100.0,
    sequence_id: 1,
    feature_schema_version: '1.0.0',
    anomaly: {
      flag: true,
      status: 'ANOMALOUS',
      score: 0.88,
      raw_score: 0.02,
      threshold: 0.54,
      confidence: 0.82,
      detector_name: 'IsolationForest',
      model_version: '1.0.0',
    },
    fault: {
      fault_class: 'OIL_PRESSURE_BIAS',
      reason: 'CONFIDENT_MATCH',
      confidence: 0.985,
      probabilities: {
        NORMAL: 0.01,
        OIL_PRESSURE_BIAS: 0.985,
        OIL_TEMP_DRIFT: 0.002,
        THROTTLE_STUCK: 0.001,
        SENSOR_DROPOUT: 0.001,
        MAP_NOISE_SPIKE: 0.001,
      },
      threshold_applied: 0.60,
      classifier_name: 'XGBoostFaultClassifier',
      model_version: '1.0.0',
    },
    top_contributions: [
      {
        feature_name: 'res_oil_p_raw',
        contribution_weight: 0.65,
        direction: 'ELEVATED',
      },
      {
        feature_name: 'oil_pressure',
        contribution_weight: 0.25,
        direction: 'ELEVATED',
      },
    ],
    inference_latency_ms: 4.85,
    disaggregated_latencies: {
      feature_extraction_ms: 0.02,
      anomaly_detection_ms: 4.20,
      fault_classification_ms: 0.55,
      explainability_ms: 0.08,
      total_inference_ms: 4.85,
    },
    validity: 'VALID',
    prototype_notice: 'PROTOTYPE RESEARCH MODEL — NOT FOR CERTIFIED FLIGHT OPERATIONS',
  };

  it('updates mlResult via setMlResult', () => {
    const store = useTwinStore.getState();
    expect(store.mlResult).toBeNull();

    store.setMlResult(mockMLResult);
    const state = useTwinStore.getState();
    expect(state.mlResult).toEqual(mockMLResult);
    expect(state.mlResult?.anomaly.flag).toBe(true);
    expect(state.mlResult?.fault.fault_class).toBe('OIL_PRESSURE_BIAS');
    expect(state.mlResult?.top_contributions.length).toBe(2);
  });

  it('ingests mlResult attached to incoming TelemetryMessage', () => {
    const store = useTwinStore.getState();

    const msg: TelemetryMessage = {
      type: 'telemetry',
      version: '1.0.0',
      timestamp: 100.1,
      sequence_id: 2,
      server_time: 100.1,
      payload: {
        version: '1.0.0',
        timestamp: 100.1,
        sequence_id: 2,
        source_type: 'SIMULATED',
        quality_flag: 'VALID',
        rpm: 2400.0,
        manifold_pressure: 29.5,
        throttle_position: 45.0,
        fuel_flow: 16.5,
        fuel_pressure: 3.0,
        injection_timing: 15.0,
        cht: [95.0, 95.0, 95.0, 95.0],
        egt: [720.0, 720.0, 720.0, 720.0],
        coolant_temp: 82.0,
        oil_temperature: 85.0,
        oil_pressure: 5.8,
        vibration_rms: 1.15,
        battery_voltage: 28.2,
        alternator_current: 20.0,
        alternator_status: 'OK',
        altitude: 500.0,
        ambient_temp: 20.0,
        true_airspeed: 45.0,
      },
      ml: mockMLResult,
    };

    store.handleIncomingTelemetry(msg);

    const updated = useTwinStore.getState();
    expect(updated.mlResult).not.toBeNull();
    expect(updated.mlResult?.fault.fault_class).toBe('OIL_PRESSURE_BIAS');
    expect(updated.mlResult?.anomaly.status).toBe('ANOMALOUS');
  });

  it('clears mlResult when store is resetToNominal', () => {
    const store = useTwinStore.getState();
    store.setMlResult(mockMLResult);
    expect(useTwinStore.getState().mlResult).not.toBeNull();

    store.resetToNominal();
    expect(useTwinStore.getState().mlResult).toBeNull();
  });
});
