import React from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';
import { Button } from './Button';

export interface ErrorStateProps {
  title?: string;
  message: string;
  requestId?: string;
  onRetry?: () => void;
  className?: string;
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  title = 'System Error Encountered',
  message,
  requestId,
  onRetry,
  className = '',
}) => {
  return (
    <div
      className={`rounded-lg border border-rose-900/60 bg-rose-950/20 p-5 text-left ${className}`}
    >
      <div className="flex items-start gap-3">
        <AlertTriangle className="h-5 w-5 text-rose-400 shrink-0 mt-0.5" />
        <div className="flex-1">
          <h4 className="text-sm font-semibold text-rose-200 tracking-wide uppercase">
            {title}
          </h4>
          <p className="text-xs text-rose-300/80 mt-1 leading-relaxed">{message}</p>
          {requestId && (
            <p className="text-[10px] font-mono text-slate-500 mt-2">
              Correlation ID: <span className="text-slate-400">{requestId}</span>
            </p>
          )}
          {onRetry && (
            <div className="mt-4">
              <Button variant="danger" size="sm" onClick={onRetry}>
                <RefreshCw className="h-3.5 w-3.5 mr-1.5" /> Retry Request
              </Button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
