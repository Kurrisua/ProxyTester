import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { Activity, AlertTriangle, CheckCircle2, Globe2, ShieldAlert, ShieldQuestion, type LucideIcon } from 'lucide-react';
import { getSecurityOverview } from '../../../api/security';
import { ChartPanel } from '../../../components/charts/ChartPanel';
import { DonutChart } from '../../../components/charts/DonutChart';
import { FunnelChart } from '../../../components/charts/FunnelChart';
import { HorizontalBarChart, type HorizontalBarDatum } from '../../../components/charts/HorizontalBarChart';
import { TrendLineChart } from '../../../components/charts/TrendLineChart';
import { Badge } from '../../../components/ui/Badge';
import { ErrorState } from '../../../components/ui/ErrorState';
import { LoadingState } from '../../../components/ui/LoadingState';
import { BEHAVIOR_CLASS_LABELS, RISK_LEVEL_LABELS, SCAN_OUTCOME_LABELS } from '../../../types/labels';
import { BehaviorClass, RiskLevel, SecurityOverview } from '../../../types';

const RISK_BAR_COLORS: Record<RiskLevel, string> = {
  unknown: 'bg-zinc-400',
  low: 'bg-emerald-600',
  medium: 'bg-amber-500',
  high: 'bg-orange-600',
  critical: 'bg-rose-600',
};

const RISK_HEX_COLORS: Record<RiskLevel, string> = {
  unknown: '#a1a1aa',
  low: '#059669',
  medium: '#f59e0b',
  high: '#ea580c',
  critical: '#e11d48',
};

export function SecurityOverviewPage() {
  const [overview, setOverview] = useState<SecurityOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    getSecurityOverview()
      .then((data) => {
        setOverview(data);
        setError(null);
      })
      .catch(() => setError('安全总览加载失败，请确认后端安全查询接口可用。'))
      .finally(() => setLoading(false));
  }, []);

  const outcomeCounts = useMemo<Record<string, number>>(() => {
    const counts: Record<string, number> = {};
    overview?.scanRecordCounts.forEach((item) => {
      counts[item.outcome] = (counts[item.outcome] ?? 0) + item.count;
    });
    return counts;
  }, [overview]);

  const chartData = useMemo(() => {
    if (!overview) return null;
    const riskBars: HorizontalBarDatum[] = (['critical', 'high', 'medium', 'low', 'unknown'] as RiskLevel[]).map((risk) => ({
      label: RISK_LEVEL_LABELS[risk],
      value: Number(overview.riskCounts[risk] ?? 0),
      colorClass: RISK_BAR_COLORS[risk],
    }));
    const eventBars: HorizontalBarDatum[] = overview.topEvents.slice(0, 8).map((event) => ({
      label: formatEventLabel(event.eventType),
      value: event.count,
      colorClass: RISK_BAR_COLORS[event.riskLevel],
      suffix: <Badge tone={riskTone(event.riskLevel)}>{RISK_LEVEL_LABELS[event.riskLevel]}</Badge>,
    }));
    const countryBars: HorizontalBarDatum[] = overview.geoRiskRanking.slice(0, 8).map((country) => ({
      label: country.countryName,
      value: country.maliciousProxies * 3 + country.suspiciousProxies * 2 + country.uncheckedProxies,
      colorClass: country.maliciousProxies > 0 ? 'bg-rose-600' : country.suspiciousProxies > 0 ? 'bg-amber-500' : 'bg-zinc-400',
      suffix: <span className="text-xs text-zinc-500">{country.totalProxies} 个</span>,
    }));
    const behaviorDonut = Object.entries(overview.behaviorCounts).map(([behavior, value]) => {
      const risk = behavior === 'normal' ? 'low' : behavior === 'stealthy_malicious' || behavior === 'mitm_suspected' ? 'critical' : 'medium';
      return { label: BEHAVIOR_CLASS_LABELS[behavior as BehaviorClass] ?? behavior, value: Number(value), color: RISK_HEX_COLORS[risk] };
    });
    const protocolDonut = [
      { label: 'HTTP', value: overview.protocolCounts.http, color: '#0284c7' },
      { label: 'HTTPS', value: overview.protocolCounts.https, color: '#059669' },
      { label: 'SOCKS5', value: overview.protocolCounts.socks5, color: '#7c3aed' },
      { label: '未知', value: overview.protocolCounts.unknown ?? 0, color: '#a1a1aa' },
    ];
    const funnel = overview.funnelStats.map((item) => ({ label: formatStageLabel(item.stage, item.funnelStage), total: item.total, anomalous: item.anomalous, skipped: item.skipped, notApplicable: item.notApplicable, error: item.error + item.timeout }));
    const trend = overview.riskTrend.map((item) => ({ label: item.date, value: item.anomalousRecords, secondaryValue: item.highRiskRecords }));
    return { riskBars, eventBars, countryBars, behaviorDonut, protocolDonut, funnel, trend };
  }, [overview]);

  if (loading) return <LoadingState label="正在加载安全总览" />;
  if (error) return <ErrorState message={error} />;
  if (!overview || !chartData) return <ErrorState message="安全总览暂无数据。" />;

  return (
    <div className="space-y-6">
      <header className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-sm font-medium text-emerald-700">安全态势</p>
          <h1 className="mt-1 text-2xl font-bold text-zinc-950">代理行为研究总览</h1>
          <p className="mt-2 max-w-3xl text-sm text-zinc-600">这里展示代理池从可用性资源升级为行为研究对象后的总体风险、漏斗路径和异常分布。未检测和不适用会单独统计。</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link to="/events" className="rounded-lg border border-zinc-300 px-3 py-2 text-sm font-medium text-zinc-700 hover:bg-zinc-50">查看事件</Link>
          <Link to="/batches" className="rounded-lg border border-emerald-700 bg-emerald-700 px-3 py-2 text-sm font-medium text-white hover:bg-emerald-800">查看批次</Link>
        </div>
      </header>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-6">
        <Metric icon={Activity} label="总代理" value={overview.totalProxies} tone="neutral" />
        <Metric icon={Globe2} label="活跃代理" value={overview.activeProxies} tone="info" />
        <Metric icon={CheckCircle2} label="正常代理" value={overview.normalProxies} tone="success" />
        <Metric icon={ShieldQuestion} label="未检测" value={overview.uncheckedProxies} tone="neutral" />
        <Metric icon={AlertTriangle} label="可疑代理" value={overview.suspiciousProxies} tone="warning" />
        <Metric icon={ShieldAlert} label="高危/恶意" value={overview.maliciousProxies} tone="danger" />
      </section>

      <section className="grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
        <ChartPanel title="最近 14 天异常趋势" subtitle="红线为异常记录，黄线为高风险记录。"><TrendLineChart data={chartData.trend} /></ChartPanel>
        <ChartPanel title="风险等级分布" subtitle="来自 proxies 最新汇总状态。"><HorizontalBarChart data={chartData.riskBars} /></ChartPanel>
      </section>

      <section className="grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
        <ChartPanel title="漏斗阶段统计" subtitle="展示正常、异常、跳过、不适用和错误记录。"><FunnelChart data={chartData.funnel} /></ChartPanel>
        <ChartPanel title="检测结果分布"><OutcomeDistribution counts={outcomeCounts} /></ChartPanel>
      </section>

      <section className="grid gap-4 xl:grid-cols-3">
        <ChartPanel title="行为分类分布"><DonutChart data={chartData.behaviorDonut} /></ChartPanel>
        <ChartPanel title="协议分布"><DonutChart data={chartData.protocolDonut} /></ChartPanel>
        <ChartPanel title="主要异常事件"><HorizontalBarChart data={chartData.eventBars} emptyLabel="暂无异常事件。" /></ChartPanel>
      </section>

      <section className="grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
        <ChartPanel title="国家/地区风险排行"><HorizontalBarChart data={chartData.countryBars} emptyLabel="暂无地理聚合数据。" /></ChartPanel>
        <ChartPanel title="最近检测批次">
          {overview.recentBatches.length === 0 ? <p className="rounded-lg bg-zinc-50 p-4 text-sm text-zinc-500">暂无检测批次。</p> : (
            <div className="grid gap-3">
              {overview.recentBatches.map((batch) => (
                <Link key={batch.batchId} to="/batches" className="rounded-lg border border-zinc-200 p-3 hover:bg-zinc-50">
                  <div className="flex items-center justify-between gap-3"><span className="min-w-0 truncate font-mono text-xs text-zinc-600">{batch.batchId}</span><Badge tone={batch.status === 'completed' ? 'success' : batch.status === 'error' ? 'danger' : 'neutral'}>{batch.status}</Badge></div>
                  <div className="mt-2 grid gap-2 text-sm text-zinc-600 sm:grid-cols-3"><span>目标 {batch.targetProxyCount}</span><span>完成 {batch.checkedProxyCount}</span><span>异常事件 {batch.anomalyEventCount}</span></div>
                </Link>
              ))}
            </div>
          )}
        </ChartPanel>
      </section>
    </div>
  );
}

function OutcomeDistribution({ counts }: { counts: Record<string, number> }) {
  const data = Object.entries(counts).map(([outcome, count]) => ({
    label: SCAN_OUTCOME_LABELS[outcome as keyof typeof SCAN_OUTCOME_LABELS] ?? outcome,
    value: count,
    colorClass: outcome === 'anomalous' ? 'bg-rose-600' : outcome === 'error' || outcome === 'timeout' ? 'bg-zinc-700' : outcome === 'skipped' ? 'bg-amber-500' : outcome === 'not_applicable' ? 'bg-sky-500' : 'bg-emerald-600',
  }));
  return <HorizontalBarChart data={data} emptyLabel="暂无扫描记录。未检测不会显示为安全。" />;
}

function Metric({ icon: Icon, label, value, tone }: { icon: LucideIcon; label: string; value: number; tone: 'success' | 'neutral' | 'warning' | 'danger' | 'info' }) {
  const toneClass = {
    success: 'text-emerald-700 bg-emerald-50 border-emerald-200',
    neutral: 'text-zinc-700 bg-white border-zinc-200',
    warning: 'text-amber-800 bg-amber-50 border-amber-200',
    danger: 'text-rose-700 bg-rose-50 border-rose-200',
    info: 'text-sky-700 bg-sky-50 border-sky-200',
  }[tone];
  return <div className={`rounded-lg border p-4 ${toneClass}`}><div className="flex items-center gap-2 text-sm font-medium"><Icon className="h-4 w-4" />{label}</div><div className="mt-3 text-3xl font-bold">{value}</div></div>;
}

function riskTone(risk: RiskLevel): 'neutral' | 'success' | 'warning' | 'danger' | 'info' {
  if (risk === 'critical' || risk === 'high') return 'danger';
  if (risk === 'medium') return 'warning';
  if (risk === 'low') return 'success';
  return 'neutral';
}

function formatStageLabel(stage: string, funnelStage: number) {
  const labels: Record<string, string> = {
    connectivity: '基础连通性',
    protocol: '协议识别',
    honeypot: '轻量蜜罐',
    dom_diff: 'DOM / HTML',
    resource_integrity: '资源完整性',
    mitm: 'MITM 检测',
    dynamic_observation: '多轮观测',
    security_scoring: '行为评分',
  };
  return labels[stage] ?? `第 ${funnelStage} 层 ${stage}`;
}

function formatEventLabel(eventType: string) {
  const labels: Record<string, string> = {
    content_hash_changed: '内容 hash 变化',
    script_injection: '脚本注入',
    ad_injection: '广告注入',
    resource_replacement: '资源替换',
    mitm_suspected: '疑似 MITM',
    cert_mismatch: '证书不一致',
    conditional_trigger: '条件触发',
    delayed_trigger: '延迟触发',
  };
  return labels[eventType] ?? eventType;
}
