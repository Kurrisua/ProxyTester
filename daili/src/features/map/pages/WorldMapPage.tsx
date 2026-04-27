import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { geoEqualEarth, geoPath } from 'd3-geo';
import { feature } from 'topojson-client';
import countriesTopology from 'world-atlas/countries-110m.json';
import { Gauge, Globe2, ShieldAlert, Signal } from 'lucide-react';
import { getSecurityGeoRegion, getSecurityGeoSummary } from '../../../api/security';
import { Badge } from '../../../components/ui/Badge';
import { ErrorState } from '../../../components/ui/ErrorState';
import { LoadingState } from '../../../components/ui/LoadingState';
import { RISK_LEVEL_LABELS } from '../../../types/labels';
import type { GeoCountrySummary, GeoRegionDetail, RiskLevel } from '../../../types';

type RegionDatum = {
  countryIds: string[];
  countryCode: string;
  countryName: string;
  totalProxies: number;
  activeProxies: number;
  uncheckedProxies: number;
  normalProxies: number;
  suspiciousProxies: number;
  maliciousProxies: number;
  avgResponseTimeMs: number;
  protocols: { http: number; https: number; socks5: number };
  topRiskLevel: RiskLevel;
  topEventTypes: GeoCountrySummary['topEventTypes'];
};

type MapCountry = {
  id: string;
  name: string;
  path: string;
  datum?: RegionDatum;
};

const MAP_WIDTH = 980;
const MAP_HEIGHT = 520;

const ISO2_TO_NUMERIC: Record<string, string> = {
  AU: '036', BR: '076', CA: '124', CN: '156', DE: '276', FR: '250', GB: '826', HK: '344',
  IN: '356', JP: '392', KR: '410', NL: '528', RU: '643', SG: '702', TW: '158', US: '840',
};

const COUNTRY_NAME_TO_NUMERIC: Record<string, string> = {
  Australia: '036', Brazil: '076', Canada: '124', China: '156', France: '250', Germany: '276',
  'Hong Kong': '344', India: '356', Japan: '392', Netherlands: '528', Russia: '643',
  Singapore: '702', 'South Korea': '410', Taiwan: '158', 'United Kingdom': '826',
  'United States': '840', USA: '840',
};

export function WorldMapPage() {
  const [regions, setRegions] = useState<RegionDatum[]>([]);
  const [selected, setSelected] = useState<RegionDatum | null>(null);
  const [regionDetail, setRegionDetail] = useState<GeoRegionDetail | null>(null);
  const [hovered, setHovered] = useState<RegionDatum | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    getSecurityGeoSummary()
      .then((payload) => {
        const mapped = (payload.data ?? []).map(toRegionDatum).filter((item): item is RegionDatum => item !== null).sort((a, b) => b.totalProxies - a.totalProxies);
        setRegions(mapped);
        setSelected(mapped[0] ?? null);
        setError(null);
      })
      .catch(() => setError('无法加载后端地理分布数据，请确认 /api/security/geo 可用。'))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!selected) {
      setRegionDetail(null);
      return;
    }
    getSecurityGeoRegion(selected.countryCode !== 'UNKNOWN' ? selected.countryCode : selected.countryName)
      .then(setRegionDetail)
      .catch(() => setRegionDetail(null));
  }, [selected]);

  const regionById = useMemo(() => {
    const map = new Map<string, RegionDatum>();
    regions.forEach((region) => region.countryIds.forEach((id) => map.set(id, region)));
    return map;
  }, [regions]);
  const countries = useMemo(() => buildMapCountries(regionById), [regionById]);
  const totals = useMemo(() => getTotals(regions), [regions]);

  if (loading) return <LoadingState label="正在加载全球地图数据" />;
  if (error) return <ErrorState message={error} />;
  if (!selected || regions.length === 0) return <EmptyMap />;

  return (
    <div className="space-y-6">
      <header className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_360px]">
        <div>
          <div className="inline-flex items-center gap-2 rounded-md border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-600">
            <Globe2 className="h-3.5 w-3.5 text-blue-600" />
            后端地理聚合
          </div>
          <h1 className="mt-4 text-3xl font-semibold tracking-tight text-slate-950 lg:text-4xl">全球代理网络态势</h1>
          <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-600">国家级地图展示代理总数、活跃数量、未检测数量、风险分布、平均响应时间、协议分布和主要异常类型。</p>
        </div>
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <div className="text-xs font-medium text-slate-500">当前选中区域</div>
          <h2 className="mt-1 text-xl font-semibold text-slate-950">{selected.countryName}</h2>
          <div className="mt-4 grid grid-cols-3 gap-2">
            <MiniReadout label="代理" value={formatNumber(selected.totalProxies)} />
            <MiniReadout label="活跃" value={formatNumber(selected.activeProxies)} />
            <MiniReadout label="风险" value={RISK_LEVEL_LABELS[selected.topRiskLevel]} />
          </div>
        </div>
      </header>

      <section className="grid gap-4 md:grid-cols-4">
        <Metric icon={Globe2} label="覆盖地区" value={regions.length} />
        <Metric icon={Signal} label="代理总量" value={totals.totalProxies} />
        <Metric icon={Gauge} label="活跃代理" value={totals.activeProxies} />
        <Metric icon={ShieldAlert} label="高危/恶意" value={totals.maliciousProxies} />
      </section>

      <section className="grid gap-5 2xl:grid-cols-[minmax(0,1fr)_390px]">
        <MapPanel countries={countries} regions={regions} selected={selected} hovered={hovered} setHovered={setHovered} setSelected={setSelected} />
        <RegionDetailPanel region={selected} detail={regionDetail} />
      </section>
    </div>
  );
}

function MapPanel({ countries, regions, selected, hovered, setHovered, setSelected }: { countries: MapCountry[]; regions: RegionDatum[]; selected: RegionDatum; hovered: RegionDatum | null; setHovered: (region: RegionDatum | null) => void; setSelected: (region: RegionDatum) => void }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <div className="flex flex-col gap-2 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <h2 className="text-lg font-semibold text-slate-950">世界地图</h2>
          <p className="mt-1 text-sm text-slate-600">Hover 查看摘要，点击国家打开区域详情面板。</p>
        </div>
        <MapLegend />
      </div>
      <div className="mt-4 overflow-hidden rounded-lg border border-slate-200 bg-[#eef6fb]">
        <div className="relative">
          <svg viewBox={`0 0 ${MAP_WIDTH} ${MAP_HEIGHT}`} className="block h-[360px] w-full md:h-[520px]" role="img" aria-label="全球代理分布地图">
            <rect width={MAP_WIDTH} height={MAP_HEIGHT} fill="#eef6fb" />
            {countries.map((country) => {
              const isSelected = selected.countryIds.includes(country.id);
              const isHovered = hovered?.countryIds.includes(country.id) ?? false;
              return (
                <path
                  key={country.id}
                  d={country.path}
                  fill={getRegionFill(country.datum, regions)}
                  stroke={isSelected || isHovered ? '#0f172a' : '#ffffff'}
                  strokeWidth={isSelected || isHovered ? 1.15 : 0.55}
                  className={country.datum ? 'cursor-pointer transition-opacity hover:opacity-90' : 'cursor-default'}
                  onMouseEnter={() => setHovered(country.datum ?? null)}
                  onMouseLeave={() => setHovered(null)}
                  onClick={() => country.datum && setSelected(country.datum)}
                >
                  <title>{country.datum ? tooltipText(country.datum) : country.name}</title>
                </path>
              );
            })}
          </svg>
          <div className="absolute left-4 top-4 max-w-[calc(100%-2rem)] rounded-lg border border-slate-200 bg-white/95 p-3 shadow-sm">
            <div className="text-xs font-semibold text-slate-600">{hovered ? hovered.countryName : '移动到有数据的国家查看摘要'}</div>
            {hovered ? (
              <div className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-slate-600">
                <span>代理 {formatNumber(hovered.totalProxies)}</span>
                <span>活跃 {formatNumber(hovered.activeProxies)}</span>
                <span>未检测 {formatNumber(hovered.uncheckedProxies)}</span>
                <span>高危 {formatNumber(hovered.maliciousProxies)}</span>
                <span>平均响应 {hovered.avgResponseTimeMs}ms</span>
                <span>最高风险 {RISK_LEVEL_LABELS[hovered.topRiskLevel]}</span>
              </div>
            ) : <p className="mt-2 text-xs text-slate-500">颜色越深表示代理规模越大。</p>}
          </div>
        </div>
      </div>
    </div>
  );
}

function RegionDetailPanel({ region, detail }: { region: RegionDatum; detail: GeoRegionDetail | null }) {
  return (
    <aside className="rounded-lg border border-slate-200 bg-white p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-medium text-slate-500">区域详情</p>
          <h2 className="mt-1 text-2xl font-semibold text-slate-950">{region.countryName}</h2>
          <p className="mt-2 text-sm leading-6 text-slate-600">代理 {formatNumber(region.totalProxies)} 个，活跃 {formatNumber(region.activeProxies)} 个，平均响应 {region.avgResponseTimeMs}ms。</p>
        </div>
        <Badge tone={riskTone(region.topRiskLevel)}>{RISK_LEVEL_LABELS[region.topRiskLevel]}</Badge>
      </div>

      <div className="mt-5 grid grid-cols-2 gap-3">
        <MiniReadout label="未检测" value={formatNumber(region.uncheckedProxies)} />
        <MiniReadout label="正常" value={formatNumber(region.normalProxies)} />
        <MiniReadout label="可疑" value={formatNumber(region.suspiciousProxies)} />
        <MiniReadout label="恶意/高危" value={formatNumber(region.maliciousProxies)} />
      </div>

      <div className="mt-5 space-y-3">
        <DistributionRow label="HTTP" value={region.protocols.http} total={region.totalProxies} color="#2563eb" />
        <DistributionRow label="HTTPS" value={region.protocols.https} total={region.totalProxies} color="#0f766e" />
        <DistributionRow label="SOCKS5" value={region.protocols.socks5} total={region.totalProxies} color="#7c3aed" />
      </div>

      <div className="mt-5 rounded-lg border border-slate-200 bg-white p-3">
        <div className="mb-2 text-sm font-medium text-slate-800">主要异常类型</div>
        {region.topEventTypes.length === 0 ? <p className="text-sm text-slate-500">暂无该地区异常事件。</p> : (
          <div className="space-y-2">{region.topEventTypes.map((event) => <div key={`${event.eventType}-${event.riskLevel}`} className="flex items-center justify-between gap-3 text-sm"><span className="truncate text-slate-600">{event.eventType}</span><span className="rounded-md border border-slate-200 bg-slate-50 px-2 py-1 text-xs font-semibold text-slate-700">{event.count}</span></div>)}</div>
        )}
      </div>

      <div className="mt-5 flex flex-wrap gap-2">
        <Link to={`/proxies?country=${encodeURIComponent(region.countryName)}`} className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50">查看代理</Link>
        <Link to={`/events?country=${encodeURIComponent(region.countryName)}`} className="rounded-lg bg-emerald-600 px-3 py-2 text-sm font-medium text-white hover:bg-emerald-700">查看事件</Link>
      </div>

      {detail ? (
        <div className="mt-5 rounded-lg border border-slate-200 bg-slate-50 p-3">
          <div className="text-sm font-medium text-slate-800">高风险代理样本</div>
          <div className="mt-2 space-y-2">
            {detail.topProxies.slice(0, 5).map((proxy) => (
              <Link key={proxy.proxy} to={`/proxies/${encodeURIComponent(proxy.ip)}/${proxy.port}`} className="block rounded-md bg-white px-3 py-2 text-xs text-slate-600 hover:text-emerald-700">
                {proxy.proxy} · {proxy.securityRisk ?? 'unknown'} · {proxy.responseTime ?? '-'}ms
              </Link>
            ))}
          </div>
        </div>
      ) : null}
    </aside>
  );
}

function EmptyMap() {
  return <div className="rounded-lg border border-slate-200 bg-white p-6"><h1 className="text-xl font-semibold text-slate-950">暂无地理分布数据</h1><p className="mt-2 text-sm text-slate-600">后端 /api/security/geo 当前没有返回可映射到世界地图的国家或地区数据。</p></div>;
}

function Metric({ icon: Icon, label, value }: { icon: typeof Globe2; label: string; value: number }) {
  return <div className="rounded-lg border border-slate-200 bg-white p-4"><div className="flex items-center justify-between gap-3"><span className="text-sm font-medium text-slate-600">{label}</span><Icon className="h-4 w-4 text-blue-600" /></div><div className="mt-3 text-3xl font-semibold tracking-tight text-slate-950">{formatNumber(value)}</div></div>;
}

function MiniReadout({ label, value }: { label: string; value: string }) {
  return <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2"><div className="text-xs text-slate-500">{label}</div><div className="mt-1 text-sm font-semibold text-slate-950">{value}</div></div>;
}

function DistributionRow({ label, value, total, color }: { label: string; value: number; total: number; color: string }) {
  const width = total > 0 ? Math.max(4, Math.round((value / total) * 100)) : 0;
  return <div><div className="mb-1 flex items-center justify-between text-xs font-medium text-slate-600"><span>{label}</span><span>{formatNumber(value)}</span></div><div className="h-2 overflow-hidden rounded-md bg-slate-100"><div className="h-full rounded-md" style={{ width: `${width}%`, backgroundColor: color }} /></div></div>;
}

function MapLegend() {
  return <div className="flex flex-wrap items-center gap-2">{['少', '中', '多', '集中'].map((label, index) => <span key={label} className="inline-flex items-center gap-1.5 text-xs text-slate-500"><span className="h-2.5 w-6 rounded-sm" style={{ backgroundColor: MAP_COLORS[index + 1] }} />{label}</span>)}</div>;
}

const MAP_COLORS = ['#e5e7eb', '#dbeafe', '#93c5fd', '#3b82f6', '#1d4ed8'];

function buildMapCountries(regionById: Map<string, RegionDatum>): MapCountry[] {
  const countriesObject = (countriesTopology as any).objects.countries;
  const geo = feature(countriesTopology as any, countriesObject) as any;
  const projection = geoEqualEarth().fitExtent([[18, 18], [MAP_WIDTH - 18, MAP_HEIGHT - 18]], geo);
  const path = geoPath(projection);
  return geo.features.map((country: any) => ({ id: String(country.id).padStart(3, '0'), name: country.properties?.name ?? 'Unknown', path: path(country) ?? '', datum: regionById.get(String(country.id).padStart(3, '0')) })).filter((country: MapCountry) => country.path.length > 0);
}

function toRegionDatum(country: GeoCountrySummary): RegionDatum | null {
  const countryIds = resolveCountryIds(country);
  if (countryIds.length === 0 || country.totalProxies <= 0) return null;
  return {
    countryIds,
    countryCode: country.countryCode,
    countryName: country.countryName,
    totalProxies: country.totalProxies,
    activeProxies: country.activeProxies,
    uncheckedProxies: country.uncheckedProxies,
    normalProxies: country.normalProxies,
    suspiciousProxies: country.suspiciousProxies,
    maliciousProxies: country.maliciousProxies,
    avgResponseTimeMs: Math.round(country.avgResponseTimeMs ?? 0),
    protocols: country.protocols,
    topRiskLevel: country.topRiskLevel,
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

function getRegionFill(region: RegionDatum | undefined, regions: RegionDatum[]) {
  if (!region) return '#e5e7eb';
  const max = Math.max(...regions.map((item) => item.totalProxies), 1);
  const ratio = Math.min(1, Math.max(0, region.totalProxies / max));
  const index = Math.min(MAP_COLORS.length - 1, Math.max(1, Math.ceil(ratio * (MAP_COLORS.length - 1))));
  return MAP_COLORS[index];
}

function getTotals(regions: RegionDatum[]) {
  return {
    totalProxies: regions.reduce((total, region) => total + region.totalProxies, 0),
    activeProxies: regions.reduce((total, region) => total + region.activeProxies, 0),
    maliciousProxies: regions.reduce((total, region) => total + region.maliciousProxies, 0),
  };
}

function riskTone(risk: RiskLevel): 'neutral' | 'success' | 'warning' | 'danger' | 'info' {
  if (risk === 'critical' || risk === 'high') return 'danger';
  if (risk === 'medium') return 'warning';
  if (risk === 'low') return 'success';
  return 'neutral';
}

function formatNumber(value: number) {
  return new Intl.NumberFormat('zh-CN').format(value);
}

function tooltipText(region: RegionDatum) {
  return `${region.countryName}\n代理总数 ${region.totalProxies}\n活跃 ${region.activeProxies}\n未检测 ${region.uncheckedProxies}\n正常 ${region.normalProxies}\n可疑 ${region.suspiciousProxies}\n恶意 ${region.maliciousProxies}\n平均响应 ${region.avgResponseTimeMs}ms\nHTTP ${region.protocols.http} / HTTPS ${region.protocols.https} / SOCKS5 ${region.protocols.socks5}\n最高风险 ${RISK_LEVEL_LABELS[region.topRiskLevel]}`;
}
