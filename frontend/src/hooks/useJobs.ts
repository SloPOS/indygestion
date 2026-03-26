import { useQuery } from '@tanstack/react-query';
import { getJobs, getStorageStats } from '../api/client';

export const useJobs = () => useQuery({ queryKey: ['jobs'], queryFn: getJobs, refetchInterval: 7000 });
export const useStorage = () => useQuery({ queryKey: ['storage'], queryFn: getStorageStats, refetchInterval: 15000 });
