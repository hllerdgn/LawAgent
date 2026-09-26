// src/admin/components/JobTable.tsx
// Scraping job listesi — status badge + polling + error tooltip + detay navigasyon + aksiyon butonları

import { useNavigate } from 'react-router-dom';
import {
  Loader2,
  AlertCircle,
  CheckCircle2,
  Clock,
  XCircle,
  Ban,
  Trash2,
  RotateCcw,
} from 'lucide-react';
import { useJobs, useDeleteJob, useCancelJob, useRetryJob } from '../hooks/useJobs';
import type { JobStatus } from '../types';

function StatusBadge({ status, error }: { status: JobStatus; error?: string | null }) {
  const configs: Record<JobStatus, { label: string; className: string; icon: React.ReactNode }> = {
    pending: {
      label: 'Bekliyor',
      className: 'admin-badge admin-badge-pending',
      icon: <Clock className="w-3 h-3" />,
    },
    running: {
      label: 'Çalışıyor',
      className: 'admin-badge admin-badge-running',
      icon: <Loader2 className="w-3 h-3 animate-spin" />,
    },
    done: {
      label: 'Tamamlandı',
      className: 'admin-badge admin-badge-done',
      icon: <CheckCircle2 className="w-3 h-3" />,
    },
    failed: {
      label: 'Başarısız',
      className: 'admin-badge admin-badge-failed',
      icon: <XCircle className="w-3 h-3" />,
    },
    canceled: {
      label: 'İptal Edildi',
      className: 'admin-badge admin-badge-canceled',
      icon: <Ban className="w-3 h-3" />,
    },
  };

  const { label, className, icon } = configs[status] ?? configs.failed;

  return (
    <span
      title={status === 'failed' && error ? error : undefined}
      className={`${className} cursor-default`}
    >
      {icon}
      {label}
      {status === 'failed' && error && (
        <AlertCircle className="w-3 h-3 ml-0.5 opacity-70" />
      )}
    </span>
  );
}


function formatDate(iso: string) {
  return new Date(iso).toLocaleString('tr-TR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function JobTable() {
  const { data: jobs, isLoading, error } = useJobs();
  const deleteMutation = useDeleteJob();
  const cancelMutation = useCancelJob();
  const retryMutation = useRetryJob();
  const navigate = useNavigate();

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 text-slate-400 text-sm p-6">
        <Loader2 className="w-4 h-4 animate-spin" />
        Job listesi yükleniyor...
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center gap-2 text-red-400 text-sm p-6 bg-red-500/10 border border-red-500/30 rounded-2xl">
        <AlertCircle className="w-4 h-4 flex-shrink-0" />
        {error.message}
      </div>
    );
  }

  if (!jobs?.length) {
    return (
      <div className="admin-card p-8 text-center text-sm" style={{ color: 'var(--color-muted)' }}>
        Henüz hiç scraping işlemi başlatılmadı.
      </div>
    );
  }

  const actionError =
    deleteMutation.error?.message ||
    cancelMutation.error?.message ||
    retryMutation.error?.message;

  return (
    <div className="space-y-4">
      {actionError && (
        <div 
          className="flex items-center justify-between gap-3 p-3.5 rounded-xl text-xs border"
          style={{
            backgroundColor: 'color-mix(in oklch, #ef4444 10%, transparent)',
            borderColor: 'color-mix(in oklch, #ef4444 30%, transparent)',
            color: '#dc2626',
          }}
        >
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <span className="font-medium">İşlem hatası: {actionError}</span>
          </div>
          <button
            type="button"
            onClick={() => {
              deleteMutation.reset();
              cancelMutation.reset();
              retryMutation.reset();
            }}
            className="px-2 py-1 rounded text-xs transition-colors cursor-pointer"
            style={{
              backgroundColor: 'color-mix(in oklch, #ef4444 20%, transparent)',
              color: '#dc2626',
            }}
          >
            Kapat
          </button>
        </div>
      )}

      <div className="admin-table-wrapper">
        <div className="overflow-x-auto">
          <table className="admin-table">
            <thead>
              <tr>
                <th>Kanun No</th>
                <th>Kanun Adı</th>
                <th>Durum</th>
                <th>Tarih</th>
                <th style={{ textAlign: 'right' }}>İşlemler</th>
              </tr>
            </thead>
            <tbody>
              {jobs.map((job) => {
                const canCancel = job.status === 'pending' || job.status === 'running';
                const canRetry = job.status === 'failed' || job.status === 'canceled';
                const canDelete =
                  job.status === 'done' ||
                  job.status === 'failed' ||
                  job.status === 'canceled';

                const isDeleting =
                  deleteMutation.isPending && deleteMutation.variables === job.id;
                const isCanceling =
                  cancelMutation.isPending && cancelMutation.variables === job.id;
                const isRetrying =
                  retryMutation.isPending && retryMutation.variables === job.id;

                return (
                  <tr
                    key={job.id}
                    onClick={() => navigate(`/admin/dashboard/scrape/${job.id}`)}
                    className="cursor-pointer group"
                  >
                    <td className="font-mono font-medium" style={{ color: 'var(--color-accent)' }}>
                      {job.law_id}
                    </td>
                    <td className="max-w-[240px] truncate font-medium">
                      {job.law_name}
                    </td>
                    <td>
                      <StatusBadge status={job.status} error={job.error} />
                    </td>
                    <td className="text-xs tabular-nums" style={{ color: 'var(--color-muted)' }}>
                      {formatDate(job.created_at)}
                    </td>
                    <td
                      style={{ textAlign: 'right', whiteSpace: 'nowrap' }}
                      onClick={(e) => e.stopPropagation()}
                    >
                      <div className="flex items-center justify-end gap-2">
                        {canCancel && (
                          <button
                            type="button"
                            title="İptal Et"
                            disabled={isCanceling}
                            onClick={(e) => {
                              e.stopPropagation();
                              cancelMutation.mutate(job.id);
                            }}
                            className="admin-btn-secondary text-xs py-1 px-2.5 cursor-pointer"
                            style={{ color: '#b45309' }}
                          >
                            {isCanceling ? (
                              <Loader2 className="w-3 h-3 animate-spin" />
                            ) : (
                              <Ban className="w-3 h-3" />
                            )}
                            İptal
                          </button>
                        )}

                        {canRetry && (
                          <button
                            type="button"
                            title="Tekrar Dene"
                            disabled={isRetrying}
                            onClick={(e) => {
                              e.stopPropagation();
                              retryMutation.mutate(job.id);
                            }}
                            className="admin-btn-secondary text-xs py-1 px-2.5 cursor-pointer"
                            style={{ color: 'var(--color-accent)' }}
                          >
                            {isRetrying ? (
                              <Loader2 className="w-3 h-3 animate-spin" />
                            ) : (
                              <RotateCcw className="w-3 h-3" />
                            )}
                            Tekrar Dene
                          </button>
                        )}

                        {canDelete && (
                          <button
                            type="button"
                            title="Sil"
                            disabled={isDeleting}
                            onClick={(e) => {
                              e.stopPropagation();
                              deleteMutation.mutate(job.id);
                            }}
                            className="admin-btn-danger text-xs py-1 px-2.5 cursor-pointer"
                          >
                            {isDeleting ? (
                              <Loader2 className="w-3 h-3 animate-spin" />
                            ) : (
                              <Trash2 className="w-3 h-3" />
                            )}
                            Sil
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
