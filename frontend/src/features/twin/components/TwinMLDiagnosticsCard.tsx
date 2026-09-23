import React, { useState } from 'react';
import {
  BrainCircuit,
  AlertTriangle,
  CheckCircle2,
  HelpCircle,
  Clock,
  ChevronDown,
  ChevronUp,
  RefreshCw,
  Sparkles,
  ArrowUpRight,
  ArrowDownRight,
  Activity,
  Layers,
} from 'lucide-react';
import { useTwinStore } from '../../../stores/useTwinStore';
import { fetchMLCurrent } from '../../../api/ml';
import { Badge } from '../../../components/common/Badge';
import { Button } from '../../../components/common/Button';

export const TwinMLDiagnosticsCard: React.FC = () => {
  const { mlResult, setMlResult } = useTwinStore();
  const [isLoading, setIsLoading] = useState(false);
  const [showLatencies, setShowLatencies] = useState(false);
  const [showProbs, setShowProbs] = useState(false);

  const handleRefresh = async () => {
    setIsLoading(true);
    try {
      const res = await fetchMLCurrent();
      if (res) {
        setMlResult(res);
      }
    } catch (err) {
      console.error('Failed to fetch current ML diagnostic state:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const getStatusBadge = (status: string, isAnom: boolean) => {
    if (isAnom || status === 'ANOMALOUS') {
      return (
        <Badge variant="danger" className="flex items-center space-x-1 animate-pulse">
          <AlertTriangle className="w-3 h-3 mr-1" />
          <span>ANOMALY DETECTED</span>
        </Badge>
      );
    }
    return (
      <Badge variant="success" className="flex items-center space-x-1">
        <CheckCircle2 className="w-3 h-3 mr-1" />
        <span>NOMINAL FLIGHT</span>
      </Badge>
    );
  };

  const getFaultBadge = (faultClass: string, reason: string) => {
    if (faultClass === 'NORMAL') {
      return (
        <span className="px-2.5 py-1 text-xs font-semibold rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
          NORMAL
        </span>
      );
    }
    if (faultClass === 'UNKNOWN') {
      const isOOD = reason === 'OUT_OF_DISTRIBUTION';
      return (
        <span
          className={`px-2.5 py-1 text-xs font-semibold rounded border ${
            isOOD
              ? 'bg-purple-500/20 text-purple-300 border-purple-500/40'
              : 'bg-amber-500/20 text-amber-300 border-amber-500/40'
          }`}
        >
          {isOOD ? 'UNKNOWN (OUT-OF-DISTRIBUTION)' : 'UNKNOWN (LOW CONFIDENCE)'}
        </span>
      );
    }
    return (
      <span className="px-2.5 py-1 text-xs font-semibold rounded bg-rose-500/20 text-rose-300 border border-rose-500/40">
        {faultClass.replace(/_/g, ' ')}
      </span>
    );
  };

  const getDirectionIcon = (dir: string) => {
    switch (dir) {
      case 'ELEVATED':
        return <ArrowUpRight className="w-3.5 h-3.5 text-rose-400" />;
      case 'DEPRESSED':
        return <ArrowDownRight className="w-3.5 h-3.5 text-sky-400" />;
      case 'IRREGULAR':
      default:
        return <Activity className="w-3.5 h-3.5 text-amber-400" />;
    }
  };

  return (
    <div className="bg-gray-900/95 backdrop-blur border border-gray-800 rounded-lg shadow-xl p-4 text-gray-200 text-sm max-w-md w-full">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-gray-800">
        <div className="flex items-center space-x-2">
          <BrainCircuit className="w-5 h-5 text-indigo-400" />
          <h2 className="font-semibold text-gray-100 text-base">AI Diagnostics & Fault Twin</h2>
        </div>
        <div className="flex items-center space-x-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleRefresh}
            disabled={isLoading}
            className="p-1 h-7 text-xs flex items-center space-x-1"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
            <span className="hidden sm:inline">Refresh</span>
          </Button>
        </div>
      </div>

      {/* Prototype Disclaimer Notice */}
      <div className="mt-2.5 px-2.5 py-1.5 rounded bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs flex items-center space-x-2">
        <AlertTriangle className="w-3.5 h-3.5 shrink-0 text-amber-400" />
        <span className="font-medium tracking-wide">
          PROTOTYPE RESEARCH MODEL — NOT FOR CERTIFIED FLIGHT OPERATIONS
        </span>
      </div>

      {mlResult ? (
        <div className="mt-3 space-y-3.5">
          {/* Status & Timing Bar */}
          <div className="flex items-center justify-between bg-gray-800/60 px-3 py-2 rounded-md border border-gray-700/60">
            <div>{getStatusBadge(mlResult.anomaly.status, mlResult.anomaly.flag)}</div>
            <div className="flex items-center space-x-3 text-xs text-gray-400">
              <span className="flex items-center">
                <Clock className="w-3.5 h-3.5 mr-1 text-gray-400" />
                {mlResult.inference_latency_ms.toFixed(2)} ms
              </span>
              <span className="bg-gray-700/80 px-1.5 py-0.5 rounded text-[11px] font-mono text-gray-300">
                v{mlResult.feature_schema_version}
              </span>
            </div>
          </div>

          {/* Anomaly Detection Score Meter */}
          <div className="bg-gray-800/40 p-3 rounded-md border border-gray-800">
            <div className="flex justify-between items-center mb-1.5">
              <span className="text-xs font-medium text-gray-300 flex items-center">
                <Sparkles className="w-3.5 h-3.5 mr-1 text-indigo-400" />
                Anomaly Severity Score
              </span>
              <div className="text-xs font-mono">
                <span
                  className={`font-semibold ${
                    mlResult.anomaly.flag ? 'text-rose-400' : 'text-emerald-400'
                  }`}
                >
                  {(mlResult.anomaly.score * 100).toFixed(1)}%
                </span>
                <span className="text-gray-500 ml-1">
                  (τ = {(mlResult.anomaly.threshold * 100).toFixed(0)}%)
                </span>
              </div>
            </div>

            {/* Progress Track */}
            <div className="relative w-full h-2.5 bg-gray-700 rounded-full overflow-hidden">
              {/* Threshold indicator line */}
              <div
                className="absolute top-0 bottom-0 w-0.5 bg-amber-400 z-10"
                style={{ left: `${Math.min(100, mlResult.anomaly.threshold * 100)}%` }}
                title={`Threshold: ${(mlResult.anomaly.threshold * 100).toFixed(1)}%`}
              />
              <div
                className={`h-full rounded-full transition-all duration-300 ${
                  mlResult.anomaly.flag
                    ? 'bg-gradient-to-r from-amber-500 to-rose-500'
                    : 'bg-gradient-to-r from-emerald-500 to-cyan-500'
                }`}
                style={{ width: `${Math.min(100, Math.max(2, mlResult.anomaly.score * 100))}%` }}
              />
            </div>
            <div className="flex justify-between text-[10px] text-gray-400 mt-1">
              <span>0% Nominal</span>
              <span>Detector: {mlResult.anomaly.detector_name}</span>
              <span>100% Outlier</span>
            </div>
          </div>

          {/* Fault Classification Section */}
          <div className="bg-gray-800/40 p-3 rounded-md border border-gray-800">
            <div className="flex justify-between items-center mb-2">
              <span className="text-xs font-medium text-gray-300">Classified Diagnosis</span>
              <div className="flex items-center space-x-1.5">
                {getFaultBadge(mlResult.fault.fault_class, mlResult.fault.reason)}
              </div>
            </div>

            <div className="flex items-center justify-between text-xs text-gray-400 mb-2">
              <span>Confidence:</span>
              <span className="font-mono font-medium text-gray-200">
                {(mlResult.fault.confidence * 100).toFixed(1)}%
              </span>
            </div>

            {/* Toggle Class Probabilities */}
            <button
              onClick={() => setShowProbs(!showProbs)}
              className="w-full flex items-center justify-between py-1 px-1.5 text-[11px] text-indigo-400 hover:text-indigo-300 bg-gray-800/60 rounded border border-gray-700/50"
            >
              <span className="flex items-center">
                <Layers className="w-3 h-3 mr-1" />
                Softmax Class Probabilities
              </span>
              {showProbs ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
            </button>

            {showProbs && mlResult.fault.probabilities && (
              <div className="mt-2 space-y-1.5 pt-2 border-t border-gray-700/60">
                {Object.entries(mlResult.fault.probabilities).map(([cls, prob]) => (
                  <div key={cls} className="text-[11px]">
                    <div className="flex justify-between text-gray-300 mb-0.5">
                      <span>{cls.replace(/_/g, ' ')}</span>
                      <span className="font-mono">{(prob * 100).toFixed(1)}%</span>
                    </div>
                    <div className="w-full h-1.5 bg-gray-700 rounded-full overflow-hidden">
                      <div
                        className={`h-full ${
                          cls === mlResult.fault.fault_class ? 'bg-indigo-400' : 'bg-gray-500'
                        }`}
                        style={{ width: `${Math.min(100, Math.max(0, prob * 100))}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Explainability & Feature Attributions */}
          {mlResult.top_contributions && mlResult.top_contributions.length > 0 && (
            <div className="bg-gray-800/40 p-3 rounded-md border border-gray-800">
              <span className="text-xs font-medium text-gray-300 block mb-2">
                Top Diagnostic Attributions
              </span>
              <div className="space-y-1.5">
                {mlResult.top_contributions.map((c, i) => (
                  <div
                    key={i}
                    className="flex items-center justify-between bg-gray-800/80 px-2 py-1 rounded text-xs border border-gray-700/50"
                  >
                    <div className="flex items-center space-x-1.5">
                      {getDirectionIcon(c.direction)}
                      <span className="font-mono text-gray-200">{c.feature_name}</span>
                    </div>
                    <div className="flex items-center space-x-2">
                      <span className="text-[10px] text-gray-400">{c.direction}</span>
                      <span className="font-mono text-xs font-semibold text-indigo-300">
                        {(c.contribution_weight * 100).toFixed(0)}%
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Disaggregated Latency Breakdown */}
          {mlResult.disaggregated_latencies && (
            <div>
              <button
                onClick={() => setShowLatencies(!showLatencies)}
                className="w-full flex items-center justify-between text-xs text-gray-400 hover:text-gray-300 py-1"
              >
                <span className="flex items-center">
                  <Clock className="w-3 h-3 mr-1 text-gray-500" />
                  Latency Breakdown (100 ms Tick Budget)
                </span>
                {showLatencies ? (
                  <ChevronUp className="w-3.5 h-3.5" />
                ) : (
                  <ChevronDown className="w-3.5 h-3.5" />
                )}
              </button>

              {showLatencies && (
                <div className="mt-1.5 p-2 rounded bg-gray-950/80 border border-gray-800 text-[11px] font-mono grid grid-cols-2 gap-1.5 text-gray-300">
                  <div>
                    Feature Extraction:{' '}
                    <span className="text-emerald-400">
                      {mlResult.disaggregated_latencies.feature_extraction_ms?.toFixed(3)} ms
                    </span>
                  </div>
                  <div>
                    Anomaly Detection:{' '}
                    <span className="text-emerald-400">
                      {mlResult.disaggregated_latencies.anomaly_detection_ms?.toFixed(3)} ms
                    </span>
                  </div>
                  <div>
                    Fault Classification:{' '}
                    <span className="text-emerald-400">
                      {mlResult.disaggregated_latencies.fault_classification_ms?.toFixed(3)} ms
                    </span>
                  </div>
                  <div>
                    Explainability XAI:{' '}
                    <span className="text-emerald-400">
                      {mlResult.disaggregated_latencies.explainability_ms?.toFixed(3)} ms
                    </span>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      ) : (
        <div className="py-8 text-center text-gray-500 text-xs flex flex-col items-center">
          <HelpCircle className="w-8 h-8 mb-2 opacity-50 text-gray-400" />
          <span>Awaiting live telemetry or click Refresh to fetch baseline</span>
        </div>
      )}
    </div>
  );
};
