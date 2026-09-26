// src/admin/components/ScrapeForm.tsx
// Kanun scraping başlatma formu
// law_id ve law_name zorunlu, url opsiyonel (backend otomatik türetir)

import React, { useState } from 'react';
import { Search, AlertCircle, CheckCircle, Loader2 } from 'lucide-react';
import { useStartScrape } from '../hooks/useScrapeActions';
import type { ScrapeRequest } from '../types';
import { useJobs } from '../hooks/useJobs';

export function ScrapeForm() {
  const [lawId, setLawId] = useState('');
  const [lawName, setLawName] = useState('');
  const [formError, setFormError] = useState('');

  const { data: jobs } = useJobs();
  const { mutate: startScrape, isPending, isSuccess, reset } = useStartScrape();

  const isDuplicate = jobs?.some((j) => j.law_id === lawId.trim());

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setFormError('');

    if (!lawId.trim() || !lawName.trim()) {
      setFormError('Kanun numarası ve adı zorunludur.');
      return;
    }

    const req: ScrapeRequest = {
      law_id: lawId.trim(),
      law_name: lawName.trim(),
    };

    startScrape(req, {
      onSuccess: () => {
        setLawId('');
        setLawName('');
        setTimeout(reset, 3000);
      },
      onError: (err) => {
        setFormError(err.message);
      },
    });
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="admin-card p-6 space-y-4"
    >
      <div className="flex items-center gap-2.5 mb-2">
        <Search className="w-4.5 h-4.5" style={{ color: 'var(--color-accent)' }} />
        <h2 className="admin-heading text-lg font-normal">
          Kanun Scraping Başlat
        </h2>
      </div>

      {/* Duplicate uyarısı — engelleme yok */}
      {isDuplicate && (
        <div 
          className="flex items-start gap-2 rounded-xl px-4 py-3 text-xs border"
          style={{
            backgroundColor: 'color-mix(in oklch, #f59e0b 10%, transparent)',
            borderColor: 'color-mix(in oklch, #f59e0b 30%, transparent)',
            color: '#b45309',
          }}
        >
          <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
          <span>
            <strong>{lawId}</strong> numaralı kanun daha önce çekildi. Devam
            ederseniz yeni versiyonlu dosya oluşturulur, eskisi silinmez.
          </span>
        </div>
      )}

      {/* Hata mesajı */}
      {formError && (
        <div 
          className="flex items-start gap-2 rounded-xl px-4 py-3 text-xs border"
          style={{
            backgroundColor: 'color-mix(in oklch, #ef4444 10%, transparent)',
            borderColor: 'color-mix(in oklch, #ef4444 30%, transparent)',
            color: '#dc2626',
          }}
        >
          <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
          <span>{formError}</span>
        </div>
      )}

      {/* Başarı */}
      {isSuccess && (
        <div 
          className="flex items-center gap-2 rounded-xl px-4 py-3 text-xs border"
          style={{
            backgroundColor: 'color-mix(in oklch, #10b981 10%, transparent)',
            borderColor: 'color-mix(in oklch, #10b981 30%, transparent)',
            color: '#059669',
          }}
        >
          <CheckCircle className="w-4 h-4 flex-shrink-0" />
          <span>Scraping başlatıldı. Aşağıdaki tablodan durumu takip edin.</span>
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {/* Kanun Numarası */}
        <div>
          <label
            htmlFor="law-id"
            className="block text-xs font-semibold mb-1.5"
            style={{ color: 'var(--color-ink-2)' }}
          >
            Kanun Numarası
            <span className="text-red-500 ml-0.5">*</span>
          </label>
          <input
            id="law-id"
            type="text"
            value={lawId}
            onChange={(e) => setLawId(e.target.value)}
            placeholder="örn. 4721"
            className="admin-input"
            required
          />
        </div>

        {/* Kanun Adı */}
        <div>
          <label
            htmlFor="law-name"
            className="block text-xs font-semibold mb-1.5"
            style={{ color: 'var(--color-ink-2)' }}
          >
            Kanun Adı
            <span className="text-red-500 ml-0.5">*</span>
          </label>
          <input
            id="law-name"
            type="text"
            value={lawName}
            onChange={(e) => setLawName(e.target.value)}
            placeholder="örn. Türk Medeni Kanunu"
            className="admin-input"
            required
          />
        </div>
      </div>

      <p className="text-xs" style={{ color: 'var(--color-muted)' }}>
        URL boş bırakılırsa sistem <code className="px-1.5 py-0.5 rounded font-mono text-[11px]" style={{ backgroundColor: 'var(--color-paper)', border: '1px solid var(--color-rule)' }}>mevzuat.gov.tr</code>'den
        otomatik türetir (Tür: 1/Kanun, Tertip: 5).
      </p>

      <button
        type="submit"
        disabled={isPending}
        className="admin-btn-primary cursor-pointer"
      >
        {isPending ? (
          <>
            <Loader2 className="w-4 h-4 animate-spin" />
            Başlatılıyor...
          </>
        ) : (
          <>
            <Search className="w-4 h-4" />
            Scraping Başlat
          </>
        )}
      </button>
    </form>
  );
}
