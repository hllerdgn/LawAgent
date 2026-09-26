// src/admin/hooks/useScrapeActions.ts
// POST /admin/scrape  — scraping başlat
// POST /admin/scrape/{id}/preprocess — preprocessing başlat

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { adminFetch } from '../api/adminClient';
import type { ScrapeRequest, ScrapeResponse, PreprocessResponse } from '../types';

export function useStartScrape() {
  const qc = useQueryClient();

  return useMutation<ScrapeResponse, Error, ScrapeRequest>({
    mutationFn: (req) =>
      adminFetch<ScrapeResponse>('/admin/scrape', {
        method: 'POST',
        body: JSON.stringify(req),
      }),
    onSuccess: () => {
      // Job listesini hemen yenile
      qc.invalidateQueries({ queryKey: ['admin', 'jobs'] });
    },
  });
}

export function usePreprocess(jobId: string) {
  const qc = useQueryClient();

  return useMutation<PreprocessResponse, Error, void>({
    mutationFn: () =>
      adminFetch<PreprocessResponse>(`/admin/scrape/${jobId}/preprocess`, {
        method: 'POST',
      }),
    onSuccess: () => {
      // Detail cache'ini hemen temizle, sağ panel güncellensin
      qc.invalidateQueries({ queryKey: ['admin', 'job', jobId] });
      qc.invalidateQueries({ queryKey: ['admin', 'jobs'] });
    },
  });
}
