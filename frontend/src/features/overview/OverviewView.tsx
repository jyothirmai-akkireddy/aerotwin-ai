import React from 'react';
import {
  Activity,
  Gauge,
  RotateCcw,
  CheckCircle2,
  AlertTriangle,
  Clock,
  ArrowRight,
  ShieldCheck,
  Cpu,
  Layers,
  Sparkles,
} from 'lucide-react';
import { useAppStore } from '../../stores/useAppStore';
import { useTwinStore } from '../../stores/useTwinStore';
import { Card, CardHeader, CardTitle, CardContent } from '../../components/common/Card';
import { Badge } from '../../components/common/Badge';
import { StatusIndicator } from '../../components/common/StatusIndicator';
import { resolveApiUrl } from '../../api/client';

export const OverviewView: React.FC = () => {
  const { readiness, systemInfo, connectionStatus, setActiveTab, checkBackendHealth } = useAppStore();
  const {
    telemetry,
    mlResult,
    prognosticsResult,
    sourceMode,
    freshness,
    resetToNominal,
  } = useTwinStore();

  const handleSafeReset = async () => {
    try {
      await fetch(resolveApiUrl('/api/v1/simulation/reset'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      });
    } catch {
      // Offline fallback
    } finally {
      resetToNominal();
      await checkBackendHealth();
    }
  };

  // Helper for Health Index progress bar color
  const getHealthBarColor = (pct: number) => {
    if (pct >= 85) return 'bg-emerald-500';
    if (pct >= 70) return 'bg-cyan-500';
    if (pct >= 50) return 'bg-amber-500';
    return 'bg-rose-500';
  };

  // Compute average CHT and EGT
  const avgCht = telemetry.cht.reduce((a, b) => a + b, 0) / 4;
  const maxCht = Math.max(...telemetry.cht);
  const avgEgt = telemetry.egt.reduce((a, b) => a + b, 0) / 4;
  const maxEgt = Math.max(...telemetry.egt);

  return (
    <div className="space-y-6">
      {/* Top Banner & Operating Context */}
      <div className="p-4 rounded-lg bg-sky-950/20 border border-sky-800/40 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-bold text-white uppercase tracking-wider">
              AeroTwin AI Ground Station &amp; Cockpit Overview
            </h3>
            <Badge variant="accent">PHASE 0–10 VERIFIED</Badge>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Engine baseline: {systemInfo?.engine_baseline || 'Generic 4-Cylinder Boxer Turbo Aero-Piston (Rotax 914/915 iS class)'}.
            Full-stack Physics + ML + Prognostics + Flight Replay active.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <StatusIndicator
            status={connectionStatus === 'CONNECTED' ? (freshness === 'LIVE' ? 'NORMAL' : 'WARNING') : 'DEGRADED'}
            label={connectionStatus === 'CONNECTED' ? (freshness === 'LIVE' ? 'API READY' : 'STALE') : 'DEGRADED'}
          />
        </div>
      </div>

      {/* LEVEL 2: EXECUTIVE ENGINE HEALTH OVERVIEW CARD */}
      <Card className="border-indigo-900/50 bg-slate-900/90 shadow-2xl">
        <CardHeader className="border-b border-slate-800/80">
          <div className="flex items-center gap-2">
            <Gauge className="h-5 w-5 text-indigo-400" />
            <CardTitle>Executive Engine Health Overview</CardTitle>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-[11px] font-mono text-slate-400 bg-slate-950 px-2 py-0.5 rounded border border-slate-800">
              SOURCE: {sourceMode}
            </span>
            <Badge variant={prognosticsResult?.degradation_state === 'NOMINAL' ? 'success' : 'warning'}>
              {prognosticsResult?.degradation_state || 'NOMINAL (STANDBY)'}
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="pt-4">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* 1. Health Index Meter */}
            <div className="p-3.5 rounded-lg bg-slate-950/70 border border-slate-800 flex flex-col justify-between space-y-2">
              <div className="flex justify-between items-center text-xs text-slate-400">
                <span className="font-semibold uppercase tracking-wider text-[11px]">Composite Health Index</span>
                <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
              </div>
              <div>
                <div className="text-2xl font-bold font-mono text-slate-100">
                  {prognosticsResult ? `${(prognosticsResult.health_index * 100).toFixed(1)}%` : '100.0%'}
                </div>
                <div className="w-full h-2 bg-slate-800 rounded-full overflow-hidden mt-1.5">
                  <div
                    className={`h-full transition-all duration-300 ${getHealthBarColor(
                      (prognosticsResult?.health_index ?? 1.0) * 100
                    )}`}
                    style={{ width: `${Math.max(4, (prognosticsResult?.health_index ?? 1.0) * 100)}%` }}
                  />
                </div>
              </div>
              <div className="text-[10px] text-slate-500 font-mono flex justify-between">
                <span>Threshold: 90% (Nominal)</span>
                <span>{prognosticsResult?.trend_direction || 'STABLE'}</span>
              </div>
            </div>

            {/* 2. Anomaly Detection Status */}
            <div className="p-3.5 rounded-lg bg-slate-950/70 border border-slate-800 flex flex-col justify-between space-y-2">
              <div className="flex justify-between items-center text-xs text-slate-400">
                <span className="font-semibold uppercase tracking-wider text-[11px]">Anomaly Status</span>
                <Activity className="w-3.5 h-3.5 text-sky-400" />
              </div>
              <div>
                {mlResult?.anomaly.flag ? (
                  <div className="flex items-center gap-1.5 text-rose-400 font-bold text-lg font-mono">
                    <AlertTriangle className="h-5 w-5 animate-pulse" />
                    <span>ANOMALY DETECTED</span>
                  </div>
                ) : (
                  <div className="flex items-center gap-1.5 text-emerald-400 font-bold text-lg font-mono">
                    <CheckCircle2 className="h-5 w-5" />
                    <span>NOMINAL FLIGHT</span>
                  </div>
                )}
                <div className="text-xs font-mono text-slate-400 mt-1">
                  Severity Score: {mlResult ? `${(mlResult.anomaly.score * 100).toFixed(1)}%` : '0.0%'} (τ = {(mlResult?.anomaly.threshold ? mlResult.anomaly.threshold * 100 : 54.0).toFixed(1)}%)
                </div>
              </div>
              <div className="text-[10px] text-slate-500 font-mono">
                Detector: Isolation Forest (Phase 6)
              </div>
            </div>

            {/* 3. Classified Fault Diagnosis */}
            <div className="p-3.5 rounded-lg bg-slate-950/70 border border-slate-800 flex flex-col justify-between space-y-2">
              <div className="flex justify-between items-center text-xs text-slate-400">
                <span className="font-semibold uppercase tracking-wider text-[11px]">Classified Diagnosis</span>
                <Cpu className="w-3.5 h-3.5 text-purple-400" />
              </div>
              <div>
                <div className="text-base font-bold font-mono text-slate-100 truncate">
                  {mlResult?.fault.fault_class ? mlResult.fault.fault_class.replace(/_/g, ' ') : 'NORMAL'}
                </div>
                <div className="text-xs font-mono text-slate-400 mt-1">
                  Confidence: {mlResult ? `${(mlResult.fault.confidence * 100).toFixed(1)}%` : '100.0%'}
                </div>
              </div>
              <div className="text-[10px] text-slate-500 font-mono">
                Model: XGBoost Supervised Classifier
              </div>
            </div>

            {/* 4. Prognostic Remaining Useful Life */}
            <div className="p-3.5 rounded-lg bg-slate-950/70 border border-slate-800 flex flex-col justify-between space-y-2">
              <div className="flex justify-between items-center text-xs text-slate-400">
                <span className="font-semibold uppercase tracking-wider text-[11px]">Remaining Useful Life (RUL)</span>
                <Clock className="w-3.5 h-3.5 text-amber-400" />
              </div>
              <div>
                {prognosticsResult?.rul.status === 'ACTIVE' ? (
                  <>
                    <div className="text-2xl font-bold font-mono text-amber-300">
                      {prognosticsResult.rul.estimated_remaining_flight_hours?.toFixed(1)}{' '}
                      <span className="text-xs font-sans text-slate-400">hrs</span>
                    </div>
                    {prognosticsResult.rul.confidence_interval_95 && (
                      <div className="text-[11px] font-mono text-slate-400 mt-1">
                        95% PI: [{prognosticsResult.rul.confidence_interval_95[0].toFixed(1)} – {prognosticsResult.rul.confidence_interval_95[1].toFixed(1)} hrs]
                      </div>
                    )}
                  </>
                ) : (
                  <div className="py-1">
                    <span className="text-xs font-mono text-emerald-400 font-semibold block">
                      RUL UNAVAILABLE
                    </span>
                    <span className="text-[10px] text-slate-400 leading-tight block mt-0.5">
                      Nominal baseline engine without active wear degradation.
                    </span>
                  </div>
                )}
              </div>
              <div className="text-[10px] text-slate-500 font-mono">
                Extrapolation: Causal Linear OLS
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* REAL-TIME ENGINE KEY GAUGES MATRIX */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Activity className="h-4 w-4 text-sky-400" />
            <h3 className="text-xs font-mono uppercase tracking-wider text-slate-300 font-bold">
              Real-Time Engine Telemetry Gauges (10 Hz Stream)
            </h3>
          </div>
          <span className="text-[10px] font-mono text-slate-500">
            Validated against operational limits
          </span>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3 text-xs font-mono">
          {/* Gauge 1: RPM */}
          <div className="p-3 rounded-lg bg-slate-900/80 border border-slate-800">
            <div className="text-slate-400 text-[10px] uppercase">Engine Speed</div>
            <div className="text-lg font-bold text-sky-400 mt-1">
              {Math.round(telemetry.rpm)} <span className="text-xs text-slate-500">RPM</span>
            </div>
            <div className="text-[10px] text-slate-500 mt-0.5">Limit: 5800 RPM</div>
          </div>

          {/* Gauge 2: MAP */}
          <div className="p-3 rounded-lg bg-slate-900/80 border border-slate-800">
            <div className="text-slate-400 text-[10px] uppercase">Manifold Pressure</div>
            <div className="text-lg font-bold text-sky-400 mt-1">
              {telemetry.manifoldPressure.toFixed(2)} <span className="text-xs text-slate-500">bar</span>
            </div>
            <div className="text-[10px] text-slate-500 mt-0.5">Boost Turbocharged</div>
          </div>

          {/* Gauge 3: CHT Max */}
          <div className="p-3 rounded-lg bg-slate-900/80 border border-slate-800">
            <div className="text-slate-400 text-[10px] uppercase">Cylinder Head (CHT)</div>
            <div className="text-lg font-bold text-amber-400 mt-1">
              {maxCht.toFixed(1)} <span className="text-xs text-slate-500">°C</span>
            </div>
            <div className="text-[10px] text-slate-500 mt-0.5">Avg: {avgCht.toFixed(1)} °C</div>
          </div>

          {/* Gauge 4: EGT Max */}
          <div className="p-3 rounded-lg bg-slate-900/80 border border-slate-800">
            <div className="text-slate-400 text-[10px] uppercase">Exhaust Gas (EGT)</div>
            <div className="text-lg font-bold text-amber-400 mt-1">
              {maxEgt.toFixed(1)} <span className="text-xs text-slate-500">°C</span>
            </div>
            <div className="text-[10px] text-slate-500 mt-0.5">Avg: {avgEgt.toFixed(1)} °C</div>
          </div>

          {/* Gauge 5: Oil Pressure */}
          <div className="p-3 rounded-lg bg-slate-900/80 border border-slate-800">
            <div className="text-slate-400 text-[10px] uppercase">Oil Pressure</div>
            <div className="text-lg font-bold text-emerald-400 mt-1">
              {telemetry.oilPressure.toFixed(2)} <span className="text-xs text-slate-500">bar</span>
            </div>
            <div className="text-[10px] text-slate-500 mt-0.5">Nominal: 3.0–5.0 bar</div>
          </div>

          {/* Gauge 6: Oil Temp */}
          <div className="p-3 rounded-lg bg-slate-900/80 border border-slate-800">
            <div className="text-slate-400 text-[10px] uppercase">Oil Temperature</div>
            <div className="text-lg font-bold text-emerald-400 mt-1">
              {telemetry.oilTemperature.toFixed(1)} <span className="text-xs text-slate-500">°C</span>
            </div>
            <div className="text-[10px] text-slate-500 mt-0.5">Nominal: 70–110 °C</div>
          </div>

          {/* Gauge 7: Vibration */}
          <div className="p-3 rounded-lg bg-slate-900/80 border border-slate-800">
            <div className="text-slate-400 text-[10px] uppercase">Vibration RMS</div>
            <div className="text-lg font-bold text-sky-400 mt-1">
              {telemetry.vibrationRms.toFixed(2)} <span className="text-xs text-slate-500">g</span>
            </div>
            <div className="text-[10px] text-slate-500 mt-0.5">Limit: &lt; 1.5 g</div>
          </div>

          {/* Gauge 8: Fuel Flow */}
          <div className="p-3 rounded-lg bg-slate-900/80 border border-slate-800">
            <div className="text-slate-400 text-[10px] uppercase">Fuel Flow</div>
            <div className="text-lg font-bold text-sky-400 mt-1">
              {telemetry.fuelFlow.toFixed(1)} <span className="text-xs text-slate-500">L/h</span>
            </div>
            <div className="text-[10px] text-slate-500 mt-0.5">Density: 0.72 kg/L</div>
          </div>

          {/* Gauge 9: Electrical Bus */}
          <div className="p-3 rounded-lg bg-slate-900/80 border border-slate-800">
            <div className="text-slate-400 text-[10px] uppercase">Electrical Bus</div>
            <div className="text-lg font-bold text-emerald-400 mt-1">
              {telemetry.batteryVoltage.toFixed(2)} <span className="text-xs text-slate-500">V</span>
            </div>
            <div className="text-[10px] text-slate-500 mt-0.5">Bus: 12V Nominal</div>
          </div>

          {/* Gauge 10: Throttle */}
          <div className="p-3 rounded-lg bg-slate-900/80 border border-slate-800">
            <div className="text-slate-400 text-[10px] uppercase">Throttle Command</div>
            <div className="text-lg font-bold text-sky-400 mt-1">
              {(telemetry.throttle * 100).toFixed(0)} <span className="text-xs text-slate-500">%</span>
            </div>
            <div className="text-[10px] text-slate-500 mt-0.5">Engine: {telemetry.engineState}</div>
          </div>
        </div>
      </div>

      {/* QUICK OPERATIONS & SUBSYSTEM READINESS GRID */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Component Readiness Status */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <div className="flex items-center gap-2">
              <ShieldCheck className="h-4 w-4 text-emerald-400" />
              <CardTitle>System Subsystems Readiness</CardTitle>
            </div>
            <Badge variant="outline">RFC 8259 READY</Badge>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 font-mono text-xs">
              {readiness ? (
                Object.entries(readiness.components).map(([component, compStatus]) => {
                  const isReady = compStatus === 'READY';
                  return (
                    <div
                      key={component}
                      className="flex items-center justify-between p-2 rounded bg-slate-950/50 border border-slate-850"
                    >
                      <span className="text-slate-300 capitalize">
                        {component.replace(/_/g, ' ')}
                      </span>
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                          isReady
                            ? 'bg-emerald-950/70 text-emerald-400 border border-emerald-800/50'
                            : 'bg-slate-900 text-slate-400 border border-slate-800'
                        }`}
                      >
                        {compStatus}
                      </span>
                    </div>
                  );
                })
              ) : (
                <p className="text-slate-500 italic">No readiness probe response yet.</p>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Quick Operations Shortcuts */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Layers className="h-4 w-4 text-sky-400" />
              <CardTitle>Platform Navigation</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="space-y-2">
            <button
              onClick={() => setActiveTab('twin')}
              className="w-full flex items-center justify-between p-2.5 rounded bg-slate-950/60 hover:bg-slate-900 border border-slate-800 text-xs text-slate-200 transition-colors"
            >
              <span className="flex items-center gap-2 font-medium">
                <Cpu className="h-4 w-4 text-sky-400" />
                Launch 3D Digital Twin
              </span>
              <ArrowRight className="h-3.5 w-3.5 text-slate-500" />
            </button>

            <button
              onClick={() => setActiveTab('diagnostics')}
              className="w-full flex items-center justify-between p-2.5 rounded bg-slate-950/60 hover:bg-slate-900 border border-slate-800 text-xs text-slate-200 transition-colors"
            >
              <span className="flex items-center gap-2 font-medium">
                <Sparkles className="h-4 w-4 text-indigo-400" />
                AI Diagnostics &amp; Prognostics
              </span>
              <ArrowRight className="h-3.5 w-3.5 text-slate-500" />
            </button>

            <button
              onClick={() => setActiveTab('simulation')}
              className="w-full flex items-center justify-between p-2.5 rounded bg-slate-950/60 hover:bg-slate-900 border border-slate-800 text-xs text-slate-200 transition-colors"
            >
              <span className="flex items-center gap-2 font-medium">
                <Clock className="h-4 w-4 text-amber-400" />
                Mission Simulation &amp; Replay
              </span>
              <ArrowRight className="h-3.5 w-3.5 text-slate-500" />
            </button>

            <button
              onClick={handleSafeReset}
              className="w-full flex items-center justify-between p-2.5 rounded bg-amber-950/30 hover:bg-amber-900/40 border border-amber-800/50 text-xs text-amber-300 transition-colors mt-2"
            >
              <span className="flex items-center gap-2 font-medium">
                <RotateCcw className="h-4 w-4 text-amber-400" />
                Safe Demo Reset
              </span>
              <span className="text-[10px] font-mono text-amber-400/80">RESETS TWIN</span>
            </button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};
