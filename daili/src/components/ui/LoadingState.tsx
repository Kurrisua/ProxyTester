export function LoadingState({ label = '加载中' }: { label?: string }) {
  return <div className="rounded-lg border border-zinc-200 bg-white p-6 text-center text-sm text-zinc-500">{label}</div>;
}
