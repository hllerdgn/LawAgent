import React from 'react';
import { Link } from 'react-router';
import { Button } from '../components/Button';
import { Award, BookOpen, Database, Scale, Cpu, Search } from 'lucide-react';
import { ImageWithFallback } from '../components/figma/ImageWithFallback';

export function AboutPage() {
  const qualifications = [
    {
      icon: Cpu,
      title: 'Llama-3 LLM',
      description: 'Açık kaynaklı ve güçlü dil modeli ile Türkçe dil desteği.'
    },
    {
      icon: Database,
      title: 'Qdrant Vektör DB',
      description: 'Mevzuat maddelerinin anlamsal (vektörel) aranması için yüksek performans.'
    },
    {
      icon: Search,
      title: 'RAG Mimarisi',
      description: 'Halüsinasyonları engelleyen, doğrudan kanun maddesi getiren sistem.'
    },
    {
      icon: Award,
      title: 'Bitirme Projesi',
      description: 'Akademik destekli üniversite bitirme çalışması.'
    }
  ];

  return (
    <div className="w-full">
      <section className="bg-gradient-to-br from-[var(--color-primary)] to-[var(--color-primary-dark)] text-white">
        <div className="max-w-[1440px] mx-auto px-6 lg:px-24 py-12 lg:py-20">
          <div className="text-center max-w-3xl mx-auto">
            <h1 className="text-white mb-6">Proje Hakkında</h1>
            <p className="text-gray-200 text-lg">
              LawAgent AI, Türk hukuku alanında uzmanlaşmış bir bitirme projesi olarak geliştirilmiş yapay zeka asistanıdır.
            </p>
          </div>
        </div>
      </section>
      <section className="bg-white">
        <div className="max-w-[1440px] mx-auto px-6 lg:px-24 py-12 lg:py-20">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-start">
            <div className="flex flex-col gap-6">
              <div className="relative rounded-2xl overflow-hidden shadow-xl">
                <ImageWithFallback
                  src="https://images.unsplash.com/photo-1550751827-4bd374c3f58b?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHw3fHxjeWJlciUyMGxhd3xlbnwwfHx8fDE3NzcyMzU1MTN8MA&ixlib=rb-4.1.0&q=80&w=1080"
                  alt="AI Law Technology"
                  className="w-full h-[600px] object-cover"
                />
              </div>
            </div>
            <div className="flex flex-col gap-6">
              <div>
                <h2 className="text-[var(--color-primary)] mb-4">LawAgent Nedir?</h2>
                <p className="text-[var(--color-text-secondary)] leading-relaxed mb-4">
                  LawAgent, hukuki metinler ve mevzuatlar (TBK, TTK, TKHK vb.) üzerinde anlamsal arama yaparak 
                  sorularınıza kanuna dayalı, hızlı ve isabetli yanıtlar üreten bir yapay zeka asistanıdır. 
                  Bu sistem bir üniversite bitirme projesi olarak hayata geçirilmiştir.
                </p>
                <p className="text-[var(--color-text-secondary)] leading-relaxed mb-4">
                  Geleneksel anahtar kelime tabanlı aramaların aksine, LawAgent RAG (Retrieval-Augmented Generation) 
                  mimarisi kullanarak sorunun bağlamını anlar. Qdrant vektör veritabanından en ilgili maddeleri bulur 
                  ve Meta'nın Llama-3 modeliyle bunları anlaşılır bir Türkçe ile özetleyerek size sunar.
                </p>
                <div className="flex gap-4 mt-6">
                  <Link to="/contact">
                    <Button variant="primary">
                      Geri Bildirim Verin
                    </Button>
                  </Link>
                  <button
                    onClick={() => {
                      window.dispatchEvent(new CustomEvent("toggle-chatbot"));
                    }}
                    className="bg-transparent border-2 border-[#1e3a5f] text-[#1e3a5f] hover:bg-gray-50 transition-all duration-300 text-sm px-6 py-2.5 rounded-lg font-semibold"
                  >
                    Asistanı Dene
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>
      <section className="bg-[var(--color-background)]">
        <div className="max-w-[1440px] mx-auto px-6 lg:px-24 py-12 lg:py-20">
          <div className="text-center mb-12">
            <h2 className="text-[var(--color-primary)] mb-4">Teknoloji Altyapımız</h2>
            <p className="text-[var(--color-text-secondary)] max-w-2xl mx-auto">
              Modern makine öğrenmesi araçları ve açık kaynaklı dil modelleri kullanılarak inşa edildi.
            </p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {qualifications.map((qual, index) => {
              const Icon = qual.icon;
              return (
                <div 
                  key={index}
                  className="bg-white p-6 rounded-xl border border-[var(--color-border)] hover:shadow-lg transition-shadow"
                >
                  <div className="flex flex-col items-center text-center gap-4">
                    <div className="w-16 h-16 bg-[var(--color-primary)] rounded-full flex items-center justify-center">
                      <Icon className="w-8 h-8 text-[var(--color-accent)]" />
                    </div>
                    <div>
                      <h3 className="text-[var(--color-primary)] mb-2">{qual.title}</h3>
                      <p className="text-[var(--color-text-secondary)] caption">{qual.description}</p>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </section>
      <section className="bg-white">
        <div className="max-w-[1440px] mx-auto px-6 lg:px-24 py-12 lg:py-20">
          <div className="max-w-4xl mx-auto">
            <div className="bg-gradient-to-br from-[var(--color-primary)] to-[var(--color-primary-dark)] text-white p-8 lg:p-12 rounded-2xl">
              <div className="flex flex-col gap-6 text-center">
                <BookOpen className="w-16 h-16 text-[var(--color-accent)] mx-auto" />
                <h2 className="text-white">Proje Vizyonu</h2>
                <p className="text-gray-200 text-lg leading-relaxed">
                  "Hukuka erişimi teknolojinin gücüyle hızlandırmak ve demokratikleştirmek. 
                  Yapay zekanın, avukatların yerini almak için değil, hukuki araştırma süreçlerini saniyelere 
                  düşüren bir asistan olarak hizmet etmesini sağlamak temel misyonumuzdur."
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>
      <section className="bg-[var(--color-background)]">
        <div className="max-w-[1440px] mx-auto px-6 lg:px-24 py-12 lg:py-16">
          <div className="text-center flex flex-col items-center gap-6">
            <h2 className="text-[var(--color-primary)] max-w-3xl">Hukuki araştırma sürecinizi hızlandırmaya hazır mısınız?</h2>
            <p className="text-[var(--color-text-secondary)] max-w-2xl text-lg">
              Sistemi test edebilir, merak ettiğiniz hukuki soruları asistanımıza sorabilirsiniz.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 mt-4">
              <button
                onClick={() => {
                  window.dispatchEvent(new CustomEvent("toggle-chatbot"));
                }}
                className="bg-[#D4A574] hover:bg-[#B8926A] text-[#1e3a5f] rounded-lg transition-all duration-300 text-base px-8 py-4 font-semibold"
              >
                Hemen Sor
              </button>
              <Link to="/practice-areas">
                <Button variant="secondary">
                  Desteklenen Kanunlar
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
