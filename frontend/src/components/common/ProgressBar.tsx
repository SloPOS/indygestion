export function ProgressBar({ value, color = 'bg-[#e94560]' }: { value: number; color?: string }) {
  return <div className="w-full h-2.5 rounded-full bg-[#0f172f] overflow-hidden"><div className={`h-full ${color}`} style={{ width: `${Math.max(0, Math.min(100, value))}%` }} /></div>;
}
