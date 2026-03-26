import type { IngestJob } from '../../types';
import { Card } from '../common/Card';
import { ProgressBar } from '../common/ProgressBar';

export function QueueStatus({ jobs }: { jobs: IngestJob[] }) {
  return <Card><h3 className="font-semibold mb-3">Queue Status</h3><div className="space-y-3">{jobs.map((job) => <div key={job.id}><div className="flex justify-between text-sm"><span>{job.jobType} • {job.clipId}</span><span>{job.progress}%</span></div><ProgressBar value={job.progress} color={job.status === 'completed' ? 'bg-emerald-500' : 'bg-[#e94560]'} /></div>)}</div></Card>;
}
