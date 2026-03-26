import { useMutation, useQuery } from '@tanstack/react-query';
import { getArchiveEstimates, getProject, getProjects } from '../api/client';

export const useProjects = () => useQuery({ queryKey: ['projects'], queryFn: getProjects });
export const useProject = (id: string) => useQuery({ queryKey: ['project', id], queryFn: () => getProject(id), enabled: !!id });
export const useArchiveEstimates = (projectId: string) => useQuery({ queryKey: ['archive-estimates', projectId], queryFn: () => getArchiveEstimates(projectId), enabled: !!projectId });
export const useStartArchive = () => useMutation({ mutationFn: async (payload: { projectId: string; preset: string }) => payload });
