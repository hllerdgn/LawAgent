import React, { useState } from 'react';

interface FormData {
  name: string;
  email: string;
  phone: string;
  subject: string;
  message: string;
}

type FormErrors = Partial<Record<keyof FormData, string>>;

const CONTACT_INFO = [
  { label: "01 · E-POSTA", title: "e-posta adresi", value: "contact@lawagent.ai", href: "mailto:contact@lawagent.ai" },
  { label: "02 · KONUM", title: "adres", value: "istanbul, türkiye", href: null },
  { label: "03 · SÜRÜM", title: "proje sürümü", value: "v1.0.0 · fastapi + react 18 + vite", href: null },
];

export function ContactPage() {
  const [formData, setFormData] = useState<FormData>({
    name: '', email: '', phone: '', subject: '', message: ''
  });
  const [errors, setErrors] = useState<FormErrors>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitSuccess, setSubmitSuccess] = useState(false);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
    if (errors[name as keyof FormData]) {
      setErrors(prev => ({ ...prev, [name]: '' }));
    }
  };

  const validate = (): boolean => {
    const newErrors: FormErrors = {};
    if (!formData.name.trim()) newErrors.name = 'isim alanı boş bırakılamaz';
    if (!formData.email.trim()) {
      newErrors.email = 'e-posta alanı gereklidir';
    } else if (!/\S+@\S+\.\S+/.test(formData.email)) {
      newErrors.email = 'geçerli bir e-posta adresi girin';
    }
    if (!formData.subject.trim()) newErrors.subject = 'konu başlığı gereklidir';
    if (!formData.message.trim()) {
      newErrors.message = 'mesaj alanı gereklidir';
    } else if (formData.message.trim().length < 15) {
      newErrors.message = 'mesaj en az 15 karakter olmalıdır';
    }
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) return;
    setIsSubmitting(true);

    const newMessage = {
      id: Date.now().toString(),
      name: formData.name,
      email: formData.email,
      phone: formData.phone || '',
      subject: formData.subject,
      message: formData.message,
      date: 'Az önce',
      raw_date: new Date().toISOString(),
      read: false,
    };

    try {
      const existingStr = localStorage.getItem('lawagent_contact_messages');
      const existing = existingStr ? JSON.parse(existingStr) : [];
      localStorage.setItem('lawagent_contact_messages', JSON.stringify([newMessage, ...existing]));
      window.dispatchEvent(new Event('lawagent_messages_updated'));
    } catch (e) {
      console.warn('LocalStorage kayıt hatası:', e);
    }

    setTimeout(() => {
      setIsSubmitting(false);
      setSubmitSuccess(true);
      setFormData({ name: '', email: '', phone: '', subject: '', message: '' });
      setTimeout(() => setSubmitSuccess(false), 5000);
    }, 1200);
  };

  const inputStyle: React.CSSProperties = {
    width: '100%',
    padding: '12px 16px',
    fontFamily: 'var(--font-body)',
    fontSize: 'var(--text-sm)',
    color: 'var(--color-ink)',
    background: 'var(--color-paper)',
    border: '1px solid var(--color-rule)',
    borderRadius: 'var(--radius-md)',
    outline: 'none',
    textTransform: 'lowercase',
    transition: 'border-color 150ms ease',
    boxSizing: 'border-box',
  };

  const labelStyle: React.CSSProperties = {
    display: 'block',
    fontFamily: 'var(--font-label)',
    fontSize: '10px',
    letterSpacing: '0.10em',
    textTransform: 'uppercase',
    color: 'var(--color-muted)',
    marginBottom: 'var(--space-2)',
  };

  const errorStyle: React.CSSProperties = {
    fontFamily: 'var(--font-label)',
    fontSize: '10px',
    color: 'oklch(55% 0.22 25)',
    marginTop: 'var(--space-1)',
    display: 'block',
  };

  return (
    <>
      {/* Page hero */}
      <section
        style={{
          background: `
            linear-gradient(var(--rule-blueprint) 1px, transparent 1px) 0 0 / 48px 48px,
            linear-gradient(90deg, var(--rule-blueprint) 1px, transparent 1px) 0 0 / 48px 48px,
            var(--color-paper)
          `,
          paddingTop: "var(--space-12)",
          paddingBottom: "var(--space-10)",
          borderBottom: "1px solid var(--color-rule)",
        }}
        aria-labelledby="contact-title"
      >
        <div className="lumen-shell">
          <span className="eyebrow" style={{ display: "block", marginBottom: "var(--space-4)" }}>
            00 · iletişim ve geri bildirim
          </span>
          <h1
            id="contact-title"
            style={{
              fontFamily: "var(--font-display)",
              fontWeight: 400,
              fontSize: "var(--text-display)",
              lineHeight: "var(--leading-tight)",
              letterSpacing: "var(--tracking-display)",
              color: "var(--color-ink)",
              maxWidth: "16ch",
              overflowWrap: "anywhere",
            }}
          >
            bizimle <em style={{ fontStyle: "normal", color: "var(--color-accent-2)" }}>iletişime</em>{" "}
            geçin.
          </h1>
          <p style={{
            marginTop: "var(--space-6)",
            fontSize: "var(--text-lg)",
            color: "var(--color-ink-2)",
            lineHeight: "var(--leading-normal)",
            maxWidth: "48ch",
          }}>
            lawagent sistemi hakkındaki soru, öneri veya geri bildirimlerinizi
            ekibimize iletebilirsiniz.
          </p>
        </div>
      </section>

      {/* Main grid */}
      <section className="lumen-section" aria-labelledby="form-title">
        <div className="lumen-shell">
          <div style={{
            display: "grid",
            gridTemplateColumns: "1fr 1.5fr",
            gap: "var(--space-10)",
            alignItems: "start",
          }}>

            {/* Left: contact info cards */}
            <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-4)" }}>
              <header style={{ marginBottom: "var(--space-2)" }}>
                <span className="eyebrow" style={{ display: "block", marginBottom: "var(--space-3)" }}>
                  01 · iletişim bilgileri
                </span>
                <h2 style={{
                  fontFamily: "var(--font-display)",
                  fontWeight: 400,
                  fontSize: "var(--text-3xl)",
                  lineHeight: "var(--leading-tight)",
                  letterSpacing: "var(--tracking-display)",
                  color: "var(--color-ink)",
                }}>
                  lawagent geliştirici ekibi.
                </h2>
                <p style={{
                  marginTop: "var(--space-3)",
                  fontSize: "var(--text-sm)",
                  color: "var(--color-ink-2)",
                  lineHeight: "var(--leading-normal)",
                }}>
                  lawagent ai geliştirici ekibine aşağıdaki kanallardan ulaşabilirsiniz.
                </p>
              </header>

              {CONTACT_INFO.map((info) => (
                <div key={info.label} className="lumen-card" style={{ padding: "var(--space-5)" }}>
                  <span className="lumen-card__eyebrow">{info.label}</span>
                  <h3 className="lumen-card__title" style={{ fontSize: "var(--text-xl)" }}>{info.title}</h3>
                  {info.href ? (
                    <a href={info.href} style={{
                      fontFamily: "var(--font-mono)",
                      fontSize: "11px",
                      letterSpacing: "0.06em",
                      color: "var(--color-accent)",
                      textDecoration: "none",
                      textTransform: "lowercase",
                    }}>{info.value}</a>
                  ) : (
                    <p style={{
                      fontFamily: "var(--font-mono)",
                      fontSize: "11px",
                      letterSpacing: "0.06em",
                      color: "var(--color-muted)",
                      textTransform: "lowercase",
                    }}>{info.value}</p>
                  )}
                </div>
              ))}

              {/* AI shortcut */}
              <button
                className="lumen-btn lumen-btn--primary"
                onClick={() => window.dispatchEvent(new CustomEvent("toggle-chatbot"))}
                style={{ width: "100%", justifyContent: "center" }}
              >
                ai asistana soru sor →
              </button>
            </div>

            {/* Right: contact form */}
            <div
              style={{
                background: "var(--color-paper-2)",
                border: "1px solid var(--color-rule)",
                borderRadius: "var(--radius-lg)",
                padding: "var(--space-8)",
              }}
            >
              <span className="eyebrow" style={{ display: "block", marginBottom: "var(--space-4)" }}>
                02 · mesaj gönderin
              </span>
              <h2 id="form-title" style={{
                fontFamily: "var(--font-display)",
                fontWeight: 400,
                fontSize: "var(--text-3xl)",
                lineHeight: "var(--leading-tight)",
                letterSpacing: "var(--tracking-display)",
                color: "var(--color-ink)",
                marginBottom: "var(--space-7)",
              }}>
                mesajınızı yazın.
              </h2>

              {submitSuccess && (
                <div style={{
                  background: "oklch(90% 0.08 145 / 0.3)",
                  border: "1px solid oklch(65% 0.15 145 / 0.4)",
                  color: "oklch(35% 0.12 145)",
                  padding: "var(--space-4)",
                  borderRadius: "var(--radius-md)",
                  marginBottom: "var(--space-6)",
                  fontFamily: "var(--font-body)",
                  fontSize: "var(--text-sm)",
                }}>
                  ✓ mesajınız başarıyla iletildi. katkınız için teşekkür ederiz.
                </div>
              )}

              <form onSubmit={handleSubmit} noValidate style={{ display: "flex", flexDirection: "column", gap: "var(--space-5)" }}>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "var(--space-5)" }}>
                  <div>
                    <label htmlFor="name" style={labelStyle}>Ad Soyad *</label>
                    <input
                      id="name" name="name" type="text"
                      value={formData.name} onChange={handleChange}
                      placeholder="adınız soyadınız"
                      style={{ ...inputStyle, borderColor: errors.name ? "oklch(55% 0.22 25)" : undefined }}
                      aria-describedby={errors.name ? "name-error" : undefined}
                    />
                    {errors.name && <span id="name-error" style={errorStyle}>{errors.name}</span>}
                  </div>
                  <div>
                    <label htmlFor="email" style={labelStyle}>E-Posta *</label>
                    <input
                      id="email" name="email" type="email"
                      value={formData.email} onChange={handleChange}
                      placeholder="ornek@lawagent.ai"
                      style={{ ...inputStyle, borderColor: errors.email ? "oklch(55% 0.22 25)" : undefined }}
                      aria-describedby={errors.email ? "email-error" : undefined}
                    />
                    {errors.email && <span id="email-error" style={errorStyle}>{errors.email}</span>}
                  </div>
                </div>

                <div>
                  <label htmlFor="subject" style={labelStyle}>Konu *</label>
                  <input
                    id="subject" name="subject" type="text"
                    value={formData.subject} onChange={handleChange}
                    placeholder="hangi konuda mesaj gönderiyorsunuz?"
                    style={{ ...inputStyle, borderColor: errors.subject ? "oklch(55% 0.22 25)" : undefined }}
                    aria-describedby={errors.subject ? "subject-error" : undefined}
                  />
                  {errors.subject && <span id="subject-error" style={errorStyle}>{errors.subject}</span>}
                </div>

                <div>
                  <label htmlFor="message" style={labelStyle}>Mesaj Detayı *</label>
                  <textarea
                    id="message" name="message"
                    value={formData.message} onChange={handleChange}
                    placeholder="lütfen detaylı bilgi veya görüşlerinizi yazın..."
                    rows={5}
                    style={{
                      ...inputStyle,
                      resize: "vertical",
                      minHeight: "120px",
                      borderColor: errors.message ? "oklch(55% 0.22 25)" : undefined,
                    }}
                    aria-describedby={errors.message ? "message-error" : undefined}
                  />
                  {errors.message && <span id="message-error" style={errorStyle}>{errors.message}</span>}
                </div>

                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="lumen-btn lumen-btn--primary"
                  style={{ justifyContent: "center", opacity: isSubmitting ? 0.6 : 1 }}
                >
                  {isSubmitting ? "gönderiliyor..." : "mesajı gönder →"}
                </button>
              </form>
            </div>

          </div>
        </div>
      </section>
    </>
  );
}
