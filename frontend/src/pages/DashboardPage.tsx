import { RecentActivity } from '../components/dashboard/RecentActivity';
import { QueueStatus } from '../components/dashboard/QueueStatus';
import { StorageChart } from '../components/dashboard/StorageChart';
import { useJobs, useStorage } from '../hooks/useJobs';
import { useQuery } from '@tanstack/react-query';
import { getFileOperations } from '../api/client';

export function DashboardPage() {
  const { data: jobs = [] } = useJobs();
  const { data: storage } = useStorage();
  const { data: operations = [] } = useQuery({ queryKey: ['operations'], queryFn: getFileOperations });
  if (!storage) return null;
  return <div className="space-y-4"><h1 className="text-2xl font-bold">Dashboard</h1><div className="grid lg:grid-cols-3 gap-4"><StorageChart stats={storage} /><div className="lg:col-span-2"><QueueStatus jobs={jobs} /></div></div><RecentActivity operations={operations} /></div>;
}
