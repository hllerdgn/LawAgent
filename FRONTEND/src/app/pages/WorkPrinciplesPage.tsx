import React from "react";
import { Link } from "react-router-dom";

const PRINCIPLES = [
  {
    code: "01",
    label: "01 · ETİK VE DOĞRULUK",
    title: "etik & doğruluk",
    body: "avukatlık meslek kurallarına ve mevzuat ruhuna %100 sadakat gösteriyor, uydurma (halüsinatif) bilgilere kesinlikle geçit vermiyoruz.",
  },
  {
    code: "02",
    label: "02 · ŞEFFAFLIK",
    title: "şeffaf veri kaynağı",
    body: "sistem tarafından üretilen her yanıtın arkasındaki kanun fıkrası ve vektörel kaynak kullanıcıya şeffafça gösterilir.",
  },
  {
    code: "03",
    label: "03 · PERFORMANS",
    title: "yüksek performans",
    body: "qdrant vektör indeksleme ile milisaniyeler düzeyinde en ilgili hukuki metin parçaları getirilir.",
  },
  {
    code: "04",
    label: "04 · GİZLİLİK",
    title: "kvkk & veri güvenliği",
    body: "kullanıcılardan gelen sorular ve oturum verileri anonimleştirilir, kvkk standartlarında güvenle işlenir.",
  },
];

const COMMITMENTS = [
  { label: "MEVZUAT DOĞRULUĞU GÜVENCESİ", text: "üretilen tüm yanıtlar ilgili kanun fıkrasına atıfta bulunur, rastgele çıkarımlardan kaçınır." },
  { label: "KESİNTİSİZ ERİŞİLEBİLİRLİK", text: "7/24 aktif bulut altyapısı sayesinde hukuki araştırma süreçlerinizi her an destekler." },
  { label: "TAM GİZLİLİK KORUMASI", text: "sisteme iletilen hukuki soru metinleri hiçbir dış modele veya üçüncü şahsa iletilmez." },
];

export function WorkPrinciplesPage() {
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
        aria-labelledby="principles-title"
      >
        <div className="lumen-shell">
          <span className="eyebrow" style={{ display: "block", marginBottom: "var(--space-4)" }}>
            00 · ilkelerimiz ve standartlarımız
          </span>
          <h1
            id="principles-title"
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
            çalışma <em style={{ fontStyle: "normal", color: "var(--color-accent-2)" }}>prensiplerimiz</em>.
          </h1>
          <p style={{
            marginTop: "var(--space-6)",
            fontSize: "var(--text-lg)",
            color: "var(--color-ink-2)",
            lineHeight: "var(--leading-normal)",
            maxWidth: "52ch",
          }}>
            lawagent ai, hukuki bilginin güvenilirliğini ve etik ilkelerini en üst
            seviyede tutacak standartlarla inşa edilmiştir.
          </p>
        </div>
      </section>

      {/* Principles Grid */}
      <section className="lumen-section" aria-labelledby="cards-title">
        <div className="lumen-shell">
          <header className="lumen-section__head">
            <span className="eyebrow">01 · temel standartlar</span>
            <h2 id="cards-title" className="lumen-section__title">
              dört temel <em style={{ fontStyle: "normal", color: "var(--color-accent-2)" }}>prensip</em>.
            </h2>
          </header>

          <div className="lumen-cards" role="list">
            {PRINCIPLES.map((p) => (
              <div key={p.code} className="lumen-card" role="listitem">
                <span className="lumen-card__eyebrow">{p.label}</span>
                <h3 className="lumen-card__title">{p.title}</h3>
                <p className="lumen-card__body">{p.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Commitments List */}
      <section
        className="lumen-section"
        style={{ borderTop: "1px solid var(--color-rule)" }}
        aria-labelledby="commitments-title"
      >
        <div className="lumen-shell">
          <header className="lumen-section__head">
            <span className="eyebrow">02 · taahhütlerimiz</span>
            <h2 id="commitments-title" className="lumen-section__title">
              kullanıcılarımıza <em style={{ fontStyle: "normal", color: "var(--color-accent-2)" }}>taahhütlerimiz</em>.
            </h2>
          </header>

          <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-4)" }}>
            {COMMITMENTS.map((c, i) => (
              <div
                key={i}
                style={{
                  background: "var(--color-paper-2)",
                  border: "1px solid var(--color-rule)",
                  borderLeft: "3px solid var(--color-accent)",
                  padding: "var(--space-6)",
                  borderRadius: "var(--radius-md)",
                }}
              >
                <span style={{
                  fontFamily: "var(--font-label)",
                  fontSize: "10px",
                  letterSpacing: "0.10em",
                  textTransform: "uppercase",
                  color: "var(--color-accent)",
                  display: "block",
                  marginBottom: "var(--space-2)",
                }}>
                  {c.label}
                </span>
                <p style={{
                  fontSize: "var(--text-sm)",
                  color: "var(--color-ink)",
                  lineHeight: "var(--leading-normal)",
                }}>
                  {c.text}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="lumen-cta" style={{ borderTop: "1px solid var(--color-rule)" }}>
        <div className="lumen-shell">
          <span className="eyebrow" style={{ display: "block", marginBottom: "var(--space-5)" }}>
            03 · soru sorun
          </span>
          <h2 className="lumen-cta__title">
            asistanı <em>deneyin</em>.
          </h2>
          <p className="lumen-cta__sub">
            etik ve şeffaf rag mimarisi ile sorularınızı hemen sorun.
          </p>
          <button
            className="lumen-btn lumen-btn--primary"
            onClick={() => window.dispatchEvent(new CustomEvent("toggle-chatbot"))}
            style={{ marginInline: "auto", display: "inline-flex" }}
          >
            asistanı başlat →
          </button>
        </div>
      </section>
    </>
  );
}
