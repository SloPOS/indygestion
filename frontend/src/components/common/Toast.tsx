import { useEffect } from 'react';

export function Toast({ message, onClose }: { message: string; onClose: () => void }) {
  useEffect(() => { const t = setTimeout(onClose, 3000); return () => clearTimeout(t); }, [onClose]);
  return <div className="fixed bottom-5 right-5 z-50 bg-[#0f3460] border border-[#2b5788] px-4 py-3 rounded-lg text-sm shadow">{message}</div>;
}
