import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { getSecurityEventDetail } from '../../../api/security';
import { Badge } from '../../../components/ui/Badge';
import { ErrorState } from '../../../components/ui/ErrorState';
import { LoadingState } from '../../../components/ui/LoadingState';
import { EXECUTION_STATUS_LABELS, RISK_LEVEL_LABELS, SCAN_OUTCOME_LABELS } from '../../../types/labels';
import { SecurityEventDetail } from '../../../types';

function riskTone(risk: string) {
  if (risk === 'critical' || risk === 'high') return 'danger';
  if (risk === 'medium') return 'warning';
  if (risk === 'low') return 'success';
  return 'neutral';
}

export function SecurityEventDetailPage() {
  const { eventId = '' } = useParams();
  const [detail, setDetail] = useState<SecurityEventDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const numericEventId = Number(eventId);

  useEffect(() => {
    if (!Number.isFinite(numericEventId)) {
      setError('安全事件编号无效。');
      setLoading(false);
      return;
    }
    getSecurityEventDetail(numericEventId)
      .then((payload) => {
        setDetail(payload);
        setError(null);
      })
      .catch(() => setError('安全事件详情加载失败，请确认该事件仍然存在。'))
      .finally(() => setLoading(false));
  }, [numericEventId]);

  if (loading) return <LoadingState label="正在加载安全事件详情" />;
  if (error) return <ErrorState message={error} />;
  if (!detail) return <ErrorState message="安全事件详情暂无数据。" />;

  const { event, proxy, record, evidenceFiles } = detail;

  return (
    <div className="space-y-6">
      <Link to="/events" className="inline-flex items-center gap-2 text-sm font-medium text-emerald-700 hover:text-emerald-800">
        <ArrowLeft className="h-4 w-4" />
        返回事件列表
      </Link>

      <section className="rounded-lg border border-zinc-200 bg-white p-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2 className="font-mono text-2xl font-bold">{event.eventType}</h2>
            <p className="mt-2 max-w-3xl text-sm text-zinc-500">{event.summary ?? '该事件暂无摘要。'}</p>
          </div>
          <Badge tone={riskTone(event.riskLevel)}>{RISK_LEVEL_LABELS[event.riskLevel]}</Badge>
        </div>
        <div className="mt-5 grid gap-3 md:grid-cols-4">
          <Metric label="行为类别" value={event.behaviorClass ?? '-'} />
          <Metric label="置信度" value={event.confidence === null || event.confidence === undefined ? '-' : `${Math.round(event.confidence * 100)}%`} />
          <Metric label="目标类型" value={event.targetType ?? '-'} />
          <Metric label="创建时间" value={event.createdAt ?? '-'} />
          <Metric label="代理" value={proxy.ip && proxy.port ? `${proxy.ip}:${proxy.port}` : '-'} />
          <Metric label="国家/地区" value={proxy.country ?? '-'} />
          <Metric label="阶段" value={record.stage ?? '-'} />
          <Metric label="检查器" value={record.checkerName ?? '-'} />
        </div>
      </section>

      <section className="grid gap-4 xl:grid-cols-2">
        <div className="rounded-lg border border-zinc-200 bg-white p-4">
          <h3 className="text-base font-bold">检测记录</h3>
          <div className="mt-3 grid gap-2 text-sm text-zinc-600">
            <div>漏斗阶段：{record.funnelStage ?? '-'}</div>
            <div>执行状态：{record.executionStatus ? EXECUTION_STATUS_LABELS[record.executionStatus as keyof typeof EXECUTION_STATUS_LABELS] ?? record.executionStatus : '-'}</div>
            <div>检测结果：{record.outcome ? SCAN_OUTCOME_LABELS[record.outcome as keyof typeof SCAN_OUTCOME_LABELS] ?? record.outcome : '-'}</div>
            <div>风险标签：{record.riskTags?.join(', ') || '-'}</div>
          </div>
        </div>
        <div className="rounded-lg border border-zinc-200 bg-white p-4">
          <h3 className="text-base font-bold">事件目标</h3>
          <div className="mt-3 grid gap-2 text-sm text-zinc-600">
            <div>URL：{event.targetUrl ?? '-'}</div>
            <div>选择器：{event.selector ?? '-'}</div>
            <div>资源：{event.affectedResourceUrl ?? '-'}</div>
            <div>外部域名：{event.externalDomain ?? '-'}</div>
          </div>
        </div>
      </section>

      <section className="overflow-hidden rounded-lg border border-zinc-200 bg-white">
        <div className="border-b border-zinc-200 p-4"><h3 className="text-base font-bold">证据文件</h3></div>
        {evidenceFiles.length === 0 ? <div className="p-6 text-sm text-zinc-500">暂无证据文件。</div> : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead className="bg-zinc-50 text-xs uppercase text-zinc-500"><tr><th className="px-4 py-3">类型</th><th className="px-4 py-3">路径</th><th className="px-4 py-3">SHA256</th><th className="px-4 py-3">大小</th><th className="px-4 py-3">MIME</th><th className="px-4 py-3">时间</th></tr></thead>
              <tbody className="divide-y divide-zinc-100">
                {evidenceFiles.map((file) => (
                  <tr key={file.id}>
                    <td className="px-4 py-3">{file.evidenceType}</td>
                    <td className="max-w-md truncate px-4 py-3 text-zinc-600">{file.storagePath}</td>
                    <td className="max-w-xs truncate px-4 py-3 font-mono text-xs text-zinc-600">{file.sha256 ?? '-'}</td>
                    <td className="px-4 py-3">{file.sizeBytes ?? '-'}</td>
                    <td className="px-4 py-3">{file.mimeType ?? '-'}</td>
                    <td className="px-4 py-3 text-zinc-500">{file.createdAt ?? '-'}</td>
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

function Metric({ label, value }: { label: string; value: string | number }) {
  return <div className="rounded-lg border border-zinc-200 bg-zinc-50 p-3"><div className="text-xs text-zinc-500">{label}</div><div className="mt-1 truncate text-sm font-semibold">{value}</div></div>;
}
