import React, { useState } from 'react';
import { Button } from '../../components/Button';
import { Plus, Edit, Trash2, Eye } from 'lucide-react';

export function AdminBlog() {
  const [posts] = useState([
    { id: '1', title: 'Ticaret Hukukunda Sık Karşılaşılan Sorunlar', status: 'Yayında', date: '15 Ocak 2025' },
    { id: '2', title: 'İş Sözleşmesi Feshi: Haklarınızı Bilin', status: 'Taslak', date: '10 Ocak 2025' },
    { id: '3', title: 'Tüketici Haklarında Yeni Düzenlemeler', status: 'Yayında', date: '5 Ocak 2025' },
  ]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-[var(--color-primary)] mb-2">Blog Yazıları</h1>
          <p className="text-[var(--color-text-secondary)]">
            Blog yazılarınızı oluşturun ve yönetin
          </p>
        </div>
        <Button variant="primary">
          <Plus className="w-5 h-5" />
          Yeni Yazı Ekle
        </Button>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="px-6 py-4 text-left text-[var(--color-primary)]">Başlık</th>
              <th className="px-6 py-4 text-left text-[var(--color-primary)]">Durum</th>
              <th className="px-6 py-4 text-left text-[var(--color-primary)]">Tarih</th>
              <th className="px-6 py-4 text-right text-[var(--color-primary)]">İşlemler</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {posts.map((post) => (
              <tr key={post.id} className="hover:bg-gray-50">
                <td className="px-6 py-4 text-[var(--color-text-primary)]">{post.title}</td>
                <td className="px-6 py-4">
                  <span className={`px-3 py-1 rounded-full text-sm ${
                    post.status === 'Yayında' 
                      ? 'bg-green-100 text-green-800' 
                      : 'bg-yellow-100 text-yellow-800'
                  }`}>
                    {post.status}
                  </span>
                </td>
                <td className="px-6 py-4 text-[var(--color-text-secondary)]">{post.date}</td>
                <td className="px-6 py-4">
                  <div className="flex items-center justify-end gap-2">
                    <button className="p-2 text-green-600 hover:bg-green-50 rounded-lg">
                      <Eye className="w-5 h-5" />
                    </button>
                    <button className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg">
                      <Edit className="w-5 h-5" />
                    </button>
                    <button className="p-2 text-red-600 hover:bg-red-50 rounded-lg">
                      <Trash2 className="w-5 h-5" />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
