export interface FunnelDatum {
  label: string;
  total: number;
  anomalous: number;
  skipped: number;
  notApplicable: number;
  error: number;
}

export function FunnelChart({ data, emptyLabel = '暂无漏斗记录' }: { data: FunnelDatum[]; emptyLabel?: string }) {
  const max = Math.max(...data.map((item) => item.total), 0);
  if (data.length === 0 || max === 0) {
    return <p className="rounded-lg bg-zinc-50 p-4 text-sm text-zinc-500">{emptyLabel}</p>;
  }

  return (
    <div className="space-y-3">
      {data.map((item) => {
        const width = Math.max(12, Math.round((item.total / max) * 100));
        return (
          <div key={item.label} className="grid gap-2 sm:grid-cols-[8rem_1fr] sm:items-center">
            <div className="min-w-0 text-sm text-zinc-600">
              <div className="truncate font-medium text-zinc-800">{item.label}</div>
              <div className="text-xs text-zinc-500">{item.total} 条记录</div>
            </div>
            <div>
              <div className="h-8 overflow-hidden rounded-md bg-zinc-100" title={`${item.label}: ${item.total}`}>
                <div className="flex h-full rounded-md" style={{ width: `${width}%` }}>
                  <Segment value={item.anomalous} total={item.total} className="bg-rose-500" label="异常" />
                  <Segment value={item.error} total={item.total} className="bg-zinc-700" label="错误" />
                  <Segment value={item.skipped} total={item.total} className="bg-amber-400" label="跳过" />
                  <Segment value={item.notApplicable} total={item.total} className="bg-sky-400" label="不适用" />
                  <Segment
                    value={Math.max(item.total - item.anomalous - item.error - item.skipped - item.notApplicable, 0)}
                    total={item.total}
                    className="bg-emerald-500"
                    label="正常"
                  />
                </div>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function Segment({ value, total, className, label }: { value: number; total: number; className: string; label: string }) {
  if (value <= 0 || total <= 0) return null;
  return (
    <div className={className} style={{ width: `${(value / total) * 100}%` }}>
      <span className="sr-only">{`${label}: ${value}`}</span>
    </div>
  );
}
