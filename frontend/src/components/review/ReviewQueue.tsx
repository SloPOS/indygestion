import { useState } from 'react';
import type { ReviewGroup } from '../../types';
import { GroupProposal } from './GroupProposal';
import { Card } from '../common/Card';

export function ReviewQueue({ groups, onApprove, onReject }: { groups: ReviewGroup[]; onApprove: (id: string, targetProjectId?: string) => void; onReject: (id: string) => void }) {
  const [localGroups] = useState(groups);
  return <div className="grid xl:grid-cols-3 gap-4">{localGroups.map((group) => <GroupProposal key={group.id} group={group} onApprove={onApprove} onReject={onReject} />)}<Card><h3 className="font-semibold mb-2">Manual Reassignment</h3><p className="text-sm text-slate-300">Drag clips between groups to correct misclassification before approval. Current build supports sortable clip stacks per group and assignment controls.</p></Card></div>;
}
