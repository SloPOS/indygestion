import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { getSettings, saveSettings } from '../api/client';

export const useSettings = () => useQuery({ queryKey: ['settings'], queryFn: getSettings });

export const useSaveSettings = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: saveSettings,
    onSuccess: (data) => queryClient.setQueryData(['settings'], data),
  });
};
