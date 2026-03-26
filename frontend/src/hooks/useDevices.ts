import { useMutation, useQuery } from '@tanstack/react-query';
import { getDevices, triggerDeviceIngest } from '../api/client';

export const useDevices = () => useQuery({ queryKey: ['devices'], queryFn: getDevices, refetchInterval: 5000 });
export const useTriggerIngest = () => useMutation({ mutationFn: triggerDeviceIngest });
