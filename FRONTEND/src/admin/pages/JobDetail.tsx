// src/admin/pages/JobDetail.tsx
// Tek job detay sayfası:
//   Sol: raw madde listesi (JsonViewer)
//   Sağ: clean madde listesi (boşsa Preprocess butonu)
// İleride: "Qdrant'a Gönder" butonu için yer bırakılmıştır (Embed aşaması)

import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  Loader2,
  AlertCircle,
  TriangleAlert,
  Sparkles,
  Cpu,
} from 'lucide-react';
import { useJobDetail } from '../hooks/useJobDetail';
import { usePreprocess } from '../hooks/useScrapeActions';
import { DiffPreview } from '../components/DiffPreview';

function StatusPill({ status }: { status: string }) {
  const map: Record<string, string> = {
    pending: 'admin-badge admin-badge-pending',
    running: 'admin-badge admin-badge-running',
    done: 'admin-badge admin-badge-done',
    failed: 'admin-badge admin-badge-failed',
    canceled: 'admin-badge admin-badge-canceled',
  };
  return (
    <span
      className={map[status] ?? 'admin-badge'}
    >
      {status === 'running' && <Loader2 className="w-3 h-3 animate-spin" />}
      {status}
    </span>
  );
}

export function JobDetail() {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();

  const { data: job, isLoading, error } = useJobDetail(jobId ?? '');
  const { mutate: runPreprocess, isPending: preprocessing } = usePreprocess(jobId ?? '');

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 text-sm p-8" style={{ color: 'var(--color-muted)' }}>
        <Loader2 className="w-4 h-4 animate-spin" />
        Yükleniyor...
      </div>
    );
  }

  if (error || !job) {
    return (
      <div 
        className="flex items-center gap-2 text-sm p-8 rounded-2xl border"
        style={{
          backgroundColor: 'color-mix(in oklch, #ef4444 10%, transparent)',
          borderColor: 'color-mix(in oklch, #ef4444 30%, transparent)',
          color: '#dc2626',
        }}
      >
        <AlertCircle className="w-4 h-4" />
        {error?.message ?? 'Job bulunamadı.'}
      </div>
    );
  }

  const rawArticles = job.raw_data?.articles ?? [];
  const cleanArticles = job.clean_data?.articles ?? [];
  const hasRaw = rawArticles.length > 0;
  const hasClean = cleanArticles.length > 0;
  const totalDuplicatesRemoved = job.clean_data?.duplicate_lines_removed ?? 0;
  const droppedArticleCount = job.clean_data?.dropped_article_count ?? 0;
  const droppedArticleNos = job.clean_data?.dropped_article_nos ?? [];

  return (
    <div className="space-y-6">
      {/* Üst bar */}
      <div className="flex flex-wrap items-center gap-4">
        <button
          onClick={() => navigate(-1)}
          className="admin-btn-secondary text-xs py-1.5 px-3 cursor-pointer"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          Geri
        </button>

        <div className="flex-1 min-w-0">
          <h1 className="admin-heading text-xl font-normal truncate">
            {job.law_name}
          </h1>
          <p className="admin-eyebrow text-xs mt-0.5">
            #{job.law_id} · Job {job.id.slice(0, 8)}
          </p>
        </div>

        <StatusPill status={job.status} />
      </div>

      {/* Hata kutusu */}
      {job.error && (
        <div 
          className="flex items-start gap-2 rounded-xl px-4 py-3 text-xs border"
          style={{
            backgroundColor: 'color-mix(in oklch, #ef4444 10%, transparent)',
            borderColor: 'color-mix(in oklch, #ef4444 30%, transparent)',
            color: '#dc2626',
          }}
        >
          <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
          <pre className="whitespace-pre-wrap break-all font-mono">{job.error}</pre>
        </div>
      )}

      {/* Aksiyon butonları */}
      {hasRaw && (
        <div className="flex flex-wrap gap-3">
          {/* Preprocess */}
          {!hasClean && job.status === 'done' && (
            <button
              onClick={() => runPreprocess()}
              disabled={preprocessing}
              className="admin-btn-primary text-xs py-2 px-4 cursor-pointer"
            >
              {preprocessing ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <Sparkles className="w-3.5 h-3.5" />
              )}
              {preprocessing ? 'İşleniyor...' : 'Preprocess Et'}
            </button>
          )}

          {/* TODO (Embed aşaması) — yer tutucu, henüz aktif değil */}
          {hasClean && (
            <button
              disabled
              title="Backend embedding pipeline henüz aktif değil"
              className="admin-btn-secondary text-xs py-2 px-4 opacity-50 cursor-not-allowed"
            >
              <Cpu className="w-3.5 h-3.5" />
              Qdrant'a Gönder (yakında)
            </button>
          )}
        </div>
      )}

      {/* Tekrar satır uyarısı */}
      {hasClean && totalDuplicatesRemoved > 0 && (
        <div 
          className="flex items-start gap-2 rounded-xl px-4 py-3 text-xs border"
          style={{
            backgroundColor: 'color-mix(in oklch, #f59e0b 10%, transparent)',
            borderColor: 'color-mix(in oklch, #f59e0b 30%, transparent)',
            color: '#b45309',
          }}
        >
          <TriangleAlert className="w-4 h-4 flex-shrink-0 mt-0.5" />
          <span>
            Preprocessing sırasında toplam <strong>{totalDuplicatesRemoved} tekrar satır</strong> otomatik temizlendi.
            Temizlenen satırlar madde detaylarında (⚠ rozeti) gösterilmektedir — lütfen kontrol edin.
          </span>
        </div>
      )}

      {/* Elenen madde uyarısı */}
      {hasClean && droppedArticleCount > 0 && (
        <div 
          className="flex items-start gap-2 rounded-xl px-4 py-3 text-xs border"
          style={{
            backgroundColor: 'color-mix(in oklch, #f59e0b 10%, transparent)',
            borderColor: 'color-mix(in oklch, #f59e0b 30%, transparent)',
            color: '#b45309',
          }}
        >
          <TriangleAlert className="w-4 h-4 flex-shrink-0 mt-0.5" />
          <span>
            ⚠ <strong>{droppedArticleCount} madde</strong> otomatik olarak elendi: [{droppedArticleNos.join(', ')}]
          </span>
        </div>
      )}

      {/* İçerik */}
      {!hasRaw && job.status === 'done' && (
        <p className="text-sm" style={{ color: 'var(--color-muted)' }}>
          Ham veri yüklenmedi — job tamamlandı ama veriye erişilemiyor.
        </p>
      )}


      {hasRaw && (
        <DiffPreview
          rawArticles={rawArticles}
          cleanArticles={cleanArticles}
          droppedArticleCount={droppedArticleCount}
          droppedArticleNos={droppedArticleNos}
        />
      )}
    </div>
  );
}
