import { Key, ReactNode } from 'react';
import { cn } from '../../lib/utils';

const TONES = {
  neutral: 'border-zinc-300 bg-zinc-50 text-zinc-700',
  success: 'border-emerald-200 bg-emerald-50 text-emerald-700',
  warning: 'border-amber-200 bg-amber-50 text-amber-800',
  danger: 'border-rose-200 bg-rose-50 text-rose-700',
  info: 'border-sky-200 bg-sky-50 text-sky-700',
} as const;

export function Badge({ children, tone = 'neutral' }: { children: ReactNode; tone?: keyof typeof TONES; key?: Key }) {
  return <span className={cn('inline-flex items-center rounded-md border px-2 py-1 text-xs font-medium', TONES[tone])}>{children}</span>;
}
