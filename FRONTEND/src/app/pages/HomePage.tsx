import React from "react";
import { Link } from "react-router";
import { Button } from "../components/Button";
import { PracticeAreaCard } from "../components/PracticeAreaCard";
import {
  Briefcase,
  Users,
  Home as HomeIcon,
  FileText,
  Building2,
  ShoppingCart,
  MessageCircle,
  Sparkles,
  CheckCircle2,
  Send,
  ArrowRight,
  Phone,
  Info,
  Scale,
  TrendingUp,
  Award,
  Zap,
  Star,
} from "lucide-react";
import { ImageWithFallback } from "../components/figma/ImageWithFallback";

export function HomePage() {
  const practiceAreas = [
    {
      icon: Briefcase,
      title: "Ticaret Hukuku (TTK)",
      description:
        "Türk Ticaret Kanunu kapsamında şirket kuruluşu, ticari işletme hukuku ve ticari uyuşmazlıklar.",
      slug: "ticaret-hukuku",
    },
    {
      icon: Users,
      title: "İş Hukuku (TBK)",
      description:
        "Türk Borçlar Kanunu kapsamında iş sözleşmeleri, işçi-işveren uyuşmazlıkları ve iş güvenliği.",
      slug: "is-hukuku",
    },
    {
      icon: ShoppingCart,
      title: "Tüketici Hukuku (TKHK)",
      description:
        "Tüketicinin Korunması Hakkında Kanun kapsamında tüketici hakları ve ayıplı mal süreçleri.",
      slug: "tuketici-hukuku",
    },
  ];

  return (
    <div className="w-full">
      <section className="bg-gradient-to-br from-slate-50 via-white to-blue-50/30">
        <div className="max-w-[1440px] mx-auto px-6 lg:px-24 py-16 lg:py-24">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">
            <div className="flex flex-col gap-8">
              <h1 className="text-[#1e3a5f] text-4xl lg:text-5xl font-bold leading-tight">
                Türk Hukuku İçin Geliştirilmiş{" "}
                <span className="text-[#D4A574]">
                  Yapay Zeka Asistanı
                </span>
              </h1>
              <div className="flex items-start gap-3 bg-gradient-to-r from-[#D4A574]/10 to-transparent p-4 rounded-xl border-l-4 border-[#D4A574]">
                <Zap className="w-6 h-6 text-[#D4A574] flex-shrink-0 mt-1" />
                <p className="text-gray-700 font-medium leading-relaxed">
                  Ticaret ve iş hukuku alanında{" "}
                  <strong>hızlı, veri destekli</strong> hukuki çözümler
                  sunuyoruz.
                </p>
              </div>
              <div className="flex flex-col sm:flex-row gap-4 pt-4">
                <button
                  onClick={() => {
                    const el = document.getElementById("practice-areas-section");
                    el?.scrollIntoView({ behavior: "smooth" });
                  }}
                  className="bg-white border-2 border-[#1e3a5f] text-[#1e3a5f] hover:bg-gray-50 transition-all duration-300 text-base px-8 py-6 rounded-lg font-semibold group flex items-center justify-center gap-2"
                >
                  Özellikleri Keşfet
                  <ArrowRight className="w-5 h-5 ml-1 group-hover:translate-x-1 transition-transform" />
                </button>
                <button
                  onClick={() => {
                    // ChatbotWidget'ı açmak için custom event kullan
                    window.dispatchEvent(new CustomEvent("toggle-chatbot"));
                  }}
                  className="inline-flex items-center justify-center gap-2 border-2 border-[#D4A574] text-[#1e3a5f] hover:bg-[#D4A574] hover:text-white transition-all duration-300 text-base px-8 py-6 rounded-lg font-semibold group"
                >
                  <Sparkles className="w-5 h-5 group-hover:rotate-12 transition-transform" />
                  AI Asistanı Başlat
                </button>
              </div>
            </div>
            <div className="flex flex-col gap-6">
              <div className="relative rounded-2xl overflow-hidden shadow-2xl bg-gradient-to-br from-[#1e3a5f]/5 to-[#D4A574]/5 group">
                <ImageWithFallback
                  src="https://images.unsplash.com/photo-1620712943543-bcc4688e7485?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwyfHxhcnRpZmljaWFsJTIwaW50ZWxsaWdlbmNlJTIwYWJzdHJhY3R8ZW58MHx8fHwxNzc3MjM0NDU2fDA&ixlib=rb-4.1.0&q=80&w=1080"
                  alt="Yapay Zeka Hukuk Asistanı"
                  className="w-full h-[450px] object-cover transition-transform duration-700 group-hover:scale-105 opacity-90"
                />
                <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-[#1e3a5f]/90 via-[#1e3a5f]/60 to-transparent p-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-white text-lg font-bold mb-1">
                        Yapay Zeka Destekli
                      </p>
                      <p className="text-blue-200 text-sm">
                        Henüz avukat girişi yapılmadı
                      </p>
                    </div>
                    <div className="w-12 h-12 bg-[#D4A574] rounded-full flex items-center justify-center">
                      <Scale className="w-6 h-6 text-white" />
                    </div>
                  </div>
                </div>
                <div className="absolute top-4 right-4 bg-white/95 backdrop-blur-sm px-3 py-2 rounded-lg shadow-lg">
                  <div className="flex items-center gap-2">
                    <Star className="w-4 h-4 text-yellow-500 fill-yellow-500" />
                    <span className="text-sm font-bold text-[#1e3a5f]">
                      4.9/5.0
                    </span>
                  </div>
                </div>
              </div>
              <div className="relative group">
                <div className="absolute -inset-1 bg-gradient-to-r from-[#D4A574] to-[#1e3a5f] rounded-xl opacity-20 group-hover:opacity-30 blur transition-all duration-300" />

                <div className="relative bg-white p-6 rounded-xl shadow-xl border-2 border-[#D4A574]/30 hover:border-[#D4A574] transition-all duration-300">
                  <div className="flex items-start gap-4 mb-4">
                    <div className="relative">
                      <div className="w-14 h-14 bg-gradient-to-br from-[#1e3a5f] to-[#152b47] rounded-xl flex items-center justify-center flex-shrink-0 shadow-lg">
                        <MessageCircle className="w-7 h-7 text-[#D4A574]" />
                      </div>
                      <span className="absolute -top-1 -right-1 flex h-4 w-4">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                        <span className="relative inline-flex rounded-full h-4 w-4 bg-green-500 border-2 border-white"></span>
                      </span>
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <h3 className="text-[#1e3a5f] font-bold text-lg">
                          AI Hukuk Asistanı
                        </h3>
                        <span className="inline-flex items-center gap-1 bg-green-50 text-green-700 px-2 py-0.5 rounded-full text-xs font-semibold">
                          <span className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse"></span>
                          Çevrimiçi
                        </span>
                      </div>
                      <div className="space-y-2 text-sm text-gray-600">
                        <div className="flex items-center gap-2">
                          <CheckCircle2 className="w-4 h-4 text-[#D4A574]" />
                          <span>7/24 anında yanıt</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <CheckCircle2 className="w-4 h-4 text-[#D4A574]" />
                          <span>Mevzuat destekli öneriler</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <CheckCircle2 className="w-4 h-4 text-[#D4A574]" />
                          <span>Yapay zeka teknolojisi</span>
                        </div>
                      </div>
                    </div>
                  </div>
                  <button
                    onClick={() => {
                      const chatButton = document.querySelector(
                        '[aria-label="AI Chatbot"]',
                      ) as HTMLButtonElement;
                      if (chatButton) chatButton.click();
                    }}
                    className="w-full bg-gradient-to-r from-[#1e3a5f] to-[#152b47] hover:from-[#152b47] hover:to-[#1e3a5f] text-white py-3 rounded-lg font-semibold flex items-center justify-center gap-2 transition-all duration-300 hover:shadow-lg hover:scale-[1.02] group/btn"
                  >
                    <Sparkles className="w-5 h-5 group-hover/btn:rotate-12 transition-transform" />
                    Hemen Sor
                    <ArrowRight className="w-5 h-5 group-hover/btn:translate-x-1 transition-transform" />
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>
      <section id="practice-areas-section" className="bg-white">
        <div className="max-w-[1440px] mx-auto px-6 lg:px-24 py-16 lg:py-24">
          <div className="text-center mb-16">
            <div className="inline-flex items-center gap-2 bg-[#D4A574]/10 text-[#D4A574] px-4 py-2 rounded-full text-sm font-semibold mb-6">
              <Sparkles className="w-4 h-4" />
              Desteklenen Mevzuatlar
            </div>
            <h2 className="text-[#1e3a5f] mb-6 text-4xl lg:text-5xl font-bold">
              Kapsamlı Hukuki Yapay Zeka
            </h2>
            <p className="text-gray-600 max-w-3xl mx-auto text-lg leading-relaxed">
              LawAgent AI asistanı, RAG (Retrieval-Augmented Generation) mimarisi sayesinde aşağıdaki temel kanunlarda 
              doğru ve mevzuat destekli yanıtlar sunar.
            </p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {practiceAreas.map((area, index) => (
              <Link key={index} to={`/practice-areas/${area.slug}`}>
                <PracticeAreaCard
                  icon={area.icon}
                  title={area.title}
                  description={area.description}
                />
              </Link>
            ))}
          </div>
          <div className="text-center mt-16">
            <Link to="/practice-areas">
              <Button
                variant="secondary"
                className="border-2 border-[#1e3a5f] text-[#1e3a5f] hover:bg-[#1e3a5f] hover:text-white transition-all duration-300 px-8 py-6 text-base font-semibold"
              >
                Tüm Kapsamı Görüntüle
                <ArrowRight className="w-5 h-5 ml-2" />
              </Button>
            </Link>
          </div>
        </div>
      </section>
      <section className="bg-gradient-to-br from-slate-50 to-blue-50/30">
        <div className="max-w-[1440px] mx-auto px-6 lg:px-24 py-16 lg:py-24">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">
            <div className="flex flex-col gap-8">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 bg-gradient-to-br from-purple-100 to-blue-100 rounded-xl flex items-center justify-center">
                  <Sparkles className="w-6 h-6 text-purple-600" />
                </div>
                <div>
                  <h3 className="text-[#1e3a5f] text-xl font-bold">
                    Yapay Zeka Destekli Hukuki Analiz
                  </h3>
                  <p className="text-gray-600 text-sm">
                    Gelişmiş AI teknolojisi ile hızlı ve doğru çözümler
                  </p>
                </div>
              </div>

              <h2 className="text-[#1e3a5f] text-4xl lg:text-5xl font-bold leading-tight">
                7/24{" "}
                <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#D4A574] to-[#1e3a5f]">
                  AI Hukuk Asistanınız
                </span>
              </h2>

              <p className="text-gray-700 text-lg leading-relaxed">
                LawAgent AI Asistanı, Llama-3 dil modeli ve Qdrant vektör veritabanı 
                altyapısıyla hukuki sorularınıza <strong>anında</strong> yanıt verir. 
                TBK, TTK ve TKHK kapsamında sık sorulan sorularınız için 
                hızlı ve isabetli asistanınızdır.
              </p>
              <div className="flex flex-col gap-5">
                <div className="flex items-start gap-4 bg-white p-5 rounded-xl shadow-sm border border-gray-100 hover:shadow-md hover:border-[#D4A574]/30 transition-all duration-300 group cursor-default">
                  <div className="w-12 h-12 bg-gradient-to-br from-[#D4A574]/10 to-[#D4A574]/5 rounded-xl flex items-center justify-center flex-shrink-0 group-hover:scale-110 transition-transform">
                    <Zap className="w-6 h-6 text-[#D4A574]" />
                  </div>
                  <div>
                    <p className="text-[#1e3a5f] font-bold mb-1 group-hover:text-[#D4A574] transition-colors">
                      Anında Hukuki Bilgi
                    </p>
                    <p className="text-gray-600 text-sm leading-relaxed">
                      Sık sorulan sorulara 7/24 profesyonel yanıtlar
                    </p>
                  </div>
                </div>
                <div className="flex items-start gap-4 bg-white p-5 rounded-xl shadow-sm border border-gray-100 hover:shadow-md hover:border-[#D4A574]/30 transition-all duration-300 group cursor-default">
                  <div className="w-12 h-12 bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl flex items-center justify-center flex-shrink-0 group-hover:scale-110 transition-transform">
                    <FileText className="w-6 h-6 text-blue-600" />
                  </div>
                  <div>
                    <p className="text-[#1e3a5f] font-bold mb-1 group-hover:text-blue-600 transition-colors">
                      Mevzuat Destekli Öneriler
                    </p>
                    <p className="text-gray-600 text-sm leading-relaxed">
                      TBK,TTK ve TKHK kapsamında güncel bilgiler
                    </p>
                  </div>
                </div>
                <div className="flex items-start gap-4 bg-white p-5 rounded-xl shadow-sm border border-gray-100 hover:shadow-md hover:border-[#D4A574]/30 transition-all duration-300 group cursor-default">
                  <div className="w-12 h-12 bg-gradient-to-br from-green-50 to-emerald-50 rounded-xl flex items-center justify-center flex-shrink-0 group-hover:scale-110 transition-transform">
                    <CheckCircle2 className="w-6 h-6 text-green-600" />
                  </div>
                  <div>
                    <p className="text-[#1e3a5f] font-bold mb-1 group-hover:text-green-600 transition-colors">
                      Her Zaman Erişilebilir
                    </p>
                    <p className="text-gray-600 text-sm leading-relaxed">
                      Gece gündüz hukuki sorularınızı yanıtlıyoruz
                    </p>
                  </div>
                </div>
              </div>
              <div>
                <button
                  onClick={() => {
                    window.dispatchEvent(new CustomEvent("toggle-chatbot"));
                  }}
                  className="inline-flex items-center justify-center gap-2 bg-gradient-to-r from-[#1e3a5f] to-[#152b47] hover:shadow-lg transition-all duration-300 px-8 py-6 text-base text-white rounded-lg font-semibold"
                >
                  <MessageCircle className="w-5 h-5" />
                  Şimdi Deneyin
                </button>
              </div>
            </div>
            <div className="relative">
              <div className="absolute -inset-4 bg-gradient-to-br from-[#1e3a5f]/5 to-[#D4A574]/10 rounded-3xl blur-2xl" />

              <div className="relative bg-white rounded-3xl shadow-2xl overflow-hidden border-2 border-gray-100">
                <div className="bg-gradient-to-r from-[#1e3a5f] to-[#152b47] p-5 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-11 h-11 bg-gradient-to-br from-[#D4A574] to-[#B8926A] rounded-xl flex items-center justify-center shadow-lg">
                      <Scale className="w-5 h-5 text-white" />
                    </div>
                    <div>
                      <p className="text-white font-bold text-sm">
                        LawAgent AI Asistan
                      </p>
                      <p className="text-blue-200 text-xs">
                        Hukuk & Danışmanlık
                      </p>
                    </div>
                  </div>
                </div>
                <div className="bg-blue-50 border-b border-blue-100 px-4 py-2.5 flex items-start gap-2">
                  <Info className="w-3.5 h-3.5 text-blue-600 flex-shrink-0 mt-0.5" />
                  <p className="text-xs text-blue-900 leading-relaxed">
                    Genel bilgilendirme amaçlıdır, profesyonel danışmanlık için
                    ekibimizle iletişime geçin.
                  </p>
                </div>
                <div className="p-6 space-y-4 bg-gradient-to-b from-slate-50 to-gray-100 min-h-[350px]">
                  <div className="flex justify-start gap-2">
                    <div className="w-8 h-8 bg-gradient-to-br from-[#D4A574] to-[#B8926A] rounded-lg flex items-center justify-center flex-shrink-0">
                      <Scale className="w-4 h-4 text-white" />
                    </div>
                    <div className="bg-white px-4 py-3 rounded-2xl rounded-bl-md shadow-sm max-w-[75%] border border-gray-100">
                      <p className="text-sm text-gray-700">
                        Merhaba! LawAgent Hukuk & Danışmanlık AI Asistanına hoş
                        geldiniz. Size nasıl yardımcı olabilirim?
                      </p>
                    </div>
                  </div>
                  <div className="flex justify-end">
                    <div className="bg-gradient-to-br from-[#1e3a5f] to-[#152b47] text-white px-4 py-3 rounded-2xl rounded-br-md max-w-[75%] shadow-md">
                      <p className="text-sm">
                        Ticari sözleşme hazırlama konusunda bilgi almak
                        istiyorum
                      </p>
                    </div>
                  </div>
                  <div className="flex justify-start gap-2">
                    <div className="w-8 h-8 bg-gradient-to-br from-[#D4A574] to-[#B8926A] rounded-lg flex items-center justify-center flex-shrink-0">
                      <Scale className="w-4 h-4 text-white" />
                    </div>
                    <div className="bg-white px-4 py-3 rounded-2xl rounded-bl-md shadow-sm max-w-[75%] border border-gray-100">
                      <p className="text-sm text-gray-700">
                        Tabii ki! Ticari sözleşmeler konusunda size yardımcı
                        olabilirim. Hangi tür sözleşme hakkında detay almak
                        istersiniz?
                      </p>
                    </div>
                  </div>
                  <div className="flex justify-start gap-2 animate-pulse">
                    <div className="w-8 h-8 bg-gradient-to-br from-[#D4A574] to-[#B8926A] rounded-lg flex items-center justify-center flex-shrink-0">
                      <Scale className="w-4 h-4 text-white" />
                    </div>
                    <div className="bg-white px-4 py-3 rounded-2xl rounded-bl-md shadow-sm border border-gray-100">
                      <div className="flex gap-1.5">
                        <span
                          className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                          style={{ animationDelay: "0ms" }}
                        ></span>
                        <span
                          className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                          style={{ animationDelay: "150ms" }}
                        ></span>
                        <span
                          className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                          style={{ animationDelay: "300ms" }}
                        ></span>
                      </div>
                    </div>
                  </div>
                </div>
                <div className="p-4 border-t border-gray-200 bg-white">
                  <div className="flex items-center gap-3">
                    <div className="flex-1 px-4 py-3 border-2 border-gray-200 rounded-xl bg-gray-50 focus-within:border-[#D4A574] transition-colors">
                      <span className="text-gray-400 text-sm">
                        Hukuki sorunuzu yazın…
                      </span>
                    </div>
                    <div className="w-12 h-12 bg-gradient-to-br from-[#1e3a5f] to-[#152b47] rounded-xl flex items-center justify-center shadow-md hover:shadow-lg transition-all cursor-pointer">
                      <Send className="w-5 h-5 text-white" />
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>
      <section className="bg-gradient-to-br from-[#1e3a5f] via-[#152b47] to-[#1e3a5f] text-white relative overflow-hidden">
        <div className="absolute inset-0 opacity-10">
          <div className="absolute top-10 right-10 w-64 h-64 bg-[#D4A574] rounded-full blur-3xl" />
          <div className="absolute bottom-10 left-10 w-96 h-96 bg-[#D4A574] rounded-full blur-3xl" />
        </div>

        <div className="max-w-[1440px] mx-auto px-6 lg:px-24 py-16 lg:py-20 relative z-10">
          <div className="text-center flex flex-col items-center gap-8">
            <div className="inline-flex items-center gap-2 bg-[#D4A574]/20 text-[#D4A574] px-4 py-2 rounded-full text-sm font-semibold backdrop-blur-sm">
              <CheckCircle2 className="w-4 h-4" />
              Bitirme Projesi
            </div>
            <h2 className="text-white max-w-3xl text-4xl lg:text-5xl font-bold leading-tight">
              Yapay Zeka Destekli Hukuk Asistanını Hemen Deneyin
            </h2>
            <p className="text-blue-100 max-w-2xl text-lg leading-relaxed">
              LawAgent AI, hukuki metinlerdeki bilgi arama sürecinizi saniyelere indirir. 
              Gelişmiş RAG mimarisiyle doğru mevzuatı bulur ve size sunar.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 mt-6">
              <button
                onClick={() => {
                  window.dispatchEvent(new CustomEvent("toggle-chatbot"));
                }}
                className="bg-[#D4A574] hover:bg-[#B8926A] text-[#1e3a5f] rounded-lg hover:shadow-2xl transition-all duration-300 text-base px-8 py-6 font-semibold flex items-center gap-2"
              >
                Asistanı Başlat
                <Sparkles className="w-5 h-5 ml-1" />
              </button>
              <Link to="/about">
                <Button
                  variant="secondary"
                  className="border-2 border-white text-white hover:bg-white hover:text-[#1e3a5f] rounded-lg transition-all duration-300 text-base px-8 py-6 font-semibold"
                >
                  <Info className="w-5 h-5 mr-1" />
                  Proje Detayları
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}


