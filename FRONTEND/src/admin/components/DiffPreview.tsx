// src/admin/components/DiffPreview.tsx
// Raw vs Clean paneller — Accordion (varsayılan kapalı), bağımsız toggle, dinamik grid
// ve sadece ikisi de açıkken çalışan çift yönlü madde senkronlu scroll

import { useState, useRef, useEffect, useMemo } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { ChevronDown } from 'lucide-react';
import { JsonViewer } from './JsonViewer';
import type { Article } from '../types';

interface DiffPreviewProps {
  rawArticles: Article[];
  cleanArticles: Article[];
  droppedArticleCount?: number;
  droppedArticleNos?: string[];
}

export function DiffPreview({
  rawArticles,
  cleanArticles,
  droppedArticleCount = 0,
  droppedArticleNos = [],
}: DiffPreviewProps) {
  // Paneller varsayılan olarak KAPALI (collapsed) başlar
  const [rawOpen, setRawOpen] = useState(false);
  const [cleanOpen, setCleanOpen] = useState(false);

  const rawScrollRef = useRef<HTMLDivElement>(null);
  const cleanScrollRef = useRef<HTMLDivElement>(null);
  const isSyncing = useRef(false);

  // Hangi madde no'lar sadece raw'da var (clean'de kaybolmuş)?
  const { missingInClean, missingInRaw } = useMemo(() => {
    if (!cleanArticles.length) {
      return { missingInClean: new Set<string>(), missingInRaw: new Set<string>() };
    }
    const rawNos = new Set(rawArticles.map((a) => a.no));
    const cleanNos = new Set(cleanArticles.map((a) => a.no));

    return {
      missingInClean: new Set([...rawNos].filter((no) => !cleanNos.has(no))),
      missingInRaw: new Set([...cleanNos].filter((no) => !rawNos.has(no))),
    };
  }, [rawArticles, cleanArticles]);

  const hasDiff = cleanArticles.length > 0 && (missingInClean.size > 0 || missingInRaw.size > 0);
  const isBothOpen = rawOpen && cleanOpen;

  // Scroll senkronizasyonu SADECE ikisi de açıkken aktif olsun
  useEffect(() => {
    if (!rawOpen || !cleanOpen) return;

    const rawEl = rawScrollRef.current;
    const cleanEl = cleanScrollRef.current;
    if (!rawEl || !cleanEl) return;

    const handleRawScroll = () => {
      if (isSyncing.current) return;
      isSyncing.current = true;

      // Madde no'ya göre eşleştirme
      const rawArticleDivs = rawEl.querySelectorAll<HTMLElement>('[data-article-no]');
      let matched = false;

      for (let i = 0; i < rawArticleDivs.length; i++) {
        const item = rawArticleDivs[i];
        if (item.offsetTop + item.offsetHeight >= rawEl.scrollTop) {
          const articleNo = item.getAttribute('data-article-no');
          if (articleNo) {
            const targetClean = cleanEl.querySelector<HTMLElement>(`[data-article-no="${articleNo}"]`);
            if (targetClean) {
              cleanEl.scrollTop = targetClean.offsetTop - 16;
              matched = true;
              break;
            }
          }
        }
      }

      // Eşleşen madde render edilmediyse veya yoksa orantısal scroll yap
      if (!matched) {
        const maxScrollRaw = rawEl.scrollHeight - rawEl.clientHeight;
        const maxScrollClean = cleanEl.scrollHeight - cleanEl.clientHeight;
        if (maxScrollRaw > 0 && maxScrollClean > 0) {
          cleanEl.scrollTop = (rawEl.scrollTop / maxScrollRaw) * maxScrollClean;
        }
      }

      requestAnimationFrame(() => {
        isSyncing.current = false;
      });
    };

    const handleCleanScroll = () => {
      if (isSyncing.current) return;
      isSyncing.current = true;

      const cleanArticleDivs = cleanEl.querySelectorAll<HTMLElement>('[data-article-no]');
      let matched = false;

      for (let i = 0; i < cleanArticleDivs.length; i++) {
        const item = cleanArticleDivs[i];
        if (item.offsetTop + item.offsetHeight >= cleanEl.scrollTop) {
          const articleNo = item.getAttribute('data-article-no');
          if (articleNo) {
            const targetRaw = rawEl.querySelector<HTMLElement>(`[data-article-no="${articleNo}"]`);
            if (targetRaw) {
              rawEl.scrollTop = targetRaw.offsetTop - 16;
              matched = true;
              break;
            }
          }
        }
      }

      if (!matched) {
        const maxScrollRaw = rawEl.scrollHeight - rawEl.clientHeight;
        const maxScrollClean = cleanEl.scrollHeight - cleanEl.clientHeight;
        if (maxScrollRaw > 0 && maxScrollClean > 0) {
          rawEl.scrollTop = (cleanEl.scrollTop / maxScrollClean) * maxScrollRaw;
        }
      }

      requestAnimationFrame(() => {
        isSyncing.current = false;
      });
    };

    rawEl.addEventListener('scroll', handleRawScroll, { passive: true });
    cleanEl.addEventListener('scroll', handleCleanScroll, { passive: true });

    return () => {
      rawEl.removeEventListener('scroll', handleRawScroll);
      cleanEl.removeEventListener('scroll', handleCleanScroll);
    };
  }, [rawOpen, cleanOpen]);

  return (
    <div className="space-y-4">
      {hasDiff && (
        <div 
          className="flex items-start gap-2 rounded-xl px-4 py-3 text-xs border"
          style={{
            backgroundColor: 'color-mix(in oklch, #f59e0b 10%, transparent)',
            borderColor: 'color-mix(in oklch, #f59e0b 30%, transparent)',
            color: '#b45309',
          }}
        >
          <span className="font-bold flex-shrink-0">⚠</span>
          <span>
            {missingInClean.size > 0 && (
              <>
                Raw'da olup clean'de <strong>eksik</strong> maddeler:{' '}
                {[...missingInClean].join(', ')}.{' '}
              </>
            )}
            {missingInRaw.size > 0 && (
              <>
                Clean'de olup raw'da <strong>bulunmayan</strong> maddeler:{' '}
                {[...missingInRaw].join(', ')}.
              </>
            )}
          </span>
        </div>
      )}

      {/* Grid Düzeni: İkisi açıkken yan yana (lg:grid-cols-2), biri veya ikisi kapalıyken flex-col */}
      <div
        className={
          isBothOpen
            ? 'grid grid-cols-1 lg:grid-cols-2 gap-4 items-start'
            : 'flex flex-col gap-3'
        }
      >
        {/* Sol Panel — Ham Veri */}
        <div className="admin-card overflow-hidden transition-all">
          <button
            type="button"
            onClick={() => setRawOpen((o) => !o)}
            className="w-full flex items-center justify-between px-5 py-4 transition-colors text-left select-none cursor-pointer"
            style={{ backgroundColor: 'var(--color-paper-2)' }}
          >
            <div className="flex items-center gap-3">
              <div
                className="w-2 h-2 rounded-full"
                style={{
                  backgroundColor: rawArticles.length > 0 ? 'var(--color-accent)' : 'var(--color-muted)',
                }}
              />
              <span className="text-sm font-semibold" style={{ color: 'var(--color-ink)' }}>
                Ham Veri ({rawArticles.length} madde)
              </span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs" style={{ color: 'var(--color-muted)' }}>
                {rawOpen ? 'Kapat' : 'Aç'}
              </span>
              <ChevronDown
                className={`w-4 h-4 transition-transform duration-200 ${
                  rawOpen ? 'rotate-180' : ''
                }`}
                style={{ color: rawOpen ? 'var(--color-accent)' : 'var(--color-muted)' }}
              />
            </div>
          </button>

          <AnimatePresence initial={false}>
            {rawOpen && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.2, ease: 'easeOut' }}
                className="overflow-hidden border-t"
                style={{ borderColor: 'var(--color-rule)' }}
              >
                <div
                  ref={rawScrollRef}
                  className="p-4 max-h-[70vh] overflow-y-auto"
                >
                  <JsonViewer
                    label="Ham Veri (Raw)"
                    articles={rawArticles}
                    highlightNos={missingInClean}
                  />
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Sağ Panel — Temiz Veri */}
        <div className="admin-card overflow-hidden transition-all">
          <button
            type="button"
            onClick={() => setCleanOpen((o) => !o)}
            className="w-full flex items-center justify-between px-5 py-4 transition-colors text-left select-none cursor-pointer"
            style={{ backgroundColor: 'var(--color-paper-2)' }}
          >
            <div className="flex items-center gap-3 flex-wrap">
              <div
                className="w-2 h-2 rounded-full"
                style={{
                  backgroundColor: cleanArticles.length > 0 ? '#10b981' : 'var(--color-muted)',
                }}
              />
              <span className="text-sm font-semibold" style={{ color: 'var(--color-ink)' }}>
                Temiz Veri ({cleanArticles.length} madde)
              </span>
              {droppedArticleCount > 0 && (
                <span className="admin-badge admin-badge-pending text-[10px]">
                  ⚠ {droppedArticleCount} madde otomatik elendi: [{droppedArticleNos.join(', ')}]
                </span>
              )}
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs" style={{ color: 'var(--color-muted)' }}>
                {cleanOpen ? 'Kapat' : 'Aç'}
              </span>
              <ChevronDown
                className={`w-4 h-4 transition-transform duration-200 ${
                  cleanOpen ? 'rotate-180' : ''
                }`}
                style={{ color: cleanOpen ? '#10b981' : 'var(--color-muted)' }}
              />
            </div>
          </button>

          <AnimatePresence initial={false}>
            {cleanOpen && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.2, ease: 'easeOut' }}
                className="overflow-hidden border-t"
                style={{ borderColor: 'var(--color-rule)' }}
              >
                <div
                  ref={cleanScrollRef}
                  className="p-4 max-h-[70vh] overflow-y-auto"
                >
                  {cleanArticles.length > 0 ? (
                    <JsonViewer
                      label="Temiz Veri (Clean)"
                      articles={cleanArticles}
                      highlightNos={missingInRaw}
                    />
                  ) : (
                    <div className="py-8 text-center text-xs" style={{ color: 'var(--color-muted)' }}>
                      Henüz temiz veri oluşturulmadı. Yukarıdaki "Preprocess Et" butonunu kullanarak oluşturabilirsiniz.
                    </div>
                  )}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}
