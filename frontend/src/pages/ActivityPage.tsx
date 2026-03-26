import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { getFileOperations, undoOperation } from '../api/client';
import { Button } from '../components/common/Button';
import { Card } from '../components/common/Card';

export function ActivityPage() {
  const queryClient = useQueryClient();
  const { data: operations = [] } = useQuery({ queryKey: ['operations'], queryFn: getFileOperations });
  const undo = useMutation({ mutationFn: undoOperation, onSuccess: () => queryClient.invalidateQueries({ queryKey: ['operations'] }) });

  return <div className="space-y-4"><h1 className="text-2xl font-bold">Activity Log</h1><div className="space-y-3">{operations.map((op) => { const canUndo = new Date(op.reversibleUntil).getTime() > Date.now() && !op.undone; return <Card key={op.id}><div className="flex justify-between items-center"><div><p className="capitalize font-medium">{op.operation}</p><p className="text-xs text-slate-400">{op.sourcePath} → {op.destPath}</p><p className="text-xs text-slate-500">{new Date(op.performedAt).toLocaleString()}</p></div><Button variant={canUndo ? 'secondary' : 'ghost'} disabled={!canUndo} onClick={() => undo.mutate(op.id)}>{canUndo ? 'Undo' : 'Undo expired'}</Button></div></Card>; })}</div></div>;
}
