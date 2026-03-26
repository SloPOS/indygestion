import type { FileOperation } from '../../types';
import { Card } from '../common/Card';

export function RecentActivity({ operations }: { operations: FileOperation[] }) {
  return <Card><h3 className="font-semibold mb-3">Recent Activity</h3><div className="space-y-3">{operations.slice(0, 6).map((op) => <div key={op.id} className="border-l-2 border-[#e94560] pl-3"><p className="text-sm capitalize">{op.operation}</p><p className="text-xs text-slate-400 truncate">{op.sourcePath}</p><p className="text-xs text-slate-500">{new Date(op.performedAt).toLocaleString()}</p></div>)}</div></Card>;
}
