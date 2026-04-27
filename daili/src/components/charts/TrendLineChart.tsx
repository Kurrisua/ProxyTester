export interface TrendPoint {
  label: string;
  value: number;
  secondaryValue?: number;
}

function buildPath(points: TrendPoint[], width: number, height: number, max: number, key: 'value' | 'secondaryValue') {
  if (points.length === 0) return '';
  const step = points.length > 1 ? width / (points.length - 1) : width;
  return points
    .map((point, index) => {
      const raw = key === 'value' ? point.value : point.secondaryValue ?? 0;
      const x = index * step;
      const y = height - (raw / max) * height;
      return `${index === 0 ? 'M' : 'L'} ${x.toFixed(1)} ${y.toFixed(1)}`;
    })
    .join(' ');
}

export function TrendLineChart({ data, emptyLabel = '暂无趋势数据' }: { data: TrendPoint[]; emptyLabel?: string }) {
  const max = Math.max(...data.flatMap((item) => [item.value, item.secondaryValue ?? 0]), 0);
  if (data.length === 0 || max === 0) {
    return <p className="rounded-lg bg-zinc-50 p-4 text-sm text-zinc-500">{emptyLabel}</p>;
  }

  const width = 520;
  const height = 160;
  const primaryPath = buildPath(data, width, height, max, 'value');
  const secondaryPath = buildPath(data, width, height, max, 'secondaryValue');

  return (
    <div>
      <svg viewBox={`0 0 ${width} ${height + 28}`} className="h-56 w-full overflow-visible" role="img" aria-label="安全趋势折线图">
        {[0, 0.5, 1].map((line) => (
          <line key={line} x1="0" x2={width} y1={height * line} y2={height * line} stroke="#e4e4e7" strokeWidth="1" />
        ))}
        <path d={primaryPath} fill="none" stroke="#e11d48" strokeWidth="3" strokeLinejoin="round" strokeLinecap="round" />
        <path d={secondaryPath} fill="none" stroke="#f59e0b" strokeWidth="3" strokeLinejoin="round" strokeLinecap="round" />
        {data.map((point, index) => {
          const x = data.length > 1 ? (index * width) / (data.length - 1) : width / 2;
          const y = height - (point.value / max) * height;
          return (
            <circle key={point.label} cx={x} cy={y} r="4" fill="#e11d48">
              <title>{`${point.label}: 异常 ${point.value}, 高风险 ${point.secondaryValue ?? 0}`}</title>
            </circle>
          );
        })}
        {data.map((point, index) => {
          if (index % Math.ceil(data.length / 5) !== 0 && index !== data.length - 1) return null;
          const x = data.length > 1 ? (index * width) / (data.length - 1) : width / 2;
          return (
            <text key={`${point.label}-label`} x={x} y={height + 24} textAnchor="middle" className="fill-zinc-500 text-[10px]">
              {point.label.slice(5)}
            </text>
          );
        })}
      </svg>
      <div className="flex flex-wrap gap-4 text-xs text-zinc-600">
        <span className="flex items-center gap-2">
          <span className="h-2 w-4 rounded-sm bg-rose-600" />
          异常记录
        </span>
        <span className="flex items-center gap-2">
          <span className="h-2 w-4 rounded-sm bg-amber-500" />
          高风险记录
        </span>
      </div>
    </div>
  );
}
