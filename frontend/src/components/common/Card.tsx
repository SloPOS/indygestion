import type { PropsWithChildren } from 'react';

export function Card({ children, className = '' }: PropsWithChildren<{ className?: string }>) {
  return <div className={`bg-[#16213e] border border-[#22325a] rounded-xl p-4 shadow-lg shadow-black/20 ${className}`}>{children}</div>;
}
