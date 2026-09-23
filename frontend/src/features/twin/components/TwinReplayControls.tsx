import React, { useState, useEffect, useCallback } from 'react';
import { useTwinStore } from '../../../stores/useTwinStore';
import {
  APPROVED_ACCELERATED_SPEEDS,
  ReplayDatasetMetadataDto,
} from '../../../services/websocket/types';
import {
  Play,
  Pause,
  RotateCcw,
  FastForward,
  Database,
  Radio,
  Clock,
  Info,
} from 'lucide-react';

export const TwinReplayControls: React.FC = () => {
  const { sourceMode, replayStatus, setSourceMode, setReplayStatus } = useTwinStore();
  const [datasets, setDatasets] = useState<ReplayDatasetMetadataDto[]>([]);
  const [selectedFile, setSelectedFile] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const fetchDatasets = useCallback(async () => {
    try {
      const resp = await fetch('http://localhost:8000/api/v1/replay/datasets');
      if (resp.ok) {
        const data: ReplayDatasetMetadataDto[] = await resp.json();
        setDatasets(data);
        if (data.length > 0 && !selectedFile) {
          setSelectedFile(data[0].filename);
        }
      }
    } catch {
      // Backend might be offline in development mode
    }
  }, [selectedFile]);

  useEffect(() => {
    fetchDatasets();
  }, [fetchDatasets]);

  const handleLoadDataset = async (filename: string) => {
    if (!filename) return;
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const resp = await fetch('http://localhost:8000/api/v1/replay/load', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filename }),
      });
      if (!resp.ok) {
        const err = await resp.json();
        throw new Error(err.detail || 'Failed to load dataset');
      }
      const status = await resp.json();
      setReplayStatus(status);
      setSelectedFile(filename);
    } catch (e: unknown) {
      setErrorMessage(e instanceof Error ? e.message : 'Error loading dataset');
    } finally {
      setIsLoading(false);
    }
  };

  const handleControl = async (action: string, target?: number | string) => {
    try {
      const resp = await fetch('http://localhost:8000/api/v1/replay/control', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action, target }),
      });
      if (resp.ok) {
        const status = await resp.json();
        setReplayStatus(status);
      }
    } catch {
      // Handled silently
    }
  };

  const handleModeSwitch = async (newMode: 'LIVE' | 'REPLAY') => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      // If switching to REPLAY and no dataset is loaded, load selected first
      if (newMode === 'REPLAY' && !replayStatus?.total_frames && selectedFile) {
        await handleLoadDataset(selectedFile);
      }

      const resp = await fetch('http://localhost:8000/api/v1/replay/mode', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode: newMode }),
      });

      if (!resp.ok) {
        const err = await resp.json();
        throw new Error(err.detail || `Failed to transition to ${newMode}`);
      }
      setSourceMode(newMode);
    } catch (e: unknown) {
      setErrorMessage(e instanceof Error ? e.message : 'Error switching source mode');
    } finally {
      setIsLoading(false);
    }
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  const isPlaying = replayStatus?.playback_state === 'PLAYING';
  const totalFrames = replayStatus?.total_frames ?? 0;
  const currentIndex = replayStatus?.current_index ?? 0;
  const elapsedSec = replayStatus?.elapsed_sim_time_sec ?? 0;
  const totalSec = replayStatus?.total_sim_time_sec ?? 0;
  const progressPct = replayStatus?.progress_pct ?? 0;

  return (
    <div className="bg-slate-900/95 backdrop-blur border border-slate-700/80 rounded-lg p-3 text-slate-100 shadow-xl space-y-2.5 text-xs">
      {/* Top Banner: Source Mode Indicator & Mode Switcher */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-2">
        <div className="flex items-center gap-2">
          <span
            className={`px-2 py-0.5 rounded text-[11px] font-semibold flex items-center gap-1.5 ${
              sourceMode === 'LIVE'
                ? 'bg-emerald-950/80 border border-emerald-500/50 text-emerald-400'
                : 'bg-amber-950/80 border border-amber-500/50 text-amber-400 animate-pulse'
            }`}
          >
            <Radio className="w-3 h-3" />
            ACTIVE SOURCE: {sourceMode}
          </span>
        </div>

        <button
          onClick={() => handleModeSwitch(sourceMode === 'LIVE' ? 'REPLAY' : 'LIVE')}
          disabled={isLoading}
          className="px-2.5 py-1 text-[11px] font-medium rounded bg-slate-800 hover:bg-slate-700 border border-slate-600 transition-colors"
        >
          {sourceMode === 'LIVE' ? 'Switch to Replay Mode' : 'Switch to Live Stream'}
        </button>
      </div>

      {errorMessage && (
        <div className="text-[11px] text-rose-400 bg-rose-950/50 border border-rose-800/60 p-1.5 rounded">
          {errorMessage}
        </div>
      )}

      {/* Dataset Selector */}
      <div className="flex items-center gap-2 text-slate-300">
        <Database className="w-4 h-4 text-sky-400 shrink-0" />
        <select
          value={selectedFile}
          onChange={(e) => {
            setSelectedFile(e.target.value);
            handleLoadDataset(e.target.value);
          }}
          disabled={isLoading || datasets.length === 0}
          className="flex-1 bg-slate-800 border border-slate-700 rounded px-2 py-1 text-slate-100 focus:outline-none focus:border-sky-500 text-xs truncate"
        >
          {datasets.length === 0 && <option value="">No datasets found in storage</option>}
          {datasets.map((d) => (
            <option key={d.filename} value={d.filename}>
              {d.filename} ({d.format} • {d.total_frames} frames • {formatTime(d.duration_sec)})
            </option>
          ))}
        </select>
        <button
          onClick={fetchDatasets}
          title="Refresh datasets"
          className="p-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-slate-200"
        >
          <RotateCcw className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Replay Scrubber & Time */}
      <div className="space-y-1 bg-slate-950/60 border border-slate-800/80 rounded p-2">
        <div className="flex justify-between items-center text-[11px] text-slate-400 font-mono">
          <span className="flex items-center gap-1 text-slate-300">
            <Clock className="w-3 h-3 text-sky-400" />
            Data Time: {formatTime(elapsedSec)} / {formatTime(totalSec)}
          </span>
          <span>
            Frame: {currentIndex} / {totalFrames > 0 ? totalFrames - 1 : 0} ({progressPct.toFixed(1)}%)
          </span>
        </div>

        <input
          type="range"
          min="0"
          max={Math.max(0, totalFrames - 1)}
          value={currentIndex}
          onChange={(e) => handleControl('seek', parseInt(e.target.value, 10))}
          disabled={totalFrames <= 1}
          className="w-full accent-sky-500 h-1.5 bg-slate-800 rounded cursor-pointer"
        />

        <div className="flex items-center justify-between text-[10px] text-slate-500">
          <span>00:00</span>
          <span className="text-amber-400/90 font-medium">
            State: {replayStatus?.playback_state || 'IDLE'}
          </span>
          <span>{formatTime(totalSec)}</span>
        </div>
      </div>

      {/* Transport Buttons & Speed Multipliers */}
      <div className="flex items-center justify-between gap-2 pt-1">
        <div className="flex items-center gap-1.5">
          <button
            onClick={() => handleControl(isPlaying ? 'pause' : 'play')}
            disabled={totalFrames === 0}
            className={`px-3 py-1.5 rounded flex items-center gap-1 font-medium transition-colors ${
              isPlaying
                ? 'bg-amber-600 hover:bg-amber-500 text-white'
                : 'bg-emerald-600 hover:bg-emerald-500 text-white'
            }`}
          >
            {isPlaying ? (
              <>
                <Pause className="w-3.5 h-3.5" /> Pause
              </>
            ) : (
              <>
                <Play className="w-3.5 h-3.5" /> Play
              </>
            )}
          </button>

          <button
            onClick={() => handleControl('reset')}
            disabled={totalFrames === 0}
            title="Reset to beginning"
            className="p-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white border border-slate-700"
          >
            <RotateCcw className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* Speed Multiplier Selectors */}
        <div className="flex items-center gap-1">
          <FastForward className="w-3 h-3 text-slate-400" />
          {APPROVED_ACCELERATED_SPEEDS.map((spd) => (
            <button
              key={spd}
              onClick={() => handleControl('speed', spd)}
              className={`px-1.5 py-0.5 rounded text-[10px] font-mono transition-colors ${
                replayStatus?.playback_speed === spd &&
                replayStatus?.execution_mode !== 'OFFLINE_BATCH'
                  ? 'bg-sky-600 text-white font-bold'
                  : 'bg-slate-800 hover:bg-slate-700 text-slate-400'
              }`}
            >
              {spd}x
            </button>
          ))}
          <button
            onClick={() => handleControl('speed', 'OFFLINE_BATCH')}
            title="OFFLINE_BATCH: Unpaced execution without wall-clock pacing delay."
            className={`px-1.5 py-0.5 rounded text-[10px] font-mono transition-colors flex items-center gap-0.5 ${
              replayStatus?.execution_mode === 'OFFLINE_BATCH'
                ? 'bg-amber-600 text-white font-bold'
                : 'bg-slate-800 hover:bg-slate-700 text-slate-400'
            }`}
          >
            <span>BATCH</span>
            <Info className="w-2.5 h-2.5 opacity-70" />
          </button>
        </div>
      </div>
    </div>
  );
};
