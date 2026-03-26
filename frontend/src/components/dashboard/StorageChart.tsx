import { formatBytes } from '../../api/client';
import type { StorageStats } from '../../types';
import { Card } from '../common/Card';

export function StorageChart({ stats }: { stats: StorageStats }) {
  const activePct = (stats.activeBytes / stats.totalBytes) * 100;
  const archivePct = (stats.archiveBytes / stats.totalBytes) * 100;
  const stagingPct = (stats.stagingBytes / stats.totalBytes) * 100;
  return <Card><h3 className="font-semibold mb-3">Storage Usage</h3><div className="relative h-44 w-44 mx-auto rounded-full" style={{ background: `conic-gradient(#0f3460 0 ${activePct}%, #e94560 ${activePct}% ${activePct + archivePct}%, #334155 ${activePct + archivePct}% ${activePct + archivePct + stagingPct}%, #0b1120 0)` }}><div className="absolute inset-5 bg-[#1a1a2e] rounded-full flex items-center justify-center text-sm">{formatBytes(stats.totalBytes)}</div></div><div className="mt-4 text-sm space-y-1"><p>Active: {formatBytes(stats.activeBytes)}</p><p>Archive: {formatBytes(stats.archiveBytes)}</p><p>Staging: {formatBytes(stats.stagingBytes)}</p></div></Card>;
}
