import React from 'react';
import { Link } from 'react-router';
import { Button } from '../components/Button';
import { Home, ArrowLeft } from 'lucide-react';

export function NotFound() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-[var(--color-background)] to-white flex items-center justify-center">
      <div className="max-w-2xl mx-auto px-6 text-center">
        <div className="mb-8">
          <h1 className="text-9xl text-[var(--color-primary)] mb-4">404</h1>
          <h2 className="text-[var(--color-primary)] mb-4">Sayfa Bulunamadı</h2>
          <p className="text-[var(--color-text-secondary)] text-lg">
            Aradığınız sayfa mevcut değil veya taşınmış olabilir.
          </p>
        </div>
        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <Link to="/">
            <Button variant="primary">
              <Home className="w-5 h-5" />
              Ana Sayfaya Dön
            </Button>
          </Link>
          <button onClick={() => window.history.back()}>
            <Button variant="secondary">
              <ArrowLeft className="w-5 h-5" />
              Geri Dön
            </Button>
          </button>
        </div>
      </div>
    </div>
  );
}
