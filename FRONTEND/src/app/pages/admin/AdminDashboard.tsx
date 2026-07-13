import React, { useState, useEffect } from 'react';
import { Link } from 'react-router';
import { Briefcase, FileText, MessageSquare, TrendingUp, Users, Eye, FileUp, Loader2, Database, FileDigit, HelpCircle } from 'lucide-react';

interface RecentQuery {
  name: string;
  subject: string;
  answer: string;
  date: string;
  raw_date: string;
}

interface AdminStats {
  site_docs: number;
  law_docs: number;
  total_questions: number;
  recent_queries: RecentQuery[];
}

export function AdminDashboard() {
  const [statsData, setStatsData] = useState<AdminStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const res = await fetch('http://localhost:7860/admin/stats');
        if (!res.ok) throw new Error('Sunucu hatası');
        const data = await res.json();
        setStatsData(data);
      } catch (err: any) {
        setError(err.message || 'İstatistikler yüklenemedi.');
      } finally {
        setLoading(false);
      }
    };
    fetchStats();
  }, []);

  const stats = [
    { icon: FileUp, label: 'Yüklenen Site Belgesi (Parça)', value: statsData?.site_docs.toString() || '0', color: 'bg-blue-500' },
    { icon: Database, label: 'Hukuk Veritabanı (Madde)', value: statsData?.law_docs.toString() || '0', color: 'bg-green-500' },
    { icon: HelpCircle, label: 'Cevaplanan Toplam Soru', value: statsData?.total_questions.toString() || '0', color: 'bg-yellow-500' },
    { icon: MessageSquare, label: 'Aktif Son Oturumlar', value: statsData?.recent_queries.length.toString() || '0', color: 'bg-purple-500' },
  ];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-[var(--color-primary)] mb-2">Dashboard (Yapay Zeka Paneli)</h1>
        <p className="text-[var(--color-text-secondary)]">
          Asistanınızın performansını ve kullanıcı sorularını buradan anlık olarak takip edebilirsiniz.
        </p>
      </div>
      
      {loading ? (
        <div className="flex items-center justify-center p-12 bg-white rounded-xl border border-gray-200">
          <Loader2 className="w-8 h-8 animate-spin text-[var(--color-accent)]" />
          <span className="ml-3 text-[var(--color-primary)] font-medium">Veriler yükleniyor...</span>
        </div>
      ) : error ? (
        <div className="p-6 bg-red-50 text-red-700 rounded-xl border border-red-200">
          <p>{error} (FastAPI sunucusunun açık olduğundan emin olun)</p>
        </div>
      ) : (
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
      )}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <Link to="/admin/dashboard/documents" className="block">
          <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm hover:shadow-md transition-shadow">
            <FileUp className="w-8 h-8 text-[var(--color-accent)] mb-4" />
            <h3 className="text-[var(--color-primary)] mb-2">Site Belgeleri</h3>
            <p className="text-[var(--color-text-secondary)] caption">
              Yapay zekanın cevaplayabilmesi için PDF belgeleri yükleyin
            </p>
          </div>
        </Link>

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
        <div className="p-6 border-b border-gray-200 flex justify-between items-center">
          <h2 className="text-[var(--color-primary)]">Son Kullanıcı Soruları ve Cevaplar</h2>
          <span className="text-sm text-gray-500">Canlı Veri</span>
        </div>
        <div className="divide-y divide-gray-200">
          {statsData?.recent_queries && statsData.recent_queries.length > 0 ? (
            statsData.recent_queries.map((query, index) => (
              <div key={index} className="p-6 hover:bg-gray-50 transition-colors">
                <div className="flex items-start justify-between mb-2">
                  <div>
                    <h3 className="text-[var(--color-primary)] font-semibold mb-1 text-sm">{query.name}</h3>
                    <p className="text-gray-800 font-medium">{query.subject}</p>
                  </div>
                  <span className="text-sm text-gray-500 whitespace-nowrap ml-4">{query.date}</span>
                </div>
                <div className="mt-2 bg-gray-100 p-3 rounded-lg border border-gray-200">
                  <p className="text-[var(--color-text-secondary)] text-sm italic">
                    "{query.answer}"
                  </p>
                </div>
              </div>
            ))
          ) : (
            <div className="p-8 text-center text-gray-500">
              Henüz soru sorulmamış. Asistanı test etmek için ana sayfadan bir soru sorun.
            </div>
          )}
        </div>
        <div className="p-6 border-t border-gray-200">
          <Link 
            to="/admin/dashboard/documents"
            className="text-[var(--color-accent)] hover:underline"
          >
            Sisteme yeni belge yükle →
          </Link>
        </div>
      </div>
    </div>
  );
}

