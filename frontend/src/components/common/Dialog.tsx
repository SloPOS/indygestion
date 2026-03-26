import type { PropsWithChildren } from 'react';

export function Dialog({ open, onClose, title, children }: PropsWithChildren<{ open: boolean; onClose: () => void; title: string }>) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 bg-black/70 z-50 flex items-center justify-center p-8">
      <div className="max-w-4xl w-full bg-[#1a1a2e] border border-[#2c3f6f] rounded-2xl p-5">
        <div className="flex justify-between items-center mb-4"><h3 className="text-lg font-semibold">{title}</h3><button onClick={onClose}>✕</button></div>
        {children}
      </div>
    </div>
  );
}
