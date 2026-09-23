import React, { useState } from 'react';
import {
  Hourglass,
  Activity,
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  RefreshCw,
  ArrowDownRight,
  ArrowUpRight,
  Minus,
  HelpCircle,
  Clock,
  Gauge,
  Layers,
} from 'lucide-react';
import { useTwinStore } from '../../../stores/useTwinStore';
import { fetchPrognosticsCurrent } from '../../../api/prognostics';
import { Badge } from '../../../components/common/Badge';
import { Button } from '../../../components/common/Button';
import {
  DegradationStateDto,
  SubsystemDegradationMetricDto,
  TrendDirectionDto,
} from '../../../services/websocket/types';

export const TwinPrognosticsCard: React.FC = () => {
  const { prognosticsResult, setPrognosticsResult } = useTwinStore();
  const [isLoading, setIsLoading] = useState(false);
  const [showDetails, setShowDetails] = useState(false);
  const [showLatencies, setShowLatencies] = useState(false);

  const handleRefresh = async () => {
    setIsLoading(true);
    try {
      const res = await fetchPrognosticsCurrent();
      if (res) {
        setPrognosticsResult(res);
      }
    } catch (err) {
      console.error('Failed to fetch current prognostics state:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const getDegradationBadge = (state: DegradationStateDto) => {
    switch (state) {
      case 'NOMINAL':
        return (
          <Badge variant="success" className="flex items-center space-x-1">
            <CheckCircle2 className="w-3 h-3 mr-1" />
            <span>NOMINAL (PROTOTYPE)</span>
          </Badge>
        );
      case 'EARLY_DEGRADATION':
        return (
          <span className="px-2 py-0.5 text-xs font-semibold rounded bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 flex items-center">
            <Activity className="w-3 h-3 mr-1" />
            EARLY DEGRADATION
          </span>
        );
      case 'MODERATE_DEGRADATION':
        return (
          <Badge variant="warning" className="flex items-center space-x-1">
            <AlertTriangle className="w-3 h-3 mr-1" />
            <span>MODERATE DEGRADATION</span>
          </Badge>
        );
      case 'SEVERE_DEGRADATION':
      case 'CRITICAL_SIMULATED_STATE':
        return (
          <Badge variant="danger" className="flex items-center space-x-1 animate-pulse">
            <AlertTriangle className="w-3 h-3 mr-1" />
            <span>{state.replace(/_/g, ' ')}</span>
          </Badge>
        );
      default:
        return null;
    }
  };

  const getTrendIcon = (trend: TrendDirectionDto) => {
    switch (trend) {
      case 'IMPROVING':
        return (
          <span className="flex items-center text-emerald-400 text-xs font-medium">
            <ArrowUpRight className="w-3.5 h-3.5 mr-0.5" />
            IMPROVING
          </span>
        );
      case 'DEGRADING':
        return (
          <span className="flex items-center text-amber-400 text-xs font-medium">
            <ArrowDownRight className="w-3.5 h-3.5 mr-0.5" />
            DEGRADING
          </span>
        );
      case 'STABLE':
        return (
          <span className="flex items-center text-cyan-400 text-xs font-medium">
            <Minus className="w-3.5 h-3.5 mr-0.5" />
            STABLE
          </span>
        );
      case 'UNKNOWN':
      default:
        return (
          <span className="flex items-center text-slate-400 text-xs font-medium">
            <HelpCircle className="w-3.5 h-3.5 mr-0.5" />
            UNKNOWN
          </span>
        );
    }
  };

  const getHealthBarColor = (pct: number) => {
    if (pct >= 85) return 'bg-emerald-500';
    if (pct >= 70) return 'bg-cyan-500';
    if (pct >= 50) return 'bg-amber-500';
    return 'bg-rose-500';
  };

  const renderTierMetric = (title: string, metric: SubsystemDegradationMetricDto) => (
    <div className="flex flex-col space-y-0.5 text-[11px] bg-slate-900/60 p-1.5 rounded border border-slate-800/80">
      <div className="flex justify-between text-slate-400">
        <span>{title}</span>
        <span className="font-mono text-slate-200">
          {metric.raw_deviation.toFixed(2)} {metric.unit}
        </span>
      </div>
      <div className="flex justify-between text-slate-500 text-[10px]">
        <span>Normalized Ratio:</span>
        <span className="font-mono text-cyan-400">{metric.normalized_deviation.toFixed(2)}σ</span>
      </div>
      <div className="flex justify-between text-slate-500 text-[10px]">
        <span>Bounded Penalty:</span>
        <span className="font-mono text-amber-400">{metric.bounded_penalty.toFixed(3)}</span>
      </div>
    </div>
  );

  return (
    <div className="flex flex-col bg-slate-900/90 border border-slate-800 rounded-lg p-4 shadow-xl backdrop-blur-md">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-slate-800">
        <div className="flex items-center space-x-2">
          <Hourglass className="w-5 h-5 text-indigo-400" />
          <h3 className="font-semibold text-sm text-slate-200 tracking-wide uppercase">
            Engine Degradation & Prognostics (RUL)
          </h3>
        </div>
        <div className="flex items-center space-x-2">
          {prognosticsResult && getDegradationBadge(prognosticsResult.degradation_state)}
          <Button
            variant="ghost"
            size="sm"
            onClick={handleRefresh}
            disabled={isLoading}
            className="h-7 w-7 p-0 text-slate-400 hover:text-slate-200"
            title="Refresh prognostics state"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
          </Button>
        </div>
      </div>

      {!prognosticsResult ? (
        <div className="flex flex-col items-center justify-center py-8 text-center text-slate-500 space-y-2">
          <Activity className="w-8 h-8 text-slate-600 animate-pulse" />
          <p className="text-xs">Awaiting telemetry stream to evaluate engine degradation...</p>
        </div>
      ) : (
        <div className="flex flex-col space-y-4 pt-3">
          {/* Section 1: Health Index & Causal Trend */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 p-3 rounded-lg bg-slate-950/60 border border-slate-800/80">
            {/* Health Index */}
            <div className="flex flex-col space-y-1">
              <div className="flex justify-between items-center text-xs text-slate-400">
                <span className="flex items-center">
                  <Gauge className="w-3.5 h-3.5 mr-1 text-indigo-400" />
                  Composite Health Index
                </span>
                <span className="font-mono text-sm font-bold text-slate-100">
                  {(prognosticsResult.health_index * 100).toFixed(1)}%
                </span>
              </div>
              <div className="w-full h-2 bg-slate-800 rounded-full overflow-hidden">
                <div
                  className={`h-full transition-all duration-300 ${getHealthBarColor(
                    prognosticsResult.health_index * 100
                  )}`}
                  style={{ width: `${Math.max(3, prognosticsResult.health_index * 100)}%` }}
                />
              </div>
              <span className="text-[10px] text-slate-500 font-mono">
                Raw HI: {prognosticsResult.health_index.toFixed(4)} (Threshold: 0.90 Nominal)
              </span>
            </div>

            {/* Causal Trend */}
            <div className="flex flex-col justify-between space-y-1">
              <div className="flex justify-between items-center text-xs text-slate-400">
                <span>Causal Trend Slope</span>
                {getTrendIcon(prognosticsResult.trend_direction)}
              </div>
              <div className="flex justify-between items-center font-mono text-xs text-slate-300">
                <span>Rate of Change:</span>
                <span
                  className={
                    prognosticsResult.trend_slope_per_sec < -0.0001
                      ? 'text-amber-400 font-semibold'
                      : 'text-slate-300'
                  }
                >
                  {prognosticsResult.trend_slope_per_sec > 0 ? '+' : ''}
                  {prognosticsResult.trend_slope_per_sec.toFixed(6)} /s
                </span>
              </div>
              <span className="text-[10px] text-slate-500">
                Evaluated over strictly causal sliding window buffer (30–300 frames)
              </span>
            </div>
          </div>

          {/* Section 2: Remaining Useful Life (RUL) with Strict Gating */}
          <div className="p-3 rounded-lg bg-indigo-950/20 border border-indigo-900/40 flex flex-col space-y-2">
            <div className="flex justify-between items-center">
              <div className="flex items-center space-x-1.5 text-xs font-semibold text-indigo-300">
                <Clock className="w-4 h-4 text-indigo-400" />
                <span>Remaining Useful Life (RUL) Projection</span>
              </div>
              <span
                className={`text-[11px] px-2 py-0.5 rounded font-mono font-medium border ${
                  prognosticsResult.rul.status === 'ACTIVE'
                    ? 'bg-amber-500/20 text-amber-300 border-amber-500/40'
                    : prognosticsResult.rul.status === 'DEGRADATION_NOT_DETECTED'
                    ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
                    : 'bg-slate-800 text-slate-400 border-slate-700'
                }`}
              >
                {prognosticsResult.rul.status}
              </span>
            </div>

            {prognosticsResult.rul.status === 'ACTIVE' ? (
              <div className="flex flex-col space-y-2 pt-1">
                <div className="flex items-baseline justify-between">
                  <div className="flex items-baseline space-x-2">
                    <span className="text-2xl font-bold font-mono text-amber-300">
                      {prognosticsResult.rul.estimated_remaining_flight_hours?.toFixed(1)}
                    </span>
                    <span className="text-xs text-slate-400">simulated flight hours</span>
                  </div>
                  {prognosticsResult.rul.confidence_interval_95 && (
                    <span className="text-xs font-mono text-slate-300 bg-slate-900 px-2 py-1 rounded border border-slate-800">
                      95% PI: [{prognosticsResult.rul.confidence_interval_95[0].toFixed(1)} –{' '}
                      {prognosticsResult.rul.confidence_interval_95[1].toFixed(1)} hrs]
                    </span>
                  )}
                </div>

                <div className="grid grid-cols-2 gap-2 text-xs pt-1">
                  <div className="flex justify-between text-slate-400">
                    <span>Limiting Subsystem:</span>
                    <span className="font-semibold text-slate-200 capitalize">
                      {prognosticsResult.rul.limiting_subsystem.replace(/_/g, ' ')}
                    </span>
                  </div>
                  <div className="flex justify-between text-slate-400">
                    <span>Prognostic Confidence:</span>
                    <span className="font-mono text-cyan-300">
                      {(prognosticsResult.rul.confidence * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>
              </div>
            ) : (
              <div className="py-2 text-xs text-slate-400 font-sans italic flex items-center space-x-1.5">
                <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                <span>
                  {prognosticsResult.rul.status === 'DEGRADATION_NOT_DETECTED'
                    ? 'RUL UNAVAILABLE — Nominal baseline engine without active wear degradation'
                    : prognosticsResult.rul.reason ||
                      'RUL estimation inactive for current operational state.'}
                </span>
              </div>
            )}
          </div>

          {/* Section 3: Subsystem Degradation Health Bars */}
          <div className="flex flex-col space-y-2">
            <div className="flex justify-between items-center">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center">
                <Layers className="w-3.5 h-3.5 mr-1" /> Subsystem Health & Degradation Breakdown
              </span>
              <button
                onClick={() => setShowDetails(!showDetails)}
                className="text-[11px] text-cyan-400 hover:text-cyan-300 flex items-center space-x-1"
              >
                <span>{showDetails ? 'Hide 3-Tier Values' : 'View 3-Tier Deviations'}</span>
                {showDetails ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
              </button>
            </div>

            <div className="grid grid-cols-2 gap-2">
              {/* Lubrication */}
              <div className="bg-slate-950/60 p-2 rounded border border-slate-800/80">
                <div className="flex justify-between text-xs text-slate-300 mb-1">
                  <span>Lubrication</span>
                  <span className="font-mono">
                    {prognosticsResult.subsystems.lubrication_health_pct.toFixed(0)}%
                  </span>
                </div>
                <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
                  <div
                    className={`h-full ${getHealthBarColor(
                      prognosticsResult.subsystems.lubrication_health_pct
                    )}`}
                    style={{
                      width: `${prognosticsResult.subsystems.lubrication_health_pct}%`,
                    }}
                  />
                </div>
              </div>

              {/* Thermal Balance */}
              <div className="bg-slate-950/60 p-2 rounded border border-slate-800/80">
                <div className="flex justify-between text-xs text-slate-300 mb-1">
                  <span>Thermal Balance</span>
                  <span className="font-mono">
                    {prognosticsResult.subsystems.thermal_health_pct.toFixed(0)}%
                  </span>
                </div>
                <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
                  <div
                    className={`h-full ${getHealthBarColor(
                      prognosticsResult.subsystems.thermal_health_pct
                    )}`}
                    style={{
                      width: `${prognosticsResult.subsystems.thermal_health_pct}%`,
                    }}
                  />
                </div>
              </div>

              {/* Turbo Induction */}
              <div className="bg-slate-950/60 p-2 rounded border border-slate-800/80">
                <div className="flex justify-between text-xs text-slate-300 mb-1">
                  <span>Turbocharger</span>
                  <span className="font-mono">
                    {prognosticsResult.subsystems.turbocharger_health_pct.toFixed(0)}%
                  </span>
                </div>
                <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
                  <div
                    className={`h-full ${getHealthBarColor(
                      prognosticsResult.subsystems.turbocharger_health_pct
                    )}`}
                    style={{
                      width: `${prognosticsResult.subsystems.turbocharger_health_pct}%`,
                    }}
                  />
                </div>
              </div>

              {/* Rotational Vibration */}
              <div className="bg-slate-950/60 p-2 rounded border border-slate-800/80">
                <div className="flex justify-between text-xs text-slate-300 mb-1">
                  <span>Mechanical / Vib</span>
                  <span className="font-mono">
                    {prognosticsResult.subsystems.rotational_health_pct.toFixed(0)}%
                  </span>
                </div>
                <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
                  <div
                    className={`h-full ${getHealthBarColor(
                      prognosticsResult.subsystems.rotational_health_pct
                    )}`}
                    style={{
                      width: `${prognosticsResult.subsystems.rotational_health_pct}%`,
                    }}
                  />
                </div>
              </div>
            </div>

            {/* Expandable 3-tier view */}
            {showDetails && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2 pt-1">
                {renderTierMetric('Lubrication Deviation', prognosticsResult.subsystems.lubrication)}
                {renderTierMetric('Thermal Imbalance', prognosticsResult.subsystems.thermal)}
                {renderTierMetric('Turbo MAP Deficit', prognosticsResult.subsystems.turbocharger)}
                {renderTierMetric(
                  'Rotational Vibration',
                  prognosticsResult.subsystems.rotational_vibration
                )}
              </div>
            )}
          </div>

          {/* Section 4: Key Prognostic Indicators */}
          {prognosticsResult.indicators && prognosticsResult.indicators.length > 0 && (
            <div className="flex flex-col space-y-1.5 pt-1">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Key Prognostic Indicators
              </span>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                {prognosticsResult.indicators.map((ind) => (
                  <div
                    key={ind.name}
                    className="flex flex-col p-2 bg-slate-950/80 rounded border border-slate-800/80 text-[11px]"
                  >
                    <span className="text-slate-400 capitalize truncate">
                      {ind.name.replace(/_/g, ' ')}
                    </span>
                    <span className="font-mono font-semibold text-slate-200 mt-0.5">
                      {ind.current_value} {ind.unit}
                    </span>
                    <span
                      className={`text-[9px] mt-1 font-semibold uppercase px-1 py-0.5 rounded text-center ${
                        ind.severity === 'CRITICAL'
                          ? 'bg-rose-500/20 text-rose-300'
                          : ind.severity === 'WARNING'
                          ? 'bg-amber-500/20 text-amber-300'
                          : ind.severity === 'ADVISORY'
                          ? 'bg-cyan-500/20 text-cyan-300'
                          : 'bg-emerald-500/10 text-emerald-400'
                      }`}
                    >
                      {ind.severity}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Footer & Latencies */}
          <div className="flex flex-col space-y-1 pt-2 border-t border-slate-800 text-[11px] text-slate-400">
            <div className="flex justify-between items-center">
              <span className="text-[10px] text-slate-500">
                PROTOTYPE BENCHMARK MODEL — NOT CERTIFIED FOR FLIGHT
              </span>
              <button
                onClick={() => setShowLatencies(!showLatencies)}
                className="flex items-center space-x-1 font-mono hover:text-slate-200"
              >
                <span>Pipeline: {prognosticsResult.pipeline_latency_ms.toFixed(2)} ms</span>
                {showLatencies ? (
                  <ChevronUp className="w-3 h-3 ml-0.5" />
                ) : (
                  <ChevronDown className="w-3 h-3 ml-0.5" />
                )}
              </button>
            </div>

            {showLatencies && prognosticsResult.disaggregated_latencies && (
              <div className="grid grid-cols-3 gap-2 bg-slate-950 p-2 rounded border border-slate-800 text-[10px] font-mono text-slate-400">
                {Object.entries(prognosticsResult.disaggregated_latencies).map(([k, v]) => (
                  <div key={k} className="flex justify-between">
                    <span className="capitalize">{k.replace(/_ms/g, '')}:</span>
                    <span className="text-cyan-400">{v.toFixed(3)} ms</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
