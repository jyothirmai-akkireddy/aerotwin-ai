import React from 'react';
import { AlertTriangle, Monitor, RefreshCw } from 'lucide-react';
import { useTwinStore } from '../../../stores/useTwinStore';
import { Card } from '../../../components/common/Card';
import { Button } from '../../../components/common/Button';

interface WebGLFallbackProps {
  errorMessage?: string;
}

export const WebGLFallback: React.FC<WebGLFallbackProps> = ({ errorMessage }) => {
  const { telemetry } = useTwinStore();

  return (
    <div className="w-full h-full flex flex-col items-center justify-center p-6 bg-slate-950 text-slate-100 rounded-lg border border-slate-800">
      <Card className="max-w-xl w-full p-6 text-center space-y-4 border-amber-500/30 bg-slate-900/90 shadow-2xl">
        <div className="flex justify-center">
          <div className="p-3 bg-amber-500/10 rounded-full border border-amber-500/30 text-amber-400">
            <AlertTriangle className="w-8 h-8" />
          </div>
        </div>

        <div>
          <h3 className="text-lg font-bold text-slate-100">3D WebGL Acceleration Unavailable</h3>
          <p className="text-xs text-slate-400 mt-1">
            {errorMessage || 'Your browser or graphical environment does not support WebGL hardware rendering.'}
          </p>
        </div>

        <div className="bg-slate-950/80 p-4 rounded-md border border-slate-800 text-left text-xs space-y-2">
          <div className="flex items-center text-slate-300 font-semibold mb-1">
            <Monitor className="w-3.5 h-3.5 mr-1.5 text-blue-400" />
            Active Engine Telemetry (Text Mode)
          </div>
          <div className="grid grid-cols-2 gap-2 text-slate-300">
            <div>Engine State: <span className="font-mono text-emerald-400 font-bold">{telemetry.engineState}</span></div>
            <div>RPM: <span className="font-mono text-cyan-400 font-bold">{telemetry.rpm.toFixed(0)}</span></div>
            <div>Throttle: <span className="font-mono text-slate-200">{telemetry.throttle.toFixed(1)}%</span></div>
            <div>Manifold Press: <span className="font-mono text-slate-200">{telemetry.manifoldPressure.toFixed(2)} inHg</span></div>
            <div>Oil Temp: <span className="font-mono text-amber-400">{telemetry.oilTemperature.toFixed(1)}°C</span></div>
            <div>Oil Press: <span className="font-mono text-emerald-400">{telemetry.oilPressure.toFixed(2)} bar</span></div>
            <div className="col-span-2">
              CHT (1-4): <span className="font-mono text-slate-300">[{telemetry.cht.map(t => `${t.toFixed(1)}°C`).join(', ')}]</span>
            </div>
          </div>
        </div>

        <div className="pt-2 flex justify-center space-x-3">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => window.location.reload()}
            className="flex items-center space-x-1.5"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Retry WebGL Initialization</span>
          </Button>
        </div>
      </Card>
    </div>
  );
};
