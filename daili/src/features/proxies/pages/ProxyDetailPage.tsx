import { ReactNode, useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ArrowLeft, ShieldCheck } from 'lucide-react';
import { getProxyDetail } from '../../../api/proxies';
import { FunnelStepper } from '../../../components/security/FunnelStepper';
import { Badge } from '../../../components/ui/Badge';
import { ErrorState } from '../../../components/ui/ErrorState';
import { LoadingState } from '../../../components/ui/LoadingState';
import { ANONYMITY_LABELS, BEHAVIOR_CLASS_LABELS, EXECUTION_STATUS_LABELS, PROXY_STATUS_LABELS, RISK_LEVEL_LABELS, SCAN_OUTCOME_LABELS } from '../../../types/labels';
import { ProxyDetailResponse, ProxyStatus } from '../../../types';

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

export function ProxyDetailPage() {
  const { ip = '', port = '' } = useParams();
  const [detail, setDetail] = useState<ProxyDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const numericPort = Number(port);

  useEffect(() => {
    if (!ip || !Number.isFinite(numericPort)) {
      setError('代理地址无效。');
      setLoading(false);
      return;
    }

    setLoading(true);
    getProxyDetail(ip, numericPort)
      .then((payload) => {
        setDetail(payload);
        setError(null);
      })
      .catch(() => setError('代理详情加载失败，请确认该代理仍然存在。'))
      .finally(() => setLoading(false));
  }, [ip, numericPort]);

  const funnelSteps = useMemo(
    () =>
      detail?.security.stageStats.map((item) => ({
        stage: item.stage,
        funnelStage: item.funnelStage,
        executionStatus: item.executionStatus,
        outcome: item.outcome,
        count: item.count,
      })) ?? [],
    [detail],
  );

  if (loading) return <LoadingState label="正在加载代理详情" />;
  if (error) return <ErrorState message={error} />;
  if (!detail) return <ErrorState message="代理详情暂无数据。" />;

  const { proxy, security } = detail;

  return (
    <div className="space-y-6">
      <Link to="/proxies" className="inline-flex items-center gap-2 text-sm font-medium text-emerald-700 hover:text-emerald-800">
        <ArrowLeft className="h-4 w-4" />
        返回代理列表
      </Link>

      <section className="rounded-lg border border-zinc-200 bg-white p-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="flex flex-wrap items-center gap-3">
              <h2 className="font-mono text-2xl font-bold">
                {proxy.ip}:{proxy.port}
              </h2>
              <Badge tone={statusTone(proxy.status)}>{PROXY_STATUS_LABELS[proxy.status]}</Badge>
              <Badge tone={riskTone(proxy.securityRisk)}>{RISK_LEVEL_LABELS[proxy.securityRisk]}</Badge>
            </div>
            <p className="mt-2 text-sm text-zinc-500">把代理作为行为研究对象追踪，而不只是判断可用或不可用。</p>
          </div>
          <div className="flex items-center gap-2 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700">
            <ShieldCheck className="h-4 w-4" />
            {(security.records ?? []).length > 0 ? '已有安全记录' : '暂无安全记录'}
          </div>
        </div>

        <div className="mt-5 grid gap-3 md:grid-cols-4">
          <Metric label="来源" value={proxy.source || '-'} />
          <Metric label="位置" value={`${proxy.location.country}, ${proxy.location.city}`} />
          <Metric label="匿名级别" value={ANONYMITY_LABELS[proxy.anonymity]} />
          <Metric label="平均响应" value={proxy.speed > 0 ? `${proxy.speed}ms` : '超时'} />
          <Metric label="安全分数" value={proxy.securityScore ?? '未评分'} />
          <Metric label="行为分类" value={BEHAVIOR_CLASS_LABELS[proxy.behaviorClass] ?? proxy.behaviorClass} />
          <Metric label="异常次数" value={`${proxy.securitySummary?.anomalyTriggerCount ?? 0} / ${proxy.securitySummary?.securityCheckCount ?? 0}`} />
          <Metric label="触发模式" value={proxy.securitySummary?.triggerPattern ?? 'not_observed'} />
          <Metric label="置信度" value={proxy.securitySummary?.confidenceLevel ?? 'unknown'} />
          <Metric label="最近安全检测" value={proxy.securitySummary?.lastSecurityCheck ?? '暂无'} />
        </div>
      </section>

      <section className="rounded-lg border border-zinc-200 bg-white p-4">
        <h3 className="mb-3 text-base font-bold">代理漏斗路径</h3>
        <FunnelStepper steps={funnelSteps} />
      </section>

      <section className="grid gap-4 xl:grid-cols-2">
        <Panel title="最近安全事件">
          {(security.events ?? []).length === 0 ? (
            <p className="text-sm text-zinc-500">暂无安全事件。未检测不表示安全。</p>
          ) : (
            <div className="space-y-2">
              {(security.events ?? []).map((event) => (
                <div key={event.id} className="rounded-lg border border-zinc-200 p-3">
                  <div className="flex items-center justify-between gap-3">
                    <span className="font-mono text-sm">{event.eventType}</span>
                    <Badge tone={riskTone(event.riskLevel)}>{RISK_LEVEL_LABELS[event.riskLevel]}</Badge>
                  </div>
                  <p className="mt-2 text-sm text-zinc-600">{event.summary ?? event.targetUrl ?? event.selector ?? '-'}</p>
                </div>
              ))}
            </div>
          )}
        </Panel>

        <Panel title="关联检测批次">
          {(security.batches ?? []).length === 0 ? (
            <p className="text-sm text-zinc-500">暂无关联批次。</p>
          ) : (
            <div className="space-y-2">
              {(security.batches ?? []).map((batch) => (
                <Link key={batch.batchId} to="/batches" className="block rounded-lg border border-zinc-200 p-3 hover:bg-zinc-50">
                  <div className="flex items-center justify-between gap-3">
                    <span className="truncate font-mono text-xs text-zinc-600">{batch.batchId}</span>
                    <Badge>{batch.status}</Badge>
                  </div>
                  <div className="mt-2 text-xs text-zinc-500">
                    目标 {batch.targetProxyCount}，异常事件 {batch.anomalyEventCount}
                  </div>
                </Link>
              ))}
            </div>
          )}
        </Panel>
      </section>

      <section className="overflow-hidden rounded-lg border border-zinc-200 bg-white">
        <div className="border-b border-zinc-200 p-4">
          <h3 className="text-base font-bold">资源完整性观测</h3>
          <p className="mt-1 text-sm text-zinc-500">资源请求失败会单独记录，不会直接判定为资源替换。</p>
        </div>
        {(security.resources ?? []).length === 0 ? (
          <div className="p-6 text-sm text-zinc-500">暂无资源观测。</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead className="bg-zinc-50 text-xs uppercase text-zinc-500">
                <tr>
                  <th className="px-4 py-3">资源</th>
                  <th className="px-4 py-3">类型</th>
                  <th className="px-4 py-3">状态码</th>
                  <th className="px-4 py-3">MIME</th>
                  <th className="px-4 py-3">大小</th>
                  <th className="px-4 py-3">风险</th>
                  <th className="px-4 py-3">失败类型</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-100">
                {(security.resources ?? []).map((resource) => (
                  <tr key={resource.id}>
                    <td className="max-w-md truncate px-4 py-3 text-zinc-600">{resource.resourceUrl}</td>
                    <td className="px-4 py-3">{resource.resourceType ?? '-'}</td>
                    <td className="px-4 py-3">
                      {resource.directStatusCode ?? '-'} / {resource.proxyStatusCode ?? '-'}
                    </td>
                    <td className="max-w-xs truncate px-4 py-3 text-zinc-600">
                      {resource.directMimeType ?? '-'} / {resource.proxyMimeType ?? '-'}
                    </td>
                    <td className="px-4 py-3">
                      {resource.directSize ?? '-'} / {resource.proxySize ?? '-'}
                    </td>
                    <td className="px-4 py-3">
                      <Badge tone={riskTone(resource.riskLevel)}>{RISK_LEVEL_LABELS[resource.riskLevel]}</Badge>
                    </td>
                    <td className="px-4 py-3 text-zinc-500">{resource.failureType ?? (resource.isModified ? 'modified' : '-')}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="overflow-hidden rounded-lg border border-zinc-200 bg-white">
        <div className="border-b border-zinc-200 p-4">
          <h3 className="text-base font-bold">TLS 证书观测</h3>
          <p className="mt-1 text-sm text-zinc-500">HTTP-only 代理会记录为不适用；证书异常只在 HTTPS/SOCKS 检测路径中判断。</p>
        </div>
        {(security.certificates ?? []).length === 0 ? (
          <div className="p-6 text-sm text-zinc-500">暂无证书观测。</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead className="bg-zinc-50 text-xs uppercase text-zinc-500">
                <tr>
                  <th className="px-4 py-3">模式</th>
                  <th className="px-4 py-3">目标</th>
                  <th className="px-4 py-3">指纹</th>
                  <th className="px-4 py-3">签发者</th>
                  <th className="px-4 py-3">风险</th>
                  <th className="px-4 py-3">异常</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-100">
                {(security.certificates ?? []).map((certificate) => (
                  <tr key={certificate.id}>
                    <td className="px-4 py-3">{certificate.observationMode}</td>
                    <td className="px-4 py-3 font-mono text-xs">
                      {certificate.host}:{certificate.port}
                    </td>
                    <td className="max-w-xs truncate px-4 py-3 font-mono text-xs text-zinc-600">{certificate.fingerprintSha256 ?? '-'}</td>
                    <td className="max-w-xs truncate px-4 py-3 text-zinc-600">{certificate.issuer ?? '-'}</td>
                    <td className="px-4 py-3">
                      <Badge tone={riskTone(certificate.riskLevel)}>{RISK_LEVEL_LABELS[certificate.riskLevel]}</Badge>
                    </td>
                    <td className="px-4 py-3 text-zinc-500">
                      {certificate.errorMessage ?? (certificate.isMismatch ? 'cert_mismatch' : certificate.isSelfSigned ? 'self_signed' : '-')}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="overflow-hidden rounded-lg border border-zinc-200 bg-white">
        <div className="border-b border-zinc-200 p-4">
          <h3 className="text-base font-bold">最近检测记录</h3>
        </div>
        {(security.records ?? []).length === 0 ? (
          <div className="p-6 text-sm text-zinc-500">暂无检测记录。</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead className="bg-zinc-50 text-xs uppercase text-zinc-500">
                <tr>
                  <th className="px-4 py-3">阶段</th>
                  <th className="px-4 py-3">轮次</th>
                  <th className="px-4 py-3">检查器</th>
                  <th className="px-4 py-3">状态</th>
                  <th className="px-4 py-3">结果</th>
                  <th className="px-4 py-3">风险</th>
                  <th className="px-4 py-3">原因</th>
                  <th className="px-4 py-3">时间</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-100">
                {(security.records ?? []).map((record) => (
                  <tr key={record.id}>
                    <td className="px-4 py-3">{record.stage}</td>
                    <td className="px-4 py-3">{record.roundIndex}</td>
                    <td className="px-4 py-3 font-mono text-xs">{record.checkerName}</td>
                    <td className="px-4 py-3">{EXECUTION_STATUS_LABELS[record.executionStatus]}</td>
                    <td className="px-4 py-3">{SCAN_OUTCOME_LABELS[record.outcome]}</td>
                    <td className="px-4 py-3">{RISK_LEVEL_LABELS[record.riskLevel]}</td>
                    <td className="max-w-xs truncate px-4 py-3 text-zinc-500">{record.skipReason ?? record.errorMessage ?? '-'}</td>
                    <td className="px-4 py-3 text-zinc-500">{record.createdAt ?? '-'}</td>
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
  return (
    <div className="rounded-lg border border-zinc-200 bg-zinc-50 p-3">
      <div className="text-xs text-zinc-500">{label}</div>
      <div className="mt-1 truncate text-sm font-semibold">{value}</div>
    </div>
  );
}

function Panel({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="rounded-lg border border-zinc-200 bg-white p-4">
      <h3 className="mb-3 text-base font-bold">{title}</h3>
      {children}
    </div>
  );
}
