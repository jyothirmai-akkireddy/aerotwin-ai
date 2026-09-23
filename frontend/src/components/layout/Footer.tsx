import React from 'react';
import { useAppStore } from '../../stores/useAppStore';

export const Footer: React.FC = () => {
  const { systemInfo } = useAppStore();

  return (
    <footer className="h-8 border-t border-slate-800 bg-[#090d15] px-6 flex items-center justify-between text-[11px] font-mono text-slate-500 select-none">
      <div className="flex items-center gap-4">
        <span>AEROTWIN AI v{systemInfo?.version || '0.1.0'}</span>
        <span className="hidden sm:inline text-slate-700">•</span>
        <span className="hidden sm:inline">SIH26054</span>
      </div>

      <div className="flex items-center gap-4">
        <span className="flex items-center gap-1.5 text-slate-400">
          <span className="h-1.5 w-1.5 rounded-full bg-sky-400" />
          Rate: {systemInfo?.telemetry_rate_hz || 10} Hz (Configurable)
        </span>
        <span className="text-slate-700">•</span>
        <span className="text-emerald-500 font-semibold">MODULAR MONOLITH</span>
      </div>
    </footer>
  );
};
