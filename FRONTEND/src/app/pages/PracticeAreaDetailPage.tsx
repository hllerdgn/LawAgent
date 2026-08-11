import React from "react";
import { Link, useParams } from "react-router-dom";

export function PracticeAreaDetailPage() {
  const { slug } = useParams();

  const practiceAreaData: Record<string, any> = {
    "ticaret-hukuku": {
      title: "türk ticaret kanunu (ttk)",
      subtitle: "01 · 6102 SAYILI TÜRK TİCARET KANUNU",
      description: "ticari şirketlerin kuruluşu, birleşme/devralma süreçleri, haksız rekabet uyuşmazlıkları ve kambiyo senetleri hukuku.",
      services: [
        "şirket kuruluşu, esas sözleşme hazırlığı ve tür değişikliği",
        "şirket birleşme, devralma ve bölünme işlemleri",
        "ticari sözleşmelerin hazırlanması, revizyonu ve risk analizi",
        "ticari uyuşmazlıkların arabuluculuk ve dava yoluyla çözümü",
        "haksız rekabet ve fikri mülkiyet danışmanlığı",
        "kambiyo senetlerine (çek, poliçe, bono) dayalı alacak takibi",
      ],
    },
    "is-hukuku": {
      title: "iş ve sosyal güvenlik hukuku",
      subtitle: "02 · 4857 SAYILI İŞ KANUNU & TBK",
      description: "işçi ve işveren haklarının korunması, fesih bildirimleri, kıdem/ihbar tazminatları ve iş sağlığı güvenliği.",
      services: [
        "belirsiz ve belirli süreli iş sözleşmelerinin hazırlanması",
        "işe iade, kıdem, ihbar ve fazla mesai alacağı davaları",
        "mobbing, psikolojik taciz ve ayrımcılık iddiaları",
        "iş kazası ve meslek hastalığı tazminat süreçleri",
        "zorunlu arabuluculuk müzakerelerinde temsil",
        "sgk idari para cezalarına ve prim uyuşmazlıklarına itiraz",
      ],
    },
    "tuketici-hukuku": {
      title: "tüketici hukuku",
      subtitle: "03 · 6502 SAYILI TKHK KAPSAMI",
      description: "tüketicinin korunması, ayıplı mal ve hizmet uyuşmazlıkları, cayma hakkı ve mesafeli satış hukuku.",
      services: [
        "ayıplı mal ve ayıplı hizmetten kaynaklı bedel iadesi talepleri",
        "tüketici hakem heyeti başvurusu ve karar takibi",
        "tüketici mahkemelerinde dava takibi ve savunma",
        "mesafeli satış ve e-ticaret sözleşmeleri danışmanlığı",
        "finansal ve bankacılık ürünlerinden kaynaklı tüketici uyuşmazlıkları",
        "abonelik sözleşmeleri ve haksız şart iddiaları",
      ],
    },
  };

  const data = practiceAreaData[slug || ""] || {
    title: "çalışma alanı detayı",
    subtitle: "00 · MEVZUAT BİLGİLENDİRMESİ",
    description: "bu uzmanlık alanında lawagent ai destekli hukuki rehberlik sunulmaktadır.",
    services: [
      "hukuki danışmanlık ve sözleşme incelemesi",
      "mevzuat maddelerine dayalı analiz ve raporlama",
    ],
  };

  return (
    <>
      {/* Hero Banner */}
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
        aria-labelledby="detail-title"
      >
        <div className="lumen-shell">
          <Link
            to="/practice-areas"
            style={{
              fontFamily: "var(--font-label)",
              fontSize: "11px",
              letterSpacing: "0.10em",
              textTransform: "uppercase",
              color: "var(--color-accent)",
              textDecoration: "none",
              display: "inline-block",
              marginBottom: "var(--space-5)",
            }}
          >
            ← uygulama alanlarına dön
          </Link>
          <span className="eyebrow" style={{ display: "block", marginBottom: "var(--space-4)" }}>
            {data.subtitle}
          </span>
          <h1
            id="detail-title"
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
            {data.title}.
          </h1>
          <p style={{
            marginTop: "var(--space-6)",
            fontSize: "var(--text-lg)",
            color: "var(--color-ink-2)",
            lineHeight: "var(--leading-normal)",
            maxWidth: "52ch",
          }}>
            {data.description}
          </p>
        </div>
      </section>

      {/* Services List */}
      <section className="lumen-section" aria-labelledby="services-title">
        <div className="lumen-shell">
          <header className="lumen-section__head">
            <span className="eyebrow">01 · hukuki konular</span>
            <h2 id="services-title" className="lumen-section__title">
              kapsanan <em style={{ fontStyle: "normal", color: "var(--color-accent-2)" }}>konular</em>.
            </h2>
          </header>

          <div style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 320px), 1fr))",
            gap: "var(--space-4)",
          }}>
            {data.services.map((service: string, index: number) => (
              <div
                key={index}
                className="lumen-card"
                style={{ padding: "var(--space-5)" }}
              >
                <span className="lumen-card__eyebrow">0{index + 1} · HİZMET</span>
                <p style={{
                  fontSize: "var(--text-sm)",
                  color: "var(--color-ink)",
                  lineHeight: "var(--leading-normal)",
                }}>
                  {service}
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
            02 · ai destekli analiz
          </span>
          <h2 className="lumen-cta__title">
            {data.title} hakkında <em>sorun</em>.
          </h2>
          <p className="lumen-cta__sub">
            lawagent ai, bu konudaki sorularınızı mevzuat maddeleriyle birlikte anında yanıtlar.
          </p>
          <button
            className="lumen-btn lumen-btn--primary"
            onClick={() => window.dispatchEvent(new CustomEvent("toggle-chatbot"))}
            style={{ marginInline: "auto", display: "inline-flex" }}
          >
            asistan ile soru sor →
          </button>
        </div>
      </section>
    </>
  );
}
