import React, { useState } from 'react';
import { FileUp, File, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';

export function AdminDocuments() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [status, setStatus] = useState<'idle' | 'uploading' | 'success' | 'error'>('idle');
  const [message, setMessage] = useState('');
  const [chunksAdded, setChunksAdded] = useState(0);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      if (file.type !== 'application/pdf') {
        setStatus('error');
        setMessage('Lütfen sadece PDF dosyası seçin.');
        return;
      }
      setSelectedFile(file);
      setStatus('idle');
      setMessage('');
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) return;

    setStatus('uploading');
    setMessage('Belge yükleniyor ve işleniyor, lütfen bekleyin...');

    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      const response = await fetch('http://localhost:7860/upload-document', {
        method: 'POST',
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Dosya yüklenirken bir hata oluştu');
      }

      setStatus('success');
      setMessage(data.message || 'Belge başarıyla yüklendi.');
      setChunksAdded(data.chunks_added || 0);
      setSelectedFile(null);
    } catch (error: any) {
      console.error('Upload error:', error);
      setStatus('error');
      setMessage(error.message || 'Sunucuya bağlanılamadı.');
    }
  };

  return (
    <div className="space-y-8 animate-fadeIn">
      <div>
        <h1 className="text-[var(--color-primary)] mb-2">Site Belgeleri</h1>
        <p className="text-[var(--color-text-secondary)]">
          Asistanın soruları yanıtlarken referans alacağı PDF belgelerini buradan yükleyebilirsiniz.
        </p>
      </div>

      <div className="bg-white p-8 rounded-xl border border-gray-200 shadow-sm max-w-2xl">
        <div className="border-2 border-dashed border-gray-300 rounded-xl p-10 text-center hover:border-[var(--color-accent)] transition-colors">
          <input
            type="file"
            id="file-upload"
            accept=".pdf"
            className="hidden"
            onChange={handleFileChange}
            disabled={status === 'uploading'}
          />
          <label
            htmlFor="file-upload"
            className={`flex flex-col items-center justify-center cursor-pointer ${
              status === 'uploading' ? 'opacity-50 pointer-events-none' : ''
            }`}
          >
            <div className="w-16 h-16 bg-gray-50 rounded-full flex items-center justify-center mb-4">
              <FileUp className="w-8 h-8 text-gray-400" />
            </div>
            <span className="text-[var(--color-primary)] font-medium mb-1">
              PDF Belgesi Seçin
            </span>
            <span className="text-[var(--color-text-secondary)] text-sm mb-4">
              Sadece .pdf formatında dosyalar
            </span>
            
            <span className="px-6 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors text-sm font-medium">
              Bilgisayardan Gözat
            </span>
          </label>
        </div>

        {selectedFile && status !== 'success' && (
          <div className="mt-6 flex items-center justify-between p-4 bg-blue-50 border border-blue-100 rounded-lg">
            <div className="flex items-center gap-3">
              <File className="w-6 h-6 text-blue-500" />
              <div>
                <p className="text-sm font-medium text-blue-900">{selectedFile.name}</p>
                <p className="text-xs text-blue-700">{(selectedFile.size / 1024 / 1024).toFixed(2)} MB</p>
              </div>
            </div>
            <button
              onClick={handleUpload}
              disabled={status === 'uploading'}
              className="px-4 py-2 bg-[var(--color-primary)] text-white rounded-lg hover:opacity-90 transition-opacity text-sm font-medium flex items-center gap-2 disabled:opacity-50"
            >
              {status === 'uploading' && <Loader2 className="w-4 h-4 animate-spin" />}
              {status === 'uploading' ? 'İşleniyor...' : 'Yükle'}
            </button>
          </div>
        )}

        {status === 'error' && (
          <div className="mt-6 flex items-start gap-3 p-4 bg-red-50 border border-red-100 rounded-lg text-red-700">
            <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
            <p className="text-sm">{message}</p>
          </div>
        )}

        {status === 'success' && (
          <div className="mt-6 flex items-start gap-3 p-4 bg-green-50 border border-green-100 rounded-lg text-green-700">
            <CheckCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-medium mb-1">{message}</p>
              <p className="text-xs text-green-600">Veritabanına eklenen bilgi parçası sayısı: {chunksAdded}</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
