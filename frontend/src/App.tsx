import React, { useEffect } from 'react';
import { useAppStore } from './stores/useAppStore';
import { ErrorBoundary } from './components/common/ErrorBoundary';
import { Header } from './components/layout/Header';
import { Sidebar } from './components/layout/Sidebar';
import { Footer } from './components/layout/Footer';
import { PageContainer } from './components/common/PageContainer';
import { OverviewView } from './features/overview/OverviewView';
import { DigitalTwin3DView } from './features/twin/DigitalTwin3DView';
import { DiagnosticsView } from './features/diagnostics/DiagnosticsView';
import { MissionSimulationView } from './features/simulation/MissionSimulationView';
import { ConfigView } from './features/config/ConfigView';
import { ErrorState } from './components/common/ErrorState';

export const App: React.FC = () => {
  const { activeTab, checkBackendHealth, errorMessage, clearError } = useAppStore();

  useEffect(() => {
    // Initial health check against backend API on mount
    checkBackendHealth();
  }, [checkBackendHealth]);

  const renderActiveTabContent = () => {
    switch (activeTab) {
      case 'overview':
        return (
          <PageContainer
            title="AeroTwin Ground Station"
            subtitle="Real-time MALE UAV Aero-Piston Engine Health Monitoring Foundation"
          >
            <OverviewView />
          </PageContainer>
        );

      case 'twin':
        return (
          <PageContainer
            title="3D Digital Twin"
            subtitle="Generic 4-Cylinder Horizontally-Opposed Turbocharged Aero-Piston Engine Visualization"
          >
            <DigitalTwin3DView />
          </PageContainer>
        );

      case 'diagnostics':
        return (
          <PageContainer
            title="AI Diagnostics & Prognostics Suite"
            subtitle="Isolation Forest Anomaly Scoring, XGBoost Multi-Class Fault Classification & Degradation RUL"
          >
            <DiagnosticsView />
          </PageContainer>
        );

      case 'simulation':
        return (
          <PageContainer
            title="Mission Simulation & Flight Replay"
            subtitle="Deterministic UAV Flight Profiles, Mathematical Transitions, and Replay Deck"
          >
            <MissionSimulationView />
          </PageContainer>
        );

      case 'config':
        return (
          <PageContainer
            title="Architecture & System Settings"
            subtitle="Runtime Configuration, Clean Architecture Boundaries, and Telemetry Rates"
          >
            <ConfigView />
          </PageContainer>
        );

      default:
        return null;
    }
  };

  return (
    <ErrorBoundary>
      <div className="min-h-screen bg-[#0a0d14] text-slate-100 flex flex-col antialiased">
        {/* Top Header */}
        <Header />

        {/* Global Connection Warning Banner if offline */}
        {errorMessage && (
          <div className="bg-amber-950/40 border-b border-amber-800/50 px-6 py-2">
            <ErrorState
              title="Backend Telemetry Bus Disconnected"
              message={`${errorMessage}. Ensure the FastAPI server is running on port 8000.`}
              onRetry={() => {
                clearError();
                checkBackendHealth();
              }}
            />
          </div>
        )}

        {/* Body Layout: Sidebar + Main Content */}
        <div className="flex-1 flex overflow-hidden">
          <Sidebar />
          <main className="flex-1 overflow-y-auto bg-[#0a0d14]">
            {renderActiveTabContent()}
          </main>
        </div>

        {/* Tactical Footer */}
        <Footer />
      </div>
    </ErrorBoundary>
  );
};

export default App;
