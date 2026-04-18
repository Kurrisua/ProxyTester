export function ErrorState({ message }: { message: string }) {
  return <div className="rounded-lg border border-rose-200 bg-rose-50 p-6 text-sm text-rose-700">{message}</div>;
}
