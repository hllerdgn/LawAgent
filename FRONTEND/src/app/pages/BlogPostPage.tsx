import React from 'react';
import { Link, useParams } from 'react-router-dom';
import { ArrowLeft, Calendar, User, Tag, Clock, Sparkles } from 'lucide-react';
import { ImageWithFallback } from '../components/figma/ImageWithFallback';

export function BlogPostPage() {
  const { slug } = useParams();

  const DEFAULT_POST = {
    title: 'Ticaret Hukukunda Sık Karşılaşılan Uyuşmazlıklar ve Çözüm Yolları',
    date: '15 Ocak 2025',
    readTime: '5 dk okuma',
    category: 'Ticaret Hukuku',
    author: 'LawAgent Ekibi',
    image: 'https://images.unsplash.com/photo-1454165804606-c3d57bc86b40?w=1200',
    content: `
      <p>Ticari faaliyetler yürütürken işletmeler birçok hukuki risk ve sözleşmesel uyuşmazlıkla karşılaşabilir. 6102 Sayılı Türk Ticaret Kanunu (TTK) kapsamında, işletmelerin hak kaybına uğramaması için dikkat etmesi gereken temel hususları derledik.</p>
      
      <h3 className="text-xl font-bold font-serif text-slate-900 mt-6 mb-3">1. Şirket Ortakları Arasındaki Uyuşmazlıklar</h3>
      <p>Şirket ortakları arasında yönetim hakkı, kar payı dağıtımı ve sermaye artırımı konularında yaşanan uyuşmazlıklar, işletmenin sürekliliğini tehdit edebilir. Şirket esas sözleşmesinin ve ortaklar arası hissedarlar sözleşmesinin (SHA) profesyonelce hazırlanması en etkili korumadır.</p>
      
      <h3 className="text-xl font-bold font-serif text-slate-900 mt-6 mb-3">2. Ticari Sözleşme İhlalleri ve Cezai Şartlar</h3>
      <p>Tedarik, bayilik ve hizmet sözleşmelerinde tarafların edimlerini zamanında ifa etmemesi sıkça karşılaşılan bir sorundur. Sözleşmede mücbir sebep, cezai şart ve yetkili mahkeme şartlarının açıkça düzenlenmesi önem taşır.</p>
      
      <h3 className="text-xl font-bold font-serif text-slate-900 mt-6 mb-3">3. Ticari Alacakların Tahsili ve İcra Süreçleri</h3>
      <p>Özellikle KOBİ'ler için zamanında tahsil edilemeyen cari hesap alacakları nakit akışını bozar. Çek ve bono gibi kambiyo senetlerine dayalı takipler ile zımnı kabul yolları hızlı sonuç verir.</p>
      
      <h3 className="text-xl font-bold font-serif text-slate-900 mt-6 mb-3">Sonuç</h3>
      <p>Ticari ilişkilerinizde hukuki riskleri önceden öngörmek ve sözleşmelerinizi uzman desteğiyle yapılandırmak olası davaları engellemenin en ekonomik yoludur.</p>
    `
  };

  const [post, setPost] = React.useState(() => {
    try {
      const saved = localStorage.getItem('lawagent_blog_posts');
      if (saved) {
        const posts = JSON.parse(saved);
        const found = posts.find((p: any) => p.slug === slug || p.id === slug);
        if (found) {
          return {
            title: found.title,
            date: found.date || 'Bugün',
            readTime: '5 dk okuma',
            category: found.category || 'Mevzuat Hukuku',
            author: 'LawAgent AI Ekibi',
            image: 'https://images.unsplash.com/photo-1454165804606-c3d57bc86b40?w=1200',
            content: found.content || `<p>${found.title} hakkında detaylı bilgi ve hukuki analiz rehberi.</p>`,
          };
        }
      }
    } catch (e) {}
    return DEFAULT_POST;
  });

  return (
    <div className="w-full bg-slate-50 font-sans antialiased">
      
      {/* Header */}
      <section className="bg-slate-900 text-white py-16 lg:py-20 border-b border-slate-800 relative overflow-hidden">
        <div className="max-w-[1440px] mx-auto px-6 lg:px-16 relative z-10">
          <div className="max-w-3xl mx-auto">
            <Link to="/blog" className="inline-flex items-center gap-2 text-slate-400 hover:text-amber-400 text-sm font-medium transition-colors mb-6">
              <ArrowLeft className="w-4 h-4" />
              <span>Blog Listesine Dön</span>
            </Link>
            
            <div className="flex flex-wrap items-center gap-4 text-xs text-amber-400 font-medium mb-4">
              <span className="flex items-center gap-1.5 bg-amber-500/10 px-3 py-1 rounded-full border border-amber-500/20">
                <Tag className="w-3.5 h-3.5" />
                {post.category}
              </span>
              <span className="flex items-center gap-1.5 text-slate-300">
                <Calendar className="w-3.5 h-3.5" />
                {post.date}
              </span>
              <span className="flex items-center gap-1.5 text-slate-300">
                <Clock className="w-3.5 h-3.5" />
                {post.readTime}
              </span>
            </div>

            <h1 className="text-white text-3xl sm:text-4xl lg:text-5xl font-bold font-serif leading-tight mb-4">
              {post.title}
            </h1>

            <div className="flex items-center gap-3 pt-2">
              <div className="w-8 h-8 rounded-full bg-amber-500/20 border border-amber-500/40 flex items-center justify-center font-bold text-amber-400 text-xs">
                LA
              </div>
              <span className="text-xs text-slate-300 font-medium">{post.author}</span>
            </div>
          </div>
        </div>
      </section>

      {/* Featured Cover Image */}
      <section className="py-10 bg-white border-b border-slate-200">
        <div className="max-w-[1440px] mx-auto px-6 lg:px-16">
          <div className="max-w-4xl mx-auto">
            <div className="relative h-80 sm:h-96 rounded-3xl overflow-hidden shadow-xl border border-slate-200">
              <ImageWithFallback
                src={post.image}
                alt={post.title}
                className="w-full h-full object-cover"
              />
            </div>
          </div>
        </div>
      </section>

      {/* Article Markdown Content */}
      <section className="py-12 bg-white pb-24">
        <div className="max-w-[1440px] mx-auto px-6 lg:px-16">
          <div className="max-w-3xl mx-auto">
            <div 
              className="prose prose-slate prose-lg max-w-none leading-relaxed text-slate-700 font-sans"
              dangerouslySetInnerHTML={{ __html: post.content }}
            />
            
            {/* AI Assistant Banner */}
            <div className="mt-12 p-6 bg-slate-900 text-white rounded-3xl border border-slate-800 flex flex-col sm:flex-row items-center justify-between gap-6 shadow-xl">
              <div>
                <h4 className="text-white font-bold font-serif text-lg mb-1">
                  Bu Konuda Aklınıza Takılan Bir Soru mu Var?
                </h4>
                <p className="text-slate-400 text-xs">
                  LawAgent AI Asistanına bu makale veya kanun maddeleri hakkında soru sorabilirsiniz.
                </p>
              </div>
              <button
                onClick={() => {
                  window.dispatchEvent(new CustomEvent("toggle-chatbot"));
                }}
                className="bg-amber-500 hover:bg-amber-600 text-slate-950 font-bold text-xs px-5 py-3 rounded-xl flex-shrink-0 flex items-center gap-2 cursor-pointer"
              >
                <Sparkles className="w-4 h-4" />
                <span>AI Asistana Sor</span>
              </button>
            </div>

          </div>
        </div>
      </section>

    </div>
  );
}
