// src/admin/components/DocumentTable.tsx
import React, { useState } from 'react';
import {
  FileText,
  Trash2,
  Loader2,
  CheckCircle2,
  XCircle,
  Clock,
  Layers,
  Calendar,
  AlertCircle,
} from 'lucide-react';
import { useDocuments, useDeleteDocument } from '../hooks/useDocuments';
import { ChunkViewer } from './ChunkViewer';
import type { DocumentRecord } from '../types';

function StatusBadge({ status, error }: { status: DocumentRecord['status']; error?: string | null }) {
  if (status === 'processing') {
    return (
      <span className="admin-badge admin-badge-running">
        <Loader2 className="w-3 h-3 animate-spin" />
        İşleniyor
      </span>
    );
  }

  if (status === 'indexed') {
    return (
      <span className="admin-badge admin-badge-done">
        <CheckCircle2 className="w-3 h-3" />
        İndekslendi
      </span>
    );
  }

  return (
    <span
      title={error || undefined}
      className="admin-badge admin-badge-failed cursor-default"
    >
      <XCircle className="w-3 h-3" />
      Başarısız
      {error && <AlertCircle className="w-3 h-3 ml-0.5 opacity-70" />}
    </span>
  );
}

function FileTypeBadge({ type }: { type: string }) {
  const colors: Record<string, { bg: string; color: string; border: string }> = {
    pdf: { bg: 'color-mix(in oklch, #ef4444 12%, transparent)', color: '#dc2626', border: 'color-mix(in oklch, #ef4444 25%, transparent)' },
    docx: { bg: 'color-mix(in oklch, var(--color-accent) 12%, transparent)', color: 'var(--color-accent)', border: 'color-mix(in oklch, var(--color-accent) 25%, transparent)' },
    txt: { bg: 'color-mix(in oklch, var(--color-muted) 12%, transparent)', color: 'var(--color-muted)', border: 'color-mix(in oklch, var(--color-muted) 25%, transparent)' },
  };

  const style = colors[type.toLowerCase()] || colors.txt;

  return (
    <span
      className="admin-badge text-[9.5px]"
      style={{ backgroundColor: style.bg, color: style.color, borderColor: style.border }}
    >
      {type}
    </span>
  );
}

export function DocumentTable() {
  const { data, isLoading, isError } = useDocuments();
  const deleteMutation = useDeleteDocument();
  const [viewingChunksDoc, setViewingChunksDoc] = useState<DocumentRecord | null>(null);

  const documents = data?.documents ?? [];

  const handleDelete = (doc: DocumentRecord) => {
    if (
      window.confirm(
        `"${doc.filename}" belgesini ve Qdrant içindeki tüm vektörlerini kalıcı olarak silmek istediğinizden emin misiniz?`
      )
    ) {
      deleteMutation.mutate(doc.id);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-12 admin-card">
        <Loader2 className="w-6 h-6 animate-spin" style={{ color: 'var(--color-accent)' }} />
      </div>
    );
  }

  if (isError) {
    return (
      <div
        className="p-6 rounded-2xl text-xs flex items-center gap-2 border"
        style={{
          backgroundColor: 'color-mix(in oklch, #ef4444 10%, transparent)',
          borderColor: 'color-mix(in oklch, #ef4444 30%, transparent)',
          color: '#dc2626',
        }}
      >
        <AlertCircle className="w-4 h-4 shrink-0" />
        <span>Belgeler yüklenirken bir sorun oluştu. Lütfen sayfayı yenileyin veya API bağlantınızı kontrol edin.</span>
      </div>
    );
  }

  if (documents.length === 0) {
    return (
      <div className="p-10 text-center admin-card">
        <FileText className="w-10 h-10 mx-auto mb-3" style={{ color: 'var(--color-muted)' }} />
        <p className="text-sm font-semibold" style={{ color: 'var(--color-ink)' }}>Henüz yüklenmiş bir belge yok</p>
        <p className="text-xs mt-1" style={{ color: 'var(--color-muted)' }}>
          Yukarıdaki form üzerinden şirket, büro veya avukat belgelerinizi yükleyebilirsiniz.
        </p>
      </div>
    );
  }

  return (
    <>
      <div className="admin-table-wrapper">
        <div className="overflow-x-auto">
          <table className="admin-table">
            <thead>
              <tr>
                <th>Belge Adı</th>
                <th>Tür</th>
                <th>Durum</th>
                <th>Chunk Sayısı</th>
                <th>Yüklenme Tarihi</th>
                <th style={{ textAlign: 'right' }}>İşlem</th>
              </tr>
            </thead>
            <tbody>
              {documents.map((doc) => (
                <tr key={doc.id}>
                  {/* Belge Adı */}
                  <td className="font-medium">
                    <div className="flex items-center gap-2 max-w-xs md:max-w-md truncate" title={doc.filename}>
                      <FileText className="w-4 h-4 shrink-0" style={{ color: 'var(--color-muted)' }} />
                      <span className="truncate">{doc.filename}</span>
                    </div>
                    {doc.error && doc.status === 'failed' && (
                      <p className="text-[11px] mt-1 truncate max-w-sm" style={{ color: '#dc2626' }} title={doc.error}>
                        Hata: {doc.error}
                      </p>
                    )}
                  </td>

                  {/* Format */}
                  <td>
                    <FileTypeBadge type={doc.file_type} />
                  </td>

                  {/* Durum */}
                  <td>
                    <StatusBadge status={doc.status} error={doc.error} />
                  </td>

                  {/* Chunk Sayısı */}
                  <td className="font-mono text-xs">
                    <div className="flex items-center gap-1.5" style={{ color: 'var(--color-muted)' }}>
                      <Layers className="w-3.5 h-3.5" />
                      <span>{doc.chunk_count} parça</span>
                    </div>
                  </td>

                  {/* Tarih */}
                  <td className="text-xs whitespace-nowrap">
                    <div className="flex items-center gap-1.5" style={{ color: 'var(--color-muted)' }}>
                      <Calendar className="w-3.5 h-3.5" />
                      <span>
                        {doc.created_at
                          ? new Date(doc.created_at).toLocaleDateString('tr-TR', {
                              day: 'numeric',
                              month: 'short',
                              year: 'numeric',
                              hour: '2-digit',
                              minute: '2-digit',
                            })
                          : '-'}
                      </span>
                    </div>
                  </td>

                  {/* Eylemler */}
                  <td style={{ textAlign: 'right' }}>
                    <div className="flex items-center justify-end gap-1.5">
                      {/* Chunk'ları Gör */}
                      <button
                        onClick={() => setViewingChunksDoc(doc)}
                        disabled={doc.status !== 'indexed' || doc.chunk_count === 0}
                        className="p-1.5 rounded-lg transition-colors cursor-pointer"
                        style={{
                          color:
                            doc.status === 'indexed' && doc.chunk_count > 0
                              ? 'var(--color-accent)'
                              : 'var(--color-muted)',
                          opacity: doc.status !== 'indexed' || doc.chunk_count === 0 ? 0.4 : 1,
                          cursor:
                            doc.status !== 'indexed' || doc.chunk_count === 0
                              ? 'not-allowed'
                              : 'pointer',
                        }}
                        title={
                          doc.status !== 'indexed'
                            ? 'Belge henüz indekslenmedi'
                            : doc.chunk_count === 0
                            ? 'Chunk bulunamadı'
                            : `${doc.chunk_count} chunk'ı görüntüle`
                        }
                      >
                        <Layers className="w-4 h-4" />
                      </button>

                      {/* Sil */}
                      <button
                        onClick={() => handleDelete(doc)}
                        disabled={deleteMutation.isPending && deleteMutation.variables === doc.id}
                        className="p-1.5 rounded-lg transition-colors cursor-pointer"
                        style={{ color: '#ef4444' }}
                        title="Belgeyi ve Vektörlerini Sil"
                      >
                        {deleteMutation.isPending && deleteMutation.variables === doc.id ? (
                          <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                          <Trash2 className="w-4 h-4" />
                        )}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* ChunkViewer Modal */}
      {viewingChunksDoc && (
        <ChunkViewer
          doc={viewingChunksDoc}
          onClose={() => setViewingChunksDoc(null)}
        />
      )}
    </>
  );
}
