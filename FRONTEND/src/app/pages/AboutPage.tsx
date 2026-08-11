import React from 'react';
import { Link } from 'react-router-dom';

const TECH_STACK = [
  { label: "01 · MODEL", title: "llama-3 llm", body: "açık kaynaklı yüksek performanslı dil modeli. doğal türkçe hukuki yanıt üretimi için ince ayar yapılmış." },
  { label: "02 · VEKTÖRİNDEKS", title: "qdrant vektör db", body: "mevzuat maddelerinin anlamsal aranması için düşük gecikmeli, yüksek hızlı vektör indeksleme." },
  { label: "03 · MİMARİ", title: "rag mimarisi", body: "halüsinasyonları engelleyen, yanıtları doğrudan ilgili kanun fıkralarına bağlayan retrieval sistemi." },
  { label: "04 · PROJE", title: "bitirme projesi", body: "yapay zeka destekli akademik üniversite bitirme çalışması — 2026." },
];

export function AboutPage() {
  return (
    <>
      {/* Page hero */}
      <section
        style={{
          background: `
            linear-gradient(var(--rule-blueprint) 1px, transparent 1px) 0 0 / 48px 48px,
            linear-gradient(90deg, var(--rule-blueprint) 1px, transparent 1px) 0 0 / 48px 48px,
            var(--color-paper)
          `,
          paddingTop: "var(--space-12)",
          paddingBottom: "var(--space-10)",
          borderBottom: "1px solid var(--color-rule)",
        }}
        aria-labelledby="about-title"
      >
        <div className="lumen-shell">
          <span className="eyebrow" style={{ display: "block", marginBottom: "var(--space-4)" }}>
            00 · proje misyonu ve teknoloji
          </span>
          <h1
            id="about-title"
            style={{
              fontFamily: "var(--font-display)",
              fontWeight: 400,
              fontSize: "var(--text-display)",
              lineHeight: "var(--leading-tight)",
              letterSpacing: "var(--tracking-display)",
              color: "var(--color-ink)",
              maxWidth: "18ch",
              overflowWrap: "anywhere",
            }}
          >
            hukuk teknolojisinde{" "}
            <em style={{ fontStyle: "normal", color: "var(--color-accent-2)" }}>yeni</em>{" "}
            bir boyut.
          </h1>
          <p
            style={{
              marginTop: "var(--space-6)",
              fontSize: "var(--text-lg)",
              color: "var(--color-ink-2)",
              lineHeight: "var(--leading-normal)",
              maxWidth: "52ch",
            }}
          >
            lawagent, türk borçlar kanunu, ticaret kanunu ve tüketici kanunu
            kapsamındaki hukuki metinleri anlamsal olarak analiz eden yapay zeka destekli
            hukuki karar destek platformudur.
          </p>
        </div>
      </section>

      {/* Stat row */}
      <div className="lumen-stats lumen-shell">
        <div className="lumen-stat">
          <span className="lumen-stat__num">%99.4</span>
          <span className="lumen-stat__label">mevzuat doğruluğu</span>
        </div>
        <div className="lumen-stat__divider" aria-hidden="true"/>
        <div className="lumen-stat">
          <span className="lumen-stat__num">2837</span>
          <span className="lumen-stat__label">indekslenen madde</span>
        </div>
        <div className="lumen-stat__divider" aria-hidden="true"/>
        <div className="lumen-stat">
          <span className="lumen-stat__num">28 ms</span>
          <span className="lumen-stat__label">p50 yanıt süresi</span>
        </div>
      </div>

      {/* What is LawAgent */}
      <section className="lumen-section" aria-labelledby="what-title">
        <div className="lumen-shell">
          <header className="lumen-section__head">
            <span className="eyebrow">01 · lawagent nedir?</span>
            <h2 id="what-title" className="lumen-section__title">
              akıllı hukuki araştırma <em style={{ fontStyle: "normal", color: "var(--color-accent-2)" }}>asistanı</em>.
            </h2>
          </header>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: "var(--space-10)",
              alignItems: "start",
            }}
          >
            <p style={{ fontSize: "var(--text-md)", color: "var(--color-ink-2)", lineHeight: "var(--leading-body)" }}>
              geleneksel kelime bazlı arama motorları, hukuki soruların içerdiği bağlamı
              tam olarak kavrayamaz. lawagent, rag (retrieval-augmented generation)
              mimarisini kullanarak sorunuzun özünü kavrar.
            </p>
            <p style={{ fontSize: "var(--text-md)", color: "var(--color-ink-2)", lineHeight: "var(--leading-body)" }}>
              qdrant vektör veritabanından en alakalı mevzuat maddelerini bulur ve
              llama-3 modeliyle anlaşılır, yapılandırılmış türkçe ile yanıt üretir.
              kaynak madde numaraları her yanıtta gösterilir.
            </p>
          </div>
          <div style={{ marginTop: "var(--space-8)", display: "flex", gap: "var(--space-4)", flexWrap: "wrap" }}>
            <button className="lumen-btn lumen-btn--primary"
              onClick={() => window.dispatchEvent(new CustomEvent("toggle-chatbot"))}>
              asistanı şimdi deneyin →
            </button>
            <Link to="/contact" className="lumen-btn lumen-btn--ghost">
              geri bildirim verin
            </Link>
          </div>
        </div>
      </section>

      {/* Tech stack */}
      <section
        className="lumen-section"
        style={{ borderTop: "1px solid var(--color-rule)" }}
        aria-labelledby="tech-title"
      >
        <div className="lumen-shell">
          <header className="lumen-section__head">
            <span className="eyebrow">02 · teknoloji altyapısı</span>
            <h2 id="tech-title" className="lumen-section__title">
              yüksek hız ve akademik{" "}
              <em style={{ fontStyle: "normal", color: "var(--color-accent-2)" }}>doğruluk</em>.
            </h2>
            <p className="lumen-section__lede">
              modern mimari bileşenleri: açık kaynak llm, vektör arama, rag pipeline.
            </p>
          </header>
          <div className="lumen-cards" role="list">
            {TECH_STACK.map((item) => (
              <div key={item.label} className="lumen-card" role="listitem">
                <span className="lumen-card__eyebrow">{item.label}</span>
                <h3 className="lumen-card__title">{item.title}</h3>
                <p className="lumen-card__body">{item.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Vision */}
      <section
        className="lumen-cta"
        style={{ borderTop: "1px solid var(--color-rule)" }}
        aria-labelledby="vision-title"
      >
        <div className="lumen-shell">
          <span className="eyebrow" style={{ display: "block", marginBottom: "var(--space-5)" }}>
            03 · proje vizyonu
          </span>
          <h2 id="vision-title" className="lumen-cta__title">
            hukukçuların değil, araştırmanın <em>hızı</em>.
          </h2>
          <p className="lumen-cta__sub">
            yapay zekanın, hukukçuların yerini almak için değil — araştırma sürelerini
            saniyelere indiren ve hataları en aza indiren güçlü bir karar destek
            asistanı olarak hizmet etmesini sağlamak.
          </p>
          <Link to="/practice-areas" className="lumen-btn lumen-btn--primary"
            style={{ marginInline: "auto", display: "inline-flex" }}>
            uygulama alanlarını incele →
          </Link>
        </div>
      </section>
    </>
  );
}
