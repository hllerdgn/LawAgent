import React, { useState, useEffect } from 'react';

import { Save, CheckCircle2, Sliders, Palette, Building2, Sparkles } from 'lucide-react';
import { useTheme } from '../../../themes/ThemeProvider';
import { IMPLEMENTED_THEMES, THEME_DISPLAY_NAMES } from '../../../themes/registry';
import type { HallmarkThemeId } from '../../../themes/types';
import { PRESET_CLIENTS } from '../../../config/clients';

export function AdminSettings() {
  const { themeId, setThemeId, theme } = useTheme();

  const [settings, setSettings] = useState({
    clientId: 'lawagent-demo',
    siteName: 'LawAgent AI',
    themeId: themeId as string,
    welcomeMessage: 'Merhaba! LawAgent AI hukuki asistanına hoş geldiniz. Size nasıl yardımcı olabilirim?',
    email: 'contact@lawagent.ai',
    phone: '+90 212 555 0100',
    address: 'İstanbul, Türkiye',
    about: 'LawAgent AI kullanıcılara güvenilir, profesyonel ve yapay zeka destekli hukuki karar desteği sunar.',
    ragK: '7',
    aiModel: 'llama-3.3-70b-versatile',
  });

  const [savedSuccess, setSavedSuccess] = useState(false);

  // Mount anında localStorage'dan kayıtlı ayarları yükle
  useEffect(() => {
    const savedClientId = localStorage.getItem('lawagent_client_id') || 'lawagent-demo';
    const preset = PRESET_CLIENTS[savedClientId] || PRESET_CLIENTS['lawagent-demo'];
    
    const savedThemeId = localStorage.getItem('lawagent_theme_id') || preset.themeId || themeId;
    const savedSiteName = localStorage.getItem('lawagent_site_name') || preset.name;
    const savedWelcome = localStorage.getItem('lawagent_welcome_message') || preset.welcomeMessage;
    const savedEmail = localStorage.getItem('lawagent_email') || preset.contactInfo.email;
    const savedPhone = localStorage.getItem('lawagent_phone') || preset.contactInfo.phone;
    const savedAddress = localStorage.getItem('lawagent_address') || preset.contactInfo.address;
    const savedAbout = localStorage.getItem('lawagent_about') || 'LawAgent AI kullanıcılara güvenilir, profesyonel ve yapay zeka destekli hukuki karar desteği sunar.';
    const savedK = localStorage.getItem('lawagent_rag_k') || '7';
    const savedModel = localStorage.getItem('lawagent_ai_model') || 'llama-3.3-70b-versatile';

    setSettings({
      clientId: savedClientId,
      siteName: savedSiteName,
      themeId: savedThemeId,
      welcomeMessage: savedWelcome,
      email: savedEmail,
      phone: savedPhone,
      address: savedAddress,
      about: savedAbout,
      ragK: savedK,
      aiModel: savedModel,
    });
  }, []);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value } = e.target;

    if (name === 'clientId') {
      const preset = PRESET_CLIENTS[value] || PRESET_CLIENTS['lawagent-demo'];
      const newTheme = preset.themeId as HallmarkThemeId;
      setSettings((prev) => ({
        ...prev,
        clientId: value,
        siteName: preset.name,
        themeId: newTheme,
        welcomeMessage: preset.welcomeMessage,
        email: preset.contactInfo.email,
        phone: preset.contactInfo.phone,
        address: preset.contactInfo.address,
      }));
      setThemeId(newTheme);
      return;
    }

    setSettings((prev) => ({ ...prev, [name]: value }));

    if (name === 'themeId') {
      setThemeId(value as HallmarkThemeId);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    localStorage.setItem('lawagent_client_id', settings.clientId);
    localStorage.setItem('lawagent_site_name', settings.siteName);
    localStorage.setItem('lawagent_theme_id', settings.themeId);
    localStorage.setItem('lawagent_welcome_message', settings.welcomeMessage);
    localStorage.setItem('lawagent_email', settings.email);
    localStorage.setItem('lawagent_phone', settings.phone);
    localStorage.setItem('lawagent_address', settings.address);
    localStorage.setItem('lawagent_about', settings.about);
    localStorage.setItem('lawagent_rag_k', settings.ragK);
    localStorage.setItem('lawagent_ai_model', settings.aiModel);

    setThemeId(settings.themeId as HallmarkThemeId);
    window.dispatchEvent(new Event('lawagent_settings_updated'));

    setSavedSuccess(true);
    setTimeout(() => setSavedSuccess(false), 4000);
  };


  return (
    <div className="space-y-8 font-sans antialiased">
      
      {/* Top Header */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200/80 shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-slate-900 text-2xl font-bold font-serif">Sistem & White-Label Ayarları</h1>
          <p className="text-slate-500 text-xs sm:text-sm mt-1">
            Multi-Tenant müşteri seçimi, Hallmark teması ve AI asistan RAG parametrelerini buradan yönetebilirsiniz.
          </p>
        </div>
      </div>

      <div className="bg-white rounded-2xl border border-slate-200/80 shadow-xs p-6 lg:p-8">
        
        {savedSuccess && (
          <div className="mb-6 bg-emerald-50 border border-emerald-200 text-emerald-800 p-4 rounded-xl flex items-center gap-3 text-xs">
            <CheckCircle2 className="w-5 h-5 text-emerald-600 flex-shrink-0" />
            <span className="font-semibold">Sistem ve Hallmark tema ayarları başarıyla kaydedildi!</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-8 max-w-3xl">
          
          {/* 1. Multi-Tenant & Theme Section */}
          <div className="pb-6 border-b border-slate-100 space-y-6">
            <h3 className="text-slate-900 font-bold font-serif text-base flex items-center gap-2">
              <Palette className="w-4 h-4 text-violet-600" />
              <span>Hallmark Tema & White-Label Yapılandırması</span>
            </h3>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5 flex items-center gap-1.5">
                  <Building2 className="w-3.5 h-3.5 text-slate-500" />
                  <span>Aktif Müşteri / Tenant (Client ID)</span>
                </label>
                <select
                  name="clientId"
                  value={settings.clientId}
                  onChange={handleChange}
                  className="w-full px-4 py-2.5 bg-slate-50 border border-slate-300 rounded-xl text-xs font-medium focus:outline-none focus:ring-2 focus:ring-violet-500"
                >
                  <option value="lawagent-demo">lawagent-demo (LawAgent AI — Default)</option>
                  <option value="yildiz-hukuk">yildiz-hukuk (Yıldız & Ortakları)</option>
                  <option value="ozkan-avukatlik">ozkan-avukatlik (Özkan Hukuk)</option>
                  <option value="kocak-hukuk">kocak-hukuk (Koçak Hukuk Bürosu)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5 flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-amber-500" />
                  <span>Atanmış Hallmark Teması</span>
                </label>
                <select
                  name="themeId"
                  value={settings.themeId}
                  onChange={handleChange}
                  className="w-full px-4 py-2.5 bg-slate-50 border border-slate-300 rounded-xl text-xs font-medium focus:outline-none focus:ring-2 focus:ring-violet-500"
                >
                  {IMPLEMENTED_THEMES.map((t) => (
                    <option key={t.id} value={t.id}>
                      {THEME_DISPLAY_NAMES[t.id as keyof typeof THEME_DISPLAY_NAMES] || t.displayName}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Live Theme Preview Badge */}
            <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
              <div>
                <div className="text-xs font-semibold text-slate-800 flex items-center gap-2">
                  <span>Seçili Tema:</span>
                  <span className="px-2 py-0.5 rounded-md text-white text-[11px] font-mono uppercase" style={{ backgroundColor: theme.colors.accent }}>
                    {theme.id} ({theme.genre})
                  </span>
                </div>
                <p className="text-slate-500 text-xs mt-1">{theme.description}</p>
              </div>

              {/* Color Swatches */}
              <div className="flex items-center gap-2 bg-white px-3 py-2 rounded-lg border border-slate-200">
                <span className="text-[10px] text-slate-400 font-mono">RENKLER:</span>
                <span className="w-4 h-4 rounded-full border border-slate-300 shadow-xs" style={{ backgroundColor: theme.colors.paper }} title="Paper (Arka Plan)" />
                <span className="w-4 h-4 rounded-full shadow-xs" style={{ backgroundColor: theme.colors.ink }} title="Ink (Metin)" />
                <span className="w-4 h-4 rounded-full shadow-xs" style={{ backgroundColor: theme.colors.accent }} title="Accent (Vurgu)" />
                <span className="w-4 h-4 rounded-full shadow-xs" style={{ backgroundColor: theme.colors.accent2 }} title="Accent 2 (İkincil Vurgu)" />
              </div>
            </div>
          </div>

          {/* 2. Büro Genel Bilgileri */}
          <div className="pb-6 border-b border-slate-100 space-y-4">
            <h3 className="text-slate-900 font-bold font-serif text-base">
              <span>Büro & Marka Bilgileri</span>
            </h3>
            
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                Büro / Proje Adı (White-Label Markası)
              </label>
              <Input
                name="siteName"
                value={settings.siteName}
                onChange={handleChange}
                className="w-full rounded-xl bg-slate-50 border-slate-300 text-sm"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                Chatbot Karşılama Mesajı
              </label>
              <textarea
                name="welcomeMessage"
                rows={2}
                value={settings.welcomeMessage}
                onChange={handleChange}
                className="w-full px-4 py-2.5 bg-slate-50 border border-slate-300 rounded-xl text-xs font-medium focus:outline-none focus:ring-2 focus:ring-violet-500"
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                  İletişim E-Posta
                </label>
                <Input
                  type="email"
                  name="email"
                  value={settings.email}
                  onChange={handleChange}
                  className="w-full rounded-xl bg-slate-50 border-slate-300 text-sm"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                  Telefon
                </label>
                <Input
                  type="tel"
                  name="phone"
                  value={settings.phone}
                  onChange={handleChange}
                  className="w-full rounded-xl bg-slate-50 border-slate-300 text-sm"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                Adres Bilgisi
              </label>
              <Input
                name="address"
                value={settings.address}
                onChange={handleChange}
                className="w-full rounded-xl bg-slate-50 border-slate-300 text-sm"
              />
            </div>
          </div>

          {/* 3. AI Asistan & RAG Parametreleri */}
          <div className="pb-4 space-y-4">
            <h3 className="text-slate-900 font-bold font-serif text-base flex items-center gap-2">
              <Sliders className="w-4 h-4 text-amber-500" />
              <span>AI Asistan & RAG Parametreleri</span>
            </h3>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                  Getirilecek Vektör Parçası (k Değeri)
                </label>
                <select
                  name="ragK"
                  value={settings.ragK}
                  onChange={handleChange}
                  className="w-full px-4 py-2.5 bg-slate-50 border border-slate-300 rounded-xl text-xs font-medium focus:outline-none focus:ring-2 focus:ring-amber-500"
                >
                  <option value="3">k = 3 (Hızlı Özet)</option>
                  <option value="5">k = 5 (Standart & Önerilen)</option>
                  <option value="7">k = 7 (Optimum RAG)</option>
                  <option value="10">k = 10 (Derinlemesine Analiz)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                  Aktif LLM Modeli
                </label>
                <select
                  name="aiModel"
                  value={settings.aiModel}
                  onChange={handleChange}
                  className="w-full px-4 py-2.5 bg-slate-50 border border-slate-300 rounded-xl text-xs font-medium focus:outline-none focus:ring-2 focus:ring-amber-500"
                >
                  <option value="llama-3.3-70b-versatile">Groq Llama-3.3-70B (Production)</option>
                  <option value="Meta-Llama-3-8B-Instruct">Meta Llama-3-8B-Instruct</option>
                </select>
              </div>
            </div>
          </div>

          <div className="flex justify-end pt-2">
            <button 
              type="submit"
              className="bg-slate-900 hover:bg-slate-800 text-white font-medium text-xs px-6 py-3 rounded-xl shadow-md transition-colors flex items-center gap-2 cursor-pointer border border-slate-800"
            >
              <Save className="w-4 h-4 text-amber-400" />
              <span>Ayarları Kaydet</span>
            </button>
          </div>

        </form>
      </div>

    </div>
  );
}
