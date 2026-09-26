// src/admin/hooks/useJobs.ts
// GET /admin/scrape — tüm job listesi, 5sn polling

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { adminFetch } from '../api/adminClient';
import type { JobRecord, ScrapeResponse } from '../types';

export function useJobs() {
  return useQuery<JobRecord[]>({
    queryKey: ['admin', 'jobs'],
    queryFn: () => adminFetch<JobRecord[]>('/admin/scrape'),
    refetchInterval: 5000,
    staleTime: 2000,
  });
}

export function useDeleteJob() {
  const queryClient = useQueryClient();
  return useMutation<{ success: boolean; message: string }, Error, string>({
    mutationFn: (jobId: string) =>
      adminFetch(`/admin/scrape/${jobId}`, {
        method: 'DELETE',
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'jobs'] });
    },
  });
}

export function useCancelJob() {
  const queryClient = useQueryClient();
  return useMutation<JobRecord, Error, string>({
    mutationFn: (jobId: string) =>
      adminFetch(`/admin/scrape/${jobId}/cancel`, {
        method: 'POST',
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'jobs'] });
    },
  });
}

export function useRetryJob() {
  const queryClient = useQueryClient();
  return useMutation<ScrapeResponse, Error, string>({
    mutationFn: (jobId: string) =>
      adminFetch(`/admin/scrape/${jobId}/retry`, {
        method: 'POST',
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'jobs'] });
    },
  });
}

