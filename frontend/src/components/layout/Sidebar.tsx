import React from 'react';
import {
  Layers,
  Cpu,
  ShieldAlert,
  Sliders,
  Settings,
} from 'lucide-react';
import { ActiveTab, useAppStore } from '../../stores/useAppStore';

interface NavItem {
  id: ActiveTab;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
}

export const Sidebar: React.FC = () => {
  const { activeTab, setActiveTab } = useAppStore();

  const navItems: NavItem[] = [
    { id: 'overview', label: 'Ground Station', icon: Layers },
    { id: 'twin', label: '3D Digital Twin', icon: Cpu },
    { id: 'diagnostics', label: 'AI Diagnostics & Prognostics', icon: ShieldAlert },
    { id: 'simulation', label: 'Mission Sim & Replay', icon: Sliders },
    { id: 'config', label: 'Architecture & System', icon: Settings },
  ];

  return (
    <aside className="w-60 border-r border-slate-800 bg-[#0c111c] flex flex-col shrink-0 select-none">
      <div className="p-3 text-[11px] font-mono text-slate-500 uppercase tracking-wider font-semibold">
        Platform Navigation
      </div>

      <nav className="flex-1 px-2 space-y-1">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={`w-full flex items-center px-3 py-2.5 rounded text-xs font-medium transition-colors ${
                isActive
                  ? 'bg-sky-950/60 text-sky-300 border border-sky-800/60 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/60 border border-transparent'
              }`}
            >
              <div className="flex items-center gap-2.5">
                <Icon className={`h-4 w-4 ${isActive ? 'text-sky-400' : 'text-slate-500'}`} />
                <span>{item.label}</span>
              </div>
            </button>
          );
        })}
      </nav>

      {/* Honesty Badge in Sidebar */}
      <div className="p-3 m-2 rounded bg-slate-950/60 border border-slate-800/80 text-[10px] text-slate-400 font-mono">
        <div className="text-amber-400 font-semibold mb-1 flex items-center gap-1">
          <span>PROTOTYPE NOTICE</span>
        </div>
        <p className="leading-tight text-slate-500">
          Generic aero-piston twin (Rotax 914/915 iS class). Synthetic benchmark models. Not certified for flight operations.
        </p>
      </div>
    </aside>
  );
};
