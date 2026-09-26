// src/admin/hooks/useDocuments.ts
// GET /admin/documents, POST /admin/documents, DELETE /admin/documents/:id
// GET /admin/documents/:id/chunks (paginated)

import { useQuery, useMutation, useQueryClient, useInfiniteQuery } from '@tanstack/react-query';
import { adminFetch } from '../api/adminClient';
import type { DocumentRecord, DocumentUploadResponse, ChunksResponse } from '../types';

interface DocumentListResponse {
  documents: DocumentRecord[];
  total: number;
}

export function useDocuments() {
  return useQuery<DocumentListResponse>({
    queryKey: ['admin', 'documents'],
    queryFn: () => adminFetch<DocumentListResponse>('/admin/documents'),
    refetchInterval: (query) => {
      const data = query.state.data;
      const hasProcessing = data?.documents?.some((d) => d.status === 'processing');
      return hasProcessing ? 3000 : 10000;
    },
    staleTime: 2000,
  });
}

export function useUploadDocument() {
  const queryClient = useQueryClient();
  return useMutation<DocumentUploadResponse, Error, File>({
    mutationFn: (file: File) => {
      const formData = new FormData();
      formData.append('file', file);
      return adminFetch<DocumentUploadResponse>('/admin/documents', {
        method: 'POST',
        body: formData,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'documents'] });
    },
  });
}

export function useDeleteDocument() {
  const queryClient = useQueryClient();
  return useMutation<{ success: boolean; message: string }, Error, string>({
    mutationFn: (docId: string) =>
      adminFetch<{ success: boolean; message: string }>(`/admin/documents/${docId}`, {
        method: 'DELETE',
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'documents'] });
    },
  });
}

const CHUNK_PAGE_SIZE = 50;

export function useDocumentChunks(docId: string | null) {
  return useInfiniteQuery<ChunksResponse, Error>({
    queryKey: ['admin', 'document-chunks', docId],
    queryFn: ({ pageParam = 0 }) =>
      adminFetch<ChunksResponse>(
        `/admin/documents/${docId}/chunks?limit=${CHUNK_PAGE_SIZE}&offset=${pageParam as number}`
      ),
    initialPageParam: 0,
    getNextPageParam: (lastPage) => {
      const nextOffset = lastPage.offset + lastPage.limit;
      return nextOffset < lastPage.total ? nextOffset : undefined;
    },
    enabled: !!docId,
    staleTime: 30000,
  });
}

export function useShiftBoundary(docId: string) {
  const queryClient = useQueryClient();
  return useMutation<
    import('../types').BoundaryShiftResponse,
    Error,
    import('../types').BoundaryShiftRequest
  >({
    mutationFn: (body) =>
      adminFetch<import('../types').BoundaryShiftResponse>(
        `/admin/documents/${docId}/chunks/boundary`,
        {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        }
      ),
    onSuccess: () => {
      // Chunk cache'ini temizle — yeniden yüklensin
      queryClient.invalidateQueries({ queryKey: ['admin', 'document-chunks', docId] });
    },
  });
}
