import React, { useState } from 'react';
import { Plus, Edit, Trash2, Eye, FileText, CheckCircle2, Clock } from 'lucide-react';

export function AdminBlog() {
  const [posts, setPosts] = useState([
    { id: '1', title: 'Ticaret Hukukunda Sık Karşılaşılan Sorunlar', status: 'Yayında', date: '15 Ocak 2025', views: '240 Okunma' },
    { id: '2', title: 'İş Sözleşmesi Feshi: Haklarınızı Bilin', status: 'Taslak', date: '10 Ocak 2025', views: '180 Okunma' },
    { id: '3', title: 'Tüketici Haklarında Yeni Düzenlemeler', status: 'Yayında', date: '5 Ocak 2025', views: '310 Okunma' },
  ]);

  const handleDelete = (id: string) => {
    if (confirm('Bu blog yazısını silmek istediğinize emin misiniz?')) {
      setPosts(posts.filter(p => p.id !== id));
    }
  };

  const handleAdd = () => {
    const newId = Date.now().toString();
    const newPost = {
      id: newId,
      title: 'Yeni Hukuki İnceleme Makalesi',
      status: 'Taslak',
      date: 'Bugün',
      views: '0 Okunma'
    };
    setPosts([newPost, ...posts]);
  };

  return (
    <div className="space-y-6 font-sans antialiased">
      
      <div className="bg-white p-6 rounded-2xl border border-slate-200/80 shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-slate-900 text-2xl font-bold font-serif">Blog & İçerik Yönetimi</h1>
          <p className="text-slate-500 text-xs sm:text-sm mt-1">
            Hukuki makalelerinizi düzenleyin, yenilerini ekleyin veya taslakları yayımlayın.
          </p>
        </div>
        <button
          onClick={handleAdd}
          className="bg-slate-900 hover:bg-slate-800 text-white px-5 py-2.5 rounded-xl font-medium text-xs flex items-center justify-center gap-2 cursor-pointer transition-colors border border-slate-800"
        >
          <Plus className="w-4 h-4 text-amber-400" />
          <span>Yeni Makale Yaz</span>
        </button>
      </div>

      <div className="bg-white rounded-2xl border border-slate-200/80 shadow-xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead className="bg-slate-50 border-b border-slate-200 text-slate-700 text-xs font-semibold uppercase tracking-wider">
              <tr>
                <th className="px-6 py-4">Makale Başlığı</th>
                <th className="px-6 py-4">Yayın Durumu</th>
                <th className="px-6 py-4">Yayın Tarihi</th>
                <th className="px-6 py-4 text-right">İşlemler</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-xs text-slate-800">
              {posts.map((post) => (
                <tr key={post.id} className="hover:bg-slate-50/80 transition-colors">
                  <td className="px-6 py-4 font-bold text-slate-900">{post.title}</td>
                  <td className="px-6 py-4">
                    <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-semibold ${
                      post.status === 'Yayında' 
                        ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' 
                        : 'bg-amber-50 text-amber-700 border border-amber-200'
                    }`}>
                      <span className={`w-1.5 h-1.5 rounded-full ${post.status === 'Yayında' ? 'bg-emerald-500' : 'bg-amber-500'}`} />
                      {post.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-slate-500">{post.date}</td>
                  <td className="px-6 py-4 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <button className="p-1.5 text-slate-600 hover:text-emerald-600 hover:bg-emerald-50 rounded-lg transition-colors cursor-pointer" title="Önizle">
                        <Eye className="w-4 h-4" />
                      </button>
                      <button className="p-1.5 text-slate-600 hover:text-amber-600 hover:bg-slate-100 rounded-lg transition-colors cursor-pointer" title="Düzenle">
                        <Edit className="w-4 h-4" />
                      </button>
                      <button 
                        onClick={() => handleDelete(post.id)}
                        className="p-1.5 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors cursor-pointer" 
                        title="Sil"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

    </div>
  );
}
