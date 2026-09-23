import { describe, it, expect, beforeEach } from 'vitest';
import { useTwinStore } from '../../../stores/useTwinStore';
import {
  TelemetryMessage,
  MissionTelemetryContextDto,
  ReplayCursorStatusDto,
} from '../../../services/websocket/types';

describe('useTwinStore Phase 8 Mission & Replay State Ingestion', () => {
  beforeEach(() => {
    useTwinStore.getState().resetToNominal();
    useTwinStore.getState().clearTelemetryBuffer();
    useTwinStore.getState().setSourceMode('LIVE');
    useTwinStore.getState().setReplayStatus(null);
    useTwinStore.getState().setMissionContext(null);
  });

  const createBaseMsg = (seq: number): TelemetryMessage => ({
    type: 'telemetry',
    version: '1.0.0',
    timestamp: 100.0 + seq * 0.1,
    sequence_id: seq,
    server_time: 100.0 + seq * 0.1,
    source_mode: 'LIVE',
    payload: {
      version: '1.0.0',
      timestamp: 100.0 + seq * 0.1,
      sequence_id: seq,
      source_type: 'SIMULATED',
      quality_flag: 'VALID',
      rpm: 2500.0,
      manifold_pressure: 29.5,
      throttle_position: 50.0,
      fuel_flow: 18.0,
      fuel_pressure: 3.2,
      injection_timing: 24.0,
      cht: [95.0, 96.0, 94.0, 95.0],
      egt: [720.0, 725.0, 718.0, 722.0],
      coolant_temp: 82.0,
      oil_temperature: 85.0,
      oil_pressure: 3.8,
      vibration_rms: 1.1,
      battery_voltage: 28.2,
      alternator_current: 18.5,
      alternator_status: 'OK',
      altitude: 1500.0,
      ambient_temp: 15.0,
      true_airspeed: 50.0,
    },
  });

  it('manages source mode state transitions', () => {
    const store = useTwinStore.getState();
    expect(store.sourceMode).toBe('LIVE');

    store.setSourceMode('REPLAY');
    expect(useTwinStore.getState().sourceMode).toBe('REPLAY');

    store.setSourceMode('LIVE');
    expect(useTwinStore.getState().sourceMode).toBe('LIVE');
  });

  it('ingests telemetry message with mission context and updates store', () => {
    const store = useTwinStore.getState();
    const msg = createBaseMsg(1);
    const missionCtx: MissionTelemetryContextDto = {
      mission_id: 'SURVEILLANCE_MISSION',
      mission_name: 'Surveillance Mission 1',
      current_phase_id: 'CRUISE_RECON',
      current_phase_type: 'CRUISE',
      phase_elapsed_sec: 145.2,
      phase_duration_sec: 300.0,
      mission_elapsed_sec: 325.2,
      total_duration_sec: 600.0,
      mission_progress_pct: 48.4,
    };
    msg.mission = missionCtx;

    store.handleIncomingTelemetry(msg);

    const updated = useTwinStore.getState();
    expect(updated.missionContext).not.toBeNull();
    expect(updated.missionContext?.mission_id).toBe('SURVEILLANCE_MISSION');
    expect(updated.missionContext?.current_phase_id).toBe('CRUISE_RECON');
    expect(updated.missionContext?.mission_progress_pct).toBe(48.4);
  });

  it('ingests telemetry message with replay status and updates store', () => {
    const store = useTwinStore.getState();
    const msg = createBaseMsg(2);
    msg.source_mode = 'REPLAY';
    const replayStat: ReplayCursorStatusDto = {
      source_filename: 'flight_test_2026_01.parquet',
      execution_mode: 'REALTIME',
      playback_state: 'PLAYING',
      current_index: 125,
      total_frames: 500,
      data_timestamp: 12.5,
      start_timestamp: 0.0,
      end_timestamp: 50.0,
      elapsed_sim_time_sec: 12.5,
      total_sim_time_sec: 50.0,
      progress_pct: 25.0,
      playback_speed: 1.0,
      is_looping: false,
    };
    msg.replay = replayStat;

    store.handleIncomingTelemetry(msg);

    const updated = useTwinStore.getState();
    expect(updated.sourceMode).toBe('REPLAY');
    expect(updated.replayStatus).not.toBeNull();
    expect(updated.replayStatus?.source_filename).toBe('flight_test_2026_01.parquet');
    expect(updated.replayStatus?.playback_state).toBe('PLAYING');
    expect(updated.replayStatus?.current_index).toBe(125);
    expect(updated.replayStatus?.progress_pct).toBe(25.0);
    expect(updated.replayStatus?.playback_speed).toBe(1.0);
  });

  it('clears and overrides replay status when explicitly set', () => {
    const store = useTwinStore.getState();
    const status: ReplayCursorStatusDto = {
      source_filename: 'sample.csv',
      execution_mode: 'ACCELERATED',
      playback_state: 'PAUSED',
      current_index: 50,
      total_frames: 100,
      data_timestamp: 5.0,
      start_timestamp: 0.0,
      end_timestamp: 10.0,
      elapsed_sim_time_sec: 5.0,
      total_sim_time_sec: 10.0,
      progress_pct: 50.0,
      playback_speed: 5.0,
      is_looping: true,
    };
    store.setReplayStatus(status);

    expect(useTwinStore.getState().replayStatus?.playback_state).toBe('PAUSED');
    expect(useTwinStore.getState().replayStatus?.is_looping).toBe(true);

    store.setReplayStatus(null);
    expect(useTwinStore.getState().replayStatus).toBeNull();
  });
});
