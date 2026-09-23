import React from 'react';

export interface LoadingStateProps {
  message?: string;
  subtext?: string;
  className?: string;
}

export const LoadingState: React.FC<LoadingStateProps> = ({
  message = 'Loading system state...',
  subtext = 'Synchronizing with ground telemetry bus',
  className = '',
}) => {
  return (
    <div className={`flex flex-col items-center justify-center p-8 text-center ${className}`}>
      <div className="relative flex h-10 w-10 mb-4">
        <div className="animate-spin rounded-full h-10 w-10 border-2 border-slate-700 border-t-sky-500" />
      </div>
      <p className="text-sm font-medium text-slate-200">{message}</p>
      {subtext && <p className="text-xs text-slate-500 font-mono mt-1">{subtext}</p>}
    </div>
  );
};
