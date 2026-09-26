import React, { useState, useEffect } from 'react';

import { Mail, MailOpen, Trash2, Reply, CheckCircle2, Search } from 'lucide-react';

export function AdminMessages() {
  const INITIAL_MESSAGES = [
    { 
      id: '1', 
      name: 'Ahmet Yılmaz', 
      email: 'ahmet@example.com',
      subject: 'Ticaret hukuku danışmanlığı talebi',
      message: 'Şirket kuruluşu ve esas sözleşme hazırlama konusunda danışmanlık almak istiyorum.',
      date: '2 saat önce',
      read: false
    },
    { 
      id: '2', 
      name: 'Zeynep Demir', 
      email: 'zeynep@example.com',
      subject: 'İş hukuku kıdem tazminatı sorusu',
      message: 'İş sözleşmem haklı sebep gösterilmeden feshedildi. Arabuluculuk sürecinde nelere dikkat etmeliyim?',
      date: '5 saat önce',
      read: false
    },
    { 
      id: '3', 
      name: 'Mehmet Kaya', 
      email: 'mehmet@example.com',
      subject: 'Ticari sözleşme inceleme talebi',
      message: 'Uluslararası distribütörlük sözleşmesini incelemenizi ve risk analizi yapmanızı istiyorum.',
      date: '1 gün önce',
      read: true
    },
  ];

  const [messages, setMessages] = useState(() => {
    try {
      const saved = localStorage.getItem('lawagent_contact_messages');
      return saved ? JSON.parse(saved) : INITIAL_MESSAGES;
    } catch (e) {
      return INITIAL_MESSAGES;
    }
  });

  useEffect(() => {
    const handleUpdate = () => {
      try {
        const saved = localStorage.getItem('lawagent_contact_messages');
        if (saved) setMessages(JSON.parse(saved));
      } catch (e) {}
    };

    window.addEventListener('storage', handleUpdate);
    window.addEventListener('lawagent_messages_updated', handleUpdate);
    return () => {
      window.removeEventListener('storage', handleUpdate);
      window.removeEventListener('lawagent_messages_updated', handleUpdate);
    };
  }, []);

  const saveMessages = (newMsgs: any[]) => {
    setMessages(newMsgs);
    try {
      localStorage.setItem('lawagent_contact_messages', JSON.stringify(newMsgs));
    } catch (e) {}
  };

  const toggleRead = (id: string) => {
    const updated = messages.map((m: any) => m.id === id ? { ...m, read: !m.read } : m);
    saveMessages(updated);
  };

  const handleDelete = (id: string) => {
    if (confirm('Bu mesajı silmek istediğinize emin misiniz?')) {
      const updated = messages.filter((m: any) => m.id !== id);
      saveMessages(updated);
    }
  };

  return (
    <div className="space-y-6">
      
      <div className="admin-card p-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="admin-heading text-2xl font-normal">Müşteri Mesajları & Talepler</h1>
          <p className="text-xs sm:text-sm mt-1" style={{ color: 'var(--color-muted)' }}>
            İletişim formundan gelen müşteri mesajlarını görüntüleyin, okundu işaretleyin ve yanıtlayın.
          </p>
        </div>
        <div className="admin-badge admin-badge-accent text-xs py-1.5 px-3">
          <span>Okunmamış: {messages.filter((m: any) => !m.read).length} Mesaj</span>
        </div>
      </div>

      <div className="admin-card overflow-hidden">
        <div className="divide-y" style={{ borderColor: 'var(--color-rule-2)' }}>
          {messages.map((msg: any) => (
            <div 
              key={msg.id} 
              className="p-6 transition-colors"
              style={{
                backgroundColor: !msg.read 
                  ? 'color-mix(in oklch, var(--color-accent) 4%, transparent)' 
                  : 'transparent',
              }}
            >
              <div className="flex items-start gap-4">
                <button 
                  onClick={() => toggleRead(msg.id)}
                  className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 transition-colors cursor-pointer border"
                  style={{
                    backgroundColor: msg.read 
                      ? 'var(--color-paper)' 
                      : 'color-mix(in oklch, var(--color-accent) 12%, transparent)',
                    color: msg.read ? 'var(--color-muted)' : 'var(--color-accent)',
                    borderColor: msg.read ? 'var(--color-rule)' : 'color-mix(in oklch, var(--color-accent) 30%, transparent)',
                  }}
                  title={msg.read ? "Okunmadı İşaretle" : "Okundu İşaretle"}
                >
                  {msg.read ? <MailOpen className="w-5 h-5" /> : <Mail className="w-5 h-5" />}
                </button>

                <div className="flex-1 min-w-0">
                  <div className="flex items-start justify-between gap-4 mb-1">
                    <div>
                      <span className="font-semibold text-sm" style={{ color: 'var(--color-ink)' }}>{msg.name}</span>
                      <span className="text-xs ml-2 font-mono" style={{ color: 'var(--color-muted)' }}>({msg.email})</span>
                    </div>
                    <span className="text-xs font-mono" style={{ color: 'var(--color-muted)' }}>{msg.date}</span>
                  </div>

                  <h4 className="font-semibold text-xs mb-2" style={{ color: 'var(--color-ink)' }}>{msg.subject}</h4>
                  <p className="text-xs leading-relaxed mb-4" style={{ color: 'var(--color-ink-2)' }}>{msg.message}</p>

                  <div className="flex items-center gap-3">
                    <a
                      href={`mailto:${msg.email}?subject=RE: ${encodeURIComponent(msg.subject)}`}
                      className="admin-btn-secondary text-xs py-1.5 px-3 no-underline"
                    >
                      <Reply className="w-3.5 h-3.5" />
                      <span>E-Posta İle Yanıtla</span>
                    </a>
                    <button 
                      onClick={() => handleDelete(msg.id)}
                      className="p-1.5 rounded-lg transition-colors cursor-pointer"
                      style={{ color: '#ef4444' }}
                      title="Mesajı Sil"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>

              </div>
            </div>
          ))}
        </div>
      </div>

    </div>
  );
}
