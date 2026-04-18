import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { Filter, RefreshCw } from 'lucide-react';
import { getSecurityEvents } from '../../../api/security';
import { Badge } from '../../../components/ui/Badge';
import { ErrorState } from '../../../components/ui/ErrorState';
import { LoadingState } from '../../../components/ui/LoadingState';
import { BEHAVIOR_CLASS_LABELS, RISK_LEVEL_LABELS } from '../../../types/labels';
import { BehaviorClass, RiskLevel, SecurityEvent } from '../../../types';

const PAGE_LIMIT = 50;
const riskOptions: Array<RiskLevel | ''> = ['', 'unknown', 'low', 'medium', 'high', 'critical'];

export function SecurityEventsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [events, setEvents] = useState<SecurityEvent[]>([]);
  const [riskLevel, setRiskLevel] = useState<RiskLevel | ''>((searchParams.get('riskLevel') as RiskLevel | null) ?? '');
  const [eventType, setEventType] = useState(searchParams.get('eventType') ?? '');
  const [country, setCountry] = useState(searchParams.get('country') ?? '');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadEvents = (nextFilters: { riskLevel?: RiskLevel | ''; eventType?: string; country?: string } = {}) => {
    const effectiveRiskLevel = nextFilters.riskLevel ?? riskLevel;
    const effectiveEventType = nextFilters.eventType ?? eventType;
    const effectiveCountry = nextFilters.country ?? country;
    setLoading(true);
    getSecurityEvents({ page: 1, limit: PAGE_LIMIT, riskLevel: effectiveRiskLevel, eventType: effectiveEventType, country: effectiveCountry })
      .then((payload) => {
        setEvents(payload.data);
        setError(null);
      })
      .catch(() => setError('安全事件加载失败，请确认后端安全查询接口可用。'))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    const next = new URLSearchParams();
    if (riskLevel) next.set('riskLevel', riskLevel);
    if (eventType) next.set('eventType', eventType);
    if (country) next.set('country', country);
    setSearchParams(next, { replace: true });
  }, [riskLevel, eventType, country, setSearchParams]);

  useEffect(() => {
    loadEvents();
  }, []);

  if (loading) return <LoadingState label="正在加载安全事件" />;
  if (error && events.length === 0) return <ErrorState message={error} />;

  return (
    <div className="space-y-4">
      <section className="rounded-lg border border-zinc-200 bg-white p-4">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h2 className="text-lg font-bold">安全事件</h2>
            <p className="mt-1 text-sm text-zinc-500">异常行为、风险标签和证据摘要会在这里汇总，未检测状态不会被当成安全结论。</p>
          </div>
          <div className="flex flex-wrap items-end gap-3">
            <TextFilter label="事件类型" value={eventType} onChange={setEventType} placeholder="script_injection" />
            <TextFilter label="国家/地区" value={country} onChange={setCountry} placeholder="Unknown" />
            <label className="grid gap-1 text-sm">
              <span className="text-xs text-zinc-500">风险等级</span>
              <select value={riskLevel} onChange={(event) => setRiskLevel(event.target.value as RiskLevel | '')} className="h-10 rounded-lg border border-zinc-200 px-3 text-sm outline-none focus:border-emerald-400">
                {riskOptions.map((risk) => <option key={risk || 'all'} value={risk}>{risk ? RISK_LEVEL_LABELS[risk] : '全部'}</option>)}
              </select>
            </label>
            <button type="button" onClick={() => loadEvents()} className="inline-flex h-10 items-center gap-2 rounded-lg border border-zinc-200 bg-white px-3 text-sm text-zinc-700 hover:bg-zinc-50">
              <Filter className="h-4 w-4" />
              应用筛选
            </button>
            <button
              type="button"
              onClick={() => {
                setRiskLevel('');
                setEventType('');
                setCountry('');
                loadEvents({ riskLevel: '', eventType: '', country: '' });
              }}
              className="inline-flex h-10 items-center gap-2 rounded-lg bg-emerald-600 px-3 text-sm text-white hover:bg-emerald-700"
            >
              <RefreshCw className="h-4 w-4" />
              重置
            </button>
          </div>
        </div>
        {error ? <div className="mt-3 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">{error}</div> : null}
      </section>

      <section className="overflow-hidden rounded-lg border border-zinc-200 bg-white">
        {events.length === 0 ? <div className="p-8 text-center text-sm text-zinc-500">暂无安全事件。</div> : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead className="bg-zinc-50 text-xs uppercase text-zinc-500"><tr><th className="px-4 py-3">事件类型</th><th className="px-4 py-3">行为类别</th><th className="px-4 py-3">风险</th><th className="px-4 py-3">置信度</th><th className="px-4 py-3">目标</th><th className="px-4 py-3">摘要</th><th className="px-4 py-3">时间</th></tr></thead>
              <tbody className="divide-y divide-zinc-100">
                {events.map((event) => (
                  <tr key={event.id}>
                    <td className="px-4 py-3 font-mono text-xs"><Link className="text-emerald-700 hover:text-emerald-800" to={`/events/${event.id}`}>{event.eventType}</Link></td>
                    <td className="px-4 py-3">{event.behaviorClass ? BEHAVIOR_CLASS_LABELS[event.behaviorClass as BehaviorClass] ?? event.behaviorClass : '-'}</td>
                    <td className="px-4 py-3"><Badge tone={event.riskLevel === 'high' || event.riskLevel === 'critical' ? 'danger' : 'warning'}>{RISK_LEVEL_LABELS[event.riskLevel]}</Badge></td>
                    <td className="px-4 py-3">{event.confidence === null || event.confidence === undefined ? '-' : `${Math.round(event.confidence * 100)}%`}</td>
                    <td className="max-w-xs truncate px-4 py-3 text-zinc-600">{event.targetUrl ?? event.selector ?? '-'}</td>
                    <td className="max-w-md truncate px-4 py-3 text-zinc-600">{event.summary ?? '-'}</td>
                    <td className="px-4 py-3 text-zinc-500">{event.createdAt ?? '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}

function TextFilter({ label, value, onChange, placeholder }: { label: string; value: string; onChange: (value: string) => void; placeholder: string }) {
  return (
    <label className="grid gap-1 text-sm">
      <span className="text-xs text-zinc-500">{label}</span>
      <input value={value} onChange={(event) => onChange(event.target.value)} placeholder={placeholder} className="h-10 rounded-lg border border-zinc-200 px-3 text-sm outline-none focus:border-emerald-400" />
    </label>
  );
}
