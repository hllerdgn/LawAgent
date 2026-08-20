import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { Scale, Lock, Mail, ShieldCheck, ArrowRight } from 'lucide-react';

export function AdminLogin() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      if (email === 'admin@lawagent.ai' && password === 'demo123') {
        localStorage.setItem('adminToken', 'demo-token');
        navigate('/admin/dashboard');
      } else {
        setError('Geçersiz e-posta veya şifre (Demo: admin@lawagent.ai / demo123)');
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleFillDemo = () => {
    setEmail('admin@lawagent.ai');
    setPassword('demo123');
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center p-6 relative overflow-hidden font-sans antialiased">
      
      {/* Glow Effects */}
      <div className="absolute top-1/4 left-1/3 w-96 h-96 bg-amber-500/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-1/4 right-1/3 w-96 h-96 bg-slate-800/40 rounded-full blur-3xl pointer-events-none" />

      <div className="max-w-md w-full relative z-10">
        <div className="bg-slate-900/90 backdrop-blur-2xl rounded-3xl border border-slate-800 p-8 lg:p-10 shadow-2xl">
          
          <div className="flex flex-col items-center text-center mb-8">
            <div className="w-14 h-14 bg-amber-500/10 border border-amber-500/30 rounded-2xl flex items-center justify-center mb-4 shadow-md">
              <Scale className="w-7 h-7 text-amber-400" />
            </div>
            <h1 className="text-white text-2xl font-bold font-serif">Admin Portalı</h1>
            <p className="text-slate-400 text-xs mt-1">LawAgent AI SaaS Paneli</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-5">
            
            {error && (
              <div className="bg-red-500/10 border border-red-500/30 text-red-400 p-3.5 rounded-xl text-xs flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 flex-shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <div>
              <label htmlFor="email" className="block text-xs font-semibold text-slate-300 mb-1.5">
                E-Posta Adresi
              </label>
              <div className="relative">
                <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="admin@lawagent.ai"
                  className="w-full pl-11 pr-4 py-3 bg-slate-950/80 border border-slate-800 text-white placeholder:text-slate-500 focus:border-amber-500 focus:outline-none rounded-xl text-sm transition-colors"
                  required
                />
              </div>
            </div>

            <div>
              <label htmlFor="password" className="block text-xs font-semibold text-slate-300 mb-1.5">
                Yönetici Şifresi
              </label>
              <div className="relative">
                <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <input
                  id="password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full pl-11 pr-4 py-3 bg-slate-950/80 border border-slate-800 text-white placeholder:text-slate-500 focus:border-amber-500 focus:outline-none rounded-xl text-sm transition-colors"
                  required
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full bg-amber-500 hover:bg-amber-600 text-slate-950 font-bold text-sm py-3.5 rounded-xl shadow-lg transition-all flex items-center justify-center gap-2 cursor-pointer border border-amber-400/20 disabled:opacity-50"
            >
              {isLoading ? (
                <span>Giriş Yapılıyor...</span>
              ) : (
                <>
                  <span>Sisteme Giriş Yap</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>

            <div className="pt-3 border-t border-slate-800 text-center">
              <button
                type="button"
                onClick={handleFillDemo}
                className="text-xs text-amber-400/80 hover:text-amber-400 transition-colors underline cursor-pointer"
              >
                Demo Bilgilerini Otomatik Doldur (admin@lawagent.ai / demo123)
              </button>
            </div>

          </form>

        </div>
      </div>
    </div>
  );
}
