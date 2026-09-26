// src/admin/components/DocumentUploadForm.tsx
import React, { useState, useRef, useMemo } from 'react';
import { UploadCloud, FileText, AlertTriangle, AlertCircle, CheckCircle2, Loader2 } from 'lucide-react';
import { useUploadDocument, useDocuments } from '../hooks/useDocuments';

const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB
const ALLOWED_EXTS = ['pdf', 'docx', 'txt'];

function slugify(text: string): string {
  const base = text.replace(/\.[^/.]+$/, '');
  return base
    .toLowerCase()
    .replace(/[^\w\s-]/g, '')
    .replace(/[\s_-]+/g, '_')
    .slice(0, 64) || 'document';
}

export function DocumentUploadForm() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const { data: docsData } = useDocuments();
  const uploadMutation = useUploadDocument();

  // Overwrite kontrolü: Seçilen dosyanın slug'ı mevcut dokümanlarda var mı?
  const isOverwrite = useMemo(() => {
    if (!selectedFile || !docsData?.documents) return false;
    const currentSlug = slugify(selectedFile.name);
    return docsData.documents.some((d) => d.document_id === currentSlug);
  }, [selectedFile, docsData]);

  const validateAndSetFile = (file: File) => {
    setValidationError(null);
    setSuccessMessage(null);

    const ext = file.name.split('.').pop()?.toLowerCase() ?? '';
    if (!ALLOWED_EXTS.includes(ext)) {
      setValidationError(`Geçersiz dosya türü (.${ext}). Sadece PDF, DOCX ve TXT desteklenir.`);
      setSelectedFile(null);
      return;
    }

    if (file.size > MAX_FILE_SIZE) {
      setValidationError(
        `Dosya boyutu 10MB sınırını aşıyor (${(file.size / (1024 * 1024)).toFixed(1)} MB). Lütfen daha küçük bir dosya yükleyin.`
      );
      setSelectedFile(null);
      return;
    }

    setSelectedFile(file);
  };

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      validateAndSetFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      validateAndSetFile(e.target.files[0]);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) return;

    uploadMutation.mutate(selectedFile, {
      onSuccess: (data) => {
        setSuccessMessage(`"${data.filename}" başarıyla yüklendi. Arka planda indeksleniyor.`);
        setSelectedFile(null);
        if (fileInputRef.current) fileInputRef.current.value = '';
      },
      onError: (err) => {
        setValidationError(err.message || 'Yükleme sırasında bir hata oluştu.');
      },
    });
  };

  return (
    <div className="admin-card p-6 space-y-4">
      <div className="flex items-center gap-3 mb-2">
        <div 
          className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0"
          style={{
            backgroundColor: 'color-mix(in oklch, var(--color-accent) 12%, transparent)',
            border: '1px solid color-mix(in oklch, var(--color-accent) 25%, transparent)',
          }}
        >
          <UploadCloud className="w-5 h-5" style={{ color: 'var(--color-accent)' }} />
        </div>
        <div>
          <h2 className="admin-heading text-lg font-normal">Yeni Belge Yükle</h2>
          <p className="admin-eyebrow text-xs mt-0.5">
            Şirket, avukat veya büro belgelerini (PDF, DOCX, TXT - maks. 10MB) vektör hafızasına aktarın
          </p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Drag & Drop Alanı */}
        <div
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className="p-8 text-center cursor-pointer transition-all duration-200 rounded-2xl border-2 border-dashed"
          style={{
            backgroundColor: dragActive ? 'color-mix(in oklch, var(--color-accent) 6%, transparent)' : 'var(--color-paper)',
            borderColor: dragActive ? 'var(--color-accent)' : 'var(--color-rule)',
          }}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.docx,.txt"
            onChange={handleFileChange}
            className="hidden"
          />
          <div className="flex flex-col items-center justify-center gap-2">
            <div 
              className="w-12 h-12 rounded-full flex items-center justify-center mb-1"
              style={{
                backgroundColor: 'color-mix(in oklch, var(--color-accent) 10%, transparent)',
                color: 'var(--color-accent)',
              }}
            >
              <FileText className="w-6 h-6" />
            </div>
            {selectedFile ? (
              <div>
                <p className="text-sm font-semibold" style={{ color: 'var(--color-accent)' }}>{selectedFile.name}</p>
                <p className="text-xs mt-0.5" style={{ color: 'var(--color-muted)' }}>
                  {(selectedFile.size / 1024).toFixed(0)} KB • Farklı bir dosya seçmek için tıklayın
                </p>
              </div>
            ) : (
              <div>
                <p className="text-sm font-medium" style={{ color: 'var(--color-ink)' }}>
                  Dosyayı buraya sürükleyin veya <span style={{ color: 'var(--color-accent)', textDecoration: 'underline' }}>seçin</span>
                </p>
                <p className="text-xs mt-1" style={{ color: 'var(--color-muted)' }}>PDF, DOCX veya TXT • Maksimum 10 MB</p>
              </div>
            )}
          </div>
        </div>

        {/* Overwrite Uyarısı */}
        {isOverwrite && (
          <div 
            className="flex items-start gap-2.5 p-3.5 rounded-xl text-xs border"
            style={{
              backgroundColor: 'color-mix(in oklch, #f59e0b 10%, transparent)',
              borderColor: 'color-mix(in oklch, #f59e0b 30%, transparent)',
              color: '#b45309',
            }}
          >
            <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0" />
            <div>
              <span className="font-semibold">Mevcut Belge Üzerine Yazılacak (Overwrite):</span> Bu ada sahip bir belge sistemde zaten var. Yüklemeye devam ederseniz eski belge ve vektörleri silinip yerine bu güncel dosya kaydedilecektir.
            </div>
          </div>
        )}

        {/* Hata Mesajı */}
        {validationError && (
          <div 
            className="flex items-center gap-2 p-3 rounded-xl text-xs border"
            style={{
              backgroundColor: 'color-mix(in oklch, #ef4444 10%, transparent)',
              borderColor: 'color-mix(in oklch, #ef4444 30%, transparent)',
              color: '#dc2626',
            }}
          >
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{validationError}</span>
          </div>
        )}

        {/* Başarı Mesajı */}
        {successMessage && (
          <div 
            className="flex items-center gap-2 p-3 rounded-xl text-xs border"
            style={{
              backgroundColor: 'color-mix(in oklch, #10b981 10%, transparent)',
              borderColor: 'color-mix(in oklch, #10b981 30%, transparent)',
              color: '#059669',
            }}
          >
            <CheckCircle2 className="w-4 h-4 shrink-0" />
            <span>{successMessage}</span>
          </div>
        )}

        {/* Yükleme Butonu */}
        <div className="flex justify-end">
          <button
            type="submit"
            disabled={!selectedFile || uploadMutation.isPending}
            className="admin-btn-primary text-xs py-2.5 px-5 cursor-pointer"
          >
            {uploadMutation.isPending ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                <span>Yükleniyor ve İndeksleniyor...</span>
              </>
            ) : (
              <>
                <UploadCloud className="w-3.5 h-3.5" />
                <span>{isOverwrite ? 'Güncelle ve Üzerine Yaz' : 'Belgeyi Sisteme Yükle'}</span>
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
}
