import type { PropsWithChildren } from 'react';

export function Badge({ children, tone = 'default' }: PropsWithChildren<{ tone?: 'default' | 'success' | 'warning' | 'danger' }>) {
  const tones = {
    default: 'bg-[#1d2844] text-slate-200 border-[#2b3a5f]',
    success: 'bg-emerald-500/20 text-emerald-300 border-emerald-600/40',
    warning: 'bg-amber-500/20 text-amber-300 border-amber-600/40',
    danger: 'bg-[#e94560]/20 text-[#ff8ca0] border-[#e94560]/50',
  };
  return <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-md border text-xs ${tones[tone]}`}>{children}</span>;
}
