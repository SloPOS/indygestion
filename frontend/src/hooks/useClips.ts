import { useQuery } from '@tanstack/react-query';
import { getClips, getReviewGroups } from '../api/client';

export const useClips = () => useQuery({ queryKey: ['clips'], queryFn: getClips });
export const useReviewGroups = () => useQuery({ queryKey: ['review-groups'], queryFn: getReviewGroups });
