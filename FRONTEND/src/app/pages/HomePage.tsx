/* Hallmark · macrostructure: Marquee Hero · genre: editorial · theme: Lumen · drop: Day Foundry
 * audience: vatandaşlar · use case: chatbot başlat + 3 hizmet alanı
 * nav/footer: Layout.tsx üzerinden (çift nav önlendi)
 */

import React from "react";
import { Link } from "react-router-dom";

/* ── Meter bar heights — gaussian envelope ───────────────────────────────────── */
const METER_BARS = Array.from({ length: 64 }, (_, i) => {
  const t = i / 63;
  const env   = Math.exp(-7 * (t - 0.5) ** 2);
  const harm1 = Math.sin(t * Math.PI * 7) * 0.18;
  const harm2 = Math.sin(t * Math.PI * 15 + 1.2) * 0.09;
  return Math.max(0.06, Math.min(1, env * 0.73 + harm1 + harm2 + 0.08));
});

const PRACTICE_AREAS = [
  {
    slug: "is-hukuku",
    code: "TBK",
    label: "01 · İŞ HUKUKU",
    title: "iş hukuku",
    sub: "türk borçlar kanunu",
    body: "iş sözleşmeleri, kıdem ve ihbar tazminatı, işçi-işveren uyuşmazlıkları ve iş güvenliği konularında mevzuat destekli yanıtlar.",
    stat: "818 madde",
  },
  {
    slug: "ticaret-hukuku",
    code: "TTK",
    label: "02 · TİCARET HUKUKU",
    title: "ticaret hukuku",
    sub: "türk ticaret kanunu",
    body: "şirket kuruluşu, ticari işletme devri, anonim ve limited şirket işlemleri, ticari uyuşmazlıklar.",
    stat: "1535 madde",
  },
  {
    slug: "tuketici-hukuku",
    code: "TKHK",
    label: "03 · TÜKETİCİ HUKUKU",
    title: "tüketici hukuku",
    sub: "tüketicinin korunması hakkında kanun",
    body: "tüketici hakları, ayıplı mal ve hizmet, cayma hakkı, garanti belgeleri ve tüketici mahkemeleri.",
    stat: "84 madde",
  },
];

function PrismApparatus() {
  return (
    <figure className="lumen-apparatus" aria-label="hukuki analiz enstrümanı" aria-hidden="true">
      <svg
        className="lumen-apparatus__svg"
        viewBox="0 0 400 360"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <defs>
          <pattern id="grid-fine" width="24" height="24" patternUnits="userSpaceOnUse">
            <path d="M 24 0 L 0 0 0 24" fill="none" stroke="oklch(18% 0.014 265 / 0.06)" strokeWidth="0.5"/>
          </pattern>
          <linearGradient id="prism-fill" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="oklch(46% 0.24 268)" stopOpacity="0.14"/>
            <stop offset="100%" stopColor="oklch(46% 0.24 268)" stopOpacity="0.05"/>
          </linearGradient>
          <linearGradient id="beam-fade" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor="oklch(55% 0.010 265)" stopOpacity="0"/>
            <stop offset="100%" stopColor="oklch(55% 0.010 265)" stopOpacity="0.6"/>
          </linearGradient>
        </defs>
        <rect width="400" height="360" fill="url(#grid-fine)" opacity="0.6"/>
        <polygon points="200,40 86,240 314,240" fill="url(#prism-fill)"
          stroke="oklch(46% 0.24 268 / 0.38)" strokeWidth="1"/>
        <line x1="143" y1="40" x2="200" y2="160"
          stroke="oklch(46% 0.24 268 / 0.18)" strokeWidth="0.5" strokeDasharray="3,4"/>
        <line x1="257" y1="40" x2="200" y2="160"
          stroke="oklch(46% 0.24 268 / 0.18)" strokeWidth="0.5" strokeDasharray="3,4"/>
        <circle cx="200" cy="160" r="2" fill="oklch(46% 0.24 268 / 0.5)"/>
        <line x1="0" y1="140" x2="143" y2="140"
          stroke="url(#beam-fade)" strokeWidth="1.5" strokeDasharray="5,4"/>
        <polygon points="143,137 150,140 143,143" fill="oklch(55% 0.010 265 / 0.5)"/>
        <line x1="143" y1="140" x2="269" y2="185"
          stroke="oklch(55% 0.010 265 / 0.25)" strokeWidth="1" strokeDasharray="3,3"/>
        {/* Spectrum rays */}
        <line x1="269" y1="185" x2="390" y2="139" stroke="oklch(68% 0.16 18)" strokeWidth="1.5" opacity="0.85"/>
        <line x1="269" y1="185" x2="394" y2="161" stroke="oklch(74% 0.18 45)" strokeWidth="1.5" opacity="0.80"/>
        <line x1="269" y1="185" x2="395" y2="185" stroke="oklch(78% 0.17 85)" strokeWidth="1.5" opacity="0.80"/>
        <line x1="269" y1="185" x2="394" y2="209" stroke="oklch(70% 0.16 145)" strokeWidth="1.5" opacity="0.80"/>
        <line x1="269" y1="185" x2="390" y2="231" stroke="oklch(58% 0.22 268)" strokeWidth="1.5" opacity="0.85"/>
        {/* Scale annotations */}
        <line x1="86" y1="262" x2="314" y2="262" stroke="oklch(18% 0.014 265 / 0.15)" strokeWidth="0.5"/>
        <line x1="86" y1="258" x2="86" y2="266" stroke="oklch(18% 0.014 265 / 0.15)" strokeWidth="0.5"/>
        <line x1="314" y1="258" x2="314" y2="266" stroke="oklch(18% 0.014 265 / 0.15)" strokeWidth="0.5"/>
        <text x="200" y="278" textAnchor="middle"
          fontFamily="'JetBrains Mono', monospace" fontSize="9" letterSpacing="0.10em"
          fill="oklch(55% 0.010 265)" opacity="0.6">θ_EXIT = 22°</text>
        <path d="M 155,140 A 20,20 0 0,1 148,124"
          stroke="oklch(18% 0.014 265 / 0.25)" strokeWidth="0.5" fill="none"/>
        <text x="158" y="120" fontFamily="'JetBrains Mono', monospace"
          fontSize="8.5" letterSpacing="0.08em" fill="oklch(55% 0.010 265)" opacity="0.55">
          θ_IN = 38°
        </text>
      </svg>
      <ul className="lumen-callouts">
        <li className="lumen-callout lumen-callout--left" style={{ top: "14%" } as React.CSSProperties}>TBK · 818 MADDE</li>
        <li className="lumen-callout lumen-callout--right" style={{ top: "34%" } as React.CSSProperties}>TTK · 1535 MADDE</li>
        <li className="lumen-callout lumen-callout--left" style={{ top: "62%" } as React.CSSProperties}>TKHK · 84 MADDE</li>
        <li className="lumen-callout lumen-callout--right" style={{ top: "80%" } as React.CSSProperties}>RAG V2 · 28 MS</li>
      </ul>
    </figure>
  );
}

export function HomePage() {
  return (
    <>
      {/* ── Hero ──────────────────────────────────────────────────────────── */}
      <section className="lumen-hero" id="hero" aria-labelledby="hero-title">
        <div className="lumen-shell">
          <div className="lumen-hero__grid">
            <div className="lumen-hero__lead">
              <div className="lumen-hero__eyebrow">
                <span className="eyebrow">00 · yapay zeka hukuk asistanı</span>
              </div>
              <h1 id="hero-title" className="lumen-hero__title">
                hukuki sorularınıza{" "}<em>yanıt</em>{" "}veriyor.
              </h1>
              <p className="lumen-hero__lede">
                türk borçlar kanunu, ticaret kanunu ve tüketici kanunu kapsamında
                mevzuat kaynaklı, güvenilir yanıtlar — saniyeler içinde.
              </p>
              <div className="lumen-hero__actions">
                <button
                  className="lumen-btn lumen-btn--primary"
                  onClick={() => window.dispatchEvent(new CustomEvent("toggle-chatbot"))}
                  aria-label="yapay zeka asistanını aç"
                >
                  asistanı başlat →
                </button>
                <Link to="/practice-areas" className="lumen-btn lumen-btn--ghost">
                  uygulama alanları
                </Link>
              </div>
            </div>
            <div>
              <PrismApparatus />
            </div>
          </div>
        </div>
      </section>

      {/* ── Meter Strip ───────────────────────────────────────────────────── */}
      <aside className="lumen-meter" aria-label="sistem sinyal okuyucu" aria-hidden="true">
        <span className="lumen-meter__label">KAYNAK · 2837 MADDE</span>
        <div className="lumen-meter__bars">
          {METER_BARS.map((h, i) => (
            <span key={i} className="lumen-meter__bar"
              style={{ height: `${Math.round(h * 26) + 2}px`, opacity: 0.28 + h * 0.72 }}/>
          ))}
        </div>
        <span className="lumen-meter__label">YANIT · 28 MS</span>
      </aside>

      {/* ── Three-Stat Row ────────────────────────────────────────────────── */}
      <section className="lumen-stats lumen-shell" aria-label="platform istatistikleri">
        <div className="lumen-stat">
          <span className="lumen-stat__num">%99.4</span>
          <span className="lumen-stat__label">mevzuat doğruluğu</span>
        </div>
        <div className="lumen-stat__divider" aria-hidden="true"/>
        <div className="lumen-stat">
          <span className="lumen-stat__num">7/24</span>
          <span className="lumen-stat__label">anlık yanıt</span>
        </div>
        <div className="lumen-stat__divider" aria-hidden="true"/>
        <div className="lumen-stat">
          <span className="lumen-stat__num">RAG v2</span>
          <span className="lumen-stat__label">vektör indeks</span>
        </div>
      </section>

      {/* ── Service Areas ─────────────────────────────────────────────────── */}
      <section className="lumen-section" id="uygulama-alanlari" aria-labelledby="areas-title">
        <div className="lumen-shell">
          <header className="lumen-section__head">
            <span className="eyebrow">01 · uygulama alanları</span>
            <h2 id="areas-title" className="lumen-section__title">
              türk hukukunun üç temel{" "}
              <span style={{ color: "var(--color-accent-2)" }}>mevzuatı</span>.
            </h2>
            <p className="lumen-section__lede">
              rag mimarisi, türk hukuk sisteminin en kritik üç kanun başlığında
              eğitilmiş vektör veritabanından beslenir.
            </p>
          </header>
          <div className="lumen-cards" role="list">
            {PRACTICE_AREAS.map((area) => (
              <Link key={area.slug} to={`/practice-areas/${area.slug}`}
                className="lumen-card" role="listitem">
                <span className="lumen-card__eyebrow">{area.label}</span>
                <div>
                  <h3 className="lumen-card__title">{area.title}</h3>
                  <p style={{
                    fontFamily: "var(--font-label)", fontSize: "10px",
                    letterSpacing: "0.10em", textTransform: "uppercase",
                    color: "var(--color-accent)", marginTop: "4px",
                  }}>
                    {area.sub} · {area.stat}
                  </p>
                </div>
                <p className="lumen-card__body">{area.body}</p>
                <span className="lumen-card__arrow" aria-hidden="true">→</span>
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA Strip ─────────────────────────────────────────────────────── */}
      <section className="lumen-cta" aria-labelledby="cta-title">
        <div className="lumen-shell">
          <div className="lumen-cta__eyebrow">
            <span className="eyebrow">02 · başla</span>
          </div>
          <h2 id="cta-title" className="lumen-cta__title">
            sorunuzu <em>sorun</em>.
          </h2>
          <p className="lumen-cta__sub">
            ücretsiz, anında, mevzuat destekli. kişisel verileriniz
            saklanmaz veya üçüncü taraflarla paylaşılmaz.
          </p>
          <button className="lumen-btn lumen-btn--primary"
            onClick={() => window.dispatchEvent(new CustomEvent("toggle-chatbot"))}
            style={{ marginInline: "auto", display: "flex" }}>
            asistanı başlat →
          </button>
        </div>
      </section>
    </>
  );
}
