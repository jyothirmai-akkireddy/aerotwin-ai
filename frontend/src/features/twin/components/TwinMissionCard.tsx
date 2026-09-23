import React from 'react';
import { useTwinStore } from '../../../stores/useTwinStore';
import { Compass, Clock, Activity } from 'lucide-react';

export const TwinMissionCard: React.FC = () => {
  const { missionContext } = useTwinStore();

  if (!missionContext) {
    return null;
  }

  const progressPercent = Math.min(100, Math.max(0, missionContext.mission_progress_pct));
  const phaseProgressPercent =
    missionContext.phase_duration_sec > 0
      ? Math.min(
          100,
          Math.max(0, (missionContext.phase_elapsed_sec / missionContext.phase_duration_sec) * 100)
        )
      : 0;

  return (
    <div className="bg-slate-900/90 backdrop-blur border border-sky-500/40 rounded-lg p-3 text-slate-100 shadow-lg text-xs space-y-2">
      <div className="flex items-center justify-between border-b border-slate-800 pb-2">
        <div className="flex items-center gap-1.5 font-semibold text-sky-400">
          <Compass className="w-4 h-4" />
          <span>ACTIVE MISSION</span>
        </div>
        <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-sky-950/70 border border-sky-800/60 text-sky-300">
          {missionContext.mission_id}
        </span>
      </div>

      <div className="space-y-1">
        <div className="flex items-center justify-between text-slate-300">
          <span className="font-medium text-slate-400">Current Phase:</span>
          <span className="font-semibold text-amber-300 flex items-center gap-1">
            <Activity className="w-3 h-3 text-amber-400 animate-pulse" />
            {missionContext.current_phase_type} ({missionContext.current_phase_id})
          </span>
        </div>

        {/* Phase Progress Bar */}
        <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
          <div
            className="bg-amber-400 h-full transition-all duration-200"
            style={{ width: `${phaseProgressPercent}%` }}
          />
        </div>
        <div className="flex justify-between text-[10px] text-slate-400">
          <span>Phase: {missionContext.phase_elapsed_sec.toFixed(1)}s</span>
          <span>{missionContext.phase_duration_sec.toFixed(1)}s</span>
        </div>
      </div>

      <div className="space-y-1 pt-1 border-t border-slate-800/80">
        <div className="flex items-center justify-between text-slate-300">
          <span className="text-slate-400 flex items-center gap-1">
            <Clock className="w-3 h-3 text-sky-400" />
            Mission Time:
          </span>
          <span className="font-mono text-slate-200">
            {missionContext.mission_elapsed_sec.toFixed(1)}s / {missionContext.total_duration_sec.toFixed(1)}s
          </span>
        </div>

        {/* Total Mission Progress Bar */}
        <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
          <div
            className="bg-sky-500 h-full transition-all duration-200"
            style={{ width: `${progressPercent}%` }}
          />
        </div>
        <div className="text-right text-[10px] text-sky-400 font-mono">
          {progressPercent.toFixed(1)}% Completed
        </div>
      </div>
    </div>
  );
};
