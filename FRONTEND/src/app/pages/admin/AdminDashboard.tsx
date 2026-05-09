import React from 'react';
import { Link } from 'react-router';
import { Briefcase, FileText, MessageSquare, TrendingUp, Users, Eye } from 'lucide-react';

export function AdminDashboard() {
  const stats = [
    { icon: Briefcase, label: 'Çalışma Alanları', value: '6', color: 'bg-blue-500' },
    { icon: FileText, label: 'Blog Yazıları', value: '12', color: 'bg-green-500' },
    { icon: MessageSquare, label: 'Yeni Mesajlar', value: '5', color: 'bg-yellow-500' },
    { icon: Eye, label: 'Toplam Görüntüleme', value: '1,234', color: 'bg-purple-500' },
  ];

  const recentMessages = [
    { name: 'Ahmet Yılmaz', subject: 'Ticaret hukuku danışmanlığı', date: '2 saat önce' },
    { name: 'Zeynep Demir', subject: 'İş hukuku konusunda bilgi', date: '5 saat önce' },
    { name: 'Mehmet Kaya', subject: 'Sözleşme incelemesi talebi', date: '1 gün önce' },
  ];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-[var(--color-primary)] mb-2">Dashboard</h1>
        <p className="text-[var(--color-text-secondary)]">
          İçerik yönetim sisteminize hoş geldiniz
        </p>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {stats.map((stat, index) => {
          const Icon = stat.icon;
          return (
            <div key={index} className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
              <div className="flex items-center justify-between mb-4">
                <div className={`w-12 h-12 ${stat.color} rounded-lg flex items-center justify-center`}>
                  <Icon className="w-6 h-6 text-white" />
                </div>
                <TrendingUp className="w-5 h-5 text-green-500" />
              </div>
              <h3 className="text-2xl text-[var(--color-primary)] mb-1">{stat.value}</h3>
              <p className="text-[var(--color-text-secondary)] caption">{stat.label}</p>
            </div>
          );
        })}
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Link to="/admin/dashboard/practice-areas" className="block">
          <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm hover:shadow-md transition-shadow">
            <Briefcase className="w-8 h-8 text-[var(--color-accent)] mb-4" />
            <h3 className="text-[var(--color-primary)] mb-2">Çalışma Alanları</h3>
            <p className="text-[var(--color-text-secondary)] caption">
              Uzmanlık alanlarınızı ekleyin ve yönetin
            </p>
          </div>
        </Link>

        <Link to="/admin/dashboard/blog" className="block">
          <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm hover:shadow-md transition-shadow">
            <FileText className="w-8 h-8 text-[var(--color-accent)] mb-4" />
            <h3 className="text-[var(--color-primary)] mb-2">Blog Yazıları</h3>
            <p className="text-[var(--color-text-secondary)] caption">
              Yeni blog yazısı ekleyin veya mevcut yazıları düzenleyin
            </p>
          </div>
        </Link>

        <Link to="/admin/dashboard/messages" className="block">
          <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm hover:shadow-md transition-shadow">
            <MessageSquare className="w-8 h-8 text-[var(--color-accent)] mb-4" />
            <h3 className="text-[var(--color-primary)] mb-2">Mesajlar</h3>
            <p className="text-[var(--color-text-secondary)] caption">
              Gelen mesajları görüntüleyin ve yanıtlayın
            </p>
          </div>
        </Link>
      </div>
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
        <div className="p-6 border-b border-gray-200">
          <h2 className="text-[var(--color-primary)]">Son Mesajlar</h2>
        </div>
        <div className="divide-y divide-gray-200">
          {recentMessages.map((message, index) => (
            <div key={index} className="p-6 hover:bg-gray-50 transition-colors">
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="text-[var(--color-primary)] mb-1">{message.name}</h3>
                  <p className="text-[var(--color-text-secondary)]">{message.subject}</p>
                </div>
                <span className="text-sm text-gray-500">{message.date}</span>
              </div>
            </div>
          ))}
        </div>
        <div className="p-6 border-t border-gray-200">
          <Link 
            to="/admin/dashboard/messages"
            className="text-[var(--color-accent)] hover:underline"
          >
            Tüm mesajları görüntüle →
          </Link>
        </div>
      </div>
    </div>
  );
}

