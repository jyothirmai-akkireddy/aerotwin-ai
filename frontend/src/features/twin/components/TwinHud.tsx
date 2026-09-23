import React from 'react';
import { Activity, Gauge, Flame, Zap, Droplets } from 'lucide-react';
import { useTwinStore } from '../../../stores/useTwinStore';
import { getThermalStatus } from '../thermal';
import { Badge } from '../../../components/common/Badge';
import { StatusIndicator } from '../../../components/common/StatusIndicator';

export const TwinHud: React.FC = () => {
  const {
    telemetry,
    selectedCylinder,
    setSelectedCylinder,
    visualizationMode,
    connectionState,
    freshness,
    lastSequenceId,
    missedFramesCount,
    transportMode,
  } = useTwinStore();

  const getEngineStateBadgeVariant = (
    state: string
  ): 'default' | 'success' | 'warning' | 'danger' | 'accent' | 'outline' => {
    switch (state) {
      case 'HIGH_POWER':
        return 'warning';
      case 'CRUISE':
      case 'IDLE':
        return 'success';
      case 'STARTING':
      case 'ACCELERATING':
      case 'DECELERATING':
        return 'accent';
      case 'SHUTDOWN':
      case 'OFF':
      default:
        return 'default';
    }
  };

  const getQualityBadgeVariant = (
    quality: string
  ): 'default' | 'success' | 'warning' | 'danger' | 'accent' | 'outline' => {
    switch (quality) {
      case 'VALID':
      case 'GOOD':
        return 'success';
      case 'DEGRADED':
        return 'warning';
      case 'INVALID':
      case 'MISSING':
        return 'danger';
      default:
        return 'default';
    }
  };

  return (
    <div className="pointer-events-none absolute inset-0 flex flex-col justify-between p-3 select-none">
      {/* ============================================================== */}
      {/* TOP HEADER BAR                                                 */}
      {/* ============================================================== */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        {/* Model Identity & Prototype Disclaimer */}
        <div className="pointer-events-auto flex items-center space-x-3 bg-slate-950/85 backdrop-blur-md px-3.5 py-2 rounded-lg border border-slate-800 shadow-xl">
          <div>
            <div className="flex items-center space-x-2">
              <span className="text-xs font-bold text-slate-100 tracking-wide">
                Generic Turbocharged Aero-Piston Engine
              </span>
              <Badge variant={getEngineStateBadgeVariant(telemetry.engineState)}>
                {telemetry.engineState}
              </Badge>
              <Badge variant={getQualityBadgeVariant(telemetry.qualityFlag)}>
                {telemetry.qualityFlag}
              </Badge>
            </div>
            <div className="text-[10px] text-slate-400">
              Inspired by the Rotax 914/915 class; prototype 3D visualization.
            </div>
          </div>
        </div>

        {/* Realtime WebSocket Connection & Transport Telemetry */}
        <div className="pointer-events-auto flex items-center space-x-3 bg-slate-950/85 backdrop-blur-md px-3.5 py-2 rounded-lg border border-slate-800 shadow-xl">
          <StatusIndicator
            status={
              connectionState === 'CONNECTED'
                ? freshness === 'LIVE'
                  ? 'NORMAL'
                  : 'WARNING'
                : connectionState === 'CONNECTING' || connectionState === 'RECONNECTING'
                ? 'WARNING'
                : connectionState === 'ERROR'
                ? 'CRITICAL'
                : 'OFFLINE'
            }
            label={
              connectionState === 'CONNECTED'
                ? freshness === 'LIVE'
                  ? 'LIVE 10 Hz'
                  : 'STALE'
                : connectionState
            }
            showPulse={
              connectionState === 'CONNECTED' && freshness === 'LIVE'
                ? true
                : connectionState === 'CONNECTING' || connectionState === 'RECONNECTING'
            }
          />

          <div className="flex items-center space-x-2 pl-2 border-l border-slate-800 text-[11px] font-mono">
            <span className="text-slate-400">
              Seq: <strong className="text-slate-200">#{telemetry.sequenceId ?? lastSequenceId ?? 0}</strong>
            </span>
            {missedFramesCount > 0 && (
              <span className="px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 text-[10px]">
                Gaps: {missedFramesCount}
              </span>
            )}
            <span className="text-[10px] px-2 py-0.5 rounded bg-slate-800 text-slate-300">
              {transportMode === 'WEBSOCKET' ? 'WS STREAM' : 'MANUAL DEV'}
            </span>
          </div>
        </div>
      </div>

      {/* ============================================================== */}
      {/* CENTER / SIDE INSTRUMENTATION OVERLAYS                         */}
      {/* ============================================================== */}
      <div className="flex items-start justify-between flex-grow my-2 pointer-events-none">
        {/* LEFT PANEL: Powertrain & Lubrication Telemetry */}
        <div className="pointer-events-auto w-56 space-y-2 bg-slate-950/80 backdrop-blur-md p-3 rounded-lg border border-slate-800/80 shadow-2xl text-xs">
          <div className="flex items-center justify-between text-slate-400 font-medium pb-1 border-b border-slate-800">
            <span className="flex items-center">
              <Gauge className="w-3.5 h-3.5 mr-1.5 text-sky-400" />
              POWERTRAIN
            </span>
            <span className="font-mono text-[10px] text-slate-400">10 Hz</span>
          </div>

          {/* RPM Bar */}
          <div>
            <div className="flex justify-between items-baseline">
              <span className="text-slate-400">Crankshaft Speed</span>
              <span className="font-mono text-sm font-bold text-sky-400">
                {telemetry.rpm.toFixed(0)} <span className="text-[10px] font-normal text-slate-400">RPM</span>
              </span>
            </div>
            <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden mt-1">
              <div
                className={`h-full transition-all duration-150 ${
                  telemetry.rpm > 5500 ? 'bg-red-500' : telemetry.rpm > 4500 ? 'bg-amber-400' : 'bg-sky-400'
                }`}
                style={{ width: `${Math.min(100, (telemetry.rpm / 6500) * 100)}%` }}
              />
            </div>
          </div>

          {/* Throttle & Manifold Pressure */}
          <div className="grid grid-cols-2 gap-2 pt-1">
            <div className="bg-slate-900/90 p-2 rounded border border-slate-800">
              <div className="text-[10px] text-slate-400">Throttle</div>
              <div className="font-mono text-xs font-semibold text-slate-100">
                {telemetry.throttle.toFixed(1)}%
              </div>
            </div>
            <div className="bg-slate-900/90 p-2 rounded border border-slate-800">
              <div className="text-[10px] text-slate-400">MAP</div>
              <div className="font-mono text-xs font-semibold text-slate-100">
                {telemetry.manifoldPressure.toFixed(1)} <span className="text-[9px] text-slate-400">inHg</span>
              </div>
            </div>
          </div>

          {/* Fuel Flow & Electrical */}
          <div className="grid grid-cols-2 gap-2">
            <div className="bg-slate-900/90 p-2 rounded border border-slate-800">
              <div className="text-[10px] text-slate-400">Fuel Flow</div>
              <div className="font-mono text-xs font-semibold text-emerald-400">
                {telemetry.fuelFlow.toFixed(1)} <span className="text-[9px] text-slate-400">L/h</span>
              </div>
            </div>
            <div className="bg-slate-900/90 p-2 rounded border border-slate-800">
              <div className="text-[10px] text-slate-400">Avionics Bus</div>
              <div className="font-mono text-xs font-semibold text-slate-100">
                {telemetry.batteryVoltage.toFixed(1)} <span className="text-[9px] text-slate-400">V</span>
              </div>
            </div>
          </div>

          {/* Lubrication & Vibration */}
          <div className="pt-1 border-t border-slate-800/80 space-y-1 text-[11px]">
            <div className="flex justify-between items-center text-slate-300">
              <span className="flex items-center text-slate-400">
                <Droplets className="w-3 h-3 mr-1 text-amber-500" /> Oil Pressure
              </span>
              <span className="font-mono font-medium">{telemetry.oilPressure.toFixed(2)} bar</span>
            </div>
            <div className="flex justify-between items-center text-slate-300">
              <span className="flex items-center text-slate-400">
                <Flame className="w-3 h-3 mr-1 text-amber-400" /> Oil Temp
              </span>
              <span className="font-mono font-medium">{telemetry.oilTemperature.toFixed(1)}°C</span>
            </div>
            <div className="flex justify-between items-center text-slate-300">
              <span className="flex items-center text-slate-400">
                <Activity className="w-3 h-3 mr-1 text-purple-400" /> Vibration
              </span>
              <span className="font-mono font-medium">{telemetry.vibrationRms.toFixed(2)} g</span>
            </div>
          </div>
        </div>

        {/* RIGHT PANEL: 4-Cylinder Thermal Matrix */}
        <div className="pointer-events-auto w-64 space-y-2 bg-slate-950/80 backdrop-blur-md p-3 rounded-lg border border-slate-800/80 shadow-2xl text-xs">
          <div className="flex items-center justify-between text-slate-400 font-medium pb-1 border-b border-slate-800">
            <span className="flex items-center">
              <Zap className="w-3.5 h-3.5 mr-1.5 text-amber-400" />
              CYLINDER HEADS & EGT
            </span>
            <span className="text-[10px] text-slate-400 font-mono">
              {visualizationMode === 'THERMAL' ? 'THERMAL ON' : 'PBR'}
            </span>
          </div>

          {/* Cylinder Cards 1-4 */}
          <div className="space-y-1.5">
            {[1, 2, 3, 4].map((cylNum) => {
              const cht = telemetry.cht[cylNum - 1] ?? 95.0;
              const egt = telemetry.egt[cylNum - 1] ?? 720.0;
              const thermalStatus = getThermalStatus(cht);
              const isSelected = selectedCylinder === cylNum;
              const bankLabel = cylNum === 1 ? 'Left Front' : cylNum === 2 ? 'Right Front' : cylNum === 3 ? 'Left Rear' : 'Right Rear';

              return (
                <div
                  key={cylNum}
                  onClick={() => setSelectedCylinder(isSelected ? null : (cylNum as 1 | 2 | 3 | 4))}
                  className={`p-2 rounded border transition-all cursor-pointer ${
                    isSelected
                      ? 'bg-sky-950/60 border-sky-400 shadow-md ring-1 ring-sky-400/40'
                      : 'bg-slate-900/80 border-slate-800 hover:border-slate-700'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-slate-200">
                      Cyl {cylNum} <span className="text-[9px] font-normal text-slate-400">({bankLabel})</span>
                    </span>
                    <span className={`text-[9px] font-mono px-1 py-0.2 rounded border ${thermalStatus.colorClass}`}>
                      {thermalStatus.label}
                    </span>
                  </div>
                  <div className="grid grid-cols-2 gap-2 mt-1 text-[11px] font-mono">
                    <div>
                      <span className="text-[9px] text-slate-400 font-sans">CHT: </span>
                      <span className="font-semibold text-slate-100">{cht.toFixed(1)}°C</span>
                    </div>
                    <div>
                      <span className="text-[9px] text-slate-400 font-sans">EGT: </span>
                      <span className="font-semibold text-slate-300">{egt.toFixed(0)}°C</span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          <div className="text-[10px] text-slate-400 text-center pt-1 border-t border-slate-800">
            Click any cylinder card or 3D label to inspect bank
          </div>
        </div>
      </div>

      {/* ============================================================== */}
      {/* BOTTOM HINTS BAR                                               */}
      {/* ============================================================== */}
      <div className="flex items-center justify-between text-[10px] text-slate-400 pointer-events-none px-2">
        <span>Controls: Left Click = Orbit | Right Click = Pan | Scroll = Zoom</span>
        {selectedCylinder && (
          <span className="pointer-events-auto bg-sky-950/80 text-sky-300 border border-sky-800 px-2 py-0.5 rounded">
            Selected: Cylinder {selectedCylinder} (Focused)
          </span>
        )}
      </div>
    </div>
  );
};
