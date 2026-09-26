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
    <div className="space-y-6">
      
      <div className="admin-card p-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="admin-heading text-2xl font-normal">Çalışma Alanları Yönetimi</h1>
          <p className="text-xs sm:text-sm mt-1" style={{ color: 'var(--color-muted)' }}>
            Sitede gösterilen ve AI tarafından desteklenen uzmanlık disiplinlerini yönetin.
          </p>
        </div>
        <button
          onClick={handleAdd}
          className="admin-btn-primary text-xs py-2.5 px-4 cursor-pointer"
        >
          <Plus className="w-4 h-4" />
          <span>Yeni Alan Ekle</span>
        </button>
      </div>

      <div className="admin-table-wrapper">
        <div className="overflow-x-auto">
          <table className="admin-table">
            <thead>
              <tr>
                <th>Çalışma Alanı</th>
                <th>Açıklama</th>
                <th>Slug (URL)</th>
                <th style={{ textAlign: 'right' }}>İşlemler</th>
              </tr>
            </thead>
            <tbody>
              {areas.map((area) => (
                <tr key={area.id}>
                  {isEditing === area.id ? (
                    <>
                      <td>
                        <input
                          type="text"
                          value={editForm.title}
                          onChange={(e) => setEditForm({ ...editForm, title: e.target.value })}
                          className="admin-input text-xs py-1.5 px-2.5"
                        />
                      </td>
                      <td>
                        <input
                          type="text"
                          value={editForm.description}
                          onChange={(e) => setEditForm({ ...editForm, description: e.target.value })}
                          className="admin-input text-xs py-1.5 px-2.5"
                        />
                      </td>
                      <td>
                        <input
                          type="text"
                          value={editForm.slug}
                          onChange={(e) => setEditForm({ ...editForm, slug: e.target.value })}
                          className="admin-input text-xs py-1.5 px-2.5 font-mono"
                        />
                      </td>
                      <td style={{ textAlign: 'right' }}>
                        <div className="flex items-center justify-end gap-2">
                          <button
                            onClick={() => handleSave(area.id)}
                            className="p-1.5 rounded-lg transition-colors cursor-pointer"
                            style={{ backgroundColor: 'var(--color-accent)', color: '#ffffff' }}
                            title="Kaydet"
                          >
                            <Save className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => setIsEditing(null)}
                            className="p-1.5 rounded-lg border transition-colors cursor-pointer"
                            style={{ borderColor: 'var(--color-rule)', color: 'var(--color-muted)' }}
                            title="İptal"
                          >
                            <X className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </>
                  ) : (
                    <>
                      <td className="font-semibold" style={{ color: 'var(--color-ink)' }}>{area.title}</td>
                      <td className="max-w-xs truncate" style={{ color: 'var(--color-ink-2)' }}>{area.description}</td>
                      <td className="font-mono text-xs" style={{ color: 'var(--color-muted)' }}>{area.slug}</td>
                      <td style={{ textAlign: 'right' }}>
                        <div className="flex items-center justify-end gap-2">
                          <button
                            onClick={() => handleEdit(area)}
                            className="p-1.5 rounded-lg transition-colors cursor-pointer"
                            style={{ color: 'var(--color-ink-2)' }}
                            title="Düzenle"
                          >
                            <Edit className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => handleDelete(area.id)}
                            className="p-1.5 rounded-lg transition-colors cursor-pointer"
                            style={{ color: '#ef4444' }}
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
