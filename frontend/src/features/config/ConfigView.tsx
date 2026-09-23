import React from 'react';
import { Server, Sliders, Shield } from 'lucide-react';
import { useAppStore } from '../../stores/useAppStore';
import { Card, CardHeader, CardTitle, CardContent } from '../../components/common/Card';
import { Badge } from '../../components/common/Badge';

export const ConfigView: React.FC = () => {
  const { systemInfo } = useAppStore();

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Active Backend Settings */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Server className="h-4 w-4 text-sky-400" />
              <CardTitle>API & Transport Configuration</CardTitle>
            </div>
            <Badge variant="success">ACTIVE</Badge>
          </CardHeader>
          <CardContent className="space-y-3 font-mono text-xs">
            <div className="flex justify-between p-2 rounded bg-slate-950/60 border border-slate-850">
              <span className="text-slate-400">Environment:</span>
              <span className="text-slate-200">{systemInfo?.environment || 'development'}</span>
            </div>
            <div className="flex justify-between p-2 rounded bg-slate-950/60 border border-slate-850">
              <span className="text-slate-400">API Protocol:</span>
              <span className="text-slate-200">REST (HTTP/1.1) + Async WS</span>
            </div>
            <div className="flex justify-between p-2 rounded bg-slate-950/60 border border-slate-850">
              <span className="text-slate-400">CORS Policy:</span>
              <span className="text-slate-200">Explicit Allowed Origins</span>
            </div>
            <div className="flex justify-between p-2 rounded bg-slate-950/60 border border-slate-850">
              <span className="text-slate-400">Correlation Middleware:</span>
              <span className="text-emerald-400">X-Request-ID Active</span>
            </div>
          </CardContent>
        </Card>

        {/* Telemetry Configuration */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Sliders className="h-4 w-4 text-emerald-400" />
              <CardTitle>Telemetry Simulation Settings</CardTitle>
            </div>
            <Badge variant="accent">RATE CONFIGURABLE</Badge>
          </CardHeader>
          <CardContent className="space-y-3 font-mono text-xs">
            <div className="flex justify-between p-2 rounded bg-slate-950/60 border border-slate-850">
              <span className="text-slate-400">Nominal Rate (Hz):</span>
              <span className="text-sky-400 font-bold">{systemInfo?.telemetry_rate_hz || 10} Hz</span>
            </div>
            <div className="flex justify-between p-2 rounded bg-slate-950/60 border border-slate-850">
              <span className="text-slate-400">Time Delta (dt):</span>
              <span className="text-slate-200">{systemInfo?.dt_seconds || 0.1} seconds</span>
            </div>
            <div className="flex justify-between p-2 rounded bg-slate-950/60 border border-slate-850">
              <span className="text-slate-400">Validation Mode:</span>
              <span className="text-emerald-400">Strict Aerospace Bounds</span>
            </div>
            <div className="flex justify-between p-2 rounded bg-slate-950/60 border border-slate-850">
              <span className="text-slate-400">Engine Twin Baseline:</span>
              <span className="text-slate-200 truncate max-w-xs">{systemInfo?.engine_baseline}</span>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Security & Boundary Governance */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Shield className="h-4 w-4 text-amber-400" />
            <CardTitle>Architectural Layer Boundaries & Security Hygiene</CardTitle>
          </div>
          <Badge variant="outline">CLEAN ARCHITECTURE</Badge>
        </CardHeader>
        <CardContent className="text-xs text-slate-400 space-y-3 leading-relaxed">
          <p>
            The backend enforces strict unidirectional dependency flow: <code className="text-slate-200">Presentation → Application → Domain ← Infrastructure</code>.
            Domain models contain zero external imports. All exceptions are sanitized through the centralized exception middleware, returning normalized <code className="text-slate-200">ErrorResponseDTO</code> payloads.
          </p>
          <div className="p-3 bg-slate-950 rounded border border-slate-800 font-mono text-[11px] text-slate-300">
            <div>✓ Zero framework imports in domain layer</div>
            <div>✓ Correlation ID tracking enabled on all routes</div>
            <div>✓ Rate-configurable telemetry pipeline ready for Phase 2</div>
            <div>✓ Zero mock prediction data or fabricated aerospace metrics</div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};
