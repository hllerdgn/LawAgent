// src/admin/hooks/useJobDetail.ts
// GET /admin/scrape/{id}?include_data=true
// status=running iken 2sn polling, done/failed'de durur

import { useQuery } from '@tanstack/react-query';
import { adminFetch } from '../api/adminClient';
import type { JobRecord } from '../types';

export function useJobDetail(jobId: string) {
  return useQuery<JobRecord>({
    queryKey: ['admin', 'job', jobId],
    queryFn: () =>
      adminFetch<JobRecord>(`/admin/scrape/${jobId}?include_data=true`),
    // status=running iken 2sn, done/failed'de polling durur
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === 'running' || status === 'pending') return 2000;
      return false;
    },
    enabled: !!jobId,
  });
}
