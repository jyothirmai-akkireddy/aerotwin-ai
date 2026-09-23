import React from 'react';

export type SystemStatus = 'NORMAL' | 'WARNING' | 'CRITICAL' | 'OFFLINE' | 'DEGRADED';

export interface StatusIndicatorProps {
  status: SystemStatus;
  label?: string;
  showPulse?: boolean;
  className?: string;
}

export const StatusIndicator: React.FC<StatusIndicatorProps> = ({
  status,
  label,
  showPulse = true,
  className = '',
}) => {
  const statusConfig = {
    NORMAL: {
      color: 'bg-emerald-500',
      textColor: 'text-emerald-400',
      pulse: 'bg-emerald-400',
      defaultLabel: 'NORMAL',
    },
    WARNING: {
      color: 'bg-amber-500',
      textColor: 'text-amber-400',
      pulse: 'bg-amber-400',
      defaultLabel: 'WARNING',
    },
    CRITICAL: {
      color: 'bg-rose-500',
      textColor: 'text-rose-400',
      pulse: 'bg-rose-400',
      defaultLabel: 'CRITICAL',
    },
    OFFLINE: {
      color: 'bg-slate-500',
      textColor: 'text-slate-400',
      pulse: 'bg-slate-400',
      defaultLabel: 'OFFLINE',
    },
    DEGRADED: {
      color: 'bg-orange-500',
      textColor: 'text-orange-400',
      pulse: 'bg-orange-400',
      defaultLabel: 'DEGRADED',
    },
  };

  const config = statusConfig[status];
  const displayLabel = label || config.defaultLabel;

  return (
    <div className={`inline-flex items-center gap-2 font-mono text-xs ${className}`}>
      <span className="relative flex h-2.5 w-2.5">
        {showPulse && status !== 'OFFLINE' && (
          <span
            className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${config.pulse}`}
          />
        )}
        <span className={`relative inline-flex rounded-full h-2.5 w-2.5 ${config.color}`} />
      </span>
      <span className={`font-semibold tracking-wide ${config.textColor}`}>
        {displayLabel}
      </span>
    </div>
  );
};
