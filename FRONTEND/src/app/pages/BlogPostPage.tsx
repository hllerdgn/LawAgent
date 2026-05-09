import React from 'react';
import { Link, useParams } from 'react-router';
import { Button } from '../components/Button';
import { ArrowLeft, Calendar, User, Tag } from 'lucide-react';
import { ImageWithFallback } from '../components/figma/ImageWithFallback';

export function BlogPostPage() {
  const { slug } = useParams();

  // Mock blog post data
  const post = {
    title: 'Ticaret Hukukunda Sık Karşılaşılan Sorunlar',
    date: '15 Ocak 2025',
    category: 'Ticaret Hukuku',
    image: 'https://images.unsplash.com/photo-1454165804606-c3d57bc86b40?w=1200',
    content: `
      <p>Ticari faaliyetler yürütürken işletmeler birçok hukuki sorunla karşılaşabilir. Bu yazıda, en sık karşılaşılan ticari hukuk sorunlarını ve çözüm yollarını ele alacağız.</p>
      
      <h3>1. Şirket Ortakları Arasındaki Uyuşmazlıklar</h3>
      <p>Şirket ortakları arasındaki uyuşmazlıklar, işletmenin sürekliliğini tehdit edebilir. Ortaklık sözleşmelerinin detaylı ve net hazırlanması, bu tür sorunları önlemenin en etkili yoludur.</p>
      
      <h3>2. Sözleşme İhlalleri</h3>
      <p>Ticari sözleşmelerde tarafların yükümlülüklerini yerine getirmemesi sıkça yaşanan bir sorundur. Sözleşmelerin hukuka uygun hazırlanması ve ihlal durumunda yapılacakların belirlenmesi önemlidir.</p>
      
      <h3>3. Ticari Alacakların Tahsili</h3>
      <p>Özellikle KOBİ'ler için ticari alacakların zamanında tahsil edilememesi büyük bir sorundur. İcra ve iflas hukuku araçlarının doğru kullanılması, alacakların tahsilinde kritik öneme sahiptir.</p>
      
      <h3>Sonuç</h3>
      <p>Ticari faaliyetlerinizi hukuki risklere karşı korumak için deneyimli bir avukatla çalışmanız önerilir. Özellikle sözleşmelerinizi profesyonelce hazırlatmak, ileride karşılaşabileceğiniz sorunları minimize edecektir.</p>
    `
  };

  return (
    <div className="w-full">
      <section className="bg-gradient-to-br from-[var(--color-primary)] to-[var(--color-primary-dark)] text-white">
        <div className="max-w-[1440px] mx-auto px-6 lg:px-24 py-12 lg:py-20">
          <div className="max-w-3xl mx-auto">
            <Link to="/blog" className="inline-flex items-center gap-2 text-gray-200 hover:text-white mb-6">
              <ArrowLeft className="w-5 h-5" />
              Blog'a Dön
            </Link>
            <div className="flex items-center gap-4 text-gray-200 mb-4">
              <span className="flex items-center gap-2">
                <Calendar className="w-5 h-5" />
                {post.date}
              </span>
              <span className="flex items-center gap-2">
                <User className="w-5 h-5" />
                Av. Fatih Emre Kılıç
              </span>
              <span className="flex items-center gap-2">
                <Tag className="w-5 h-5" />
                {post.category}
              </span>
            </div>
            <h1 className="text-white">{post.title}</h1>
          </div>
        </div>
      </section>
      <section className="bg-white">
        <div className="max-w-[1440px] mx-auto px-6 lg:px-24 py-12">
          <div className="max-w-4xl mx-auto">
            <div className="relative h-96 rounded-2xl overflow-hidden">
              <ImageWithFallback
                src={post.image}
                alt={post.title}
                className="w-full h-full object-cover"
              />
            </div>
          </div>
        </div>
      </section>
      <section className="bg-white pb-20">
        <div className="max-w-[1440px] mx-auto px-6 lg:px-24">
          <div className="max-w-3xl mx-auto">
            <div 
              className="prose prose-lg max-w-none"
              dangerouslySetInnerHTML={{ __html: post.content }}
              style={{
                color: 'var(--color-text-primary)',
              }}
            />
          </div>
        </div>
      </section>
      <section className="bg-[var(--color-background)]">
        <div className="max-w-[1440px] mx-auto px-6 lg:px-24 py-12 lg:py-16">
          <div className="text-center flex flex-col items-center gap-6">
            <h2 className="text-[var(--color-primary)] max-w-3xl">Hukuki konularınızda profesyonel destek alın</h2>
            <p className="text-[var(--color-text-secondary)] max-w-2xl text-lg">
              Deneyimli avukatlık hizmetimizle yanınızdayız.
            </p>
            <Link to="/contact">
              <Button variant="primary">
                İletişime Geçin
              </Button>
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}

