// src/admin/components/JsonViewer.tsx
// Madde listesini sanallaştırarak (virtualization) render eder.
// 1000+ maddelik kanunlarda DOM'u kilitlemez.
// Sayfalama yaklaşımı: slice + "Daha Fazla Yükle" butonu (react-window kurmadan)

import { useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import type { Article } from '../types';

const PAGE_SIZE = 50;

function ArticleRow({
  article,
  highlight = false,
}: {
  article: Article;
  highlight?: boolean;
}) {
  const [open, setOpen] = useState(false);

  return (
    <div
      data-article-no={article.no}
      className={`border rounded-xl overflow-hidden transition-colors ${
        highlight
          ? 'border-orange-500/50 bg-orange-500/5'
          : 'admin-card-inner'
      }`}
    >
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center gap-3 px-4 py-3 text-left transition-colors cursor-pointer"
        style={{ backgroundColor: 'transparent' }}
      >
        {open ? (
          <ChevronDown className="w-4 h-4 flex-shrink-0" style={{ color: 'var(--color-muted)' }} />
        ) : (
          <ChevronRight className="w-4 h-4 flex-shrink-0" style={{ color: 'var(--color-muted)' }} />
        )}
        <span className="font-mono text-xs font-semibold flex-shrink-0" style={{ color: 'var(--color-accent)' }}>
          Madde {article.no}
        </span>
        {article.baslik && (
          <span className="text-xs truncate font-medium" style={{ color: 'var(--color-ink)' }}>{article.baslik}</span>
        )}
        {highlight && (
          <span className="ml-auto text-xs font-medium flex-shrink-0" style={{ color: '#b45309' }}>
            ⚠ Eşleşme yok
          </span>
        )}
      </button>

      {open && (
        <div className="px-4 pb-4 pt-1">
          {article.baslik && (
            <p className="text-xs font-semibold mb-2" style={{ color: 'var(--color-ink)' }}>
              {article.baslik}
            </p>
          )}
          <p className="text-xs leading-relaxed whitespace-pre-wrap" style={{ color: 'var(--color-ink-2)' }}>
            {article.metin}
          </p>
          {article.alt_baslik && (
            <p 
              className="mt-3 text-xs font-semibold pt-2 border-t"
              style={{ color: 'var(--color-accent)', borderColor: 'var(--color-rule-2)' }}
            >
              ↳ {article.alt_baslik}
            </p>
          )}
          {(article.duplicate_lines_removed ?? 0) > 0 && (
            <p 
              className="mt-2 text-xs rounded-lg px-3 py-1.5 border"
              style={{
                backgroundColor: 'color-mix(in oklch, #f59e0b 10%, transparent)',
                borderColor: 'color-mix(in oklch, #f59e0b 25%, transparent)',
                color: '#b45309',
              }}
            >
              ⚠ Bu maddede {article.duplicate_lines_removed} tekrar satır otomatik temizlendi — kontrol edin.
            </p>
          )}
        </div>
      )}
    </div>
  );
}

interface JsonViewerProps {
  articles: Article[];
  /** Madde no'larının vurgulanacağı set — eşleşmeyen maddeler için */
  highlightNos?: Set<string>;
  label: string;
}

export function JsonViewer({ articles, highlightNos, label }: JsonViewerProps) {
  const [page, setPage] = useState(1);
  const visible = articles.slice(0, page * PAGE_SIZE);
  const hasMore = visible.length < articles.length;

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center justify-between mb-1">
        <span className="admin-eyebrow text-xs font-medium">
          {label}
        </span>
        <span className="text-xs tabular-nums font-mono" style={{ color: 'var(--color-muted)' }}>
          {articles.length} madde
        </span>
      </div>

      <div className="space-y-1.5">
        {visible.map((a) => (
          <ArticleRow
            key={a.no}
            article={a}
            highlight={highlightNos?.has(a.no)}
          />
        ))}
      </div>

      {hasMore && (
        <button
          onClick={() => setPage((p) => p + 1)}
          className="admin-btn-secondary text-xs py-2 text-center cursor-pointer mt-1"
        >
          + {Math.min(PAGE_SIZE, articles.length - visible.length)} madde daha yükle
        </button>
      )}
    </div>
  );
}
