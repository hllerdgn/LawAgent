// src/admin/pages/ScrapeDashboard.tsx
// Ana sayfa: ScrapeForm (üstte) + JobTable (altta)

import { ScrapeForm } from '../components/ScrapeForm';
import { JobTable } from '../components/JobTable';
import { Database } from 'lucide-react';

export function ScrapeDashboard() {
  return (
    <div className="space-y-6">
      {/* Başlık */}
      <div className="flex items-center gap-3.5">
        <div 
          className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0"
          style={{
            backgroundColor: 'color-mix(in oklch, var(--color-accent) 12%, transparent)',
            border: '1px solid color-mix(in oklch, var(--color-accent) 25%, transparent)',
          }}
        >
          <Database className="w-5 h-5" style={{ color: 'var(--color-accent)' }} />
        </div>
        <div>
          <h1 className="admin-heading text-2xl font-normal">Corpus Yönetimi</h1>
          <p className="admin-eyebrow text-xs mt-0.5">
            Mevzuat scraping &amp; preprocessing yönetim paneli
          </p>
        </div>
      </div>

      {/* Scraping Formu */}
      <ScrapeForm />

      {/* Job Listesi */}
      <div>
        <h2 className="admin-eyebrow text-xs mb-3">
          İşlem Geçmişi
        </h2>
        <JobTable />
      </div>
    </div>
  );
}
