import React, { useState } from 'react';
import { Mail, MailOpen, Trash2, Reply } from 'lucide-react';

export function AdminMessages() {
  const [messages] = useState([
    { 
      id: '1', 
      name: 'Ahmet Yılmaz', 
      email: 'ahmet@example.com',
      subject: 'Ticaret hukuku danışmanlığı',
      message: 'Şirket kuruluşu konusunda danışmanlık almak istiyorum.',
      date: '2 saat önce',
      read: false
    },
    { 
      id: '2', 
      name: 'Zeynep Demir', 
      email: 'zeynep@example.com',
      subject: 'İş hukuku konusunda bilgi',
      message: 'İş sözleşmem feshedildi. Haklarım nelerdir?',
      date: '5 saat önce',
      read: false
    },
    { 
      id: '3', 
      name: 'Mehmet Kaya', 
      email: 'mehmet@example.com',
      subject: 'Sözleşme incelemesi talebi',
      message: 'Bir ticari sözleşmeyi incelemenizi istiyorum.',
      date: '1 gün önce',
      read: true
    },
  ]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-[var(--color-primary)] mb-2">Mesajlar</h1>
        <p className="text-[var(--color-text-secondary)]">
          İletişim formundan gelen mesajları görüntüleyin ve yönetin
        </p>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        <div className="divide-y divide-gray-200">
          {messages.map((msg) => (
            <div 
              key={msg.id} 
              className={`p-6 hover:bg-gray-50 transition-colors ${!msg.read ? 'bg-blue-50/30' : ''}`}
            >
              <div className="flex items-start gap-4">
                <div className="w-10 h-10 bg-[var(--color-primary)] rounded-full flex items-center justify-center flex-shrink-0">
                  {msg.read ? (
                    <MailOpen className="w-5 h-5 text-white" />
                  ) : (
                    <Mail className="w-5 h-5 text-white" />
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-start justify-between mb-2">
                    <div>
                      <h3 className="text-[var(--color-primary)] mb-1">{msg.name}</h3>
                      <p className="text-sm text-[var(--color-text-secondary)]">{msg.email}</p>
                    </div>
                    <span className="text-sm text-gray-500">{msg.date}</span>
                  </div>
                  <h4 className="text-[var(--color-text-primary)] mb-2">{msg.subject}</h4>
                  <p className="text-[var(--color-text-secondary)] mb-4">{msg.message}</p>
                  <div className="flex items-center gap-2">
                    <button className="flex items-center gap-2 px-4 py-2 bg-[var(--color-primary)] text-white rounded-lg hover:bg-[var(--color-primary-dark)] transition-colors">
                      <Reply className="w-4 h-4" />
                      Yanıtla
                    </button>
                    <button className="p-2 text-red-600 hover:bg-red-50 rounded-lg">
                      <Trash2 className="w-5 h-5" />
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
