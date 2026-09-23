import React, { useEffect, useState } from 'react';
import { Activity, RefreshCw, RotateCcw, Radio, Film, ShieldAlert, Cpu } from 'lucide-react';
import { useAppStore } from '../../stores/useAppStore';
import { useTwinStore } from '../../stores/useTwinStore';
import { StatusIndicator, SystemStatus } from '../common/StatusIndicator';

export const Header: React.FC = () => {
  const { connectionStatus, checkBackendHealth, systemInfo } = useAppStore();
  const {
    sourceMode,
    missionContext,
    telemetry,
    freshness,
    resetToNominal,
  } = useTwinStore();
  const [utcTime, setUtcTime] = useState<string>('');
  const [isResetting, setIsResetting] = useState<boolean>(false);

  useEffect(() => {
    const updateTime = () => {
      setUtcTime(new Date().toUTCString().slice(17, 25) + ' UTC');
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  const handleSafeReset = async () => {
    setIsResetting(true);
    try {
      // 1. Send reset to backend simulation API
      await fetch('http://localhost:8000/api/v1/simulation/reset', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      });
    } catch {
      // Backend may be offline or local
    } finally {
      // 2. Reset frontend twin store state to nominal
      resetToNominal();
      // 3. Re-verify health
      await checkBackendHealth();
      setIsResetting(false);
    }
  };

  const statusMap: Record<string, SystemStatus> = {
    CONNECTED: freshness === 'LIVE' ? 'NORMAL' : 'WARNING',
    CHECKING: 'WARNING',
    DEGRADED: 'DEGRADED',
    DISCONNECTED: 'OFFLINE',
  };

  const getEffectiveSourceMode = () => {
    if (missionContext) return 'MISSION';
    return sourceMode;
  };

  const effectiveSource = getEffectiveSourceMode();

  return (
    <header className="h-14 border-b border-slate-800 bg-[#0d131f]/95 backdrop-blur px-4 lg:px-6 flex items-center justify-between select-none">
      {/* Brand & Prototype Designation */}
      <div className="flex items-center gap-3">
        <div className="p-1.5 rounded bg-sky-950/70 border border-sky-800/60 text-sky-400">
          <Activity className="h-5 w-5 animate-pulse" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-sm lg:text-base font-bold tracking-wider text-white">
              AEROTWIN <span className="text-sky-400 font-mono text-xs">AI</span>
            </h1>
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
              SIH26054
            </span>
            <span className="hidden md:inline-flex items-center gap-1 text-[10px] font-mono px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/30">
              <ShieldAlert className="h-3 w-3" />
              PROTOTYPE RESEARCH SYSTEM
            </span>
          </div>
          <p className="text-[10px] text-slate-400 font-mono truncate max-w-xs sm:max-w-md hidden sm:block">
            {systemInfo?.engine_baseline || 'Generic 4-Cylinder Turbo Boxer Aero-Piston (Rotax 914/915 iS class)'}
          </p>
        </div>
      </div>

      {/* Operational State, Source Mode & Stream Rates */}
      <div className="flex items-center gap-2 lg:gap-4 text-xs font-mono">
        {/* Source Mode Pill */}
        <div className="flex items-center">
          {effectiveSource === 'LIVE' && (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] font-semibold bg-emerald-950/80 text-emerald-400 border border-emerald-800/60 shadow-sm">
              <Radio className="h-3 w-3 animate-pulse text-emerald-400" />
              LIVE
            </span>
          )}
          {effectiveSource === 'REPLAY' && (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] font-semibold bg-sky-950/80 text-sky-400 border border-sky-800/60 shadow-sm">
              <Film className="h-3 w-3 text-sky-400" />
              REPLAY
            </span>
          )}
          {effectiveSource === 'MISSION' && (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] font-semibold bg-purple-950/80 text-purple-400 border border-purple-800/60 shadow-sm">
              <Cpu className="h-3 w-3 text-purple-400" />
              MISSION
            </span>
          )}
        </div>

        {/* Telemetry Stream Rate */}
        <div className="hidden lg:flex items-center gap-1 text-slate-400 bg-slate-900/80 px-2 py-1 rounded border border-slate-800 text-[11px]">
          <span className="text-slate-500">RATE:</span>
          <span className="text-sky-400 font-semibold">{systemInfo?.telemetry_rate_hz || 10} Hz</span>
        </div>

        {/* Engine Operational State */}
        {telemetry.engineState && (
          <div className="hidden md:flex items-center gap-1 text-slate-400 bg-slate-900/80 px-2 py-1 rounded border border-slate-800 text-[11px]">
            <span className="text-slate-500">STATE:</span>
            <span className="text-slate-200 font-semibold">{telemetry.engineState}</span>
          </div>
        )}

        {/* UTC Clock */}
        <div className="hidden xl:block text-slate-400 font-mono text-[11px] bg-slate-900/80 px-2.5 py-1 rounded border border-slate-800">
          {utcTime}
        </div>

        {/* Realtime Connection Indicator */}
        <div className="flex items-center gap-1.5">
          <StatusIndicator
            status={statusMap[connectionStatus] || 'OFFLINE'}
            label={
              connectionStatus === 'CONNECTED'
                ? freshness === 'LIVE'
                  ? 'CONNECTED'
                  : 'STALE'
                : connectionStatus
            }
          />
        </div>

        {/* Safe Demo Reset Action Button */}
        <button
          onClick={handleSafeReset}
          disabled={isResetting}
          title="Safe Demo Reset: resets simulator, physics thermal state, prognostics buffer, and UI state"
          className="flex items-center gap-1 px-2.5 py-1 rounded text-[11px] font-medium text-amber-300 bg-amber-950/40 hover:bg-amber-900/50 border border-amber-800/60 transition-colors disabled:opacity-50"
        >
          <RotateCcw className={`h-3 w-3 ${isResetting ? 'animate-spin' : ''}`} />
          <span className="hidden sm:inline">Reset Twin</span>
        </button>

        {/* Refresh Backend Status */}
        <button
          onClick={() => checkBackendHealth()}
          title="Refresh backend status"
          className="p-1 text-slate-400 hover:text-slate-200 transition-colors rounded hover:bg-slate-800"
        >
          <RefreshCw className="h-3.5 w-3.5" />
        </button>
      </div>
    </header>
  );
};
