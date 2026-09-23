import React from 'react';
import { Layers, Calendar, ArrowRight } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '../../components/common/Card';
import { Badge } from '../../components/common/Badge';

interface PlannedFeatureProps {
  title: string;
  phase: string;
  description: string;
  plannedCapabilities: string[];
}

export const PlannedFeatureView: React.FC<PlannedFeatureProps> = ({
  title,
  phase,
  description,
  plannedCapabilities,
}) => {
  return (
    <div className="max-w-3xl mx-auto space-y-6 pt-4">
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2.5">
            <Layers className="h-5 w-5 text-sky-400" />
            <CardTitle>{title}</CardTitle>
          </div>
          <Badge variant="accent">{phase}</Badge>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="p-4 rounded bg-slate-950/60 border border-slate-800 text-xs text-slate-300 leading-relaxed">
            {description}
          </div>

          <div>
            <h4 className="text-xs font-mono uppercase tracking-wider text-slate-400 font-semibold mb-3">
              Planned Deliverables in {phase}
            </h4>
            <div className="space-y-2">
              {plannedCapabilities.map((capability, idx) => (
                <div
                  key={idx}
                  className="flex items-start gap-2.5 text-xs text-slate-300 font-mono bg-slate-900/40 p-2.5 rounded border border-slate-850"
                >
                  <ArrowRight className="h-3.5 w-3.5 text-sky-400 shrink-0 mt-0.5" />
                  <span>{capability}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="pt-4 border-t border-slate-800/80 flex items-center justify-between text-xs text-slate-500 font-mono">
            <div className="flex items-center gap-2">
              <Calendar className="h-3.5 w-3.5 text-slate-500" />
              <span>Status: Awaiting Phase Completion Gate</span>
            </div>
            <span className="text-amber-400/90 font-semibold">NO FAKE MOCK DATA</span>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};
