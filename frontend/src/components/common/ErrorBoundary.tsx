import { Component, ErrorInfo, ReactNode } from 'react';
import { AlertOctagon, RotateCcw } from 'lucide-react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Unhandled React ErrorBoundary caught an exception:', error, errorInfo);
  }

  private handleReset = () => {
    this.setState({ hasError: false, error: null });
    window.location.reload();
  };

  public render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="min-h-screen bg-[#0a0d14] text-slate-100 flex items-center justify-center p-6">
          <div className="max-w-md w-full bg-[#111726] border border-rose-900/60 rounded-lg p-6 shadow-xl text-center">
            <div className="inline-flex p-3 rounded-full bg-rose-950/60 border border-rose-800 mb-4">
              <AlertOctagon className="h-8 w-8 text-rose-500" />
            </div>
            <h2 className="text-lg font-bold text-white tracking-wide uppercase">
              Application Render Failure
            </h2>
            <p className="text-xs text-slate-400 mt-2 leading-relaxed">
              A UI rendering exception was trapped by the ground station error boundary.
            </p>
            {this.state.error && (
              <pre className="mt-4 p-3 bg-slate-950 text-rose-300 font-mono text-[11px] rounded border border-slate-800 text-left overflow-x-auto max-h-32">
                {this.state.error.message}
              </pre>
            )}
            <div className="mt-6 flex justify-center">
              <button
                onClick={this.handleReset}
                className="inline-flex items-center gap-2 px-4 py-2 bg-sky-600 hover:bg-sky-500 text-white rounded text-xs font-semibold uppercase tracking-wider transition-colors"
              >
                <RotateCcw className="h-3.5 w-3.5" /> Reload Application
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
