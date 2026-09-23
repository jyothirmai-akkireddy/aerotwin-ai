/**
 * Development Adapter component supporting both Live WebSocket command dispatch
 * and isolated offline Manual Simulation stepping/overrides.
 */

import React, { useState } from 'react';
import { Play, Pause, RotateCcw, Sliders, ChevronDown, ChevronUp, Cpu, Radio } from 'lucide-react';
import { useTwinStore } from '../../../stores/useTwinStore';
import { apiClient } from '../../../api/client';
import { Button } from '../../../components/common/Button';
import { ClientCommand } from '../../../services/websocket/types';

interface StepResponseFrame {
  sequence_id: number;
  timestamp: number;
  rpm: number;
  throttle_position: number;
  manifold_pressure: number;
  fuel_flow: number;
  cht: [number, number, number, number];
  egt: [number, number, number, number];
  oil_temperature: number;
  oil_pressure: number;
  vibration_rms: number;
  battery_voltage: number;
  quality_flag: string;
}

export interface TwinDevAdapterProps {
  onSendCommand?: (
    command: ClientCommand['command'],
    params?: Record<string, unknown>
  ) => void;
}

export const TwinDevAdapter: React.FC<TwinDevAdapterProps> = ({ onSendCommand }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [isStepping, setIsStepping] = useState(false);
  const [isPausedBackend, setIsPausedBackend] = useState(false);

  const {
    telemetry,
    updateFromTelemetry,
    resetToNominal,
    transportMode,
    setTransportMode,
    connectionState,
  } = useTwinStore();

  const handleStepSimulation = async () => {
    setIsStepping(true);
    try {
      const frame = await apiClient.post<StepResponseFrame>('/api/v1/simulation/step', {
        phase_name: 'DEV_ADAPTER_STEP',
        target_throttle_pct: telemetry.throttle,
        target_altitude_m: 1000.0,
        ignition_on: true,
      });

      if (frame) {
        updateFromTelemetry({
          rpm: frame.rpm,
          throttle: frame.throttle_position,
          engineState:
            frame.rpm > 5000
              ? 'HIGH_POWER'
              : frame.rpm > 2000
              ? 'CRUISE'
              : frame.rpm > 400
              ? 'IDLE'
              : 'OFF',
          cht: frame.cht,
          egt: frame.egt,
          oilTemperature: frame.oil_temperature,
          oilPressure: frame.oil_pressure,
          manifoldPressure: frame.manifold_pressure,
          fuelFlow: frame.fuel_flow,
          batteryVoltage: frame.battery_voltage,
          vibrationRms: frame.vibration_rms,
          qualityFlag: frame.quality_flag,
          timestamp: frame.timestamp,
        });
      }
    } catch {
      updateFromTelemetry({
        rpm: Math.min(5800, telemetry.rpm + 150),
        timestamp: Date.now() / 1000,
      });
    } finally {
      setIsStepping(false);
    }
  };

  const handleWsPauseResume = () => {
    if (isPausedBackend) {
      onSendCommand?.('resume');
      setIsPausedBackend(false);
    } else {
      onSendCommand?.('pause');
      setIsPausedBackend(true);
    }
  };

  const handleWsReset = () => {
    onSendCommand?.('reset');
    resetToNominal();
  };

  const handleWsScenario = (scenario: string) => {
    onSendCommand?.('set_scenario', { phase_name: scenario });
  };

  const setManualPreset = (presetName: string) => {
    switch (presetName) {
      case 'COLD_OFF':
        updateFromTelemetry({
          rpm: 0.0,
          throttle: 0.0,
          engineState: 'OFF',
          cht: [35.0, 35.0, 35.0, 35.0],
          egt: [50.0, 50.0, 50.0, 50.0],
          oilTemperature: 30.0,
          oilPressure: 0.0,
          vibrationRms: 0.05,
        });
        break;
      case 'IDLE_WARMUP':
        updateFromTelemetry({
          rpm: 1400.0,
          throttle: 15.0,
          engineState: 'IDLE',
          cht: [75.0, 72.0, 78.0, 74.0],
          egt: [610.0, 605.0, 615.0, 608.0],
          oilTemperature: 65.0,
          oilPressure: 2.8,
          vibrationRms: 0.75,
        });
        break;
      case 'CRUISE_NOMINAL':
        updateFromTelemetry({
          rpm: 2400.0,
          throttle: 45.0,
          engineState: 'CRUISE',
          cht: [95.0, 92.5, 98.0, 94.0],
          egt: [720.0, 715.0, 730.0, 722.0],
          oilTemperature: 85.0,
          oilPressure: 3.8,
          vibrationRms: 1.15,
        });
        break;
      case 'TAKEOFF_FULL':
        updateFromTelemetry({
          rpm: 5500.0,
          throttle: 100.0,
          engineState: 'HIGH_POWER',
          cht: [135.0, 130.0, 140.0, 132.0],
          egt: [860.0, 850.0, 875.0, 855.0],
          oilTemperature: 110.0,
          oilPressure: 4.8,
          vibrationRms: 2.8,
        });
        break;
      case 'THERMAL_HOT_CYL3':
        updateFromTelemetry({
          rpm: 3800.0,
          throttle: 65.0,
          engineState: 'CRUISE',
          cht: [105.0, 102.0, 175.0, 108.0],
          egt: [780.0, 760.0, 910.0, 775.0],
          oilTemperature: 98.0,
          oilPressure: 3.5,
          vibrationRms: 2.1,
        });
        break;
    }
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg overflow-hidden shadow-lg text-xs">
      {/* Header Accordion Bar */}
      <div
        className="flex items-center justify-between px-4 py-2.5 bg-slate-950/60 cursor-pointer hover:bg-slate-800/50 transition-colors"
        onClick={() => setIsOpen(!isOpen)}
      >
        <div className="flex items-center space-x-2">
          <Cpu className="w-4 h-4 text-sky-400" />
          <span className="font-semibold text-slate-200 uppercase tracking-wider">
            Development Adapter (Phase 4 Transport & Simulation Bridge)
          </span>
          <span
            className={`px-2 py-0.5 rounded text-[10px] font-mono ${
              transportMode === 'WEBSOCKET'
                ? 'bg-emerald-500/20 text-emerald-300'
                : 'bg-amber-500/20 text-amber-300'
            }`}
          >
            {transportMode === 'WEBSOCKET' ? 'LIVE WEBSOCKET' : 'MANUAL OVERRIDE'}
          </span>
        </div>

        <div className="flex items-center space-x-2">
          <span className="text-[11px] text-slate-400">
            {isOpen ? 'Collapse Panel' : 'Expand Controls'}
          </span>
          {isOpen ? (
            <ChevronUp className="w-4 h-4 text-slate-400" />
          ) : (
            <ChevronDown className="w-4 h-4 text-slate-400" />
          )}
        </div>
      </div>

      {/* Expanded Controls Body */}
      {isOpen && (
        <div className="p-4 space-y-4 border-t border-slate-800">
          {/* Transport Mode Toggle */}
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <span className="text-slate-300 font-medium">Authoritative Transport Mode:</span>
            <div className="flex space-x-2">
              <Button
                size="sm"
                variant={transportMode === 'WEBSOCKET' ? 'primary' : 'outline'}
                onClick={() => setTransportMode('WEBSOCKET')}
                className="text-xs"
              >
                <Radio className="w-3 h-3 mr-1" />
                Live WebSocket Stream
              </Button>
              <Button
                size="sm"
                variant={transportMode === 'MANUAL_DEV' ? 'primary' : 'outline'}
                onClick={() => setTransportMode('MANUAL_DEV')}
                className="text-xs"
              >
                <Sliders className="w-3 h-3 mr-1" />
                Manual Dev Mode
              </Button>
            </div>
          </div>

          {/* MODE 1: LIVE WEBSOCKET CONTROL */}
          {transportMode === 'WEBSOCKET' ? (
            <div className="space-y-3">
              <div className="flex items-center justify-between text-slate-400 text-[11px]">
                <span>
                  Status:{' '}
                  <strong className="text-slate-200">{connectionState}</strong> | Streaming at nominal 10 Hz
                </span>
                <div className="flex space-x-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={handleWsPauseResume}
                    className="text-xs"
                  >
                    {isPausedBackend ? (
                      <>
                        <Play className="w-3 h-3 mr-1 text-emerald-400" />
                        Resume Stream
                      </>
                    ) : (
                      <>
                        <Pause className="w-3 h-3 mr-1 text-amber-400" />
                        Pause Stream
                      </>
                    )}
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={handleWsReset}
                    className="text-xs"
                  >
                    <RotateCcw className="w-3 h-3 mr-1 text-sky-400" />
                    Reset Simulator
                  </Button>
                </div>
              </div>

              {/* Scenario Dispatch */}
              <div>
                <span className="text-slate-400 block mb-1.5 font-medium text-[11px]">
                  Dispatch Simulation Scenario to Backend:
                </span>
                <div className="flex flex-wrap gap-2">
                  {[
                    { label: 'Idle Warmup', id: 'IDLE_WARMUP' },
                    { label: 'Standard Cruise', id: 'STANDARD_SURVEILLANCE' },
                    { label: 'Takeoff Climb', id: 'TAKEOFF_CLIMB' },
                    { label: 'High Altitude', id: 'HIGH_ALTITUDE_LOITER' },
                    { label: 'Rapid Descent', id: 'RAPID_DESCENT' },
                  ].map((sc) => (
                    <Button
                      key={sc.id}
                      size="sm"
                      variant="outline"
                      onClick={() => handleWsScenario(sc.id)}
                      className="text-[11px] py-1 px-2.5"
                    >
                      {sc.label}
                    </Button>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            /* MODE 2: MANUAL DEV OVERRIDE */
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-amber-400 font-medium">
                  Manual Dev Mode Active: Telemetry override enabled for isolated component testing.
                </span>
                <Button
                  size="sm"
                  variant="primary"
                  onClick={handleStepSimulation}
                  disabled={isStepping}
                  className="text-xs"
                >
                  <Play className="w-3 h-3 mr-1" />
                  {isStepping ? 'Stepping...' : 'Step Simulator (REST)'}
                </Button>
              </div>

              {/* Presets */}
              <div className="flex flex-wrap gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setManualPreset('COLD_OFF')}
                  className="text-[11px]"
                >
                  Cold Engine
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setManualPreset('IDLE_WARMUP')}
                  className="text-[11px]"
                >
                  Idle Warmup
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setManualPreset('CRUISE_NOMINAL')}
                  className="text-[11px]"
                >
                  Cruise (2400 RPM)
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setManualPreset('TAKEOFF_FULL')}
                  className="text-[11px]"
                >
                  Takeoff (5500 RPM)
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setManualPreset('THERMAL_HOT_CYL3')}
                  className="text-[11px] text-rose-400 border-rose-500/40"
                >
                  Hot Spot (Cyl 3 @ 175°C)
                </Button>
              </div>

              {/* Manual Sliders */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
                <div>
                  <div className="flex justify-between text-[11px] text-slate-400 mb-1">
                    <span>RPM Override</span>
                    <span className="font-mono text-sky-400">{telemetry.rpm.toFixed(0)}</span>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="6000"
                    step="50"
                    value={telemetry.rpm}
                    onChange={(e) =>
                      updateFromTelemetry({
                        rpm: parseFloat(e.target.value),
                        engineState:
                          parseFloat(e.target.value) > 5000
                            ? 'HIGH_POWER'
                            : parseFloat(e.target.value) > 2000
                            ? 'CRUISE'
                            : parseFloat(e.target.value) > 400
                            ? 'IDLE'
                            : 'OFF',
                      })
                    }
                    className="w-full accent-sky-400"
                  />
                </div>

                <div>
                  <div className="flex justify-between text-[11px] text-slate-400 mb-1">
                    <span>Throttle (%)</span>
                    <span className="font-mono text-amber-400">
                      {telemetry.throttle.toFixed(0)}%
                    </span>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="100"
                    step="1"
                    value={telemetry.throttle}
                    onChange={(e) =>
                      updateFromTelemetry({ throttle: parseFloat(e.target.value) })
                    }
                    className="w-full accent-amber-400"
                  />
                </div>

                <div>
                  <div className="flex justify-between text-[11px] text-slate-400 mb-1">
                    <span>Cylinder 3 CHT (°C)</span>
                    <span className="font-mono text-rose-400">
                      {telemetry.cht[2].toFixed(1)}°C
                    </span>
                  </div>
                  <input
                    type="range"
                    min="40"
                    max="200"
                    step="1"
                    value={telemetry.cht[2]}
                    onChange={(e) => {
                      const val = parseFloat(e.target.value);
                      updateFromTelemetry({
                        cht: [telemetry.cht[0], telemetry.cht[1], val, telemetry.cht[3]],
                      });
                    }}
                    className="w-full accent-rose-400"
                  />
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
