import { useEffect, useState } from 'react';
import { getHoneypotManifest } from '../../../api/security';
import { Badge } from '../../../components/ui/Badge';
import { ErrorState } from '../../../components/ui/ErrorState';
import { LoadingState } from '../../../components/ui/LoadingState';
import { HoneypotTarget } from '../../../types';

export function HoneypotTargetsPage() {
  const [targets, setTargets] = useState<HoneypotTarget[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getHoneypotManifest()
      .then((payload) => {
        setTargets(payload.data ?? []);
        setError(null);
      })
      .catch(() => setError('蜜罐目标清单加载失败，请确认 /api/security/honeypot/manifest 可用。'))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <LoadingState label="正在加载蜜罐目标" />;
  if (error) return <ErrorState message={error} />;

  return (
    <div className="space-y-6">
      <header className="rounded-lg border border-zinc-200 bg-white p-5">
        <p className="text-sm font-medium text-emerald-700">Honeypot Baseline</p>
        <h1 className="mt-1 text-2xl font-bold text-zinc-950">蜜罐目标与基准资源</h1>
        <p className="mt-2 max-w-3xl text-sm text-zinc-600">这些固定页面和资源为直连与代理双路径访问提供基准。页面内容保持静态，便于 HTML hash、DOM 规则、资源完整性和下载篡改检测。</p>
      </header>

      {targets.length === 0 ? (
        <div className="rounded-lg border border-zinc-200 bg-white p-8 text-center text-sm text-zinc-500">暂无蜜罐目标。</div>
      ) : (
        <section className="grid gap-4 xl:grid-cols-2">
          {targets.map((target) => (
            <article key={target.path} className="rounded-lg border border-zinc-200 bg-white p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h2 className="font-mono text-base font-bold">{target.name}</h2>
                  <p className="mt-1 font-mono text-xs text-zinc-500">{target.path}</p>
                </div>
                <Badge tone="info">{target.targetType}</Badge>
              </div>
              <div className="mt-4 grid gap-3 sm:grid-cols-2">
                <Metric label="状态码" value={target.expectedStatusCode} />
                <Metric label="MIME" value={target.expectedMimeType} />
                <Metric label="SHA256" value={target.expectedSha256} mono />
                <Metric label="必需选择器" value={target.requiredSelectors.join(', ') || '-'} />
                <Metric label="禁止标签" value={target.forbiddenTags.join(', ') || '-'} />
                <Metric label="禁止属性前缀" value={target.forbiddenAttrsPrefix.join(', ') || '-'} />
              </div>
            </article>
          ))}
        </section>
      )}
    </div>
  );
}

function Metric({ label, value, mono }: { label: string; value: string | number; mono?: boolean }) {
  return (
    <div className="rounded-lg border border-zinc-200 bg-zinc-50 p-3">
      <div className="text-xs text-zinc-500">{label}</div>
      <div className={`mt-1 truncate text-sm font-semibold ${mono ? 'font-mono text-xs' : ''}`}>{value}</div>
    </div>
  );
}
