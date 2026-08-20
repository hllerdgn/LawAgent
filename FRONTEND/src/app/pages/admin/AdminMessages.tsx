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
    <div className="space-y-6 font-sans antialiased">
      
      <div className="bg-white p-6 rounded-2xl border border-slate-200/80 shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-slate-900 text-2xl font-bold font-serif">Müşteri Mesajları & Talepler</h1>
          <p className="text-slate-500 text-xs sm:text-sm mt-1">
            İletişim formundan gelen müşteri mesajlarını görüntüleyin, okundu işaretleyin ve yanıtlayın.
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs font-semibold text-slate-600 bg-slate-100 px-3.5 py-2 rounded-xl border border-slate-200">
          <span>Okunmamış: {messages.filter(m => !m.read).length} Mesaj</span>
        </div>
      </div>

      <div className="bg-white rounded-2xl border border-slate-200/80 shadow-xs overflow-hidden">
        <div className="divide-y divide-slate-100">
          {messages.map((msg) => (
            <div 
              key={msg.id} 
              className={`p-6 hover:bg-slate-50/80 transition-colors ${!msg.read ? 'bg-amber-500/5' : ''}`}
            >
              <div className="flex items-start gap-4">
                <button 
                  onClick={() => toggleRead(msg.id)}
                  className={`w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 transition-colors cursor-pointer ${
                    msg.read ? 'bg-slate-100 text-slate-400' : 'bg-amber-500/10 text-amber-600 border border-amber-500/30'
                  }`}
                  title={msg.read ? "Okunmadı İşaretle" : "Okundu İşaretle"}
                >
                  {msg.read ? <MailOpen className="w-5 h-5" /> : <Mail className="w-5 h-5" />}
                </button>

                <div className="flex-1 min-w-0">
                  <div className="flex items-start justify-between gap-4 mb-1">
                    <div>
                      <span className="text-slate-900 font-bold text-sm">{msg.name}</span>
                      <span className="text-slate-400 text-xs ml-2">({msg.email})</span>
                    </div>
                    <span className="text-xs text-slate-400 font-medium">{msg.date}</span>
                  </div>

                  <h4 className="text-slate-800 font-semibold text-xs mb-2 font-sans">{msg.subject}</h4>
                  <p className="text-slate-600 text-xs leading-relaxed mb-4">{msg.message}</p>

                  <div className="flex items-center gap-3">
                    <a
                      href={`mailto:${msg.email}?subject=RE: ${encodeURIComponent(msg.subject)}`}
                      className="inline-flex items-center gap-2 px-3.5 py-1.5 bg-slate-900 hover:bg-slate-800 text-white rounded-xl text-xs font-medium transition-colors border border-slate-800"
                    >
                      <Reply className="w-3.5 h-3.5 text-amber-400" />
                      <span>E-Posta İle Yanıtla</span>
                    </a>
                    <button 
                      onClick={() => handleDelete(msg.id)}
                      className="p-1.5 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors cursor-pointer"
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
