import React from 'react';
import {
  Camera,
  Layers,
  Pause,
  Play,
  RotateCcw,
  Sliders,
  Tag,
  Eye,
  Thermometer,
  Box,
} from 'lucide-react';
import {
  CameraPreset,
  useTwinStore,
  VisualizationMode,
} from '../../../stores/useTwinStore';
import { Button } from '../../../components/common/Button';

export const TwinControls: React.FC = () => {
  const {
    visualizationMode,
    setVisualizationMode,
    cameraPreset,
    setCameraPreset,
    isPaused,
    togglePause,
    visualRpmMultiplier,
    setVisualRpmMultiplier,
    explodedDistance,
    setExplodedDistance,
    wireframe,
    toggleWireframe,
    showLabels,
    toggleLabels,
    resetCamera,
  } = useTwinStore();

  const modes: { id: VisualizationMode; label: string; icon: React.ReactNode }[] = [
    { id: 'NORMAL', label: 'PBR Normal', icon: <Box className="w-3.5 h-3.5 mr-1" /> },
    { id: 'THERMAL', label: 'Thermal CHT', icon: <Thermometer className="w-3.5 h-3.5 mr-1 text-amber-400" /> },
    { id: 'CUTAWAY', label: 'Cutaway', icon: <Eye className="w-3.5 h-3.5 mr-1 text-sky-400" /> },
    { id: 'EXPLODED', label: 'Exploded', icon: <Layers className="w-3.5 h-3.5 mr-1 text-purple-400" /> },
  ];

  const presets: { id: CameraPreset; label: string }[] = [
    { id: 'ISOMETRIC', label: 'Iso' },
    { id: 'FRONT', label: 'Front' },
    { id: 'TOP', label: 'Top' },
    { id: 'LEFT_BANK', label: 'Bank L' },
    { id: 'RIGHT_BANK', label: 'Bank R' },
  ];

  return (
    <div className="bg-slate-950/90 backdrop-blur-md border border-slate-800 rounded-lg p-3 space-y-3 text-xs shadow-xl">
      {/* Row 1: Mode Selection & Camera Presets */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        {/* Visualization Modes */}
        <div className="flex items-center space-x-1">
          <span className="text-slate-400 font-medium mr-1 text-[11px] flex items-center">
            <Layers className="w-3.5 h-3.5 mr-1 text-slate-400" /> Mode:
          </span>
          {modes.map((m) => (
            <button
              key={m.id}
              onClick={() => setVisualizationMode(m.id)}
              className={`flex items-center px-2.5 py-1 rounded text-xs font-medium transition-colors border ${
                visualizationMode === m.id
                  ? 'bg-sky-500 text-slate-950 border-sky-400 font-semibold'
                  : 'bg-slate-900 text-slate-300 border-slate-700 hover:border-slate-600'
              }`}
            >
              {m.icon}
              {m.label}
            </button>
          ))}
        </div>

        {/* Camera Views */}
        <div className="flex items-center space-x-1">
          <span className="text-slate-400 font-medium mr-1 text-[11px] flex items-center">
            <Camera className="w-3.5 h-3.5 mr-1 text-slate-400" /> View:
          </span>
          {presets.map((p) => (
            <button
              key={p.id}
              onClick={() => setCameraPreset(p.id)}
              className={`px-2 py-1 rounded text-xs transition-colors border ${
                cameraPreset === p.id
                  ? 'bg-slate-800 text-sky-400 border-sky-500 font-semibold'
                  : 'bg-slate-900 text-slate-400 border-slate-800 hover:border-slate-700'
              }`}
            >
              {p.label}
            </button>
          ))}
          <Button
            variant="ghost"
            size="sm"
            onClick={resetCamera}
            className="text-slate-400 hover:text-slate-200"
            title="Reset Camera View"
          >
            <RotateCcw className="w-3 h-3 mr-1" /> Reset
          </Button>
        </div>
      </div>

      {/* Row 2: Playback Controls, Speed & Exploded Slider */}
      <div className="flex flex-wrap items-center justify-between gap-3 pt-2 border-t border-slate-800/80">
        {/* Animation Playback */}
        <div className="flex items-center space-x-2">
          <button
            onClick={togglePause}
            className={`flex items-center px-2.5 py-1 rounded font-medium border text-xs ${
              isPaused
                ? 'bg-amber-500/20 text-amber-300 border-amber-500/40 hover:bg-amber-500/30'
                : 'bg-slate-900 text-slate-200 border-slate-700 hover:bg-slate-800'
            }`}
          >
            {isPaused ? <Play className="w-3 h-3 mr-1 text-amber-400" /> : <Pause className="w-3 h-3 mr-1 text-sky-400" />}
            {isPaused ? 'Resume Motion' : 'Pause'}
          </button>

          {/* Speed Multiplier */}
          <div className="flex items-center space-x-1 pl-2 border-l border-slate-800">
            <span className="text-slate-400 text-[11px]">Visual Speed:</span>
            {[0.05, 0.15, 0.5, 1.0].map((val) => (
              <button
                key={val}
                onClick={() => setVisualRpmMultiplier(val)}
                className={`px-1.5 py-0.5 rounded text-[11px] font-mono border ${
                  visualRpmMultiplier === val
                    ? 'bg-sky-950 text-sky-300 border-sky-500 font-bold'
                    : 'bg-slate-900 text-slate-400 border-slate-800 hover:border-slate-700'
                }`}
              >
                {val}x
              </button>
            ))}
          </div>
        </div>

        {/* Exploded Slider (Visible when Exploded mode is active) */}
        {visualizationMode === 'EXPLODED' && (
          <div className="flex items-center space-x-2 bg-slate-900 px-3 py-1 rounded border border-purple-500/30">
            <Sliders className="w-3 h-3 text-purple-400" />
            <span className="text-[11px] text-purple-300 font-medium">Explosion:</span>
            <input
              type="range"
              min="0"
              max="1"
              step="0.05"
              value={explodedDistance}
              onChange={(e) => setExplodedDistance(parseFloat(e.target.value))}
              className="w-24 accent-purple-500 cursor-pointer"
            />
            <span className="font-mono text-[10px] text-purple-300 w-8">
              {(explodedDistance * 100).toFixed(0)}%
            </span>
          </div>
        )}

        {/* Toggles */}
        <div className="flex items-center space-x-2">
          <button
            onClick={toggleWireframe}
            className={`px-2 py-0.5 rounded text-[11px] border ${
              wireframe
                ? 'bg-sky-950 text-sky-300 border-sky-500 font-semibold'
                : 'bg-slate-900 text-slate-400 border-slate-800'
            }`}
          >
            Wireframe
          </button>
          <button
            onClick={toggleLabels}
            className={`flex items-center px-2 py-0.5 rounded text-[11px] border ${
              showLabels
                ? 'bg-sky-950 text-sky-300 border-sky-500 font-semibold'
                : 'bg-slate-900 text-slate-400 border-slate-800'
            }`}
          >
            <Tag className="w-2.5 h-2.5 mr-1" />
            Labels
          </button>
        </div>
      </div>
    </div>
  );
};
