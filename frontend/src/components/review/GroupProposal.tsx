import type { ReviewGroup } from '../../types';
import { Button } from '../common/Button';
import { Card } from '../common/Card';
import { SimilarityBadge } from './SimilarityBadge';

export function GroupProposal({ group, onApprove, onReject }: { group: ReviewGroup; onApprove: (id: string, targetProjectId?: string) => void; onReject: (id: string) => void }) {
  return <Card className="space-y-3"><div className="flex items-start justify-between"><div><h3 className="font-semibold">{group.title}</h3><p className="text-xs text-slate-400">{group.why}</p></div><SimilarityBadge score={group.confidence} why={group.why} /></div><div className="space-y-2">{group.clips.map((clip) => <div className="p-2 rounded bg-[#121d36] border border-[#25345b]" key={clip.id}><p className="text-sm font-medium">{clip.filename}</p><p className="text-xs text-slate-400 line-clamp-2">{clip.transcriptText}</p></div>)}</div><div className="flex gap-2"><Button onClick={() => onApprove(group.id, group.targetProjectId)}>Approve</Button><Button variant="danger" onClick={() => onReject(group.id)}>Reject</Button><Button variant="secondary" onClick={() => onApprove(group.id)}>Create New Project</Button></div></Card>;
}
