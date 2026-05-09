import React from 'react';
import { Link } from 'react-router';
import { Button } from '../components/Button';
import { Shield, Eye, Heart, Lock } from 'lucide-react';

export function WorkPrinciplesPage() {
  const principles = [
    {
      icon: Shield,
      title: 'Etik',
      description: 'Avukatlık mesleğinin etik kurallarına tam bağlılık gösteriyor, her zaman dürüstlük ve adalet ilkesi doğrultusunda hareket ediyorum.'
    },
    {
      icon: Eye,
      title: 'Şeffaflık',
      description: 'Müvekkillerimle açık ve net iletişim kuruyorum. Süreç boyunca tüm gelişmeler hakkında düzenli olarak bilgilendirme yapıyorum.'
    },
    {
      icon: Heart,
      title: 'Profesyonellik',
      description: 'Her dosyaya özen gösteriyor, titiz araştırma ve hazırlıkla en iyi sonucu elde etmek için çalışıyorum.'
    },
    {
      icon: Lock,
      title: 'Gizlilik',
      description: 'Müvekkil-avukat gizliliği ilkesine tam saygı gösteriyor, paylaşılan tüm bilgileri en üst düzey gizlilikle koruyorum.'
    }
  ];

  return (
    <div className="w-full">
      <section className="bg-gradient-to-br from-[var(--color-primary)] to-[var(--color-primary-dark)] text-white">
        <div className="max-w-[1440px] mx-auto px-6 lg:px-24 py-12 lg:py-20">
          <div className="text-center max-w-3xl mx-auto">
            <h1 className="text-white mb-6">Çalışma Prensiblerim</h1>
            <p className="text-gray-200 text-lg">
              Mesleğimi icra ederken bağlı olduğum değerler ve ilkeler.
            </p>
          </div>
        </div>
      </section>
      <section className="bg-white">
        <div className="max-w-[1440px] mx-auto px-6 lg:px-24 py-12 lg:py-20">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            {principles.map((principle, index) => {
              const Icon = principle.icon;
              return (
                <div 
                  key={index}
                  className="bg-[var(--color-background)] p-8 lg:p-10 rounded-2xl border border-[var(--color-border)] hover:shadow-xl transition-shadow"
                >
                  <div className="flex flex-col gap-6">
                    <div className="w-20 h-20 bg-[var(--color-primary)] rounded-full flex items-center justify-center">
                      <Icon className="w-10 h-10 text-[var(--color-accent)]" />
                    </div>
                    <div>
                      <h2 className="text-[var(--color-primary)] mb-4">{principle.title}</h2>
                      <p className="text-[var(--color-text-secondary)] leading-relaxed">
                        {principle.description}
                      </p>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </section>
      <section className="bg-[var(--color-background)]">
        <div className="max-w-[1440px] mx-auto px-6 lg:px-24 py-12 lg:py-20">
          <div className="max-w-4xl mx-auto">
            <div className="text-center mb-12">
              <h2 className="text-[var(--color-primary)] mb-4">Size Verdiğim Taahhütler</h2>
            </div>
            <div className="grid grid-cols-1 gap-6">
              <div className="bg-white p-6 rounded-xl border-l-4 border-[var(--color-accent)]">
                <h3 className="text-[var(--color-primary)] mb-2">Adalet Arayışı</h3>
                <p className="text-[var(--color-text-secondary)]">
                  Her müvekkilimin hakkını sonuna kadar savunuyor, adaleti sağlamak için elimden gelen her şeyi yapıyorum.
                </p>
              </div>
              <div className="bg-white p-6 rounded-xl border-l-4 border-[var(--color-accent)]">
                <h3 className="text-[var(--color-primary)] mb-2">Sürekli İletişim</h3>
                <p className="text-[var(--color-text-secondary)]">
                  Dosyanızın her aşamasında sizinle iletişim halinde kalıyor, sorularınızı yanıtlıyor ve sizi bilgilendiriyorum.
                </p>
              </div>
              <div className="bg-white p-6 rounded-xl border-l-4 border-[var(--color-accent)]">
                <h3 className="text-[var(--color-primary)] mb-2">Kişiye Özel Yaklaşım</h3>
                <p className="text-[var(--color-text-secondary)]">
                  Her dosyanın kendine özgü olduğunu biliyor, ihtiyaçlarınıza uygun özelleştirilmiş çözümler üretiyorum.
                </p>
              </div>
              <div className="bg-white p-6 rounded-xl border-l-4 border-[var(--color-accent)]">
                <h3 className="text-[var(--color-primary)] mb-2">Hızlı Yanıt</h3>
                <p className="text-[var(--color-text-secondary)]">
                  Sorularınıza ve taleplerinize mümkün olan en kısa sürede dönüş yapıyor, acil durumlarda hızlı hareket ediyorum.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>
      <section className="bg-white">
        <div className="max-w-[1440px] mx-auto px-6 lg:px-24 py-12 lg:py-16">
          <div className="text-center flex flex-col items-center gap-6">
            <h2 className="text-[var(--color-primary)] max-w-3xl">Bu prensiplerle size hizmet etmek isterim</h2>
            <p className="text-[var(--color-text-secondary)] max-w-2xl text-lg">
              Hukuki konularınızda profesyonel destek için benimle iletişime geçin.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 mt-4">
              <Link to="/contact">
                <Button variant="primary">
                  İletişime Geçin
                </Button>
              </Link>
              <Link to="/about">
                <Button variant="secondary">
                  Hakkımda Daha Fazla
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}

