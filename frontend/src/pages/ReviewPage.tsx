import { useMutation, useQueryClient } from '@tanstack/react-query';
import { approveReviewGroup, rejectReviewGroup } from '../api/client';
import { ReviewQueue } from '../components/review/ReviewQueue';
import { useReviewGroups } from '../hooks/useClips';

export function ReviewPage() {
  const queryClient = useQueryClient();
  const { data: groups = [] } = useReviewGroups();
  const approve = useMutation({ mutationFn: ({ id, targetProjectId }: { id: string; targetProjectId?: string }) => approveReviewGroup(id, targetProjectId), onSuccess: () => queryClient.invalidateQueries({ queryKey: ['review-groups'] }) });
  const reject = useMutation({ mutationFn: (id: string) => rejectReviewGroup(id), onSuccess: () => queryClient.invalidateQueries({ queryKey: ['review-groups'] }) });

  return <div className="space-y-4"><h1 className="text-2xl font-bold">Review Queue</h1><p className="text-slate-300">Approve model groupings, drag clips between groups, or split into new projects.</p><ReviewQueue groups={groups} onApprove={(id, targetProjectId) => approve.mutate({ id, targetProjectId })} onReject={(id) => reject.mutate(id)} /></div>;
}
