// src/admin/pages/DocumentsDashboard.tsx
import React from 'react';
import { FolderOpen } from 'lucide-react';
import { DocumentUploadForm } from '../components/DocumentUploadForm';
import { DocumentTable } from '../components/DocumentTable';

export function DocumentsDashboard() {
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
          <FolderOpen className="w-5 h-5" style={{ color: 'var(--color-accent)' }} />
        </div>
        <div>
          <h1 className="admin-heading text-2xl font-normal">Şirket / Büro / Avukat Belgeleri</h1>
          <p className="admin-eyebrow text-xs mt-0.5">
            Özel dokümanların (PDF, DOCX, TXT) vektörleştirilmesi ve yönetimi
          </p>
        </div>
      </div>

      {/* Belge Yükleme Formu */}
      <DocumentUploadForm />

      {/* Belge Listesi */}
      <div>
        <h2 className="admin-eyebrow text-xs mb-3">
          Yüklü Belgeler
        </h2>
        <DocumentTable />
      </div>
    </div>
  );
}
