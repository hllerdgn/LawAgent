import React, { useState } from 'react';
import { Button } from '../../components/Button';
import { Plus, Edit, Trash2, Save, X } from 'lucide-react';

interface PracticeArea {
  id: string;
  title: string;
  description: string;
  slug: string;
}

export function AdminPracticeAreas() {
  const [areas, setAreas] = useState<PracticeArea[]>([
    { id: '1', title: 'Ticaret Hukuku', description: 'Şirket kuruluşu, birleşme...', slug: 'ticaret-hukuku' },
    { id: '2', title: 'İş Hukuku', description: 'İş sözleşmeleri, işçi-işveren...', slug: 'is-hukuku' },
  ]);
  const [isEditing, setIsEditing] = useState<string | null>(null);
  const [editForm, setEditForm] = useState({ title: '', description: '', slug: '' });

  const handleEdit = (area: PracticeArea) => {
    setIsEditing(area.id);
    setEditForm({ title: area.title, description: area.description, slug: area.slug });
  };

  const handleSave = (id: string) => {
    setAreas(areas.map(a => a.id === id ? { ...a, ...editForm } : a));
    setIsEditing(null);
  };

  const handleDelete = (id: string) => {
    if (confirm('Bu çalışma alanını silmek istediğinizden emin misiniz?')) {
      setAreas(areas.filter(a => a.id !== id));
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-[var(--color-primary)] mb-2">Çalışma Alanları</h1>
          <p className="text-[var(--color-text-secondary)]">
            Uzmanlık alanlarınızı ekleyin, düzenleyin veya kaldırın
          </p>
        </div>
        <Button variant="primary">
          <Plus className="w-5 h-5" />
          Yeni Alan Ekle
        </Button>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="px-6 py-4 text-left text-[var(--color-primary)]">Başlık</th>
              <th className="px-6 py-4 text-left text-[var(--color-primary)]">Açıklama</th>
              <th className="px-6 py-4 text-left text-[var(--color-primary)]">Slug</th>
              <th className="px-6 py-4 text-right text-[var(--color-primary)]">İşlemler</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {areas.map((area) => (
              <tr key={area.id} className="hover:bg-gray-50">
                {isEditing === area.id ? (
                  <>
                    <td className="px-6 py-4">
                      <input
                        type="text"
                        value={editForm.title}
                        onChange={(e) => setEditForm({ ...editForm, title: e.target.value })}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                      />
                    </td>
                    <td className="px-6 py-4">
                      <input
                        type="text"
                        value={editForm.description}
                        onChange={(e) => setEditForm({ ...editForm, description: e.target.value })}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                      />
                    </td>
                    <td className="px-6 py-4">
                      <input
                        type="text"
                        value={editForm.slug}
                        onChange={(e) => setEditForm({ ...editForm, slug: e.target.value })}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                      />
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => handleSave(area.id)}
                          className="p-2 text-green-600 hover:bg-green-50 rounded-lg"
                        >
                          <Save className="w-5 h-5" />
                        </button>
                        <button
                          onClick={() => setIsEditing(null)}
                          className="p-2 text-gray-600 hover:bg-gray-100 rounded-lg"
                        >
                          <X className="w-5 h-5" />
                        </button>
                      </div>
                    </td>
                  </>
                ) : (
                  <>
                    <td className="px-6 py-4 text-[var(--color-text-primary)]">{area.title}</td>
                    <td className="px-6 py-4 text-[var(--color-text-secondary)]">{area.description}</td>
                    <td className="px-6 py-4 text-[var(--color-text-secondary)] caption">{area.slug}</td>
                    <td className="px-6 py-4">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => handleEdit(area)}
                          className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg"
                        >
                          <Edit className="w-5 h-5" />
                        </button>
                        <button
                          onClick={() => handleDelete(area.id)}
                          className="p-2 text-red-600 hover:bg-red-50 rounded-lg"
                        >
                          <Trash2 className="w-5 h-5" />
                        </button>
                      </div>
                    </td>
                  </>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
