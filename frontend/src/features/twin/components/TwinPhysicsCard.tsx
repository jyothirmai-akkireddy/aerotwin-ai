import React, { useState } from 'react';
import {
  Cpu,
  Activity,
  Flame,
  Droplets,
  AlertTriangle,
  CheckCircle,
  AlertOctagon,
  RefreshCw,
  Gauge,
  Wind,
} from 'lucide-react';
import { useTwinStore } from '../../../stores/useTwinStore';
import { fetchPhysicsCurrent } from '../../../api/physics';
import { Badge } from '../../../components/common/Badge';
import { Button } from '../../../components/common/Button';

export const TwinPhysicsCard: React.FC = () => {
  const { physicsResult, telemetry, setPhysicsResult } = useTwinStore();
  const [isLoading, setIsLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<'OVERVIEW' | 'CYLINDERS'>('OVERVIEW');

  const handleFetchCurrent = async () => {
    setIsLoading(true);
    try {
      const result = await fetchPhysicsCurrent();
      setPhysicsResult(result);
    } catch (err) {
      console.error('Failed to fetch physics twin current state:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const getValidityBadge = (validity: string) => {
    switch (validity) {
      case 'VALID':
        return (
          <Badge variant="success" className="flex items-center space-x-1">
            <CheckCircle className="w-3 h-3 mr-1" />
            <span>VALID</span>
          </Badge>
        );
      case 'DEGRADED':
        return (
          <Badge variant="warning" className="flex items-center space-x-1">
            <AlertTriangle className="w-3 h-3 mr-1" />
            <span>DEGRADED</span>
          </Badge>
        );
      case 'OUT_OF_RANGE':
        return (
          <Badge variant="accent" className="flex items-center space-x-1">
            <AlertTriangle className="w-3 h-3 mr-1" />
            <span>OUT_OF_RANGE</span>
          </Badge>
        );
      case 'INVALID':
      default:
        return (
          <Badge variant="danger" className="flex items-center space-x-1">
            <AlertOctagon className="w-3 h-3 mr-1" />
            <span>INVALID</span>
          </Badge>
        );
    }
  };

  // Helper for rendering normalized deviation bar
  const renderDeviationBar = (normVal: number) => {
    // Clamp visual range between -3.0 and +3.0 sigma
    const clamped = Math.max(-3.0, Math.min(3.0, normVal));
    const pct = ((clamped + 3.0) / 6.0) * 100;
    const isExtreme = Math.abs(normVal) > 2.0;
    const isModerate = Math.abs(normVal) > 1.0;

    const barColor = isExtreme
      ? 'bg-rose-500'
      : isModerate
      ? 'bg-amber-400'
      : 'bg-emerald-400';

    return (
      <div className="flex items-center space-x-1.5 w-28">
        <span className="text-[10px] font-mono text-slate-400 w-10 text-right">
          {normVal > 0 ? `+${normVal.toFixed(2)}` : normVal.toFixed(2)}σ
        </span>
        <div className="relative flex-grow h-2 bg-slate-800 rounded-full overflow-hidden">
          {/* Zero center marker */}
          <div className="absolute top-0 bottom-0 left-1/2 w-0.5 bg-slate-600 z-10" />
          {/* Indicator pin */}
          <div
            className={`absolute top-0 bottom-0 w-2 rounded-full -ml-1 ${barColor} transition-all duration-200`}
            style={{ left: `${pct}%` }}
          />
        </div>
      </div>
    );
  };

  if (!physicsResult) {
    return (
      <div className="bg-slate-900/90 border border-slate-800 rounded-lg p-4 shadow-xl">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center space-x-2">
            <Cpu className="w-5 h-5 text-sky-400" />
            <div>
              <h3 className="text-sm font-semibold text-slate-100">
                Physics-Informed Digital Twin (PIDT)
              </h3>
              <p className="text-xs text-slate-400">
                Low-order analytical physics models & normalized residual calculation
              </p>
            </div>
          </div>
          <Button
            size="sm"
            variant="outline"
            onClick={handleFetchCurrent}
            disabled={isLoading}
            className="flex items-center space-x-1.5"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
            <span>Evaluate Engine State</span>
          </Button>
        </div>
        <div className="mt-3 p-3 bg-slate-950/60 rounded border border-slate-800/80 text-xs text-slate-400 flex items-center justify-between">
          <span>
            Awaiting streaming frames from realtime telemetry or on-demand physics evaluation.
          </span>
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300">
            PROTOTYPE APPROXIMATION
          </span>
        </div>
      </div>
    );
  }

  const { expected_state: exp, residuals: res, diagnostics } = physicsResult;
  const raw = res.raw_residuals;
  const norm = res.normalized_residuals;

  const rawNum = (val: number | number[] | undefined, idx = 0): number => {
    if (val === undefined) return 0;
    if (Array.isArray(val)) return val[idx] ?? 0;
    return val;
  };

  const normNum = (val: number | number[] | undefined, idx = 0): number => {
    if (val === undefined) return 0;
    if (Array.isArray(val)) return val[idx] ?? 0;
    return val;
  };

  // Mean CHT & EGT across 4 cylinders
  const expChtMean = exp.cht.reduce((a, b) => a + b, 0) / 4;
  const obsChtMean = telemetry.cht.reduce((a, b) => a + b, 0) / 4;
  const expEgtMean = exp.egt.reduce((a, b) => a + b, 0) / 4;
  const obsEgtMean = telemetry.egt.reduce((a, b) => a + b, 0) / 4;

  const primaryChannels = [
    {
      label: 'Manifold Absolute Pressure',
      unit: 'inHg',
      icon: Gauge,
      expVal: exp.manifold_pressure,
      obsVal: telemetry.manifoldPressure,
      rawRes: rawNum(raw['manifold_pressure']),
      normRes: normNum(norm['manifold_pressure']),
    },
    {
      label: 'Fuel Consumption Flow',
      unit: 'L/h',
      icon: Droplets,
      expVal: exp.fuel_flow,
      obsVal: telemetry.fuelFlow,
      rawRes: rawNum(raw['fuel_flow']),
      normRes: normNum(norm['fuel_flow']),
    },
    {
      label: 'Mean Cylinder Head Temp',
      unit: '°C',
      icon: Flame,
      expVal: expChtMean,
      obsVal: obsChtMean,
      rawRes: obsChtMean - expChtMean,
      normRes: (obsChtMean - expChtMean) / 3.5, // 3.5°C empirical sigma
    },
    {
      label: 'Mean Exhaust Gas Temp',
      unit: '°C',
      icon: Wind,
      expVal: expEgtMean,
      obsVal: obsEgtMean,
      rawRes: obsEgtMean - expEgtMean,
      normRes: (obsEgtMean - expEgtMean) / 14.2, // 14.2°C empirical sigma
    },
    {
      label: 'Main Gallery Oil Pressure',
      unit: 'bar',
      icon: Gauge,
      expVal: exp.oil_pressure,
      obsVal: telemetry.oilPressure,
      rawRes: rawNum(raw['oil_pressure']),
      normRes: normNum(norm['oil_pressure']),
    },
    {
      label: 'Sump Oil Temperature',
      unit: '°C',
      icon: Flame,
      expVal: exp.oil_temperature,
      obsVal: telemetry.oilTemperature,
      rawRes: rawNum(raw['oil_temperature']),
      normRes: normNum(norm['oil_temperature']),
    },
    {
      label: 'Airframe Vibration RMS',
      unit: 'g',
      icon: Activity,
      expVal: exp.vibration_rms,
      obsVal: telemetry.vibrationRms,
      rawRes: rawNum(raw['vibration_rms']),
      normRes: normNum(norm['vibration_rms']),
    },
  ];

  return (
    <div className="bg-slate-900/95 border border-slate-800 rounded-lg p-4 shadow-xl text-slate-200">
      {/* ============================================================== */}
      {/* HEADER SECTION                                                 */}
      {/* ============================================================== */}
      <div className="flex flex-wrap items-center justify-between gap-2 pb-3 border-b border-slate-800">
        <div className="flex items-center space-x-2.5">
          <div className="p-1.5 rounded bg-sky-950/80 border border-sky-800/80 text-sky-400">
            <Cpu className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h3 className="text-sm font-bold text-slate-100 tracking-wide">
                PHYSICS-INFORMED DIGITAL TWIN
              </h3>
              {getValidityBadge(exp.validity)}
              <Badge variant="outline" className="text-[10px]">
                v{exp.model_version}
              </Badge>
              <Badge variant="outline" className="text-[10px] text-amber-300 border-amber-800/60">
                PROTOTYPE APPROXIMATION
              </Badge>
            </div>
            <p className="text-[11px] text-slate-400">
              Low-order analytical expectations &amp; empirical σ-normalized residuals (MALE UAV Rotax 914/915 baseline)
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-2 text-xs">
          <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded bg-slate-950 border border-slate-800 font-mono text-[11px]">
            <span className="text-slate-400">Conf:</span>
            <span className="font-semibold text-emerald-400">
              {(exp.confidence * 100).toFixed(0)}%
            </span>
          </div>

          <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded bg-slate-950 border border-slate-800 font-mono text-[11px]">
            <span className="text-slate-400">Latency:</span>
            <span className="font-semibold text-sky-400">
              {diagnostics && typeof diagnostics.compute_time_ms === 'number'
                ? `${diagnostics.compute_time_ms.toFixed(3)} ms`
                : '< 0.05 ms'}
            </span>
          </div>

          <Button
            size="sm"
            variant="outline"
            onClick={handleFetchCurrent}
            disabled={isLoading}
            className="h-7 px-2"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
          </Button>
        </div>
      </div>

      {/* ============================================================== */}
      {/* SUMMARY BANNER: RESIDUAL INTENSITY & THERMAL SPREAD            */}
      {/* ============================================================== */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2.5 my-3">
        <div className="p-2.5 rounded bg-slate-950/70 border border-slate-800">
          <div className="text-[10px] text-slate-400 uppercase tracking-wider">
            Mean Abs Norm Residual
          </div>
          <div className="flex items-baseline space-x-1 mt-0.5">
            <span className="font-mono text-base font-bold text-sky-400">
              {res.mean_absolute_normalized_residual.toFixed(2)}
            </span>
            <span className="text-[10px] text-slate-400 font-mono">σ</span>
          </div>
          <div className="text-[10px] text-slate-400 mt-0.5">
            Overall model deviation magnitude
          </div>
        </div>

        <div className="p-2.5 rounded bg-slate-950/70 border border-slate-800">
          <div className="text-[10px] text-slate-400 uppercase tracking-wider">
            CHT Cylinder Spread
          </div>
          <div className="flex items-baseline space-x-1 mt-0.5">
            <span
              className={`font-mono text-base font-bold ${
                res.cht_max_imbalance_celsius > 18.0 ? 'text-amber-400' : 'text-emerald-400'
              }`}
            >
              {res.cht_max_imbalance_celsius.toFixed(1)}
            </span>
            <span className="text-[10px] text-slate-400 font-mono">°C</span>
          </div>
          <div className="text-[10px] text-slate-400 mt-0.5">Max cylinder CHT deviation</div>
        </div>

        <div className="p-2.5 rounded bg-slate-950/70 border border-slate-800">
          <div className="text-[10px] text-slate-400 uppercase tracking-wider">
            EGT Cylinder Spread
          </div>
          <div className="flex items-baseline space-x-1 mt-0.5">
            <span
              className={`font-mono text-base font-bold ${
                res.egt_max_imbalance_celsius > 45.0 ? 'text-amber-400' : 'text-emerald-400'
              }`}
            >
              {res.egt_max_imbalance_celsius.toFixed(0)}
            </span>
            <span className="text-[10px] text-slate-400 font-mono">°C</span>
          </div>
          <div className="text-[10px] text-slate-400 mt-0.5">Exhaust enthalpy balance</div>
        </div>

        <div className="p-2.5 rounded bg-slate-950/70 border border-slate-800">
          <div className="text-[10px] text-slate-400 uppercase tracking-wider">
            Air Induction Mass Flow
          </div>
          <div className="flex items-baseline space-x-1 mt-0.5">
            <span className="font-mono text-base font-bold text-slate-200">
              {exp.air_mass_flow.toFixed(1)}
            </span>
            <span className="text-[10px] text-slate-400 font-mono">kg/h</span>
          </div>
          <div className="text-[10px] text-slate-400 mt-0.5">Speed-density air intake</div>
        </div>
      </div>

      {/* ============================================================== */}
      {/* NAVIGATION TABS: OVERVIEW VS CYLINDERS                         */}
      {/* ============================================================== */}
      <div className="flex items-center space-x-2 border-b border-slate-800 pb-2 mb-3">
        <button
          onClick={() => setActiveTab('OVERVIEW')}
          className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
            activeTab === 'OVERVIEW'
              ? 'bg-sky-950 text-sky-300 border border-sky-800'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          Primary Powertrain Residuals
        </button>
        <button
          onClick={() => setActiveTab('CYLINDERS')}
          className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
            activeTab === 'CYLINDERS'
              ? 'bg-sky-950 text-sky-300 border border-sky-800'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          4-Cylinder Thermal Balance
        </button>
      </div>

      {/* ============================================================== */}
      {/* TAB 1: PRIMARY POWERTRAIN RESIDUALS TABLE                      */}
      {/* ============================================================== */}
      {activeTab === 'OVERVIEW' && (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-slate-800 text-[10px] text-slate-400 font-mono uppercase tracking-wider">
                <th className="py-1.5 px-2">Channel</th>
                <th className="py-1.5 px-2 text-right">Expected (Physics)</th>
                <th className="py-1.5 px-2 text-right">Observed (Sensor)</th>
                <th className="py-1.5 px-2 text-right">Raw Residual (Δy)</th>
                <th className="py-1.5 px-2 text-right">Normalized (Δy/σ)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono">
              {primaryChannels.map((item, idx) => {
                const IconComp = item.icon;
                const isPositive = item.rawRes > 0;
                return (
                  <tr key={idx} className="hover:bg-slate-800/30 transition-colors">
                    <td className="py-2 px-2 text-slate-300 font-sans flex items-center space-x-1.5">
                      <IconComp className="w-3.5 h-3.5 text-slate-400 flex-shrink-0" />
                      <span>{item.label}</span>
                    </td>
                    <td className="py-2 px-2 text-right text-slate-300">
                      {item.expVal.toFixed(2)} <span className="text-[10px] text-slate-400">{item.unit}</span>
                    </td>
                    <td className="py-2 px-2 text-right text-slate-100 font-bold">
                      {item.obsVal.toFixed(2)} <span className="text-[10px] text-slate-400">{item.unit}</span>
                    </td>
                    <td
                      className={`py-2 px-2 text-right font-medium ${
                        Math.abs(item.normRes) > 2.0
                          ? 'text-rose-400'
                          : Math.abs(item.normRes) > 1.0
                          ? 'text-amber-400'
                          : 'text-slate-300'
                      }`}
                    >
                      {isPositive ? `+${item.rawRes.toFixed(2)}` : item.rawRes.toFixed(2)}{' '}
                      <span className="text-[10px] text-slate-400">{item.unit}</span>
                    </td>
                    <td className="py-2 px-2 text-right">
                      <div className="flex justify-end">
                        {renderDeviationBar(item.normRes)}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* ============================================================== */}
      {/* TAB 2: 4-CYLINDER THERMAL BALANCE                              */}
      {/* ============================================================== */}
      {activeTab === 'CYLINDERS' && (
        <div className="space-y-3">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {/* CHT 4-Cylinder Matrix */}
            <div className="p-3 bg-slate-950/70 rounded border border-slate-800">
              <div className="text-xs font-semibold text-slate-200 mb-2 flex items-center justify-between">
                <span>Cylinder Head Temperature (CHT)</span>
                <span className="text-[10px] text-slate-400 font-mono">σ = 3.5°C</span>
              </div>
              <div className="space-y-2">
                {[0, 1, 2, 3].map((i) => {
                  const eCht = exp.cht[i] ?? 0;
                  const oCht = telemetry.cht[i] ?? 0;
                  const delta = oCht - eCht;
                  const normDev = delta / 3.5;
                  return (
                    <div
                      key={i}
                      className="p-2 rounded bg-slate-900/80 border border-slate-800 text-xs font-mono"
                    >
                      <div className="flex justify-between items-center text-slate-300 font-sans mb-1">
                        <span className="font-semibold text-slate-200">Cylinder {i + 1}</span>
                        {renderDeviationBar(normDev)}
                      </div>
                      <div className="flex justify-between text-[11px] text-slate-400">
                        <span>
                          Exp: <strong className="text-slate-300">{eCht.toFixed(1)}°C</strong>
                        </span>
                        <span>
                          Obs: <strong className="text-slate-100">{oCht.toFixed(1)}°C</strong>
                        </span>
                        <span
                          className={
                            Math.abs(normDev) > 2.0
                              ? 'text-rose-400'
                              : Math.abs(normDev) > 1.0
                              ? 'text-amber-400'
                              : 'text-emerald-400'
                          }
                        >
                          Δ: {delta > 0 ? `+${delta.toFixed(1)}` : delta.toFixed(1)}°C
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* EGT 4-Cylinder Matrix */}
            <div className="p-3 bg-slate-950/70 rounded border border-slate-800">
              <div className="text-xs font-semibold text-slate-200 mb-2 flex items-center justify-between">
                <span>Exhaust Gas Temperature (EGT)</span>
                <span className="text-[10px] text-slate-400 font-mono">σ = 14.2°C</span>
              </div>
              <div className="space-y-2">
                {[0, 1, 2, 3].map((i) => {
                  const eEgt = exp.egt[i] ?? 0;
                  const oEgt = telemetry.egt[i] ?? 0;
                  const delta = oEgt - eEgt;
                  const normDev = delta / 14.2;
                  return (
                    <div
                      key={i}
                      className="p-2 rounded bg-slate-900/80 border border-slate-800 text-xs font-mono"
                    >
                      <div className="flex justify-between items-center text-slate-300 font-sans mb-1">
                        <span className="font-semibold text-slate-200">Cylinder {i + 1}</span>
                        {renderDeviationBar(normDev)}
                      </div>
                      <div className="flex justify-between text-[11px] text-slate-400">
                        <span>
                          Exp: <strong className="text-slate-300">{eEgt.toFixed(0)}°C</strong>
                        </span>
                        <span>
                          Obs: <strong className="text-slate-100">{oEgt.toFixed(0)}°C</strong>
                        </span>
                        <span
                          className={
                            Math.abs(normDev) > 2.0
                              ? 'text-rose-400'
                              : Math.abs(normDev) > 1.0
                              ? 'text-amber-400'
                              : 'text-emerald-400'
                          }
                        >
                          Δ: {delta > 0 ? `+${delta.toFixed(0)}` : delta.toFixed(0)}°C
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ============================================================== */}
      {/* FOOTER NOTICE                                                  */}
      {/* ============================================================== */}
      <div className="mt-3 pt-2 border-t border-slate-800/80 text-[10px] text-slate-400 flex flex-wrap justify-between items-center gap-1">
        <span>
          Residual features are generated from deterministic low-order physical conservation equations and empirical baseline flight scales.
        </span>
        <span className="font-mono text-slate-400">
          Rotax 914/915 Baseline | Phase 5
        </span>
      </div>
    </div>
  );
};
