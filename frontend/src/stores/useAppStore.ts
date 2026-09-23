/**
 * Minimal Application UI and Connection State Store.
 * Does NOT contain mock telemetry or engine physics (preserved for Phase 2/3 stores).
 */

import { create } from 'zustand';
import { fetchHealth, fetchReadiness, fetchSystemInfo } from '../api/health';
import { HealthResponse, ReadinessResponse, SystemInfoResponse } from '../api/types';

export type ActiveTab = 'overview' | 'twin' | 'diagnostics' | 'simulation' | 'config';
export type ConnectionStatus = 'CHECKING' | 'CONNECTED' | 'DISCONNECTED' | 'DEGRADED';

interface AppState {
  activeTab: ActiveTab;
  connectionStatus: ConnectionStatus;
  health: HealthResponse | null;
  readiness: ReadinessResponse | null;
  systemInfo: SystemInfoResponse | null;
  lastCheckedTime: number | null;
  errorMessage: string | null;

  // Actions
  setActiveTab: (tab: ActiveTab) => void;
  checkBackendHealth: () => Promise<void>;
  clearError: () => void;
}

export const useAppStore = create<AppState>((set) => ({
  activeTab: 'overview',
  connectionStatus: 'CHECKING',
  health: null,
  readiness: null,
  systemInfo: null,
  lastCheckedTime: null,
  errorMessage: null,

  setActiveTab: (tab: ActiveTab) => set({ activeTab: tab }),

  checkBackendHealth: async () => {
    try {
      const [health, readiness, info] = await Promise.all([
        fetchHealth(),
        fetchReadiness(),
        fetchSystemInfo(),
      ]);

      const status: ConnectionStatus =
        readiness.status === 'ready'
          ? 'CONNECTED'
          : readiness.status === 'degraded'
          ? 'DEGRADED'
          : 'DISCONNECTED';

      set({
        connectionStatus: status,
        health,
        readiness,
        systemInfo: info,
        lastCheckedTime: Date.now(),
        errorMessage: null,
      });
    } catch (err) {
      set({
        connectionStatus: 'DISCONNECTED',
        lastCheckedTime: Date.now(),
        errorMessage: (err as Error).message || 'Failed to connect to AeroTwin backend API',
      });
    }
  },

  clearError: () => set({ errorMessage: null }),
}));
