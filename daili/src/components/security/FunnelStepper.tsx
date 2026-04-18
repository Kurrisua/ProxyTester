import { CheckCircle2, CircleDashed, Clock, XCircle } from 'lucide-react';
import { EXECUTION_STATUS_LABELS, SCAN_OUTCOME_LABELS } from '../../types/labels';
import { ExecutionStatus, ScanOutcome } from '../../types';

export interface FunnelStep {
  stage: string;
  funnelStage: number;
  executionStatus: ExecutionStatus;
  outcome: ScanOutcome;
  count: number;
}

const statusTone: Record<ExecutionStatus, string> = {
  planned: 'border-zinc-200 bg-white text-zinc-600',
  running: 'border-sky-200 bg-sky-50 text-sky-700',
  completed: 'border-emerald-200 bg-emerald-50 text-emerald-700',
  skipped: 'border-zinc-200 bg-zinc-50 text-zinc-600',
  error: 'border-rose-200 bg-rose-50 text-rose-700',
  timeout: 'border-amber-200 bg-amber-50 text-amber-800',
};

const outcomeIcon: Record<ScanOutcome, typeof CheckCircle2> = {
  normal: CheckCircle2,
  anomalous: XCircle,
  not_applicable: CircleDashed,
  skipped: CircleDashed,
  error: XCircle,
  timeout: Clock,
};

export function FunnelStepper({ steps }: { steps: FunnelStep[] }) {
  if (steps.length === 0) {
    return (
      <div className="rounded-lg border border-zinc-200 bg-zinc-50 p-4 text-sm text-zinc-500">
        暂无漏斗阶段记录。未检测不会被视为安全。
      </div>
    );
  }

  const ordered = [...steps].sort((a, b) => a.funnelStage - b.funnelStage || a.stage.localeCompare(b.stage));

  return (
    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
      {ordered.map((step) => {
        const Icon = outcomeIcon[step.outcome];
        return (
          <div key={`${step.funnelStage}-${step.stage}-${step.executionStatus}-${step.outcome}`} className={`rounded-lg border p-3 ${statusTone[step.executionStatus]}`}>
            <div className="flex items-start justify-between gap-3">
              <div>
                <div className="text-xs font-medium uppercase tracking-normal">阶段 {step.funnelStage}</div>
                <div className="mt-1 text-sm font-semibold">{step.stage}</div>
              </div>
              <Icon className="h-4 w-4 shrink-0" />
            </div>
            <div className="mt-3 flex flex-wrap gap-2 text-xs">
              <span>{EXECUTION_STATUS_LABELS[step.executionStatus]}</span>
              <span>{SCAN_OUTCOME_LABELS[step.outcome]}</span>
              <span>{step.count} 条</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
