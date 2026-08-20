import React from "react";
import { Link } from "react-router-dom";

const AREAS = [
  {
    slug: "ticaret-hukuku",
    label: "01 · TİCARET HUKUKU",
    title: "türk ticaret kanunu (ttk)",
    sub: "6102 sayılı kanun · 1535 madde",
    body: "şirket kuruluşu, haksız rekabet, ticari sözleşmeler, ticari uyuşmazlıkların çözümü ve şirketler hukukuna dair sorularınız için.",
  },
  {
    slug: "is-hukuku",
    label: "02 · İŞ HUKUKU",
    title: "türk borçlar kanunu (tbk)",
    sub: "6098 sayılı kanun · 818 madde",
    body: "iş akitlerinin feshi, kıdem ve ihbar tazminatları, işçi-işveren uyuşmazlıkları ve arabuluculuk süreçleri.",
  },
  {
    slug: "tuketici-hukuku",
    label: "03 · TÜKETİCİ HUKUKU",
    title: "tüketicinin korunması hakkında kanun (tkhk)",
    sub: "6502 sayılı kanun · 84 madde",
    body: "ayıplı mal ve hizmetler, mesafeli satış cayma hakkı, hakem heyeti ve tüketici mahkemesi süreçleri.",
  },
];

export function PracticeAreasPage() {
  const DEFAULT_AREAS = [
    {
      slug: "ticaret-hukuku",
      label: "01 · TİCARET HUKUKU",
      title: "türk ticaret kanunu (ttk)",
      sub: "6102 sayılı kanun · 1535 madde",
      body: "şirket kuruluşu, haksız rekabet, ticari sözleşmeler, ticari uyuşmazlıkların çözümü ve şirketler hukukuna dair sorularınız için.",
    },
    {
      slug: "is-hukuku",
      label: "02 · İŞ HUKUKU",
      title: "türk borçlar kanunu (tbk)",
      sub: "6098 sayılı kanun · 818 madde",
      body: "iş akitlerinin feshi, kıdem ve ihbar tazminatları, işçi-işveren uyuşmazlıkları ve arabuluculuk süreçleri.",
    },
    {
      slug: "tuketici-hukuku",
      label: "03 · TÜKETİCİ HUKUKU",
      title: "tüketicinin korunması hakkında kanun (tkhk)",
      sub: "6502 sayılı kanun · 84 madde",
      body: "ayıplı mal ve hizmetler, mesafeli satış cayma hakkı, hakem heyeti ve tüketici mahkemesi süreçleri.",
    },
  ];

  const [areas, setAreas] = React.useState(() => {
    try {
      const saved = localStorage.getItem('lawagent_practice_areas');
      if (saved) {
        const parsed = JSON.parse(saved);
        return parsed.map((item: any, idx: number) => ({
          slug: item.slug || `alan-${item.id}`,
          label: `0${idx + 1} · ${item.title.toUpperCase()}`,
          title: item.title.toLowerCase(),
          sub: 'güncel mevzuat normu',
          body: item.description.toLowerCase(),
        }));
      }
    } catch (e) {}
    return DEFAULT_AREAS;
  });

  React.useEffect(() => {
    const handleUpdate = () => {
      try {
        const saved = localStorage.getItem('lawagent_practice_areas');
        if (saved) {
          const parsed = JSON.parse(saved);
          setAreas(parsed.map((item: any, idx: number) => ({
            slug: item.slug || `alan-${item.id}`,
            label: `0${idx + 1} · ${item.title.toUpperCase()}`,
            title: item.title.toLowerCase(),
            sub: 'güncel mevzuat normu',
            body: item.description.toLowerCase(),
          })));
        }
      } catch (e) {}
    };
    window.addEventListener('storage', handleUpdate);
    window.addEventListener('lawagent_practice_areas_updated', handleUpdate);
    return () => {
      window.removeEventListener('storage', handleUpdate);
      window.removeEventListener('lawagent_practice_areas_updated', handleUpdate);
    };
  }, []);

  return (
    <>
      {/* Page hero */}
      <section
        style={{
          background: `
            linear-gradient(var(--rule-blueprint) 1px, transparent 1px) 0 0 / 48px 48px,
            linear-gradient(90deg, var(--rule-blueprint) 1px, transparent 1px) 0 0 / 48px 48px,
            radial-gradient(60% 40% at 80% 50%, var(--color-paper-emit) 0%, transparent 65%),
            var(--color-paper)
          `,
          paddingTop: "var(--space-12)",
          paddingBottom: "var(--space-10)",
          borderBottom: "1px solid var(--color-rule)",
        }}
        aria-labelledby="areas-title"
      >
        <div className="lumen-shell">
          <span className="eyebrow" style={{ display: "block", marginBottom: "var(--space-4)" }}>
            00 · mevzuat kapsamı ve uzmanlık
          </span>
          <h1
            id="areas-title"
            style={{
              fontFamily: "var(--font-display)",
              fontWeight: 400,
              fontSize: "var(--text-display)",
              lineHeight: "var(--leading-tight)",
              letterSpacing: "var(--tracking-display)",
              color: "var(--color-ink)",
              maxWidth: "16ch",
              overflowWrap: "anywhere",
            }}
          >
            desteklenen hukuk{" "}
            <em style={{ fontStyle: "normal", color: "var(--color-accent-2)" }}>disiplinleri</em>.
          </h1>
          <p style={{
            marginTop: "var(--space-6)",
            fontSize: "var(--text-lg)",
            color: "var(--color-ink-2)",
            lineHeight: "var(--leading-normal)",
            maxWidth: "52ch",
          }}>
            lawagent ai, aşağıdaki temel kanun maddeleri ve güncel mevzuat normları
            üzerinde eğitilmiştir.
          </p>
        </div>
      </section>

      {/* Stat row */}
      <div className="lumen-stats lumen-shell">
        <div className="lumen-stat">
          <span className="lumen-stat__num">{areas.length}</span>
          <span className="lumen-stat__label">temel kanun & alan</span>
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

      {/* Practice area cards */}
      <section className="lumen-section" aria-labelledby="areas-cards-title">
        <div className="lumen-shell">
          <header className="lumen-section__head">
            <span className="eyebrow">01 · uygulama alanları</span>
            <h2 id="areas-cards-title" className="lumen-section__title">
              türk hukukunun {areas.length} temel <em style={{ fontStyle: "normal", color: "var(--color-accent-2)" }}>mevzuatı</em>.
            </h2>
            <p className="lumen-section__lede">
              eklenen {areas.length} farklı uygulama alanı için özel olarak indekslenmiş vektör veri tabanı. ilgili kanun maddesine kaynak referansıyla yanıt.
            </p>
          </header>
          <div className="lumen-cards" role="list">
            {areas.map((area) => (
              <Link
                key={area.slug}
                to={`/practice-areas/${area.slug}`}
                className="lumen-card"
                role="listitem"
              >
                <span className="lumen-card__eyebrow">{area.label}</span>
                <div>
                  <h2 className="lumen-card__title">{area.title}</h2>
                  <p style={{
                    fontFamily: "var(--font-label)",
                    fontSize: "10px",
                    letterSpacing: "0.10em",
                    textTransform: "uppercase",
                    color: "var(--color-accent)",
                    marginTop: "var(--space-2)",
                  }}>
                    {area.sub}
                  </p>
                </div>
                <p className="lumen-card__body">{area.body}</p>
                <span className="lumen-card__arrow" aria-hidden="true">→</span>
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="lumen-cta" style={{ borderTop: "1px solid var(--color-rule)" }}>
        <div className="lumen-shell">
          <span className="eyebrow" style={{ display: "block", marginBottom: "var(--space-5)" }}>
            02 · mevzuat sorgulama
          </span>
          <h2 className="lumen-cta__title">
            özel bir kanun maddesini <em>sorgulayın</em>.
          </h2>
          <p className="lumen-cta__sub">
            merak ettiğiniz kanun fıkrasını doğrudan lawagent ai asistanına sorabilirsiniz.
          </p>
          <button
            className="lumen-btn lumen-btn--primary"
            onClick={() => window.dispatchEvent(new CustomEvent("toggle-chatbot"))}
            style={{ marginInline: "auto", display: "inline-flex" }}
          >
            asistan ile sorgulama yap →
          </button>
        </div>
      </section>
    </>
  );
}
