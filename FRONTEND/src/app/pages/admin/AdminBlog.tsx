import React, { useState, useEffect } from 'react';
import { Plus, Edit, Trash2, Eye, FileText, CheckCircle2, Clock, X, Save, Sparkles, Tag, Globe, FileCheck } from 'lucide-react';
import { Link } from 'react-router-dom';

interface BlogPost {
  id: string;
  title: string;
  slug: string;
  category: string;
  status: 'Yayında' | 'Taslak';
  date: string;
  views: string;
  content?: string;
  excerpt?: string;
}

export function AdminBlog() {
  const DEFAULT_POSTS: BlogPost[] = [
    {
      id: '1',
      title: 'Ticaret Hukukunda Sık Karşılaşılan Sorunlar',
      slug: 'ticaret-hukukunda-sik-karsilasilan-sorunlar',
      category: 'TTK · TİCARET',
      status: 'Yayında',
      date: '15 Ocak 2025',
      views: '240 Okunma',
      excerpt: '6102 sayılı türk ticaret kanunu çerçevesinde şirket ortakları uyuşmazlıkları ve ticari alacak tahsili rehberi.',
      content: '<p>Ticari faaliyetler yürütürken işletmeler birçok hukuki risk ve sözleşmesel uyuşmazlıkla karşılaşabilir. 6102 Sayılı Türk Ticaret Kanunu (TTK) kapsamında, işletmelerin hak kaybına uğramaması için dikkat etmesi gereken temel hususları derledik.</p><h3>1. Şirket Ortakları Arasındaki Uyuşmazlıklar</h3><p>Şirket ortakları arasında yönetim hakkı, kar payı dağıtımı ve sermaye artırımı konularında yaşanan uyuşmazlıklar, işletmenin sürekliliğini tehdit edebilir.</p>',
    },
    {
      id: '2',
      title: 'İş Sözleşmesi Feshi: Haklarınızı Bilin',
      slug: 'is-sozlesmesi-feshi-haklarinizi-bilin',
      category: 'TBK · İŞ',
      status: 'Taslak',
      date: '10 Ocak 2025',
      views: '180 Okunma',
      excerpt: 'İşçinin ve işverenin 4857 sayılı iş kanunu kapsamındaki hakları ve kıdem tazminatı hesaplama kuralları.',
      content: '<p>İş akitlerinin feshi süreçlerinde kıdem ve ihbar tazminatı hakları büyük önem taşır. Arabuluculuk başvurusu zorunlu ilk adımdır.</p>',
    },
    {
      id: '3',
      title: 'Tüketici Haklarında Yeni Düzenlemeler',
      slug: 'tuketici-haklarinda-yeni-duzenlemeler',
      category: 'TKHK · TÜKETİCİ',
      status: 'Yayında',
      date: '5 Ocak 2025',
      views: '310 Okunma',
      excerpt: '6502 sayılı TKHK uyarınca ayıplı mal iadesi, mesafeli satışlarda cayma hakkı ve Tüketici Hakem Heyeti sınırları.',
      content: '<p>Tüketicilerin e-ticaret alışverişlerinde 14 günlük cayma hakkı ve ayıplı mal iadelerinde Hakem Heyeti parasal sınırları güncellenmiştir.</p>',
    },
  ];

  const [posts, setPosts] = useState<BlogPost[]>(() => {
    try {
      const saved = localStorage.getItem('lawagent_blog_posts');
      return saved ? JSON.parse(saved) : DEFAULT_POSTS;
    } catch (e) {
      return DEFAULT_POSTS;
    }
  });

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingPost, setEditingPost] = useState<BlogPost | null>(null);

  const [formData, setFormData] = useState({
    title: '',
    slug: '',
    category: 'TTK · TİCARET',
    status: 'Yayında' as 'Yayında' | 'Taslak',
    excerpt: '',
    content: '',
  });

  useEffect(() => {
    const handleUpdate = () => {
      try {
        const saved = localStorage.getItem('lawagent_blog_posts');
        if (saved) setPosts(JSON.parse(saved));
      } catch (e) {}
    };

    window.addEventListener('storage', handleUpdate);
    window.addEventListener('lawagent_blog_updated', handleUpdate);
    return () => {
      window.removeEventListener('storage', handleUpdate);
      window.removeEventListener('lawagent_blog_updated', handleUpdate);
    };
  }, []);

  const savePosts = (newPosts: BlogPost[]) => {
    setPosts(newPosts);
    try {
      localStorage.setItem('lawagent_blog_posts', JSON.stringify(newPosts));
      window.dispatchEvent(new Event('lawagent_blog_updated'));
    } catch (e) {}
  };

  const handleOpenAdd = () => {
    setEditingPost(null);
    setFormData({
      title: '',
      slug: '',
      category: 'TTK · TİCARET',
      status: 'Yayında',
      excerpt: '',
      content: '',
    });
    setIsModalOpen(true);
  };

  const handleOpenEdit = (post: BlogPost) => {
    setEditingPost(post);
    setFormData({
      title: post.title,
      slug: post.slug,
      category: post.category || 'MEVZUAT',
      status: post.status,
      excerpt: post.excerpt || '',
      content: post.content || '',
    });
    setIsModalOpen(true);
  };

  const handleToggleStatus = (id: string) => {
    const updated = posts.map((p) =>
      p.id === id
        ? { ...p, status: (p.status === 'Yayında' ? 'Taslak' : 'Yayında') as 'Yayında' | 'Taslak' }
        : p
    );
    savePosts(updated);
  };

  const handleDelete = (id: string) => {
    if (confirm('Bu makaleyi ve içeriğini silmek istediğinizden emin misiniz?')) {
      savePosts(posts.filter((p) => p.id !== id));
    }
  };

  const handleSubmitForm = (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.title.trim()) return;

    const generatedSlug =
      formData.slug.trim() ||
      formData.title
        .toLowerCase()
        .replace(/ğ/g, 'g')
        .replace(/ü/g, 'u')
        .replace(/ş/g, 's')
        .replace(/ı/g, 'i')
        .replace(/ö/g, 'o')
        .replace(/ç/g, 'c')
        .replace(/[^a-z0-9]/g, '-')
        .replace(/-+/g, '-')
        .replace(/^-|-$/g, '');

    const todayStr = new Date().toLocaleDateString('tr-TR', {
      day: 'numeric',
      month: 'long',
      year: 'numeric',
    });

    if (editingPost) {
      // Güncelleme
      const updated = posts.map((p) =>
        p.id === editingPost.id
          ? {
              ...p,
              title: formData.title,
              slug: generatedSlug,
              category: formData.category,
              status: formData.status,
              excerpt: formData.excerpt || formData.title + ' hakkında hukuki analiz.',
              content: formData.content || `<p>${formData.title} makale içeriği.</p>`,
            }
          : p
      );
      savePosts(updated);
    } else {
      // Yeni Ekleme
      const newPost: BlogPost = {
        id: Date.now().toString(),
        title: formData.title,
        slug: generatedSlug,
        category: formData.category,
        status: formData.status,
        date: todayStr,
        views: '1 Okunma',
        excerpt: formData.excerpt || formData.title + ' hakkında hukuki analiz.',
        content: formData.content || `<p>${formData.title} makale içeriği.</p>`,
      };
      savePosts([newPost, ...posts]);
    }

    setIsModalOpen(false);
  };

  return (
    <div className="space-y-6 font-sans antialiased">
      
      {/* Top Header */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200/80 shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-slate-900 text-2xl font-bold font-serif">Blog & İçerik Yönetimi</h1>
          <p className="text-slate-500 text-xs sm:text-sm mt-1">
            Sitede yayımlanan hukuki makaleleri ekleyin, içeriğini düzenleyin veya yayın durumunu değiştirin.
          </p>
        </div>
        <button
          onClick={handleOpenAdd}
          className="bg-slate-900 hover:bg-slate-800 text-white px-5 py-2.5 rounded-xl font-medium text-xs flex items-center justify-center gap-2 cursor-pointer transition-colors border border-slate-800 shadow-md"
        >
          <Plus className="w-4 h-4 text-amber-400" />
          <span>Yeni Makale Ekle</span>
        </button>
      </div>

      {/* Posts Table */}
      <div className="bg-white rounded-2xl border border-slate-200/80 shadow-xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead className="bg-slate-50 border-b border-slate-200 text-slate-700 text-xs font-semibold uppercase tracking-wider">
              <tr>
                <th className="px-6 py-4">Makale Başlığı</th>
                <th className="px-6 py-4">Kategori</th>
                <th className="px-6 py-4">Yayın Durumu</th>
                <th className="px-6 py-4">Yayın Tarihi</th>
                <th className="px-6 py-4 text-right">İşlemler</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-xs text-slate-800">
              {posts.map((post) => (
                <tr key={post.id} className="hover:bg-slate-50/80 transition-colors">
                  <td className="px-6 py-4">
                    <span className="font-bold text-slate-900 block">{post.title}</span>
                    <span className="text-[11px] text-slate-400 font-mono">/blog/{post.slug}</span>
                  </td>
                  <td className="px-6 py-4 font-semibold text-violet-700">
                    <span className="bg-violet-50 border border-violet-200 px-2.5 py-1 rounded-md text-[11px]">
                      {post.category || 'Mevzuat'}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <button
                      onClick={() => handleToggleStatus(post.id)}
                      className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-semibold cursor-pointer transition-all ${
                        post.status === 'Yayında'
                          ? 'bg-emerald-50 text-emerald-700 border border-emerald-200 hover:bg-emerald-100'
                          : 'bg-amber-50 text-amber-700 border border-amber-200 hover:bg-amber-100'
                      }`}
                      title="Yayın durumunu değiştirmek için tıklayın"
                    >
                      <span className={`w-1.5 h-1.5 rounded-full ${post.status === 'Yayında' ? 'bg-emerald-500' : 'bg-amber-500'}`} />
                      {post.status}
                    </button>
                  </td>
                  <td className="px-6 py-4 text-slate-500">{post.date}</td>
                  <td className="px-6 py-4 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <Link
                        to={`/blog/${post.slug}`}
                        className="p-1.5 text-slate-600 hover:text-emerald-600 hover:bg-emerald-50 rounded-lg transition-colors cursor-pointer"
                        title="Sitede Önizle"
                      >
                        <Eye className="w-4 h-4" />
                      </Link>
                      <button
                        onClick={() => handleOpenEdit(post)}
                        className="p-1.5 text-slate-600 hover:text-amber-600 hover:bg-slate-100 rounded-lg transition-colors cursor-pointer"
                        title="Düzenle"
                      >
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

      {/* Edit / Create Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/60 backdrop-blur-xs">
          <div className="bg-white rounded-3xl border border-slate-200 shadow-2xl max-w-2xl w-full p-6 lg:p-8 space-y-6 max-h-[90vh] overflow-y-auto">
            
            <div className="flex items-center justify-between pb-4 border-b border-slate-100">
              <div className="flex items-center gap-2">
                <FileText className="w-5 h-5 text-amber-500" />
                <h3 className="text-slate-900 font-bold font-serif text-lg">
                  {editingPost ? 'Makaleyi Düzenle' : 'Yeni Makale Oluştur'}
                </h3>
              </div>
              <button
                onClick={() => setIsModalOpen(false)}
                className="p-2 text-slate-400 hover:text-slate-600 rounded-xl hover:bg-slate-100"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSubmitForm} className="space-y-5">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                  Makale Başlığı *
                </label>
                <input
                  type="text"
                  required
                  value={formData.title}
                  onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                  placeholder="örn. İş Sözleşmesi Feshi ve Kıdem Tazminatı Hakları"
                  className="w-full px-4 py-2.5 bg-slate-50 border border-slate-300 rounded-xl text-xs font-medium focus:ring-2 focus:ring-amber-500 focus:outline-none"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                    Kategori / Etiket
                  </label>
                  <select
                    value={formData.category}
                    onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                    className="w-full px-4 py-2.5 bg-slate-50 border border-slate-300 rounded-xl text-xs font-medium focus:ring-2 focus:ring-amber-500 focus:outline-none"
                  >
                    <option value="TTK · TİCARET">TTK · TİCARET</option>
                    <option value="TBK · İŞ">TBK · İŞ</option>
                    <option value="TKHK · TÜKETİCİ">TKHK · TÜKETİCİ</option>
                    <option value="MEVZUAT · REHBER">MEVZUAT · REHBER</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                    Yayın Durumu
                  </label>
                  <select
                    value={formData.status}
                    onChange={(e) => setFormData({ ...formData, status: e.target.value as any })}
                    className="w-full px-4 py-2.5 bg-slate-50 border border-slate-300 rounded-xl text-xs font-medium focus:ring-2 focus:ring-amber-500 focus:outline-none"
                  >
                    <option value="Yayında">Yayında</option>
                    <option value="Taslak">Taslak</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                  Özet / Giriş Cümlesi
                </label>
                <input
                  type="text"
                  value={formData.excerpt}
                  onChange={(e) => setFormData({ ...formData, excerpt: e.target.value })}
                  placeholder="Makalenin sitede görünen 1-2 cümlelik özeti"
                  className="w-full px-4 py-2.5 bg-slate-50 border border-slate-300 rounded-xl text-xs font-medium focus:ring-2 focus:ring-amber-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                  Makale Metni (HTML / Paragraflar)
                </label>
                <textarea
                  rows={6}
                  value={formData.content}
                  onChange={(e) => setFormData({ ...formData, content: e.target.value })}
                  placeholder="<p>Makale paragrafları ve içerik metni...</p>"
                  className="w-full px-4 py-2.5 bg-slate-50 border border-slate-300 rounded-xl text-xs font-mono leading-relaxed focus:ring-2 focus:ring-amber-500 focus:outline-none"
                />
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-5 py-2.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl text-xs font-medium"
                >
                  İptal
                </button>
                <button
                  type="submit"
                  className="px-6 py-2.5 bg-slate-900 hover:bg-slate-800 text-white rounded-xl text-xs font-medium shadow-md flex items-center gap-2"
                >
                  <Save className="w-4 h-4 text-amber-400" />
                  <span>{editingPost ? 'Değişiklikleri Kaydet' : 'Makaleyi Yayınla'}</span>
                </button>
              </div>
            </form>

          </div>
        </div>
      )}

    </div>
  );
}
