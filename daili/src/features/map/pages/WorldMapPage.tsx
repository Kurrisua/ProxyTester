import { useEffect, useMemo, useState } from 'react';
import { geoEqualEarth, geoPath } from 'd3-geo';
import { feature } from 'topojson-client';
import countriesTopology from 'world-atlas/countries-110m.json';
import { AlertTriangle, ArrowDownRight, ArrowUpRight, Gauge, Globe2, MousePointer2, Radar, ShieldCheck, Signal, type LucideIcon } from 'lucide-react';
import { getSecurityGeoSummary, getSecurityOverview } from '../../../api/security';
import { ErrorState } from '../../../components/ui/ErrorState';
import { LoadingState } from '../../../components/ui/LoadingState';
import type { GeoCountrySummary, SecurityRiskTrendPoint } from '../../../types';

type MetricMode = 'volume' | 'availability' | 'latency' | 'normalShare';

type ProxyRegionDatum = {
  countryIds: string[];
  countryCode: string;
  regionName: string;
  proxyCount: number;
  activeCount: number;
  availabilityRate: number;
  avgLatencyMs: number;
  normalShare: number;
  suspiciousCount: number;
  maliciousCount: number;
  uncheckedCount: number;
  protocols: { http: number; https: number; socks5: number };
  topEventTypes: GeoCountrySummary['topEventTypes'];
};

type MapCountry = {
  id: string;
  name: string;
  path: string;
  datum?: ProxyRegionDatum;
};

const MAP_WIDTH = 980;
const MAP_HEIGHT = 520;

const ISO2_TO_NUMERIC: Record<string, string> = {
  AU: '036',
  BR: '076',
  CA: '124',
  CN: '156',
  DE: '276',
  FR: '250',
  GB: '826',
  HK: '344',
  IN: '356',
  JP: '392',
  KR: '410',
  NL: '528',
  RU: '643',
  SG: '702',
  TW: '158',
  US: '840',
};

const COUNTRY_NAME_TO_NUMERIC: Record<string, string> = {
  Australia: '036',
  Brazil: '076',
  Canada: '124',
  China: '156',
  France: '250',
  Germany: '276',
  'Hong Kong': '344',
  India: '356',
  Japan: '392',
  Netherlands: '528',
  Russia: '643',
  Singapore: '702',
  'South Korea': '410',
  Taiwan: '158',
  'United Kingdom': '826',
  'United States': '840',
  USA: '840',
};

const MODE_LABELS: Record<MetricMode, string> = {
  volume: '代理规模',
  availability: '可用率',
  latency: '平均延迟',
  normalShare: '低风险占比',
};

const MODE_DESCRIPTIONS: Record<MetricMode, string> = {
  volume: '颜色越深代表该地区代理数量越多。',
  availability: '颜色越深代表该地区可用率越高。',
  latency: '颜色越深代表延迟压力越高。',
  normalShare: '颜色越深代表该地区低风险代理占比越高。',
};

export function WorldMapPage() {
  const [regions, setRegions] = useState<ProxyRegionDatum[]>([]);
  const [trend, setTrend] = useState<SecurityRiskTrendPoint[]>([]);
  const [selected, setSelected] = useState<ProxyRegionDatum | null>(null);
  const [hovered, setHovered] = useState<ProxyRegionDatum | null>(null);
  const [mode, setMode] = useState<MetricMode>('volume');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    Promise.all([getSecurityGeoSummary(), getSecurityOverview()])
      .then(([geoPayload, overview]) => {
        if (cancelled) return;
        const mappedRegions = (geoPayload.data ?? [])
          .map(toRegionDatum)
          .filter((region): region is ProxyRegionDatum => region !== null)
          .sort((a, b) => b.proxyCount - a.proxyCount);
        setRegions(mappedRegions);
        setTrend(overview.riskTrend ?? []);
        setSelected(mappedRegions[0] ?? null);
        setError(null);
      })
      .catch(() => {
        if (cancelled) return;
        setRegions([]);
        setTrend([]);
        setSelected(null);
        setError('无法加载后端地理分布数据，请确认 /api/security/geo 和 /api/security/overview 可用。');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const regionById = useMemo(() => {
    const map = new Map<string, ProxyRegionDatum>();
    regions.forEach((region) => region.countryIds.forEach((id) => map.set(id, region)));
    return map;
  }, [regions]);
  const countries = useMemo(() => buildMapCountries(regionById), [regionById]);
  const totals = useMemo(() => getTotals(regions), [regions]);
  const rankedRegions = useMemo(() => regions.slice(0, 8), [regions]);

  if (loading) return <LoadingState label="正在加载后端地图数据" />;
  if (error) return <ErrorState message={error} />;
  if (!selected || regions.length === 0) {
    return (
      <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-[0_18px_45px_rgba(15,23,42,0.06)]">
        <h1 className="text-xl font-semibold text-slate-950">暂无地理分布数据</h1>
        <p className="mt-2 text-sm text-slate-600">后端 /api/security/geo 当前没有返回可映射到世界地图的国家或地区数据。</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen space-y-6 bg-[#f8fafc] text-slate-950">
      <header className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_360px]">
        <div>
          <div className="inline-flex items-center gap-2 rounded-md border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-600 shadow-[0_8px_24px_rgba(15,23,42,0.04)]">
            <Globe2 className="h-3.5 w-3.5 text-blue-600" />
            后端实时地理分布
          </div>
          <h1 className="mt-4 text-3xl font-semibold tracking-tight text-slate-950 lg:text-4xl">全球代理网络态势</h1>
          <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-600">
            地图使用 world-atlas 标准 TopoJSON 世界边界，业务数据全部来自后端接口。中国区域会同时高亮中国大陆与台湾地区地图面。
          </p>
        </div>
        <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-[0_18px_45px_rgba(15,23,42,0.06)]">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-slate-500">当前选中区域</p>
              <h2 className="mt-1 text-xl font-semibold text-slate-950">{selected.regionName}</h2>
            </div>
            <RegionHealthBadge value={selected.availabilityRate} />
          </div>
          <div className="mt-4 grid grid-cols-3 gap-2">
            <MiniReadout label="代理" value={formatNumber(selected.proxyCount)} />
            <MiniReadout label="可用率" value={`${selected.availabilityRate}%`} />
            <MiniReadout label="延迟" value={`${selected.avgLatencyMs}ms`} />
          </div>
        </div>
      </header>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard icon={Radar} label="覆盖地区" value={String(regions.length)} helper="来自 /api/security/geo" />
        <MetricCard icon={Signal} label="代理总量" value={formatNumber(totals.proxyCount)} helper={`${formatNumber(totals.activeCount)} 个活跃代理`} />
        <MetricCard icon={Gauge} label="平均可用率" value={`${totals.availabilityRate}%`} helper="按代理规模加权" />
        <MetricCard icon={ShieldCheck} label="低风险占比" value={`${totals.normalShare}%`} helper="由 low 风险代理占比计算" />
      </section>

      <section className="grid gap-5 2xl:grid-cols-[minmax(0,1fr)_390px]">
        <MapPanel countries={countries} regions={regions} selected={selected} hovered={hovered} mode={mode} setHovered={setHovered} setSelected={setSelected} setMode={setMode} />
        <RegionDetailPanel region={selected} />
      </section>

      <section className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_420px]">
        <TrendPanel data={trend} />
        <RankingPanel regions={rankedRegions} setSelected={setSelected} />
      </section>
    </div>
  );
}

function MapPanel({
  countries,
  regions,
  selected,
  hovered,
  mode,
  setHovered,
  setSelected,
  setMode,
}: {
  countries: MapCountry[];
  regions: ProxyRegionDatum[];
  selected: ProxyRegionDatum;
  hovered: ProxyRegionDatum | null;
  mode: MetricMode;
  setHovered: (region: ProxyRegionDatum | null) => void;
  setSelected: (region: ProxyRegionDatum) => void;
  setMode: (mode: MetricMode) => void;
}) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-[0_18px_45px_rgba(15,23,42,0.06)]">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <h2 className="text-lg font-semibold text-slate-950">世界地图</h2>
          <p className="mt-1 max-w-2xl text-sm leading-6 text-slate-600">
            Hover 查看摘要，点击锁定详情。国家边界来自 Natural Earth TopoJSON，不使用手写轮廓。
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {Object.entries(MODE_LABELS).map(([key, label]) => (
            <MetricModeButton key={key} active={mode === key} onClick={() => setMode(key as MetricMode)}>
              {label}
            </MetricModeButton>
          ))}
        </div>
      </div>

      <div className="mt-4 overflow-hidden rounded-lg border border-slate-200 bg-[#eef6fb]">
        <div className="relative">
          <svg viewBox={`0 0 ${MAP_WIDTH} ${MAP_HEIGHT}`} className="block h-[360px] w-full md:h-[520px]" role="img" aria-label="全球代理分布交互式世界地图">
            <defs>
              <linearGradient id="oceanGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#f8fbff" />
                <stop offset="100%" stopColor="#e5f0f8" />
              </linearGradient>
            </defs>
            <rect width={MAP_WIDTH} height={MAP_HEIGHT} fill="url(#oceanGradient)" />
            <path d={buildGraticulePath()} fill="none" stroke="#cbd5e1" strokeWidth="0.6" opacity="0.45" />
            {countries.map((country) => {
              const isSelected = selected.countryIds.includes(country.id);
              const isHovered = hovered?.countryIds.includes(country.id) ?? false;
              const interactive = Boolean(country.datum);
              return (
                <path
                  key={country.id}
                  d={country.path}
                  fill={getRegionFill(country.datum, regions, mode)}
                  stroke={isSelected || isHovered ? '#0f172a' : '#ffffff'}
                  strokeWidth={isSelected || isHovered ? 1.15 : 0.55}
                  className={`${interactive ? 'cursor-pointer' : 'cursor-default'} transition-[fill,stroke,opacity] duration-200 outline-none hover:opacity-95 focus-visible:opacity-95`}
                  tabIndex={interactive ? 0 : -1}
                  role={interactive ? 'button' : 'img'}
                  aria-label={country.datum ? `${country.datum.regionName} 代理分布详情` : country.name}
                  onMouseEnter={() => setHovered(country.datum ?? null)}
                  onMouseLeave={() => setHovered(null)}
                  onFocus={() => setHovered(country.datum ?? null)}
                  onBlur={() => setHovered(null)}
                  onClick={() => country.datum && setSelected(country.datum)}
                  onKeyDown={(event) => {
                    if (country.datum && (event.key === 'Enter' || event.key === ' ')) {
                      event.preventDefault();
                      setSelected(country.datum);
                    }
                  }}
                >
                  <title>{country.datum ? tooltipText(country.datum) : country.name}</title>
                </path>
              );
            })}
          </svg>

          <div className="absolute left-4 top-4 max-w-[calc(100%-2rem)] rounded-lg border border-slate-200 bg-white/95 p-3 shadow-[0_18px_45px_rgba(15,23,42,0.10)] backdrop-blur">
            <div className="flex items-center gap-2 text-xs font-semibold text-slate-600">
              <MousePointer2 className="h-3.5 w-3.5 text-blue-600" />
              {hovered ? hovered.regionName : '移动到有数据的国家查看摘要'}
            </div>
            {hovered ? (
              <div className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-slate-600">
                <span>代理 {formatNumber(hovered.proxyCount)}</span>
                <span>可用率 {hovered.availabilityRate}%</span>
                <span>延迟 {hovered.avgLatencyMs}ms</span>
                <span>低风险 {hovered.normalShare}%</span>
              </div>
            ) : (
              <p className="mt-2 text-xs text-slate-500">{MODE_DESCRIPTIONS[mode]}</p>
            )}
          </div>
        </div>
        <div className="flex flex-col gap-3 border-t border-slate-200 bg-white px-4 py-3 lg:flex-row lg:items-center lg:justify-between">
          <div className="text-xs text-slate-500">{MODE_DESCRIPTIONS[mode]}</div>
          <MapLegend mode={mode} />
        </div>
      </div>
    </div>
  );
}

function RegionDetailPanel({ region }: { region: ProxyRegionDatum }) {
  const healthDelta = region.availabilityRate - 90;
  return (
    <aside className="rounded-lg border border-slate-200 bg-white p-4 shadow-[0_18px_45px_rgba(15,23,42,0.06)]">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-medium text-slate-500">区域详情</p>
          <h2 className="mt-1 text-2xl font-semibold text-slate-950">{region.regionName}</h2>
          <p className="mt-2 text-sm leading-6 text-slate-600">
            来自后端聚合：{formatNumber(region.proxyCount)} 个代理，{formatNumber(region.activeCount)} 个活跃，平均响应 {region.avgLatencyMs}ms。
          </p>
        </div>
        <RegionHealthBadge value={region.availabilityRate} />
      </div>

      <div className="mt-5 grid grid-cols-2 gap-3">
        <MiniReadout label="代理数量" value={formatNumber(region.proxyCount)} />
        <MiniReadout label="活跃代理" value={formatNumber(region.activeCount)} />
        <MiniReadout label="未检测" value={formatNumber(region.uncheckedCount)} />
        <MiniReadout label="低风险占比" value={`${region.normalShare}%`} />
      </div>

      <div className="mt-5 rounded-lg border border-slate-200 bg-slate-50 p-3">
        <div className="mb-2 flex items-center justify-between text-sm">
          <span className="font-medium text-slate-800">质量判断</span>
          <DeltaPill value={healthDelta} />
        </div>
        <p className="text-sm leading-6 text-slate-600">
          可疑代理 {formatNumber(region.suspiciousCount)} 个，高风险/恶意代理 {formatNumber(region.maliciousCount)} 个。低风险占比由后端 `low` 风险计数派生。
        </p>
      </div>

      <div className="mt-5 space-y-3">
        <DistributionRow label="HTTP" value={region.protocols.http} total={region.proxyCount} color="#2563eb" />
        <DistributionRow label="HTTPS" value={region.protocols.https} total={region.proxyCount} color="#0f766e" />
        <DistributionRow label="SOCKS5" value={region.protocols.socks5} total={region.proxyCount} color="#f97316" />
      </div>

      <div className="mt-5 rounded-lg border border-slate-200 bg-white p-3">
        <div className="mb-2 text-sm font-medium text-slate-800">主要异常类型</div>
        {region.topEventTypes.length === 0 ? (
          <p className="text-sm text-slate-500">后端暂无该地区异常事件。</p>
        ) : (
          <div className="space-y-2">
            {region.topEventTypes.map((event) => (
              <div key={`${event.eventType}-${event.riskLevel}`} className="flex items-center justify-between gap-3 text-sm">
                <span className="truncate text-slate-600">{event.eventType}</span>
                <span className="rounded-md border border-slate-200 bg-slate-50 px-2 py-1 text-xs font-semibold text-slate-700">{event.count}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </aside>
  );
}

function TrendPanel({ data }: { data: SecurityRiskTrendPoint[] }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-[0_18px_45px_rgba(15,23,42,0.06)]">
      <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className="text-lg font-semibold text-slate-950">后端风险趋势</h2>
          <p className="mt-1 text-sm text-slate-600">来自 /api/security/overview 的全局扫描趋势。</p>
        </div>
        <div className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-xs font-medium text-slate-600">Backend trend</div>
      </div>
      <div className="mt-4">
        {data.length === 0 ? (
          <p className="rounded-lg border border-slate-200 bg-slate-50 p-4 text-sm text-slate-500">后端暂无趋势数据。</p>
        ) : (
          <TrendChart data={data} />
        )}
      </div>
    </div>
  );
}

function RankingPanel({ regions, setSelected }: { regions: ProxyRegionDatum[]; setSelected: (region: ProxyRegionDatum) => void }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-[0_18px_45px_rgba(15,23,42,0.06)]">
      <h2 className="text-lg font-semibold text-slate-950">代理规模排行</h2>
      <p className="mt-1 text-sm text-slate-600">全部来自后端地理聚合，点击切换右侧详情。</p>
      <div className="mt-4 space-y-3">
        {regions.map((region) => (
          <button
            key={region.countryIds.join('-')}
            type="button"
            onClick={() => setSelected(region)}
            className="block w-full rounded-lg border border-slate-200 bg-white p-3 text-left shadow-[0_10px_24px_rgba(15,23,42,0.04)] transition duration-200 hover:border-blue-200 hover:bg-blue-50/40 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-500 active:scale-[0.99]"
          >
            <div className="flex items-center justify-between gap-3 text-sm">
              <span className="font-medium text-slate-800">{region.regionName}</span>
              <span className="font-semibold text-slate-950">{formatNumber(region.proxyCount)}</span>
            </div>
            <div className="mt-2 h-2 overflow-hidden rounded-md bg-slate-100">
              <div className="h-full rounded-md bg-blue-600 transition-all duration-300" style={{ width: `${Math.max(8, (region.proxyCount / regions[0].proxyCount) * 100)}%` }} />
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}

function TrendChart({ data }: { data: SecurityRiskTrendPoint[] }) {
  const width = 920;
  const height = 260;
  const padding = { top: 18, right: 28, bottom: 34, left: 42 };
  const innerWidth = width - padding.left - padding.right;
  const innerHeight = height - padding.top - padding.bottom;
  const maxValue = Math.max(...data.flatMap((point) => [point.totalRecords, point.anomalousRecords, point.highRiskRecords]), 1);
  const xFor = (index: number) => padding.left + (index / Math.max(1, data.length - 1)) * innerWidth;
  const yFor = (value: number) => padding.top + innerHeight - (value / maxValue) * innerHeight;
  const pathFor = (key: 'totalRecords' | 'anomalousRecords' | 'highRiskRecords') =>
    data.map((point, index) => `${index === 0 ? 'M' : 'L'} ${xFor(index)} ${yFor(point[key])}`).join(' ');

  return (
    <div>
      <svg viewBox={`0 0 ${width} ${height}`} className="h-[260px] w-full" role="img" aria-label="后端风险趋势折线图">
        {[0, 0.25, 0.5, 0.75, 1].map((ratio) => (
          <line key={ratio} x1={padding.left} x2={width - padding.right} y1={padding.top + innerHeight * ratio} y2={padding.top + innerHeight * ratio} stroke="#e2e8f0" strokeWidth="1" />
        ))}
        <path d={pathFor('totalRecords')} fill="none" stroke="#2563eb" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
        <path d={pathFor('anomalousRecords')} fill="none" stroke="#f97316" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
        <path d={pathFor('highRiskRecords')} fill="none" stroke="#e11d48" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
        {data.map((point, index) => (
          <g key={point.date}>
            <circle cx={xFor(index)} cy={yFor(point.totalRecords)} r="4" fill="#2563eb">
              <title>{`${point.date} 总记录 ${point.totalRecords}`}</title>
            </circle>
            <circle cx={xFor(index)} cy={yFor(point.anomalousRecords)} r="4" fill="#f97316">
              <title>{`${point.date} 异常 ${point.anomalousRecords}`}</title>
            </circle>
            <circle cx={xFor(index)} cy={yFor(point.highRiskRecords)} r="4" fill="#e11d48">
              <title>{`${point.date} 高风险 ${point.highRiskRecords}`}</title>
            </circle>
            <text x={xFor(index)} y={height - 10} textAnchor="middle" className="fill-slate-500 text-[11px]">
              {point.date.slice(5)}
            </text>
          </g>
        ))}
      </svg>
      <div className="flex flex-wrap gap-4 text-xs font-medium text-slate-600">
        <LegendItem color="#2563eb" label="总记录" />
        <LegendItem color="#f97316" label="异常记录" />
        <LegendItem color="#e11d48" label="高风险记录" />
      </div>
    </div>
  );
}

function MetricCard({ icon: Icon, label, value, helper }: { icon: LucideIcon; label: string; value: string; helper: string }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-[0_14px_36px_rgba(15,23,42,0.05)]">
      <div className="flex items-center justify-between gap-3">
        <span className="text-sm font-medium text-slate-600">{label}</span>
        <span className="rounded-md border border-blue-100 bg-blue-50 p-2 text-blue-700">
          <Icon className="h-4 w-4" />
        </span>
      </div>
      <div className="mt-3 text-3xl font-semibold tracking-tight text-slate-950">{value}</div>
      <p className="mt-1 text-xs text-slate-500">{helper}</p>
    </div>
  );
}

function MiniReadout({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2">
      <div className="text-xs text-slate-500">{label}</div>
      <div className="mt-1 text-sm font-semibold text-slate-950">{value}</div>
    </div>
  );
}

function MetricModeButton({ active, onClick, children }: { active: boolean; onClick: () => void; children: string; key?: string }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={[
        'rounded-md border px-3 py-2 text-sm font-medium transition duration-200 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-500 active:scale-[0.98]',
        active
          ? 'border-blue-600 bg-blue-600 text-white shadow-[0_10px_24px_rgba(37,99,235,0.18)]'
          : 'border-slate-200 bg-white text-slate-600 hover:border-blue-200 hover:bg-blue-50 hover:text-blue-700',
      ].join(' ')}
    >
      {children}
    </button>
  );
}

function RegionHealthBadge({ value }: { value: number }) {
  const tone =
    value >= 94
      ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
      : value >= 88
        ? 'border-amber-200 bg-amber-50 text-amber-800'
        : 'border-rose-200 bg-rose-50 text-rose-700';
  return <span className={`rounded-md border px-2.5 py-1 text-xs font-semibold ${tone}`}>{value >= 94 ? '稳定' : value >= 88 ? '观察' : '拥塞'}</span>;
}

function DeltaPill({ value }: { value: number }) {
  const positive = value >= 0;
  const Icon = positive ? ArrowUpRight : ArrowDownRight;
  return (
    <span
      className={[
        'inline-flex items-center gap-1 rounded-md border px-2 py-1 text-xs font-semibold',
        positive ? 'border-emerald-200 bg-emerald-50 text-emerald-700' : 'border-amber-200 bg-amber-50 text-amber-800',
      ].join(' ')}
    >
      <Icon className="h-3.5 w-3.5" />
      {positive ? '+' : ''}
      {value.toFixed(1)}%
    </span>
  );
}

function DistributionRow({ label, value, total, color }: { label: string; value: number; total: number; color: string }) {
  const width = total > 0 ? Math.max(4, Math.round((value / total) * 100)) : 0;
  return (
    <div>
      <div className="mb-1 flex items-center justify-between text-xs font-medium text-slate-600">
        <span>{label}</span>
        <span>{formatNumber(value)}</span>
      </div>
      <div className="h-2 overflow-hidden rounded-md bg-slate-100">
        <div className="h-full rounded-md" style={{ width: `${width}%`, backgroundColor: color }} />
      </div>
    </div>
  );
}

function MapLegend({ mode }: { mode: MetricMode }) {
  const labels =
    mode === 'latency'
      ? ['低延迟', '中等', '高延迟', '拥塞']
      : mode === 'availability'
        ? ['低可用', '一般', '稳定', '高稳定']
        : mode === 'normalShare'
          ? ['较低', '中等', '较高', '低风险']
          : ['较少', '中等', '较多', '高度集中'];

  return (
    <div className="flex flex-wrap items-center gap-2">
      {labels.map((label, index) => (
        <span key={label} className="inline-flex items-center gap-1.5 text-xs text-slate-500">
          <span className="h-2.5 w-6 rounded-sm" style={{ backgroundColor: mode === 'latency' ? LATENCY_COLORS[index + 1] : MAP_COLORS[index + 1] }} />
          {label}
        </span>
      ))}
    </div>
  );
}

function LegendItem({ color, label }: { color: string; label: string }) {
  return (
    <span className="inline-flex items-center gap-2">
      <span className="h-2 w-5 rounded-sm" style={{ backgroundColor: color }} />
      {label}
    </span>
  );
}

const MAP_COLORS = ['#e5e7eb', '#dbeafe', '#93c5fd', '#3b82f6', '#1d4ed8'];
const LATENCY_COLORS = ['#e5e7eb', '#dcfce7', '#fde68a', '#fb923c', '#dc2626'];

function buildMapCountries(regionById: Map<string, ProxyRegionDatum>): MapCountry[] {
  const countriesObject = (countriesTopology as any).objects.countries;
  const geo = feature(countriesTopology as any, countriesObject) as any;
  const projection = geoEqualEarth().fitExtent([[18, 18], [MAP_WIDTH - 18, MAP_HEIGHT - 18]], geo);
  const path = geoPath(projection);
  return geo.features
    .map((country: any) => ({
      id: String(country.id).padStart(3, '0'),
      name: country.properties?.name ?? 'Unknown',
      path: path(country) ?? '',
      datum: regionById.get(String(country.id).padStart(3, '0')),
    }))
    .filter((country: MapCountry) => country.path.length > 0);
}

function buildGraticulePath() {
  const projection = geoEqualEarth().fitExtent([[18, 18], [MAP_WIDTH - 18, MAP_HEIGHT - 18]], { type: 'Sphere' } as any);
  const path = geoPath(projection);
  const lines = [];
  for (let lon = -150; lon <= 150; lon += 30) lines.push({ type: 'LineString', coordinates: [[lon, -70], [lon, 80]] });
  for (let lat = -60; lat <= 60; lat += 20) lines.push({ type: 'LineString', coordinates: [[-180, lat], [180, lat]] });
  return lines.map((line) => path(line as any)).filter(Boolean).join(' ');
}

function toRegionDatum(country: GeoCountrySummary): ProxyRegionDatum | null {
  const countryIds = resolveCountryIds(country);
  if (countryIds.length === 0 || country.totalProxies <= 0) return null;
  const availabilityRate = round1((country.activeProxies / country.totalProxies) * 100);
  const normalShare = round1((country.normalProxies / country.totalProxies) * 100);
  return {
    countryIds,
    countryCode: country.countryCode,
    regionName: country.countryName,
    proxyCount: country.totalProxies,
    activeCount: country.activeProxies,
    availabilityRate,
    avgLatencyMs: Math.round(country.avgResponseTimeMs ?? 0),
    normalShare,
    suspiciousCount: country.suspiciousProxies,
    maliciousCount: country.maliciousProxies,
    uncheckedCount: country.uncheckedProxies,
    protocols: country.protocols,
    topEventTypes: country.topEventTypes ?? [],
  };
}

function resolveCountryIds(country: GeoCountrySummary) {
  const code = (country.countryCode || '').toUpperCase();
  const name = country.countryName || '';
  const primary = ISO2_TO_NUMERIC[code] ?? COUNTRY_NAME_TO_NUMERIC[name];
  if (!primary) return [];
  if (code === 'CN' || name === 'China') return ['156', '158'];
  return [primary];
}

function getRegionFill(region: ProxyRegionDatum | undefined, regions: ProxyRegionDatum[], mode: MetricMode) {
  if (!region) return '#e5e7eb';
  if (mode === 'latency') return bucketColor(region.avgLatencyMs, 0, Math.max(...regions.map((item) => item.avgLatencyMs), 1), LATENCY_COLORS);
  if (mode === 'availability') return bucketColor(region.availabilityRate, 70, 100, MAP_COLORS);
  if (mode === 'normalShare') return bucketColor(region.normalShare, 0, 100, MAP_COLORS);
  return bucketColor(region.proxyCount, 0, Math.max(...regions.map((item) => item.proxyCount), 1), MAP_COLORS);
}

function bucketColor(value: number, min: number, max: number, colors: string[]) {
  const ratio = Math.min(1, Math.max(0, (value - min) / Math.max(1, max - min)));
  const index = Math.min(colors.length - 1, Math.max(1, Math.ceil(ratio * (colors.length - 1))));
  return colors[index];
}

function getTotals(regions: ProxyRegionDatum[]) {
  const proxyCount = regions.reduce((total, region) => total + region.proxyCount, 0);
  const activeCount = regions.reduce((total, region) => total + region.activeCount, 0);
  const normalCount = regions.reduce((total, region) => total + Math.round((region.normalShare / 100) * region.proxyCount), 0);
  return {
    proxyCount,
    activeCount,
    availabilityRate: proxyCount > 0 ? round1((activeCount / proxyCount) * 100) : 0,
    normalShare: proxyCount > 0 ? round1((normalCount / proxyCount) * 100) : 0,
  };
}

function round1(value: number) {
  return Math.round(value * 10) / 10;
}

function formatNumber(value: number) {
  return new Intl.NumberFormat('zh-CN').format(value);
}

function tooltipText(region: ProxyRegionDatum) {
  return `${region.regionName}\n代理数量 ${region.proxyCount}\n可用率 ${region.availabilityRate}%\n平均延迟 ${region.avgLatencyMs}ms\n低风险占比 ${region.normalShare}%`;
}
