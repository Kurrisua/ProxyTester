export interface DonutDatum {
  label: string;
  value: number;
  color: string;
}

const RADIUS = 42;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

export function DonutChart({ data, emptyLabel = '暂无分布数据' }: { data: DonutDatum[]; emptyLabel?: string }) {
  const total = data.reduce((sum, item) => sum + item.value, 0);
  if (total === 0) {
    return <p className="rounded-lg bg-zinc-50 p-4 text-sm text-zinc-500">{emptyLabel}</p>;
  }

  let offset = 0;

  return (
    <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
      <svg viewBox="0 0 120 120" className="h-36 w-36 shrink-0" role="img" aria-label="分布环形图">
        <circle cx="60" cy="60" r={RADIUS} fill="none" stroke="#f4f4f5" strokeWidth="16" />
        {data.map((item) => {
          const length = (item.value / total) * CIRCUMFERENCE;
          const segment = (
            <circle
              key={item.label}
              cx="60"
              cy="60"
              r={RADIUS}
              fill="none"
              stroke={item.color}
              strokeWidth="16"
              strokeDasharray={`${length} ${CIRCUMFERENCE - length}`}
              strokeDashoffset={-offset}
              strokeLinecap="butt"
              transform="rotate(-90 60 60)"
            >
              <title>{`${item.label}: ${item.value}`}</title>
            </circle>
          );
          offset += length;
          return segment;
        })}
        <text x="60" y="56" textAnchor="middle" className="fill-zinc-900 text-lg font-bold">
          {total}
        </text>
        <text x="60" y="74" textAnchor="middle" className="fill-zinc-500 text-[10px]">
          总量
        </text>
      </svg>
      <div className="grid flex-1 gap-2">
        {data.map((item) => (
          <div key={item.label} className="flex items-center justify-between gap-3 text-sm">
            <span className="flex min-w-0 items-center gap-2 text-zinc-600">
              <span className="h-2.5 w-2.5 shrink-0 rounded-sm" style={{ backgroundColor: item.color }} />
              <span className="truncate">{item.label}</span>
            </span>
            <span className="font-medium text-zinc-900">{item.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
