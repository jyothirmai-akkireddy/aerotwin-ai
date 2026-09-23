import { describe, it, expect, beforeEach } from 'vitest';
import { useTwinStore } from '../../../stores/useTwinStore';

describe('useTwinStore 3D Digital Twin State Management', () => {
  beforeEach(() => {
    useTwinStore.getState().resetToNominal();
  });

  it('initializes with nominal baseline telemetry and controls', () => {
    const state = useTwinStore.getState();
    expect(state.visualizationMode).toBe('NORMAL');
    expect(state.cameraPreset).toBe('ISOMETRIC');
    expect(state.selectedCylinder).toBeNull();
    expect(state.isPaused).toBe(false);
    expect(state.telemetry.rpm).toBe(2400.0);
    expect(state.telemetry.cht).toHaveLength(4);
    expect(state.telemetry.qualityFlag).toBe('VALID');
  });

  it('switches visualization modes and configures default exploded distance', () => {
    const store = useTwinStore.getState();
    store.setVisualizationMode('THERMAL');
    expect(useTwinStore.getState().visualizationMode).toBe('THERMAL');

    store.setVisualizationMode('EXPLODED');
    expect(useTwinStore.getState().visualizationMode).toBe('EXPLODED');
    expect(useTwinStore.getState().explodedDistance).toBeGreaterThan(0.0);

    store.setVisualizationMode('CUTAWAY');
    expect(useTwinStore.getState().visualizationMode).toBe('CUTAWAY');
  });

  it('changes camera presets and tracks reset triggers', () => {
    const store = useTwinStore.getState();
    store.setCameraPreset('FRONT');
    expect(useTwinStore.getState().cameraPreset).toBe('FRONT');

    store.setCameraPreset('LEFT_BANK');
    expect(useTwinStore.getState().cameraPreset).toBe('LEFT_BANK');

    const triggerBefore = useTwinStore.getState().cameraResetTrigger;
    store.resetCamera();
    expect(useTwinStore.getState().cameraPreset).toBe('ISOMETRIC');
    expect(useTwinStore.getState().cameraResetTrigger).toBe(triggerBefore + 1);
  });

  it('selects and deselects cylinders', () => {
    const store = useTwinStore.getState();
    store.setSelectedCylinder(2);
    expect(useTwinStore.getState().selectedCylinder).toBe(2);

    store.setSelectedCylinder(null);
    expect(useTwinStore.getState().selectedCylinder).toBeNull();
  });

  it('toggles pause and wireframe flags', () => {
    const store = useTwinStore.getState();
    expect(useTwinStore.getState().isPaused).toBe(false);
    store.togglePause();
    expect(useTwinStore.getState().isPaused).toBe(true);
    store.togglePause();
    expect(useTwinStore.getState().isPaused).toBe(false);

    expect(useTwinStore.getState().wireframe).toBe(false);
    store.toggleWireframe();
    expect(useTwinStore.getState().wireframe).toBe(true);
  });

  it('updates telemetry state accurately from partial data', () => {
    const store = useTwinStore.getState();
    store.updateFromTelemetry({
      rpm: 5200.0,
      engineState: 'HIGH_POWER',
      cht: [110.0, 115.0, 108.0, 112.0],
      oilPressure: 4.2,
    });

    const updated = useTwinStore.getState().telemetry;
    expect(updated.rpm).toBe(5200.0);
    expect(updated.engineState).toBe('HIGH_POWER');
    expect(updated.cht[1]).toBe(115.0);
    expect(updated.oilPressure).toBe(4.2);
    // Other fields preserve previous values
    expect(updated.manifoldPressure).toBe(29.5);
  });
});
