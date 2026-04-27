import { useEffect, useMemo, useState } from 'react';
import { ChevronRight, RefreshCw } from 'lucide-react';
import { getSecurityBatchDetail, getSecurityBatches } from '../../../api/security';
import { FunnelStepper } from '../../../components/security/FunnelStepper';
import { Badge } from '../../../components/ui/Badge';
import { ErrorState } from '../../../components/ui/ErrorState';
import { LoadingState } from '../../../components/ui/LoadingState';
import { EXECUTION_STATUS_LABELS, RISK_LEVEL_LABELS, SCAN_OUTCOME_LABELS } from '../../../types/labels';
import { SecurityBatchDetail, SecurityBatchSummary } from '../../../types';

const PAGE_LIMIT = 20;

export function SecurityBatchesPage() {
  const [batches, setBatches] = useState<SecurityBatchSummary[]>([]);
  const [selectedBatchId, setSelectedBatchId] = useState<string | null>(null);
  const [detail, setDetail] = useState<SecurityBatchDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadBatches = () => {
    setLoading(true);
    getSecurityBatches({ page: 1, limit: PAGE_LIMIT })
      .then((payload) => {
        setBatches(payload.data);
        setError(null);
        if (!selectedBatchId && payload.data[0]) setSelectedBatchId(payload.data[0].batchId);
      })
      .catch(() => setError('检测批次加载失败，请确认后端安全查询接口可用。'))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadBatches();
  }, []);

  useEffect(() => {
    if (!selectedBatchId) {
      setDetail(null);
      return;
    }
    setDetailLoading(true);
    getSecurityBatchDetail(selectedBatchId, { recordLimit: 120 })
      .then((payload) => {
        setDetail(payload);
        setError(null);
      })
      .catch(() => setError('批次详情加载失败，请确认该批次仍然存在。'))
      .finally(() => setDetailLoading(false));
  }, [selectedBatchId]);

  const stageSteps = useMemo(
    () => detail?.stageStats.map((item) => ({ stage: item.stage, funnelStage: item.funnelStage, executionStatus: item.executionStatus, outcome: item.outcome, count: item.count })) ?? [],
    [detail],
  );

  if (loading) return <LoadingState label="正在加载检测批次" />;
  if (error && batches.length === 0) return <ErrorState message={error} />;

  return (
    <div className="grid gap-6 xl:grid-cols-[360px_1fr]">
      <section className="space-y-3">
        <div className="flex items-center justify-between gap-3">
          <div>
            <h2 className="text-lg font-bold">检测批次</h2>
            <p className="text-sm text-zinc-500">批次记录用于追踪每轮漏斗式检测的执行语义。</p>
          </div>
          <button type="button" onClick={loadBatches} className="inline-flex items-center gap-2 rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm text-zinc-700 hover:bg-zinc-50">
            <RefreshCw className="h-4 w-4" />
            刷新
          </button>
        </div>

        {error ? <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">{error}</div> : null}

        {batches.length === 0 ? (
          <div className="rounded-lg border border-zinc-200 bg-white p-6 text-sm text-zinc-500">暂无检测批次。</div>
        ) : (
          <div className="space-y-2">
            {batches.map((batch) => (
              <button
                type="button"
                key={batch.batchId}
                onClick={() => setSelectedBatchId(batch.batchId)}
                className={`w-full rounded-lg border p-3 text-left transition-colors ${selectedBatchId === batch.batchId ? 'border-emerald-300 bg-emerald-50' : 'border-zinc-200 bg-white hover:bg-zinc-50'}`}
              >
                <div className="flex items-center justify-between gap-3">
                  <span className="truncate font-mono text-xs text-zinc-600">{batch.batchId}</span>
                  <ChevronRight className="h-4 w-4 shrink-0 text-zinc-400" />
                </div>
                <div className="mt-2 flex flex-wrap gap-2">
                  <Badge>{batch.status}</Badge>
                  <Badge tone="neutral">{batch.maxScanDepth ?? 'basic'}</Badge>
                </div>
                <div className="mt-2 text-xs text-zinc-500">目标 {batch.targetProxyCount}，已检 {batch.checkedProxyCount}，异常 {batch.anomalyEventCount}</div>
              </button>
            ))}
          </div>
        )}
      </section>

      <section className="space-y-4">
        {detailLoading ? <LoadingState label="正在加载批次详情" /> : detail ? (
          <>
            <div className="rounded-lg border border-zinc-200 bg-white p-4">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <h2 className="text-lg font-bold">批次详情</h2>
                  <p className="mt-1 font-mono text-xs text-zinc-500">{detail.batch.batchId}</p>
                </div>
                <Badge>{detail.batch.status}</Badge>
              </div>
              <div className="mt-4 grid gap-3 md:grid-cols-4">
                <Metric label="目标代理" value={detail.batch.targetProxyCount} />
                <Metric label="完成检测" value={detail.batch.checkedProxyCount} />
                <Metric label="跳过" value={detail.batch.skippedProxyCount ?? 0} />
                <Metric label="异常事件" value={detail.batch.anomalyEventCount} />
              </div>
            </div>

            <div className="rounded-lg border border-zinc-200 bg-white p-4">
              <h3 className="mb-3 text-base font-bold">漏斗路径</h3>
              <FunnelStepper steps={stageSteps} />
            </div>

            <div className="overflow-hidden rounded-lg border border-zinc-200 bg-white">
              <div className="border-b border-zinc-200 p-4"><h3 className="text-base font-bold">最近检测记录</h3></div>
              {detail.records.length === 0 ? <div className="p-6 text-sm text-zinc-500">暂无检测记录。</div> : (
                <div className="overflow-x-auto">
                  <table className="min-w-full text-left text-sm">
                    <thead className="bg-zinc-50 text-xs uppercase text-zinc-500"><tr><th className="px-4 py-3">代理</th><th className="px-4 py-3">阶段</th><th className="px-4 py-3">状态</th><th className="px-4 py-3">结果</th><th className="px-4 py-3">风险</th><th className="px-4 py-3">原因</th></tr></thead>
                    <tbody className="divide-y divide-zinc-100">
                      {detail.records.map((record) => (
                        <tr key={record.id}>
                          <td className="px-4 py-3 font-mono text-xs">{record.proxy}</td>
                          <td className="px-4 py-3">{record.stage}</td>
                          <td className="px-4 py-3">{EXECUTION_STATUS_LABELS[record.executionStatus]}</td>
                          <td className="px-4 py-3">{SCAN_OUTCOME_LABELS[record.outcome]}</td>
                          <td className="px-4 py-3">{RISK_LEVEL_LABELS[record.riskLevel]}</td>
                          <td className="max-w-xs truncate px-4 py-3 text-zinc-500">{record.skipReason ?? record.errorMessage ?? '-'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </>
        ) : <div className="rounded-lg border border-zinc-200 bg-white p-6 text-sm text-zinc-500">请选择一个检测批次。</div>}
      </section>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return <div className="rounded-lg border border-zinc-200 bg-zinc-50 p-3"><div className="text-xs text-zinc-500">{label}</div><div className="mt-1 text-2xl font-bold">{value}</div></div>;
}
