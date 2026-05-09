import React, { useState } from 'react';
import { Button } from '../../components/Button';
import { Input } from '../../components/Input';
import { Save } from 'lucide-react';

export function AdminSettings() {
  const [settings, setSettings] = useState({
    siteName: 'FEK Hukuk & Danışmanlık',
    email: 'info@fekhukuk.com',
    phone: '0(212) 000 00 00',
    address: 'Büyükdere Cad. No: 123, Levent, İstanbul 34394',
    about: 'Müvekkillerime güvenilir, profesyonel ve çözüm odaklı hukuki danışmanlık hizmeti sunuyorum.',
  });

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    setSettings({ ...settings, [e.target.name]: e.target.value });
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    alert('Ayarlar kaydedildi!');
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-[var(--color-primary)] mb-2">Ayarlar</h1>
        <p className="text-[var(--color-text-secondary)]">
          Site ayarlarını ve genel bilgileri düzenleyin
        </p>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-8">
        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label className="block text-[var(--color-text-primary)] mb-2">
              Site Adı
            </label>
            <Input
              name="siteName"
              value={settings.siteName}
              onChange={handleChange}
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-[var(--color-text-primary)] mb-2">
                E-posta
              </label>
              <Input
                type="email"
                name="email"
                value={settings.email}
                onChange={handleChange}
              />
            </div>

            <div>
              <label className="block text-[var(--color-text-primary)] mb-2">
                Telefon
              </label>
              <Input
                type="tel"
                name="phone"
                value={settings.phone}
                onChange={handleChange}
              />
            </div>
          </div>

          <div>
            <label className="block text-[var(--color-text-primary)] mb-2">
              Adres
            </label>
            <Input
              name="address"
              value={settings.address}
              onChange={handleChange}
            />
          </div>

          <div>
            <label className="block text-[var(--color-text-primary)] mb-2">
              Hakkımda Metni
            </label>
            <textarea
              name="about"
              value={settings.about}
              onChange={handleChange}
              rows={4}
              className="w-full px-4 py-3 border border-[var(--color-border)] rounded-lg focus:outline-none focus:ring-2 focus:ring-[var(--color-accent)]"
            />
          </div>

          <div className="flex justify-end">
            <Button type="submit" variant="primary">
              <Save className="w-5 h-5" />
              Kaydet
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
