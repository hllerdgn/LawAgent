import React, { useState } from 'react';
import { Button } from '../components/Button';
import { Input } from '../components/Input';
import { Code2, Phone, Mail, Clock, Send, Terminal } from 'lucide-react';

export function ContactPage() {
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    phone: '',
    subject: '',
    message: ''
  });

  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitSuccess, setSubmitSuccess] = useState(false);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
    // Clear error when user starts typing
    if (errors[name]) {
      setErrors(prev => ({ ...prev, [name]: '' }));
    }
  };

  const validate = () => {
    const newErrors: Record<string, string> = {};
    
    if (!formData.name.trim()) newErrors.name = 'İsim gereklidir';
    if (!formData.email.trim()) {
      newErrors.email = 'E-posta gereklidir';
    } else if (!/\\S+@\\S+\\.\\S+/.test(formData.email)) {
      newErrors.email = 'Geçerli bir e-posta adresi girin';
    }
    if (!formData.subject.trim()) newErrors.subject = 'Konu gereklidir';
    if (!formData.message.trim()) {
      newErrors.message = 'Mesaj gereklidir';
    } else if (formData.message.trim().length < 20) {
      newErrors.message = 'Mesaj en az 20 karakter olmalıdır';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validate()) return;

    setIsSubmitting(true);
    
    // Simulate API call
    setTimeout(() => {
      setIsSubmitting(false);
      setSubmitSuccess(true);
      setFormData({ name: '', email: '', phone: '', subject: '', message: '' });
      
      setTimeout(() => setSubmitSuccess(false), 5000);
    }, 1500);
  };

  return (
    <div className="w-full">
      <section className="bg-gradient-to-br from-[var(--color-primary)] to-[var(--color-primary-dark)] text-white">
        <div className="max-w-[1440px] mx-auto px-6 lg:px-24 py-12 lg:py-20">
          <div className="text-center max-w-3xl mx-auto">
            <h1 className="text-white mb-6">İletişim & Geri Bildirim</h1>
            <p className="text-gray-200 text-lg">
              LawAgent AI asistanı ile ilgili hata bildirimleri, sistem önerileri veya projeye katkı sağlamak için geliştirici ekibimizle iletişime geçin.
            </p>
          </div>
        </div>
      </section>
      <section className="bg-white">
        <div className="max-w-[1440px] mx-auto px-6 lg:px-24 py-12 lg:py-20">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12">
            <div className="flex flex-col gap-8">
              <div>
                <h2 className="text-[var(--color-primary)] mb-6">Geliştirici Ekibi</h2>
                <p className="text-[var(--color-text-secondary)] leading-relaxed mb-8">
                  LawAgent AI projesi geliştirme aşamasındadır. Sistemi denerken karşılaştığınız mantıksal hataları (halüsinasyonlar) veya yeni özellik fikirlerini bizimle paylaşabilirsiniz.
                </p>
              </div>

              <div className="flex flex-col gap-6">
                <div className="flex items-start gap-4 p-4 bg-[var(--color-background)] rounded-xl">
                  <div className="w-12 h-12 bg-[var(--color-primary)] rounded-lg flex items-center justify-center flex-shrink-0">
                    <Code2 className="w-6 h-6 text-[var(--color-accent)]" />
                  </div>
                  <div>
                    <h3 className="text-[var(--color-primary)] mb-1">Github / Repo</h3>
                    <p className="text-[var(--color-text-secondary)]">
                      Yakında açık kaynaklı repolarımız burada duyurulacaktır.
                    </p>
                  </div>
                </div>

                <div className="flex items-start gap-4 p-4 bg-[var(--color-background)] rounded-xl">
                  <div className="w-12 h-12 bg-[var(--color-primary)] rounded-lg flex items-center justify-center flex-shrink-0">
                    <Mail className="w-6 h-6 text-[var(--color-accent)]" />
                  </div>
                  <div>
                    <h3 className="text-[var(--color-primary)] mb-1">E-posta (Destek)</h3>
                    <p className="text-[var(--color-text-secondary)]">iletisim@lawagent.ai</p>
                  </div>
                </div>

                <div className="flex items-start gap-4 p-4 bg-[var(--color-background)] rounded-xl">
                  <div className="w-12 h-12 bg-[var(--color-primary)] rounded-lg flex items-center justify-center flex-shrink-0">
                    <Terminal className="w-6 h-6 text-[var(--color-accent)]" />
                  </div>
                  <div>
                    <h3 className="text-[var(--color-primary)] mb-1">Proje Durumu</h3>
                    <p className="text-[var(--color-text-secondary)]">
                      Beta v1.0 <br />
                      Sistem aktif olarak eğitilmeye devam etmektedir.
                    </p>
                  </div>
                </div>
              </div>
            </div>
            <div className="bg-[var(--color-background)] p-6 lg:p-8 rounded-2xl border border-[var(--color-border)]">
              <h2 className="text-[var(--color-primary)] mb-6">Geri Bildirim Formu</h2>
              
              {submitSuccess && (
                <div className="bg-green-50 border border-green-200 text-green-800 px-4 py-3 rounded-lg mb-6">
                  <p className="">Mesajınız başarıyla gönderildi. Katkınız için teşekkür ederiz.</p>
                </div>
              )}

              <form onSubmit={handleSubmit} className="flex flex-col gap-6">
                <div>
                  <label htmlFor="name" className="block text-[var(--color-text-primary)] mb-2">
                    İsim Soyisim *
                  </label>
                  <Input
                    id="name"
                    name="name"
                    value={formData.name}
                    onChange={handleChange}
                    placeholder="Adınız ve soyadınız"
                    className={errors.name ? 'border-red-500' : ''}
                  />
                  {errors.name && (
                    <p className="text-red-500 text-sm mt-1">{errors.name}</p>
                  )}
                </div>

                <div>
                  <label htmlFor="email" className="block text-[var(--color-text-primary)] mb-2">
                    E-posta *
                  </label>
                  <Input
                    id="email"
                    name="email"
                    type="email"
                    value={formData.email}
                    onChange={handleChange}
                    placeholder="ornek@email.com"
                    className={errors.email ? 'border-red-500' : ''}
                  />
                  {errors.email && (
                    <p className="text-red-500 text-sm mt-1">{errors.email}</p>
                  )}
                </div>

                <div>
                  <label htmlFor="subject" className="block text-[var(--color-text-primary)] mb-2">
                    Konu *
                  </label>
                  <Input
                    id="subject"
                    name="subject"
                    value={formData.subject}
                    onChange={handleChange}
                    placeholder="Hata bildirimi, öneri vb."
                    className={errors.subject ? 'border-red-500' : ''}
                  />
                  {errors.subject && (
                    <p className="text-red-500 text-sm mt-1">{errors.subject}</p>
                  )}
                </div>

                <div>
                  <label htmlFor="message" className="block text-[var(--color-text-primary)] mb-2">
                    Mesaj / Hata Detayı *
                  </label>
                  <textarea
                    id="message"
                    name="message"
                    value={formData.message}
                    onChange={handleChange}
                    placeholder="Lütfen asistanın verdiği yanlış yanıtı veya önerinizi detaylıca yazın..."
                    rows={6}
                    className={`w-full px-4 py-3 border rounded-lg focus:outline-none focus:ring-2 focus:ring-[var(--color-accent)] ${
                      errors.message ? 'border-red-500' : 'border-[var(--color-border)]'
                    }`}
                  />
                  {errors.message && (
                    <p className="text-red-500 text-sm mt-1">{errors.message}</p>
                  )}
                </div>

                <Button 
                  type="submit" 
                  variant="primary" 
                  disabled={isSubmitting}
                  className="w-full"
                >
                  {isSubmitting ? (
                    'Gönderiliyor...'
                  ) : (
                    <>
                      <Send className="w-5 h-5" />
                      Gönder
                    </>
                  )}
                </Button>
              </form>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
