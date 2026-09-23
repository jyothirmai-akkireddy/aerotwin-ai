import React, { useEffect, useRef, useCallback } from 'react';

import { ErrorBoundary } from '../../components/common/ErrorBoundary';
import { EngineScene } from './components/EngineScene';
import { TwinHud } from './components/TwinHud';
import { TwinControls } from './components/TwinControls';
import { TwinReplayControls } from './components/TwinReplayControls';
import { TwinMissionCard } from './components/TwinMissionCard';
import { TwinPhysicsCard } from './components/TwinPhysicsCard';
import { TwinMLDiagnosticsCard } from './components/TwinMLDiagnosticsCard';
import { TwinPrognosticsCard } from './components/TwinPrognosticsCard';
import { TwinDevAdapter } from './components/TwinDevAdapter';
import { WebSocketClient } from '../../services/websocket/WebSocketClient';
import { ClientCommand } from '../../services/websocket/types';
import { useTwinStore } from '../../stores/useTwinStore';

export const DigitalTwin3DView: React.FC = () => {
  const wsClientRef = useRef<WebSocketClient | null>(null);
  const {
    transportMode,
    setConnectionState,
    setFreshness,
    handleIncomingTelemetry,
    recordSequenceAnomaly,
  } = useTwinStore();

  useEffect(() => {
    console.log('🔥 DigitalTwin3DView WebSocket effect:', transportMode);
    if (transportMode === 'WEBSOCKET') {
      const client = new WebSocketClient({
        onTelemetry: (msg) => {
          handleIncomingTelemetry(msg);
        },
        onStateChange: (state) => {
          setConnectionState(state);
        },
        onFreshnessChange: (freshness) => {
          setFreshness(freshness);
        },
        onSequenceAnomaly: (type, expected, actual) => {
          recordSequenceAnomaly(type, expected, actual);
        },
      });

      wsClientRef.current = client;
      client.connect();

      return () => {
        client.disconnect();
        wsClientRef.current = null;
      };
    } else {
      if (wsClientRef.current) {
        wsClientRef.current.disconnect();
        wsClientRef.current = null;
      }
      setConnectionState('DISCONNECTED');
      setFreshness('NO_DATA');
    }
  }, [transportMode, setConnectionState, setFreshness, handleIncomingTelemetry, recordSequenceAnomaly]);

  const handleSendCommand = useCallback(
    (command: ClientCommand['command'], params?: Record<string, unknown>) => {
      wsClientRef.current?.sendCommand(command, params);
    },
    []
  );

  return (
    <div className="flex flex-col space-y-3 w-full h-full">
      {/* 3D Viewport with HUD Overlay */}
      <div className="relative w-full h-[540px] md:h-[620px] rounded-lg border border-slate-800 overflow-hidden shadow-2xl bg-slate-950">
        <ErrorBoundary>
          <EngineScene />
          <TwinHud />
        </ErrorBoundary>
      </div>

      {/* Viewport & Camera Controls */}
      <TwinControls />

      {/* Flight Replay Controls & Active Mission HUD */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-3 w-full">
        <div className="lg:col-span-2">
          <TwinReplayControls />
        </div>
        <div>
          <TwinMissionCard />
        </div>
      </div>

      {/* Diagnostics Grid: Physics Twin, AI Diagnostics, and Prognostics RUL */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-3 w-full">
        <TwinPhysicsCard />
        <TwinMLDiagnosticsCard />
        <TwinPrognosticsCard />
      </div>

      {/* Development Adapter */}
      <TwinDevAdapter onSendCommand={handleSendCommand} />
    </div>
  );
};
