import { ReactNode } from 'react';

export interface HorizontalBarDatum {
  label: string;
  value: number;
  colorClass?: string;
  suffix?: ReactNode;
}

export function HorizontalBarChart({ data, emptyLabel = '暂无统计数据' }: { data: HorizontalBarDatum[]; emptyLabel?: string }) {
  const max = Math.max(...data.map((item) => item.value), 0);
  if (data.length === 0 || max === 0) {
    return <p className="rounded-lg bg-zinc-50 p-4 text-sm text-zinc-500">{emptyLabel}</p>;
  }

  return (
    <div className="space-y-3">
      {data.map((item) => {
        const width = max > 0 ? Math.max(4, Math.round((item.value / max) * 100)) : 0;
        return (
          <div key={item.label}>
            <div className="mb-1 flex items-center justify-between gap-3 text-sm">
              <span className="truncate text-zinc-600">{item.label}</span>
              <span className="flex shrink-0 items-center gap-2 font-medium text-zinc-900">
                {item.suffix}
                {item.value}
              </span>
            </div>
            <div className="h-2 overflow-hidden rounded-md bg-zinc-100" title={`${item.label}: ${item.value}`}>
              <div className={`h-full rounded-md ${item.colorClass ?? 'bg-emerald-600'}`} style={{ width: `${width}%` }} />
            </div>
          </div>
        );
      })}
    </div>
  );
}
