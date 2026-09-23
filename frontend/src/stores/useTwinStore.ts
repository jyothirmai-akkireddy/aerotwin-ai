/**
 * Zustand store for 3D Digital Twin visualization controls, telemetry streaming,
 * and authoritative engine state.
 */

import { create } from 'zustand';
import {
  ConnectionState,
  TelemetryFreshness,
  TransportMode,
  TelemetryMessage,
  PhysicsTwinResultDto,
  MLInferenceResultDto,
  PrognosticResultDto,
  ReplayCursorStatusDto,
  MissionTelemetryContextDto,
} from '../services/websocket/types';
import { WEBSOCKET_CONFIG } from '../config/websocket';

export type VisualizationMode = 'NORMAL' | 'THERMAL' | 'EXPLODED' | 'CUTAWAY';
export type CameraPreset = 'ISOMETRIC' | 'FRONT' | 'TOP' | 'LEFT_BANK' | 'RIGHT_BANK';

export interface TwinTelemetryState {
  rpm: number;
  throttle: number;
  engineState: string;
  cht: [number, number, number, number];
  egt: [number, number, number, number];
  oilTemperature: number;
  oilPressure: number;
  manifoldPressure: number;
  fuelFlow: number;
  batteryVoltage: number;
  vibrationRms: number;
  timestamp: number;
  qualityFlag: string;
  sequenceId?: number;
}

export interface TwinStoreState {
  // Visualization controls
  visualizationMode: VisualizationMode;
  cameraPreset: CameraPreset;
  selectedCylinder: 1 | 2 | 3 | 4 | null;
  visualRpmMultiplier: number;
  isPaused: boolean;
  wireframe: boolean;
  showLabels: boolean;
  explodedDistance: number;
  cameraResetTrigger: number;

  // Realtime transport & connection state
  connectionState: ConnectionState;
  freshness: TelemetryFreshness;
  transportMode: TransportMode;
  lastSequenceId: number | null;
  missedFramesCount: number;
  duplicateFramesCount: number;

  // Bounded ring buffer for live telemetry charts and trends
  telemetryBuffer: TwinTelemetryState[];

  // Active engine telemetry state
  telemetry: TwinTelemetryState;

  // Active Physics-Informed Digital Twin output
  physicsResult: PhysicsTwinResultDto | null;

  // Active Machine Learning diagnostic result
  mlResult: MLInferenceResultDto | null;

  // Active Prognostics & RUL degradation result
  prognosticsResult: PrognosticResultDto | null;

  // Active operational source mode & Phase 8 additions
  sourceMode: 'LIVE' | 'REPLAY';
  replayStatus: ReplayCursorStatusDto | null;
  missionContext: MissionTelemetryContextDto | null;

  // Actions
  setVisualizationMode: (mode: VisualizationMode) => void;
  setCameraPreset: (preset: CameraPreset) => void;
  setSelectedCylinder: (cyl: 1 | 2 | 3 | 4 | null) => void;
  setVisualRpmMultiplier: (multiplier: number) => void;
  togglePause: () => void;
  toggleWireframe: () => void;
  toggleLabels: () => void;
  setExplodedDistance: (dist: number) => void;
  resetCamera: () => void;
  updateFromTelemetry: (data: Partial<TwinTelemetryState>) => void;
  resetToNominal: () => void;
  setSourceMode: (mode: 'LIVE' | 'REPLAY') => void;
  setReplayStatus: (status: ReplayCursorStatusDto | null) => void;
  setMissionContext: (ctx: MissionTelemetryContextDto | null) => void;

  // Realtime actions
  setConnectionState: (state: ConnectionState) => void;
  setFreshness: (freshness: TelemetryFreshness) => void;
  setTransportMode: (mode: TransportMode) => void;
  recordSequenceAnomaly: (
    type: 'GAP' | 'DUPLICATE',
    expected: number,
    actual: number
  ) => void;
  handleIncomingTelemetry: (msg: TelemetryMessage) => void;
  clearTelemetryBuffer: () => void;
  setPhysicsResult: (result: PhysicsTwinResultDto | null) => void;
  setMlResult: (result: MLInferenceResultDto | null) => void;
  setPrognosticsResult: (result: PrognosticResultDto | null) => void;
}

const DEFAULT_TELEMETRY: TwinTelemetryState = {
  rpm: 2400.0,
  throttle: 45.0,
  engineState: 'CRUISE',
  cht: [95.0, 92.5, 98.0, 94.0],
  egt: [720.0, 715.0, 730.0, 722.0],
  oilTemperature: 85.0,
  oilPressure: 3.8,
  manifoldPressure: 29.5,
  fuelFlow: 16.5,
  batteryVoltage: 28.2,
  vibrationRms: 1.15,
  timestamp: Date.now() / 1000,
  qualityFlag: 'VALID',
  sequenceId: 0,
};

function inferEngineState(rpm: number, throttle: number): string {
  if (rpm < 100) return 'OFF';
  if (rpm < 800) return 'IDLE';
  if (rpm > 5200 || throttle > 85) return 'HIGH_POWER';
  if (rpm > 2000) return 'CRUISE';
  return 'STARTING';
}

export const useTwinStore = create<TwinStoreState>((set) => ({
  visualizationMode: 'NORMAL',
  cameraPreset: 'ISOMETRIC',
  selectedCylinder: null,
  visualRpmMultiplier: 0.15,
  isPaused: false,
  wireframe: false,
  showLabels: true,
  explodedDistance: 0.0,
  cameraResetTrigger: 0,

  // Transport defaults
  connectionState: 'DISCONNECTED',
  freshness: 'NO_DATA',
  transportMode: 'WEBSOCKET',
  lastSequenceId: null,
  missedFramesCount: 0,
  duplicateFramesCount: 0,
  telemetryBuffer: [],
  physicsResult: null,
  mlResult: null,
  prognosticsResult: null,
  sourceMode: 'LIVE',
  replayStatus: null,
  missionContext: null,

  telemetry: DEFAULT_TELEMETRY,

  setVisualizationMode: (mode) =>
    set((state) => ({
      visualizationMode: mode,
      explodedDistance:
        mode === 'EXPLODED' && state.explodedDistance === 0 ? 0.6 : state.explodedDistance,
    })),

  setCameraPreset: (preset) => set({ cameraPreset: preset }),

  setSelectedCylinder: (cyl) => set({ selectedCylinder: cyl }),

  setVisualRpmMultiplier: (multiplier) =>
    set({ visualRpmMultiplier: Math.max(0.0, Math.min(2.0, multiplier)) }),

  togglePause: () => set((state) => ({ isPaused: !state.isPaused })),

  toggleWireframe: () => set((state) => ({ wireframe: !state.wireframe })),

  toggleLabels: () => set((state) => ({ showLabels: !state.showLabels })),

  setExplodedDistance: (dist) =>
    set({ explodedDistance: Math.max(0.0, Math.min(1.0, dist)) }),

  resetCamera: () =>
    set((state) => ({
      cameraResetTrigger: state.cameraResetTrigger + 1,
      cameraPreset: 'ISOMETRIC',
      selectedCylinder: null,
    })),

  updateFromTelemetry: (data) =>
    set((state) => ({
      telemetry: {
        ...state.telemetry,
        ...data,
        timestamp: data.timestamp ?? Date.now() / 1000,
      },
    })),

  resetToNominal: () =>
    set({
      telemetry: DEFAULT_TELEMETRY,
      physicsResult: null,
      mlResult: null,
      prognosticsResult: null,
      replayStatus: null,
      missionContext: null,
      telemetryBuffer: [],
      lastSequenceId: null,
      missedFramesCount: 0,
      duplicateFramesCount: 0,
      sourceMode: 'LIVE',
      visualizationMode: 'NORMAL',
      selectedCylinder: null,
      explodedDistance: 0.0,
      isPaused: false,
    }),

  // Realtime Actions
  setConnectionState: (connectionState) => set({ connectionState }),

  setFreshness: (freshness) => set({ freshness }),

  setTransportMode: (transportMode) => set({ transportMode }),

  recordSequenceAnomaly: (type, expected, actual) =>
    set((state) => {
      if (type === 'GAP') {
        const gap = Math.max(0, actual - expected);
        return { missedFramesCount: state.missedFramesCount + gap };
      }
      return { duplicateFramesCount: state.duplicateFramesCount + 1 };
    }),

  handleIncomingTelemetry: (msg) =>
    set((state) => {
      const p = msg.payload;
      const newTelemetry: TwinTelemetryState = {
        rpm: p.rpm,
        throttle: p.throttle_position,
        engineState: inferEngineState(p.rpm, p.throttle_position),
        cht: p.cht,
        egt: p.egt,
        oilTemperature: p.oil_temperature,
        oilPressure: p.oil_pressure,
        manifoldPressure: p.manifold_pressure,
        fuelFlow: p.fuel_flow,
        batteryVoltage: p.battery_voltage,
        vibrationRms: p.vibration_rms,
        timestamp: p.timestamp,
        qualityFlag: p.quality_flag,
        sequenceId: msg.sequence_id,
      };

      // Append to bounded circular buffer
      const newBuffer = [...state.telemetryBuffer, newTelemetry];
      if (newBuffer.length > WEBSOCKET_CONFIG.bufferCapacity) {
        newBuffer.splice(0, newBuffer.length - WEBSOCKET_CONFIG.bufferCapacity);
      }

      return {
        telemetry: newTelemetry,
        lastSequenceId: msg.sequence_id,
        telemetryBuffer: newBuffer,
        sourceMode: msg.source_mode !== undefined ? msg.source_mode : state.sourceMode,
        missionContext: msg.mission !== undefined ? msg.mission : state.missionContext,
        replayStatus: msg.replay !== undefined ? msg.replay : state.replayStatus,
        physicsResult: msg.physics !== undefined ? msg.physics : state.physicsResult,
        mlResult: msg.ml !== undefined ? msg.ml : state.mlResult,
        prognosticsResult:
          msg.prognostics !== undefined ? msg.prognostics : state.prognosticsResult,
      };
    }),

  clearTelemetryBuffer: () => set({ telemetryBuffer: [] }),

  setPhysicsResult: (physicsResult) => set({ physicsResult }),

  setMlResult: (mlResult) => set({ mlResult }),

  setPrognosticsResult: (prognosticsResult) => set({ prognosticsResult }),

  setSourceMode: (sourceMode) => set({ sourceMode }),

  setReplayStatus: (replayStatus) => set({ replayStatus }),

  setMissionContext: (missionContext) => set({ missionContext }),
}));
