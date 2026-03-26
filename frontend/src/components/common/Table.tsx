import type { PropsWithChildren } from 'react';

export function Table({ children }: PropsWithChildren) { return <table className="w-full text-sm">{children}</table>; }
export function Th({ children }: PropsWithChildren) { return <th className="text-left text-slate-400 font-medium py-2 border-b border-[#2a3960]">{children}</th>; }
export function Td({ children, className = '' }: PropsWithChildren<{ className?: string }>) { return <td className={`py-2 border-b border-[#202d4d] ${className}`}>{children}</td>; }
