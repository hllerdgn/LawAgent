import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Scale, Key, ShieldCheck, ArrowRight, Loader2 } from 'lucide-react';
import { saveAdminKey } from '../../../admin/api/adminClient';

export function AdminLogin() {
  const [apiKey, setApiKey] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      // Verilen key ile /admin/scrape'e GET atarak doğrulama
      const res = await fetch(
        `${import.meta.env.VITE_API_URL ?? 'http://localhost:7860'}/admin/scrape`,
        {
          headers: { 'X-Admin-Key': apiKey.trim() },
        }
      );

      if (res.status === 401 || res.status === 403) {
        setError('Geçersiz API anahtarı. Lütfen .env dosyanızdaki ADMIN_API_KEY değerini girin.');
        return;
      }

      // Key geçerli — sessionStorage'a kaydet (sekme kapanınca silinir)
      saveAdminKey(apiKey.trim());
      navigate('/admin/dashboard');
    } catch {
      setError('Sunucuya bağlanılamadı. Backend çalışıyor mu?');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div 
      className="min-h-screen flex items-center justify-center p-6 relative overflow-hidden"
      style={{
        backgroundColor: 'var(--color-paper)',
        color: 'var(--color-ink)',
        fontFamily: 'var(--font-body)',
      }}
    >
      {/* Hallmark Ambient Glow */}
      <div 
        className="absolute top-1/4 left-1/3 w-96 h-96 rounded-full blur-3xl pointer-events-none opacity-40"
        style={{ backgroundColor: 'var(--color-glow)' }}
      />

      <div className="max-w-md w-full relative z-10">
        <div className="admin-card p-8 lg:p-10">

          <div className="flex flex-col items-center text-center mb-8">
            <div 
              className="w-14 h-14 rounded-2xl flex items-center justify-center mb-4 transition-transform hover:scale-105"
              style={{
                backgroundColor: 'color-mix(in oklch, var(--color-accent) 12%, transparent)',
                border: '1px solid color-mix(in oklch, var(--color-accent) 30%, transparent)',
              }}
            >
              <Scale className="w-7 h-7" style={{ color: 'var(--color-accent)' }} />
            </div>
            <h1 className="admin-heading text-3xl font-normal tracking-tight">yönetim portalı</h1>
            <p className="admin-eyebrow text-xs mt-2">LawAgent AI Karar Destek Sistemi</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-5">

            {error && (
              <div 
                className="p-3.5 rounded-xl text-xs flex items-start gap-2 border"
                style={{
                  backgroundColor: 'color-mix(in oklch, #ef4444 10%, transparent)',
                  borderColor: 'color-mix(in oklch, #ef4444 30%, transparent)',
                  color: '#dc2626',
                }}
              >
                <ShieldCheck className="w-4 h-4 flex-shrink-0 mt-0.5" />
                <span>{error}</span>
              </div>
            )}

            <div>
              <label 
                htmlFor="api-key" 
                className="block text-xs font-semibold mb-1.5"
                style={{ color: 'var(--color-ink-2)' }}
              >
                Admin API Anahtarı
              </label>
              <div className="relative">
                <Key 
                  className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4" 
                  style={{ color: 'var(--color-muted)' }}
                />
                <input
                  id="api-key"
                  type="password"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  placeholder="ADMIN_API_KEY değerini girin"
                  className="admin-input pl-11 pr-4 py-3 text-sm"
                  required
                  autoComplete="current-password"
                />
              </div>
              <p className="text-xs mt-2" style={{ color: 'var(--color-muted)' }}>
                Backend <code className="px-1.5 py-0.5 rounded font-mono text-[11px]" style={{ backgroundColor: 'var(--color-paper)', border: '1px solid var(--color-rule)' }}>.env</code> dosyasındaki{' '}
                <code className="px-1.5 py-0.5 rounded font-mono text-[11px]" style={{ backgroundColor: 'var(--color-paper)', border: '1px solid var(--color-rule)' }}>ADMIN_API_KEY</code> değeri
              </p>
            </div>

            <button
              type="submit"
              disabled={isLoading || !apiKey.trim()}
              className="admin-btn-primary w-full py-3.5 text-sm cursor-pointer shadow-md"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Doğrulanıyor...
                </>
              ) : (
                <>
                  <span>Sisteme Giriş Yap</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>

          </form>
        </div>
      </div>
    </div>
  );
}

