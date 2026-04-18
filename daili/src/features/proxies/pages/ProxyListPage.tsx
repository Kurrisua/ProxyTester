import { ReactNode, useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { RefreshCw, ShieldCheck, Trash2 } from 'lucide-react';
import { deleteProxy, getFilters, getProxies, getStats, refreshProxies } from '../../../api/proxies';
import { Badge } from '../../../components/ui/Badge';
import { ErrorState } from '../../../components/ui/ErrorState';
import { LoadingState } from '../../../components/ui/LoadingState';
import { ANONYMITY_LABELS, BEHAVIOR_CLASS_LABELS, PROXY_STATUS_LABELS, RISK_LEVEL_LABELS } from '../../../types/labels';
import { DashboardStats, ProxyNode, ProxyStatus } from '../../../types';

const PAGE_SIZE = 10;

const STATUS_OPTIONS: Array<{ value: '' | ProxyStatus; label: string }> = [
  { value: '', label: '全部状态' },
  { value: 'alive', label: '存活' },
  { value: 'slow', label: '缓慢' },
  { value: 'dead', label: '失效' },
];

function statusTone(status: ProxyStatus) {
  if (status === 'alive') return 'success';
  if (status === 'slow') return 'warning';
  return 'danger';
}

function riskTone(risk: string) {
  if (risk === 'critical' || risk === 'high') return 'danger';
  if (risk === 'medium') return 'warning';
  if (risk === 'low') return 'success';
  return 'neutral';
}

export function ProxyListPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [proxies, setProxies] = useState<ProxyNode[]>([]);
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [countries, setCountries] = useState<string[]>([]);
  const [proxyTypes, setProxyTypes] = useState<string[]>([]);
  const [country, setCountry] = useState(searchParams.get('country') ?? '');
  const [type, setType] = useState(searchParams.get('type') ?? '');
  const [status, setStatus] = useState<'' | ProxyStatus>((searchParams.get('status') as ProxyStatus | null) ?? '');
  const [sort, setSort] = useState(searchParams.get('sort') ?? 'response_time');
  const [page, setPage] = useState(Number(searchParams.get('page') ?? 1));
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const totalPages = useMemo(() => Math.max(1, Math.ceil(total / PAGE_SIZE)), [total]);

  async function loadPage() {
    setLoading(true);
    setError(null);
    try {
      const result = await getProxies({ country, type, status, sort, page, limit: PAGE_SIZE });
      setProxies(result.data ?? []);
      setTotal(result.total ?? 0);
    } catch {
      setError('代理列表加载失败，请确认 Flask API 是否可用。');
      setProxies([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    const next = new URLSearchParams();
    if (country) next.set('country', country);
    if (type) next.set('type', type);
    if (status) next.set('status', status);
    if (sort !== 'response_time') next.set('sort', sort);
    if (page > 1) next.set('page', String(page));
    setSearchParams(next, { replace: true });
  }, [country, type, status, sort, page, setSearchParams]);

  useEffect(() => {
    void Promise.all([getStats(), getFilters()])
      .then(([statsData, filterData]) => {
        setStats(statsData);
        setCountries(filterData.countries ?? []);
        setProxyTypes(filterData.proxyTypes ?? []);
      })
      .catch(() => {
        setError('基础统计或筛选项加载失败。');
      });
  }, []);

  useEffect(() => {
    void loadPage();
  }, [country, type, status, sort, page]);

  async function handleRefresh() {
    setRefreshing(true);
    try {
      await refreshProxies();
      await Promise.all([loadPage(), getStats().then(setStats)]);
    } catch {
      setError('刷新任务提交失败。');
    } finally {
      setRefreshing(false);
    }
  }

  async function handleDelete(proxy: ProxyNode) {
    try {
      await deleteProxy(proxy.ip, proxy.port);
      await loadPage();
    } catch {
      setError(`删除 ${proxy.ip}:${proxy.port} 失败。`);
    }
  }

  return (
    <div className="space-y-6">
      <section className="grid gap-4 md:grid-cols-4">
        <Metric label="总代理数" value={stats?.totalProxies ?? 0} />
        <Metric label="活跃代理" value={stats?.activeProxies ?? 0} />
        <Metric label="国家/地区" value={stats?.countriesCount ?? 0} />
        <Metric label="平均响应" value={`${stats?.avgResponseTime ?? 0}ms`} />
      </section>

      <section className="rounded-lg border border-zinc-200 bg-white p-4">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
          <div className="grid flex-1 gap-3 md:grid-cols-4">
            <Select label="国家/地区" value={country} onChange={(value) => { setCountry(value); setPage(1); }}>
              <option value="">全部国家</option>
              {countries.map((item) => <option key={item} value={item}>{item}</option>)}
            </Select>
            <Select label="协议" value={type} onChange={(value) => { setType(value); setPage(1); }}>
              <option value="">全部协议</option>
              {proxyTypes.map((item) => <option key={item} value={item}>{item}</option>)}
            </Select>
            <Select label="状态" value={status} onChange={(value) => { setStatus(value as '' | ProxyStatus); setPage(1); }}>
              {STATUS_OPTIONS.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
            </Select>
            <Select label="排序" value={sort} onChange={setSort}>
              <option value="response_time">响应时间</option>
              <option value="success_rate">成功率</option>
              <option value="business_score">业务评分</option>
              <option value="quality_score">质量评分</option>
              <option value="last_check">最后检测</option>
            </Select>
          </div>
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="inline-flex items-center justify-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-emerald-700 disabled:cursor-not-allowed disabled:bg-zinc-300"
          >
            <RefreshCw className="h-4 w-4" />
            {refreshing ? '刷新中' : '刷新代理'}
          </button>
        </div>
      </section>

      {error ? <ErrorState message={error} /> : null}
      {loading ? <LoadingState label="正在加载代理列表" /> : <ProxyTable proxies={proxies} onDelete={handleDelete} />}

      <div className="flex items-center justify-between text-sm text-zinc-600">
        <span>共 {total} 条记录，第 {page} / {totalPages} 页</span>
        <div className="flex gap-2">
          <button className="rounded-lg border border-zinc-300 bg-white px-3 py-2 disabled:opacity-50" disabled={page <= 1} onClick={() => setPage((value) => Math.max(1, value - 1))}>上一页</button>
          <button className="rounded-lg border border-zinc-300 bg-white px-3 py-2 disabled:opacity-50" disabled={page >= totalPages} onClick={() => setPage((value) => value + 1)}>下一页</button>
        </div>
      </div>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-lg border border-zinc-200 bg-white p-4">
      <div className="text-sm text-zinc-500">{label}</div>
      <div className="mt-2 text-2xl font-bold">{value}</div>
    </div>
  );
}

function Select({ label, value, onChange, children }: { label: string; value: string; onChange: (value: string) => void; children: ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1 block text-sm font-medium text-zinc-700">{label}</span>
      <select className="w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm" value={value} onChange={(event) => onChange(event.target.value)}>
        {children}
      </select>
    </label>
  );
}

function ProxyTable({ proxies, onDelete }: { proxies: ProxyNode[]; onDelete: (proxy: ProxyNode) => void }) {
  if (proxies.length === 0) {
    return <div className="rounded-lg border border-zinc-200 bg-white p-8 text-center text-sm text-zinc-500">暂无代理数据</div>;
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-zinc-200 bg-white">
      <table className="w-full min-w-[1120px] text-left text-sm">
        <thead className="border-b border-zinc-200 bg-zinc-50 text-zinc-600">
          <tr>
            <th className="px-4 py-3">代理</th>
            <th className="px-4 py-3">来源</th>
            <th className="px-4 py-3">位置</th>
            <th className="px-4 py-3">协议</th>
            <th className="px-4 py-3">匿名性</th>
            <th className="px-4 py-3">速度</th>
            <th className="px-4 py-3">安全风险</th>
            <th className="px-4 py-3">行为分类</th>
            <th className="px-4 py-3">触发模式</th>
            <th className="px-4 py-3">异常/检测</th>
            <th className="px-4 py-3">状态</th>
            <th className="px-4 py-3">最后检测</th>
            <th className="px-4 py-3 text-right">操作</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-zinc-200">
          {proxies.map((proxy) => (
            <tr key={proxy.id} className="hover:bg-zinc-50">
              <td className="px-4 py-3 font-mono">
                <Link className="text-emerald-700 hover:text-emerald-800" to={`/proxies/${encodeURIComponent(proxy.ip)}/${proxy.port}`}>
                  {proxy.ip}:{proxy.port}
                </Link>
              </td>
              <td className="px-4 py-3 text-zinc-600">{proxy.source}</td>
              <td className="px-4 py-3 text-zinc-600">{proxy.location.country}, {proxy.location.city}</td>
              <td className="px-4 py-3">
                <div className="flex flex-wrap gap-1">
                  {proxy.types.map((type) => <Badge key={type} tone="info">{type}</Badge>)}
                </div>
              </td>
              <td className="px-4 py-3">{ANONYMITY_LABELS[proxy.anonymity] ?? ANONYMITY_LABELS.unknown}</td>
              <td className="px-4 py-3">{proxy.speed > 0 ? `${proxy.speed}ms` : '超时'}</td>
              <td className="px-4 py-3">
                <Badge tone={riskTone(proxy.securityRisk)}>{RISK_LEVEL_LABELS[proxy.securityRisk] ?? proxy.securityRisk}</Badge>
              </td>
              <td className="px-4 py-3">{BEHAVIOR_CLASS_LABELS[proxy.behaviorClass] ?? proxy.behaviorClass}</td>
              <td className="px-4 py-3 text-zinc-600">{proxy.securitySummary?.triggerPattern ?? 'not_observed'}</td>
              <td className="px-4 py-3 text-zinc-600">
                {proxy.securitySummary?.anomalyTriggerCount ?? 0} / {proxy.securitySummary?.securityCheckCount ?? 0}
              </td>
              <td className="px-4 py-3">
                <Badge tone={statusTone(proxy.status)}>{PROXY_STATUS_LABELS[proxy.status]}</Badge>
              </td>
              <td className="px-4 py-3 text-zinc-600">{proxy.lastCheck}</td>
              <td className="px-4 py-3 text-right">
                <Link className="mr-2 inline-flex rounded-lg px-2 py-2 text-xs font-medium text-emerald-700 hover:bg-emerald-50" to={`/proxies/${encodeURIComponent(proxy.ip)}/${proxy.port}`}>
                  详情
                </Link>
                <button className="inline-flex rounded-lg p-2 text-zinc-500 hover:bg-rose-50 hover:text-rose-700" onClick={() => onDelete(proxy)} aria-label={`删除 ${proxy.ip}:${proxy.port}`}>
                  <Trash2 className="h-4 w-4" />
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="flex items-center gap-2 border-t border-zinc-200 px-4 py-3 text-xs text-zinc-500">
        <ShieldCheck className="h-4 w-4 text-emerald-600" />
        未检测不会显示为安全；风险为 unknown 时表示尚无完成的安全检测结论。
      </div>
    </div>
  );
}
