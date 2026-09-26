// src/admin/components/ChunkViewer.tsx
// Modal: belge chunk'larini surekli metin akisi + tiklanabilir sinir cizgisiyle gosterir.
// Sinir tiklaninca: secim modu acilir, kullanici yeni kesim noktasini secer.

import React, { useCallback, useRef, useState } from 'react';
import {
  X,
  Layers,
  ChevronDown,
  AlertCircle,
  Loader2,
  Hash,
  Type,
  Scissors,
  Pencil,
  Check,
  XCircle,
} from 'lucide-react';
import { useDocumentChunks, useShiftBoundary } from '../hooks/useDocuments';
import type { DocumentRecord, ChunkRecord } from '../types';

// ─── Sabitler ─────────────────────────────────────────────────────────────────
const CONTEXT_CHARS = 80; // Sinir cizgisi etrafinda gosterilecek karakter sayisi

// ─── Yardimci Bilesenler ──────────────────────────────────────────────────────

function ManualBadge() {
  return (
    <span
      title="Bu chunk elle duzenlenmistir"
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '3px',
        padding: '1px 6px',
        borderRadius: '999px',
        fontSize: '9px',
        fontWeight: 600,
        fontFamily: 'var(--font-label, monospace)',
        background: 'color-mix(in oklch, #f59e0b 15%, transparent)',
        color: '#d97706',
        border: '1px solid color-mix(in oklch, #f59e0b 30%, transparent)',
        flexShrink: 0,
      }}
    >
      <Pencil style={{ width: '7px', height: '7px' }} />
      elle düzenlendi
    </span>
  );
}

function ChunkHeader({ chunk }: { chunk: ChunkRecord }) {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
        marginBottom: '6px',
        padding: '0 2px',
      }}
    >
      <span
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '4px',
          padding: '2px 8px',
          borderRadius: '999px',
          fontSize: '10px',
          fontWeight: 600,
          fontFamily: 'var(--font-label, monospace)',
          background: 'color-mix(in oklch, var(--color-accent) 14%, transparent)',
          color: 'var(--color-accent)',
          border: '1px solid color-mix(in oklch, var(--color-accent) 28%, transparent)',
          flexShrink: 0,
        }}
      >
        <Hash style={{ width: '9px', height: '9px' }} />
        {String(chunk.chunk_index).padStart(3, '0')}
      </span>
      <span
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '4px',
          fontSize: '10px',
          color: 'var(--color-muted)',
          fontFamily: 'var(--font-label, monospace)',
        }}
      >
        <Type style={{ width: '9px', height: '9px' }} />
        {chunk.char_count.toLocaleString('tr-TR')} karakter
        {chunk.start_char != null && (
          <span style={{ opacity: 0.6 }}>
            &nbsp;· @{chunk.start_char}–{chunk.end_char}
          </span>
        )}
      </span>
      {chunk.manually_edited && <ManualBadge />}
    </div>
  );
}

// ─── Sinir Secim Modalı ────────────────────────────────────────────────────────

interface BoundaryEditorProps {
  chunkA: ChunkRecord;
  chunkB: ChunkRecord;
  boundaryIndex: number;
  docId: string;
  onClose: () => void;
}

function BoundaryEditor({ chunkA, chunkB, boundaryIndex, docId, onClose }: BoundaryEditorProps) {
  const shiftMutation = useShiftBoundary(docId);

  // Sinir bolgesindeki metin: A'nin sonu + B'nin basi
  const contextA = chunkA.chunk_text.slice(-CONTEXT_CHARS);
  const contextB = chunkB.chunk_text.slice(0, CONTEXT_CHARS);
  const fullContext = contextA + contextB;

  // Mevcut sinir: contextA.length pozisyonunda (0-indexed)
  const [selectedPos, setSelectedPos] = useState<number>(contextA.length);

  const handleConfirm = () => {
    if (chunkA.end_char == null || chunkA.start_char == null) return;

    // Secili pozisyonu full_text ofsetine cevir:
    // contextA, chunkA'nin sonundan CONTEXT_CHARS karakter.
    // Yeni kesim noktasi = (chunkA.end_char - CONTEXT_CHARS) + selectedPos
    const contextAStart = Math.max(chunkA.start_char, chunkA.end_char - CONTEXT_CHARS);
    const newOffset = contextAStart + selectedPos;

    shiftMutation.mutate(
      { boundary_index: boundaryIndex, new_offset: newOffset },
      { onSuccess: onClose }
    );
  };

  const error = shiftMutation.error?.message;

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 60,
        background: 'rgba(0,0,0,0.65)',
        backdropFilter: 'blur(4px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '24px',
      }}
      onClick={onClose}
    >
      <div
        style={{
          width: '100%',
          maxWidth: '600px',
          background: 'var(--color-paper)',
          border: '1px solid color-mix(in oklch, #f59e0b 30%, transparent)',
          borderRadius: '16px',
          boxShadow: '0 20px 60px rgba(0,0,0,0.5)',
          overflow: 'hidden',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Baslik */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            padding: '16px 18px',
            borderBottom: '1px solid color-mix(in oklch, #f59e0b 20%, transparent)',
          }}
        >
          <Scissors style={{ width: '16px', height: '16px', color: '#d97706', flexShrink: 0 }} />
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--color-ink)' }}>
              Sınır #{boundaryIndex} ↔ #{boundaryIndex + 1} Kaydır
            </div>
            <div style={{ fontSize: '10px', color: 'var(--color-muted)', marginTop: '2px' }}>
              Metin üzerinde tıklayarak yeni kesim noktasını seçin
            </div>
          </div>
          <button onClick={onClose} style={{ color: 'var(--color-muted)', cursor: 'pointer', background: 'none', border: 'none' }}>
            <X style={{ width: '15px', height: '15px' }} />
          </button>
        </div>

        {/* Sinir Bolge Metin Secici */}
        <div style={{ padding: '16px 18px' }}>
          <div style={{ fontSize: '10px', color: 'var(--color-muted)', marginBottom: '8px', fontFamily: 'var(--font-label)' }}>
            Tıkladığınız yere göre kesim yapılır — sarı çizgi mevcut sınırı gösterir
          </div>
          <div
            style={{
              fontFamily: '"JetBrains Mono", ui-monospace, monospace',
              fontSize: '12px',
              lineHeight: '1.7',
              background: 'color-mix(in oklch, var(--color-paper-2) 80%, transparent)',
              border: '1px solid color-mix(in oklch, var(--color-accent) 15%, transparent)',
              borderRadius: '8px',
              padding: '12px',
              userSelect: 'none',
              cursor: 'text',
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
              position: 'relative',
            }}
            onClick={(e) => {
              // Tiklanan karakterin indexini bul
              const target = e.currentTarget;
              const range = document.caretRangeFromPoint?.(e.clientX, e.clientY);
              if (!range) return;
              // Range, text node icindeki ofset
              const preNode = target.childNodes[0];
              if (!preNode) return;
              const r2 = document.createRange();
              r2.setStart(target, 0);
              r2.setEnd(range.startContainer, range.startOffset);
              const clickedPos = r2.toString().length;
              // 0 ve fullContext.length arasinda klamp
              setSelectedPos(Math.max(0, Math.min(fullContext.length, clickedPos)));
            }}
          >
            {/* Metin: secilen noktada dikey cizgi */}
            <span style={{ color: 'var(--color-muted)' }}>{fullContext.slice(0, selectedPos)}</span>
            <span
              style={{
                display: 'inline-block',
                width: '2px',
                height: '1.4em',
                background: '#f59e0b',
                verticalAlign: 'middle',
                borderRadius: '1px',
              }}
            />
            <span style={{ color: 'var(--color-ink)' }}>{fullContext.slice(selectedPos)}</span>
          </div>

          {/* Mevcut sinir gostergesi */}
          <div style={{ marginTop: '8px', fontSize: '10px', color: 'var(--color-muted)', fontFamily: 'var(--font-label)' }}>
            Mevcut sınır: karakter <strong>{contextA.length}</strong> &nbsp;|&nbsp;
            Yeni sınır: karakter <strong>{selectedPos}</strong>
            {selectedPos === contextA.length && (
              <span style={{ marginLeft: '6px', color: '#d97706' }}>(değişiklik yok)</span>
            )}
          </div>

          {/* Hata */}
          {error && (
            <div
              style={{
                marginTop: '10px',
                padding: '10px 12px',
                borderRadius: '8px',
                background: 'color-mix(in oklch, #ef4444 10%, transparent)',
                border: '1px solid color-mix(in oklch, #ef4444 25%, transparent)',
                color: '#dc2626',
                fontSize: '12px',
                display: 'flex',
                alignItems: 'flex-start',
                gap: '8px',
              }}
            >
              <AlertCircle style={{ width: '14px', height: '14px', flexShrink: 0, marginTop: '1px' }} />
              {error}
            </div>
          )}
        </div>

        {/* Footer */}
        <div
          style={{
            display: 'flex',
            justifyContent: 'flex-end',
            gap: '8px',
            padding: '12px 18px',
            borderTop: '1px solid color-mix(in oklch, var(--color-accent) 10%, transparent)',
          }}
        >
          <button
            onClick={onClose}
            style={{
              padding: '7px 16px',
              borderRadius: '8px',
              fontSize: '12px',
              color: 'var(--color-muted)',
              background: 'color-mix(in oklch, var(--color-paper-2) 80%, transparent)',
              border: '1px solid color-mix(in oklch, var(--color-accent) 15%, transparent)',
              cursor: 'pointer',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '5px',
            }}
          >
            <XCircle style={{ width: '12px', height: '12px' }} />
            İptal
          </button>
          <button
            onClick={handleConfirm}
            disabled={shiftMutation.isPending || selectedPos === contextA.length}
            style={{
              padding: '7px 16px',
              borderRadius: '8px',
              fontSize: '12px',
              fontWeight: 600,
              color: '#fff',
              background: selectedPos === contextA.length ? '#6b7280' : '#d97706',
              border: 'none',
              cursor: selectedPos === contextA.length ? 'not-allowed' : 'pointer',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '5px',
              opacity: shiftMutation.isPending ? 0.6 : 1,
            }}
          >
            {shiftMutation.isPending ? (
              <>
                <Loader2 style={{ width: '12px', height: '12px', animation: 'spin 1s linear infinite' }} />
                Kaydırılıyor...
              </>
            ) : (
              <>
                <Check style={{ width: '12px', height: '12px' }} />
                Onayla
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Sinir Cizgisi ─────────────────────────────────────────────────────────────

interface BoundaryDividerProps {
  chunkA: ChunkRecord;
  chunkB: ChunkRecord;
  boundaryIndex: number;
  hasOffsets: boolean;
  docId: string;
}

function BoundaryDivider({ chunkA, chunkB, boundaryIndex, hasOffsets, docId }: BoundaryDividerProps) {
  const [editing, setEditing] = useState(false);
  const canEdit = hasOffsets && chunkA.start_char != null && chunkB.end_char != null;

  return (
    <>
      <div
        onClick={canEdit ? () => setEditing(true) : undefined}
        title={
          canEdit
            ? `Sınır #${boundaryIndex}↔${boundaryIndex + 1} — tıkla ve kaydır`
            : 'Sınır kaydırma: bu belge için ofset bilgisi yok (yeniden yükleyin)'
        }
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          margin: '4px 0',
          cursor: canEdit ? 'pointer' : 'not-allowed',
          opacity: canEdit ? 1 : 0.5,
          transition: 'all 0.15s',
          userSelect: 'none',
        }}
        className="boundary-divider"
      >
        <div
          style={{
            flex: 1,
            height: '1.5px',
            background: canEdit
              ? 'color-mix(in oklch, var(--color-accent) 30%, transparent)'
              : 'color-mix(in oklch, var(--color-muted) 20%, transparent)',
            transition: 'background 0.15s',
          }}
        />
        <span
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '4px',
            padding: '3px 8px',
            borderRadius: '999px',
            fontSize: '9px',
            fontWeight: 600,
            fontFamily: 'var(--font-label, monospace)',
            background: canEdit
              ? 'color-mix(in oklch, var(--color-accent) 10%, transparent)'
              : 'color-mix(in oklch, var(--color-muted) 8%, transparent)',
            color: canEdit ? 'var(--color-accent)' : 'var(--color-muted)',
            border: `1px solid ${canEdit
              ? 'color-mix(in oklch, var(--color-accent) 25%, transparent)'
              : 'color-mix(in oklch, var(--color-muted) 15%, transparent)'}`,
            whiteSpace: 'nowrap',
          }}
        >
          {canEdit ? (
            <>
              <Scissors style={{ width: '8px', height: '8px' }} />
              sınır {boundaryIndex}↔{boundaryIndex + 1}
            </>
          ) : (
            `── sınır ──`
          )}
        </span>
        <div
          style={{
            flex: 1,
            height: '1.5px',
            background: canEdit
              ? 'color-mix(in oklch, var(--color-accent) 30%, transparent)'
              : 'color-mix(in oklch, var(--color-muted) 20%, transparent)',
            transition: 'background 0.15s',
          }}
        />
      </div>

      {editing && (
        <BoundaryEditor
          chunkA={chunkA}
          chunkB={chunkB}
          boundaryIndex={boundaryIndex}
          docId={docId}
          onClose={() => setEditing(false)}
        />
      )}
    </>
  );
}

// ─── Ana Modal ────────────────────────────────────────────────────────────────

interface ChunkViewerProps {
  doc: DocumentRecord;
  onClose: () => void;
}

export function ChunkViewer({ doc, onClose }: ChunkViewerProps) {
  const overlayRef = useRef<HTMLDivElement>(null);

  const {
    data,
    isLoading,
    isError,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
  } = useDocumentChunks(doc.id);

  const allChunks: ChunkRecord[] =
    data?.pages.flatMap((page) => page.chunks) ?? [];
  const total = data?.pages[0]?.total ?? doc.chunk_count;
  const hasOffsets = data?.pages[0]?.has_offsets ?? false;

  const handleOverlayClick = useCallback(
    (e: React.MouseEvent) => {
      if (e.target === overlayRef.current) onClose();
    },
    [onClose]
  );

  return (
    <div
      ref={overlayRef}
      onClick={handleOverlayClick}
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 50,
        background: 'rgba(0,0,0,0.55)',
        backdropFilter: 'blur(4px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '24px',
      }}
    >
      <div
        style={{
          width: '100%',
          maxWidth: '820px',
          maxHeight: '92vh',
          display: 'flex',
          flexDirection: 'column',
          background: 'var(--color-paper)',
          border: '1px solid color-mix(in oklch, var(--color-accent) 20%, transparent)',
          borderRadius: '18px',
          boxShadow: '0 24px 80px rgba(0,0,0,0.45)',
          overflow: 'hidden',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* ── Başlık ── */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '12px',
            padding: '18px 20px',
            borderBottom: '1px solid color-mix(in oklch, var(--color-accent) 12%, transparent)',
            flexShrink: 0,
          }}
        >
          <div
            style={{
              width: '36px',
              height: '36px',
              borderRadius: '10px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              background: 'color-mix(in oklch, var(--color-accent) 14%, transparent)',
              border: '1px solid color-mix(in oklch, var(--color-accent) 28%, transparent)',
              flexShrink: 0,
            }}
          >
            <Layers style={{ width: '16px', height: '16px', color: 'var(--color-accent)' }} />
          </div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div
              style={{
                fontSize: '13px',
                fontWeight: 600,
                color: 'var(--color-ink)',
                fontFamily: 'var(--font-display)',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}
            >
              {doc.filename}
            </div>
            <div
              style={{
                fontSize: '11px',
                color: 'var(--color-muted)',
                fontFamily: 'var(--font-label)',
                marginTop: '2px',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
              }}
            >
              <span>{total} chunk · {allChunks.length} yüklendi</span>
              {!hasOffsets && allChunks.length > 0 && (
                <span
                  style={{
                    fontSize: '9px',
                    padding: '1px 6px',
                    borderRadius: '999px',
                    background: 'color-mix(in oklch, #f59e0b 15%, transparent)',
                    color: '#d97706',
                    border: '1px solid color-mix(in oklch, #f59e0b 25%, transparent)',
                  }}
                >
                  ⚠ Sınır kaydırma: belgeyi yeniden yükleyin
                </span>
              )}
            </div>
          </div>
          <button
            onClick={onClose}
            style={{
              padding: '6px',
              borderRadius: '8px',
              color: 'var(--color-muted)',
              cursor: 'pointer',
              background: 'transparent',
              border: 'none',
              flexShrink: 0,
            }}
            title="Kapat"
          >
            <X style={{ width: '16px', height: '16px' }} />
          </button>
        </div>

        {/* ── Chunk Listesi ── */}
        <div
          style={{
            flex: 1,
            overflowY: 'auto',
            padding: '16px 20px',
            display: 'flex',
            flexDirection: 'column',
          }}
        >
          {isLoading && (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                height: '200px',
                gap: '8px',
                color: 'var(--color-muted)',
              }}
            >
              <Loader2
                style={{
                  width: '20px',
                  height: '20px',
                  color: 'var(--color-accent)',
                  animation: 'spin 1s linear infinite',
                }}
              />
              <span style={{ fontSize: '13px' }}>Chunk'lar yükleniyor...</span>
            </div>
          )}

          {isError && !isLoading && (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '14px',
                borderRadius: '10px',
                background: 'color-mix(in oklch, #ef4444 10%, transparent)',
                border: '1px solid color-mix(in oklch, #ef4444 25%, transparent)',
                color: '#dc2626',
                fontSize: '13px',
              }}
            >
              <AlertCircle style={{ width: '16px', height: '16px', flexShrink: 0 }} />
              Chunk'lar yüklenirken bir hata oluştu. Lütfen tekrar deneyin.
            </div>
          )}

          {!isLoading && !isError && allChunks.length === 0 && (
            <div
              style={{
                textAlign: 'center',
                padding: '48px',
                color: 'var(--color-muted)',
                fontSize: '13px',
              }}
            >
              Bu belgeye ait chunk bulunamadı.
            </div>
          )}

          {/* Chunk'lar — surekli metin akisi + sinir cizgileri */}
          {allChunks.map((chunk, idx) => (
            <React.Fragment key={chunk.chunk_index}>
              {/* Chunk Kart */}
              <div
                style={{
                  background: 'color-mix(in oklch, var(--color-paper-2) 50%, transparent)',
                  borderRadius: '10px',
                  padding: '12px 14px',
                }}
              >
                <ChunkHeader chunk={chunk} />
                <pre
                  style={{
                    margin: 0,
                    fontFamily: '"JetBrains Mono", "Fira Code", ui-monospace, monospace',
                    fontSize: '11px',
                    lineHeight: '1.7',
                    color: 'var(--color-ink)',
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-word',
                  }}
                >
                  {chunk.chunk_text}
                </pre>
              </div>

              {/* Sinir cizgisi — son chunk sonrasi gosterme */}
              {idx < allChunks.length - 1 && (
                <BoundaryDivider
                  chunkA={chunk}
                  chunkB={allChunks[idx + 1]}
                  boundaryIndex={chunk.chunk_index}
                  hasOffsets={hasOffsets}
                  docId={doc.id}
                />
              )}
            </React.Fragment>
          ))}

          {/* Daha Fazla Yukle */}
          {(hasNextPage || isFetchingNextPage) && (
            <div style={{ display: 'flex', justifyContent: 'center', padding: '8px 0 4px' }}>
              <button
                onClick={() => fetchNextPage()}
                disabled={isFetchingNextPage}
                className="admin-btn-primary"
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '8px 20px',
                  fontSize: '12px',
                  opacity: isFetchingNextPage ? 0.6 : 1,
                  cursor: isFetchingNextPage ? 'not-allowed' : 'pointer',
                }}
              >
                {isFetchingNextPage ? (
                  <>
                    <Loader2 style={{ width: '13px', height: '13px', animation: 'spin 1s linear infinite' }} />
                    Yükleniyor...
                  </>
                ) : (
                  <>
                    <ChevronDown style={{ width: '13px', height: '13px' }} />
                    Daha Fazla Yükle ({total - allChunks.length} kaldı)
                  </>
                )}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
