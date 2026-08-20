import React, { useState } from 'react';
import { Plus, Edit, Trash2, Save, X, Briefcase } from 'lucide-react';

interface PracticeArea {
  id: string;
  title: string;
  description: string;
  slug: string;
}

export function AdminPracticeAreas() {
  const DEFAULT_AREAS: PracticeArea[] = [
    { id: '1', title: 'Ticaret Hukuku (TTK)', description: 'Şirket kuruluşu, birleşme/devralma ve ticari uyuşmazlıklar.', slug: 'ticaret-hukuku' },
    { id: '2', title: 'İş Hukuku (TBK)', description: 'İş sözleşmeleri, işçi-işveren hakları ve arabuluculuk.', slug: 'is-hukuku' },
    { id: '3', title: 'Tüketici Hukuku (TKHK)', description: 'Ayıplı mal iadesi, mesafeli satış ve Hakem Heyetleri.', slug: 'tuketici-hukuku' },
  ];

  const [areas, setAreas] = useState<PracticeArea[]>(() => {
    try {
      const saved = localStorage.getItem('lawagent_practice_areas');
      return saved ? JSON.parse(saved) : DEFAULT_AREAS;
    } catch (e) {
      return DEFAULT_AREAS;
    }
  });

  const [isEditing, setIsEditing] = useState<string | null>(null);
  const [editForm, setEditForm] = useState({ title: '', description: '', slug: '' });

  const saveAreas = (newAreas: PracticeArea[]) => {
    setAreas(newAreas);
    try {
      localStorage.setItem('lawagent_practice_areas', JSON.stringify(newAreas));
      window.dispatchEvent(new Event('lawagent_practice_areas_updated'));
    } catch (e) {}
  };

  const handleEdit = (area: PracticeArea) => {
    setIsEditing(area.id);
    setEditForm({ title: area.title, description: area.description, slug: area.slug });
  };

  const handleSave = (id: string) => {
    const updated = areas.map(a => a.id === id ? { ...a, ...editForm } : a);
    saveAreas(updated);
    setIsEditing(null);
  };

  const handleDelete = (id: string) => {
    if (confirm('Bu çalışma alanını silmek istediğinizden emin misiniz?')) {
      const updated = areas.filter(a => a.id !== id);
      saveAreas(updated);
    }
  };

  const handleAdd = () => {
    const newId = Date.now().toString();
    const newArea: PracticeArea = {
      id: newId,
      title: 'Yeni Çalışma Alanı',
      description: 'Açıklama giriniz...',
      slug: `yeni-alan-${newId}`
    };
    const updated = [...areas, newArea];
    saveAreas(updated);
    handleEdit(newArea);
  };

  return (
    <div className="space-y-6 font-sans antialiased">
      
      <div className="bg-white p-6 rounded-2xl border border-slate-200/80 shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-slate-900 text-2xl font-bold font-serif">Çalışma Alanları Yönetimi</h1>
          <p className="text-slate-500 text-xs sm:text-sm mt-1">
            Sitede gösterilen ve AI tarafından desteklenen uzmanlık disiplinlerini yönetin.
          </p>
        </div>
        <button
          onClick={handleAdd}
          className="bg-slate-900 hover:bg-slate-800 text-white px-5 py-2.5 rounded-xl font-medium text-xs flex items-center justify-center gap-2 cursor-pointer transition-colors border border-slate-800"
        >
          <Plus className="w-4 h-4 text-amber-400" />
          <span>Yeni Alan Ekle</span>
        </button>
      </div>

      <div className="bg-white rounded-2xl border border-slate-200/80 shadow-xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead className="bg-slate-50 border-b border-slate-200 text-slate-700 text-xs font-semibold uppercase tracking-wider">
              <tr>
                <th className="px-6 py-4">Çalışma Alanı</th>
                <th className="px-6 py-4">Açıklama</th>
                <th className="px-6 py-4">Slug (URL)</th>
                <th className="px-6 py-4 text-right">İşlemler</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-xs text-slate-800">
              {areas.map((area) => (
                <tr key={area.id} className="hover:bg-slate-50/80 transition-colors">
                  {isEditing === area.id ? (
                    <>
                      <td className="px-6 py-4">
                        <input
                          type="text"
                          value={editForm.title}
                          onChange={(e) => setEditForm({ ...editForm, title: e.target.value })}
                          className="w-full px-3 py-1.5 border border-amber-500 rounded-lg text-xs bg-white focus:outline-none"
                        />
                      </td>
                      <td className="px-6 py-4">
                        <input
                          type="text"
                          value={editForm.description}
                          onChange={(e) => setEditForm({ ...editForm, description: e.target.value })}
                          className="w-full px-3 py-1.5 border border-amber-500 rounded-lg text-xs bg-white focus:outline-none"
                        />
                      </td>
                      <td className="px-6 py-4">
                        <input
                          type="text"
                          value={editForm.slug}
                          onChange={(e) => setEditForm({ ...editForm, slug: e.target.value })}
                          className="w-full px-3 py-1.5 border border-amber-500 rounded-lg text-xs bg-white focus:outline-none"
                        />
                      </td>
                      <td className="px-6 py-4 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <button
                            onClick={() => handleSave(area.id)}
                            className="p-1.5 bg-emerald-500 text-white rounded-lg hover:bg-emerald-600 transition-colors"
                            title="Kaydet"
                          >
                            <Save className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => setIsEditing(null)}
                            className="p-1.5 bg-slate-200 text-slate-700 rounded-lg hover:bg-slate-300 transition-colors"
                            title="İptal"
                          >
                            <X className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </>
                  ) : (
                    <>
                      <td className="px-6 py-4 font-bold text-slate-900">{area.title}</td>
                      <td className="px-6 py-4 text-slate-600 max-w-xs truncate">{area.description}</td>
                      <td className="px-6 py-4 font-mono text-slate-500">{area.slug}</td>
                      <td className="px-6 py-4 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <button
                            onClick={() => handleEdit(area)}
                            className="p-1.5 text-slate-600 hover:text-amber-600 hover:bg-slate-100 rounded-lg transition-colors cursor-pointer"
                            title="Düzenle"
                          >
                            <Edit className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => handleDelete(area.id)}
                            className="p-1.5 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors cursor-pointer"
                            title="Sil"
                          >
                            <Trash2 className="w-4 h-4" />
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
    </div>
  );
}
