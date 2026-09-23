import React, { useState, useEffect } from 'react';
import {
  Compass,
  Play,
  RotateCcw,
  CheckCircle,
  AlertTriangle,
  Flame,
  Droplets,
  Activity,
  Layers,
  ShieldAlert,
  FileCheck,
} from 'lucide-react';
import { useTwinStore } from '../../stores/useTwinStore';

interface PredefinedMissionSummary {
  mission_id: string;
  name: string;
  description: string;
  total_duration_sec: number;
  phase_count: number;
  is_synthetic: boolean;
  version: string;
}

interface PhaseDetail {
  phase_id: string;
  phase_type: string;
  start_time_sec: number;
  duration_sec: number;
  fuel_burned_liters: number;
  avg_rpm: number;
  max_cht_c: number;
  max_egt_c: number;
}

interface SimulationSummaryResult {
  run_id: string;
  mission_id: string;
  mission_version: string;
  duration_sec: number;
  frame_count: number;
  summary: {
    fuel_consumed_liters: number;
    fuel_mass_kg: number;
    max_cht_c: number;
    max_egt_c: number;
    max_oil_temp_c: number;
    min_oil_pressure_bar: number;
    peak_vibration_rms: number;
    max_altitude_m: number;
  };
  phase_summaries: PhaseDetail[];
  dataset_path: string | null;
  prototype_disclaimer: string;
}

export const MissionSimulationView: React.FC = () => {
  const { setSourceMode, setReplayStatus } = useTwinStore();
  const [missions, setMissions] = useState<PredefinedMissionSummary[]>([]);
  const [selectedMissionId, setSelectedMissionId] = useState<string>('SURVEILLANCE_MISSION');
  const [rateHz, setRateHz] = useState<number>(10);
  const [seed, setSeed] = useState<number>(42);
  const [isSimulating, setIsSimulating] = useState<boolean>(false);
  const [simResult, setSimResult] = useState<SimulationSummaryResult | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [exportNotice, setExportNotice] = useState<string | null>(null);

  useEffect(() => {
    const fetchMissions = async () => {
      try {
        const resp = await fetch('http://localhost:8000/api/v1/missions/predefined');
        if (resp.ok) {
          const data: PredefinedMissionSummary[] = await resp.json();
          setMissions(data);
          if (data.length > 0) {
            setSelectedMissionId(data[0].mission_id);
          }
        }
      } catch {
        // Fallback for offline dev
      }
    };
    fetchMissions();
  }, []);

  const handleSimulate = async () => {
    setIsSimulating(true);
    setErrorMessage(null);
    setExportNotice(null);
    try {
      const resp = await fetch('http://localhost:8000/api/v1/missions/simulate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          mission_id: selectedMissionId,
          rate_hz: rateHz,
          seed: seed,
          persist_dataset: true,
          include_frames: false,
        }),
      });

      if (!resp.ok) {
        const err = await resp.json();
        throw new Error(err.detail || 'Simulation failed');
      }

      const data: SimulationSummaryResult = await resp.json();
      setSimResult(data);
    } catch (e: unknown) {
      setErrorMessage(e instanceof Error ? e.message : 'Error executing mission simulation');
    } finally {
      setIsSimulating(false);
    }
  };

  const handleQueueForReplay = async () => {
    if (!simResult?.dataset_path) return;
    try {
      const filename = simResult.dataset_path.split(/[\\/]/).pop() || '';
      const resp = await fetch('http://localhost:8000/api/v1/replay/load', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filename }),
      });
      if (resp.ok) {
        const status = await resp.json();
        setReplayStatus(status);
        await fetch('http://localhost:8000/api/v1/replay/mode', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ mode: 'REPLAY' }),
        });
        setSourceMode('REPLAY');
        setExportNotice(`Mission log '${filename}' loaded into Replay Engine! Switch to 3D Twin tab to replay.`);
      }
    } catch (e: unknown) {
      setErrorMessage(e instanceof Error ? e.message : 'Error queuing dataset for replay');
    }
  };

  const selectedMission = missions.find((m) => m.mission_id === selectedMissionId);

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* 1. Header Banner & Prototype Disclaimer */}
      <div className="bg-amber-950/30 border border-amber-500/40 rounded-xl p-4 text-amber-200 flex items-start gap-3 shadow-lg">
        <ShieldAlert className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
        <div className="space-y-1 text-xs">
          <div className="font-semibold text-amber-300 text-sm flex items-center gap-2">
            <span>SYNTHETIC / PROTOTYPE MISSION SIMULATOR & FLIGHT REPLAY</span>
            <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-amber-900/60 border border-amber-700/60">
              Phase 8 Operational
            </span>
          </div>
          <p className="text-amber-200/80 leading-relaxed">
            All mission flight profiles, transition curves (cubic Hermite smoothstep), control events, and flight replay
            systems developed herein represent engineering research prototypes based on simplified synthetic aerodynamics
            and the existing deterministic Rotax 914/915 iS engine dynamics model. They do NOT represent certified
            flight operations or OEM performance data.
          </p>
        </div>
      </div>

      {errorMessage && (
        <div className="p-3 rounded-lg bg-rose-950/60 border border-rose-800 text-rose-300 text-sm flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0 text-rose-400" />
          <span>{errorMessage}</span>
        </div>
      )}

      {exportNotice && (
        <div className="p-3 rounded-lg bg-emerald-950/60 border border-emerald-800 text-emerald-300 text-sm flex items-center gap-2">
          <CheckCircle className="w-4 h-4 shrink-0 text-emerald-400" />
          <span>{exportNotice}</span>
        </div>
      )}

      {/* 2. Mission Selection & Control Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Preset Catalog */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 shadow-lg space-y-4">
          <div className="flex items-center gap-2 text-sky-400 font-semibold border-b border-slate-800 pb-3">
            <Compass className="w-5 h-5" />
            <span>Select Reference Mission</span>
          </div>

          <div className="space-y-2">
            {missions.map((m) => {
              const isSelected = m.mission_id === selectedMissionId;
              return (
                <button
                  key={m.mission_id}
                  onClick={() => setSelectedMissionId(m.mission_id)}
                  className={`w-full text-left p-3 rounded-lg border transition-all ${
                    isSelected
                      ? 'bg-sky-950/70 border-sky-500/80 text-white shadow-md'
                      : 'bg-slate-950/50 border-slate-800/80 text-slate-300 hover:bg-slate-800/60 hover:text-white'
                  }`}
                >
                  <div className="flex items-center justify-between font-medium text-xs">
                    <span className="truncate">{m.name.replace(/\[.*\]/, '')}</span>
                    <span className="text-[10px] font-mono text-slate-400 bg-slate-800 px-1.5 py-0.5 rounded">
                      {m.total_duration_sec}s
                    </span>
                  </div>
                  <div className="text-[11px] text-slate-400 mt-1 line-clamp-2">
                    {m.description.replace(/^SYNTHETIC \/ PROTOTYPE SCENARIO:\s*/, '')}
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Right Column: Active Mission Configuration & Simulation Execution */}
        <div className="lg:col-span-2 bg-slate-900/80 border border-slate-800 rounded-xl p-5 shadow-lg space-y-5">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div>
              <h2 className="text-base font-semibold text-slate-100 flex items-center gap-2">
                <span>{selectedMission?.name || selectedMissionId}</span>
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">{selectedMission?.description}</p>
            </div>
            <span className="text-xs font-mono px-2 py-1 rounded bg-slate-800 border border-slate-700 text-sky-400">
              {selectedMission?.phase_count || 0} Phases • {selectedMission?.total_duration_sec || 0}s Total
            </span>
          </div>

          {/* Simulation Parameters Deck */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 bg-slate-950/60 border border-slate-800 p-3.5 rounded-lg text-xs">
            <div>
              <label className="text-slate-400 block mb-1">Sampling Frequency</label>
              <select
                value={rateHz}
                onChange={(e) => setRateHz(parseInt(e.target.value, 10))}
                className="w-full bg-slate-900 border border-slate-700 rounded px-2.5 py-1.5 text-slate-100 focus:outline-none focus:border-sky-500"
              >
                <option value={10}>10 Hz (Standard Aviation Telemetry)</option>
                <option value={20}>20 Hz (High Frequency Dynamics)</option>
                <option value={50}>50 Hz (Transient Burst Rate)</option>
              </select>
            </div>

            <div>
              <label className="text-slate-400 block mb-1">Deterministic Noise Seed</label>
              <input
                type="number"
                value={seed}
                onChange={(e) => setSeed(parseInt(e.target.value, 10) || 42)}
                className="w-full bg-slate-900 border border-slate-700 rounded px-2.5 py-1.5 text-slate-100 focus:outline-none focus:border-sky-500 font-mono"
              />
            </div>

            <div className="flex items-end">
              <button
                onClick={handleSimulate}
                disabled={isSimulating}
                className="w-full py-2 px-4 rounded-lg bg-sky-600 hover:bg-sky-500 text-white font-medium flex items-center justify-center gap-2 transition-colors shadow-md disabled:opacity-50"
              >
                {isSimulating ? (
                  <>
                    <RotateCcw className="w-4 h-4 animate-spin" /> Simulating...
                  </>
                ) : (
                  <>
                    <Play className="w-4 h-4 fill-current" /> Run Simulation
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Results Summary Card */}
          {simResult && (
            <div className="space-y-4 pt-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-emerald-400 flex items-center gap-1.5">
                  <CheckCircle className="w-4 h-4" /> Simulation Completed ({simResult.run_id})
                </span>

                <button
                  onClick={handleQueueForReplay}
                  className="px-3 py-1 text-xs font-medium rounded-lg bg-amber-600 hover:bg-amber-500 text-white flex items-center gap-1.5 shadow transition-colors"
                >
                  <FileCheck className="w-3.5 h-3.5" /> Queue for Flight Replay
                </button>
              </div>

              {/* Key Metrics Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                <div className="bg-slate-950/80 border border-slate-800 p-3 rounded-lg">
                  <div className="text-slate-400 flex items-center gap-1">
                    <Droplets className="w-3.5 h-3.5 text-sky-400" /> Fuel Consumed
                  </div>
                  <div className="text-base font-bold text-sky-300 font-mono mt-1">
                    {simResult.summary.fuel_consumed_liters.toFixed(3)} L
                  </div>
                  <div className="text-[10px] text-slate-500">
                    {simResult.summary.fuel_mass_kg.toFixed(3)} kg (ρ=0.72)
                  </div>
                </div>

                <div className="bg-slate-950/80 border border-slate-800 p-3 rounded-lg">
                  <div className="text-slate-400 flex items-center gap-1">
                    <Flame className="w-3.5 h-3.5 text-amber-400" /> Peak Thermal CHT / EGT
                  </div>
                  <div className="text-base font-bold text-amber-300 font-mono mt-1">
                    {simResult.summary.max_cht_c.toFixed(1)}° / {simResult.summary.max_egt_c.toFixed(1)}°
                  </div>
                  <div className="text-[10px] text-slate-500">Maximum cylinder values</div>
                </div>

                <div className="bg-slate-950/80 border border-slate-800 p-3 rounded-lg">
                  <div className="text-slate-400 flex items-center gap-1">
                    <Activity className="w-3.5 h-3.5 text-emerald-400" /> Min Oil Pressure
                  </div>
                  <div className="text-base font-bold text-emerald-300 font-mono mt-1">
                    {simResult.summary.min_oil_pressure_bar.toFixed(2)} bar
                  </div>
                  <div className="text-[10px] text-slate-500">
                    Oil Temp: {simResult.summary.max_oil_temp_c.toFixed(1)}°C
                  </div>
                </div>

                <div className="bg-slate-950/80 border border-slate-800 p-3 rounded-lg">
                  <div className="text-slate-400 flex items-center gap-1">
                    <Layers className="w-3.5 h-3.5 text-purple-400" /> Peak Vib / Max Alt
                  </div>
                  <div className="text-base font-bold text-purple-300 font-mono mt-1">
                    {simResult.summary.peak_vibration_rms.toFixed(2)} g / {simResult.summary.max_altitude_m.toFixed(0)}m
                  </div>
                  <div className="text-[10px] text-slate-500">{simResult.frame_count} total frames</div>
                </div>
              </div>

              {/* Phase Breakdown Table */}
              <div className="space-y-2 pt-2">
                <span className="text-xs font-semibold text-slate-300">Phase Breakdown</span>
                <div className="border border-slate-800 rounded-lg overflow-x-auto">
                  <table className="w-full text-[11px] text-left">
                    <thead className="bg-slate-950 text-slate-400 border-b border-slate-800">
                      <tr>
                        <th className="p-2">Phase ID</th>
                        <th className="p-2">Type</th>
                        <th className="p-2">Start</th>
                        <th className="p-2">Duration</th>
                        <th className="p-2">Fuel (L)</th>
                        <th className="p-2">Avg RPM</th>
                        <th className="p-2">Max CHT</th>
                        <th className="p-2">Max EGT</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60 font-mono text-slate-300">
                      {simResult.phase_summaries.map((ps) => (
                        <tr key={ps.phase_id} className="hover:bg-slate-800/40">
                          <td className="p-2 font-sans font-medium text-slate-200">{ps.phase_id}</td>
                          <td className="p-2 text-sky-400">{ps.phase_type}</td>
                          <td className="p-2">{ps.start_time_sec.toFixed(1)}s</td>
                          <td className="p-2">{ps.duration_sec.toFixed(1)}s</td>
                          <td className="p-2 text-sky-300">{ps.fuel_burned_liters.toFixed(3)}</td>
                          <td className="p-2">{ps.avg_rpm.toFixed(0)}</td>
                          <td className="p-2">{ps.max_cht_c.toFixed(1)}°</td>
                          <td className="p-2">{ps.max_egt_c.toFixed(1)}°</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
