import React from "react";
import { Link } from "react-router-dom";

const BLOG_POSTS = [
  {
    title: "ticaret hukukunda sık karşılaşılan uyuşmazlıklar ve çözüm yolları",
    slug: "ticaret-hukukunda-sik-karsilasilan-sorunlar",
    excerpt: "6102 sayılı türk ticaret kanunu çerçevesinde şirket ortakları uyuşmazlıkları, ticari alacak tahsili ve sözleşme ihlalleri hakkında rehber.",
    date: "15 ocak 2025",
    readTime: "5 dk",
    category: "TTK · TİCARET",
  },
  {
    title: "iş sözleşmesi feshi ve kıdem tazminatı hakları",
    slug: "is-sozlesmesi-feshi-haklarinizi-bilin",
    excerpt: "işçinin ve işverenin 4857 sayılı iş kanunu kapsamındaki hakları, fesih bildirimi süreleri ve arabuluculuk başvuru adımları.",
    date: "10 ocak 2025",
    readTime: "6 dk",
    category: "TBK · İŞ",
  },
  {
    title: "6502 sayılı tkhk kapsamında tüketici hakları rehberi",
    slug: "tuketici-haklarinda-yeni-duzenlemeler",
    excerpt: "ayıplı mal iadesi, mesafeli satış cayma hakkı ve tüketici hakem heyetlerine e-devlet üzerinden başvuru yöntemleri.",
    date: "5 ocak 2025",
    readTime: "4 dk",
    category: "TKHK · TÜKETİCİ",
  },
];

export function BlogPage() {
  const DEFAULT_POSTS = [
    {
      title: "ticaret hukukunda sık karşılaşılan uyuşmazlıklar ve çözüm yolları",
      slug: "ticaret-hukukunda-sik-karsilasilan-sorunlar",
      excerpt: "6102 sayılı türk ticaret kanunu çerçevesinde şirket ortakları uyuşmazlıkları, ticari alacak tahsili ve sözleşme ihlalleri hakkında rehber.",
      date: "15 ocak 2025",
      readTime: "5 dk",
      category: "TTK · TİCARET",
    },
    {
      title: "iş sözleşmesi feshi ve kıdem tazminatı hakları",
      slug: "is-sozlesmesi-feshi-haklarinizi-bilin",
      excerpt: "işçinin ve işverenin 4857 sayılı iş kanunu kapsamındaki hakları, fesih bildirimi süreleri ve arabuluculuk başvuru adımları.",
      date: "10 ocak 2025",
      readTime: "6 dk",
      category: "TBK · İŞ",
    },
    {
      title: "6502 sayılı tkhk kapsamında tüketici hakları rehberi",
      slug: "tuketici-haklarinda-yeni-duzenlemeler",
      excerpt: "ayıplı mal iadesi, mesafeli satış cayma hakkı ve tüketici hakem heyetlerine e-devlet üzerinden başvuru yöntemleri.",
      date: "5 ocak 2025",
      readTime: "4 dk",
      category: "TKHK · TÜKETİCİ",
    },
  ];

  const [posts, setPosts] = React.useState(() => {
    try {
      const saved = localStorage.getItem('lawagent_blog_posts');
      if (saved) {
        const parsed = JSON.parse(saved);
        return parsed.map((p: any) => ({
          title: p.title.toLowerCase(),
          slug: p.slug || p.title.toLowerCase().replace(/\s+/g, '-'),
          excerpt: p.title + ' hakkında detaylı hukuki inceleme ve mevzuat analiz raporu.',
          date: p.date || 'Bugün',
          readTime: '5 dk',
          category: p.status === 'Yayında' ? 'MEVZUAT · İNCELEME' : 'TASLAK · REHBER',
        }));
      }
    } catch (e) {}
    return DEFAULT_POSTS;
  });

  React.useEffect(() => {
    const handleUpdate = () => {
      try {
        const saved = localStorage.getItem('lawagent_blog_posts');
        if (saved) {
          const parsed = JSON.parse(saved);
          setPosts(parsed.map((p: any) => ({
            title: p.title.toLowerCase(),
            slug: p.slug || p.title.toLowerCase().replace(/\s+/g, '-'),
            excerpt: p.title + ' hakkında detaylı hukuki inceleme ve mevzuat analiz raporu.',
            date: p.date || 'Bugün',
            readTime: '5 dk',
            category: p.status === 'Yayında' ? 'MEVZUAT · İNCELEME' : 'TASLAK · REHBER',
          })));
        }
      } catch (e) {}
    };
    window.addEventListener('storage', handleUpdate);
    window.addEventListener('lawagent_blog_updated', handleUpdate);
    return () => {
      window.removeEventListener('storage', handleUpdate);
      window.removeEventListener('lawagent_blog_updated', handleUpdate);
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
            var(--color-paper)
          `,
          paddingTop: "var(--space-12)",
          paddingBottom: "var(--space-10)",
          borderBottom: "1px solid var(--color-rule)",
        }}
        aria-labelledby="blog-title"
      >
        <div className="lumen-shell">
          <span className="eyebrow" style={{ display: "block", marginBottom: "var(--space-4)" }}>
            00 · hukuki içerik ve içtihat
          </span>
          <h1
            id="blog-title"
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
            hukuki makaleler ve{" "}
            <em style={{ fontStyle: "normal", color: "var(--color-accent-2)" }}>incelemeler</em>.
          </h1>
          <p style={{
            marginTop: "var(--space-6)",
            fontSize: "var(--text-lg)",
            color: "var(--color-ink-2)",
            lineHeight: "var(--leading-normal)",
            maxWidth: "52ch",
          }}>
            güncel mevzuat değişiklikleri, emsal mahkeme kararları ve pratik hukuki
            bilgilendirme yazıları.
          </p>
        </div>
      </section>

      {/* Blog feed */}
      <section className="lumen-section" aria-labelledby="posts-title">
        <div className="lumen-shell">
          <header className="lumen-section__head">
            <span className="eyebrow">01 · son makaleler</span>
            <h2 id="posts-title" className="lumen-section__title" style={{ display: "none" }}>
              son makaleler
            </h2>
          </header>

          <div style={{ display: "flex", flexDirection: "column", gap: "1px", borderTop: "1px solid var(--color-rule)" }}>
            {posts.map((post) => (
              <Link
                key={post.slug}
                to={`/blog/${post.slug}`}
                style={{ textDecoration: "none", color: "inherit" }}
              >
                <article
                  style={{
                    display: "grid",
                    gridTemplateColumns: "auto 1fr auto",
                    gap: "var(--space-7)",
                    alignItems: "center",
                    padding: "var(--space-6) 0",
                    borderBottom: "1px solid var(--color-rule-2)",
                    transition: "background 150ms ease",
                  }}
                  onMouseEnter={e => (e.currentTarget.style.background = "oklch(94% 0.010 265)")}
                  onMouseLeave={e => (e.currentTarget.style.background = "transparent")}
                >
                  {/* Category tag */}
                  <span style={{
                    fontFamily: "var(--font-label)",
                    fontSize: "10px",
                    letterSpacing: "0.10em",
                    textTransform: "uppercase",
                    color: "var(--color-accent)",
                    whiteSpace: "nowrap",
                    minWidth: "120px",
                  }}>
                    {post.category}
                  </span>

                  {/* Content */}
                  <div>
                    <h3 style={{
                      fontFamily: "var(--font-display)",
                      fontWeight: 400,
                      fontSize: "var(--text-2xl)",
                      lineHeight: "var(--leading-snug)",
                      letterSpacing: "var(--tracking-display)",
                      color: "var(--color-ink)",
                      marginBottom: "var(--space-2)",
                    }}>
                      {post.title}
                    </h3>
                    <p style={{
                      fontSize: "var(--text-sm)",
                      color: "var(--color-ink-2)",
                      lineHeight: "var(--leading-normal)",
                      maxWidth: "60ch",
                    }}>
                      {post.excerpt}
                    </p>
                  </div>

                  {/* Meta */}
                  <div style={{
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "flex-end",
                    gap: "var(--space-2)",
                    whiteSpace: "nowrap",
                  }}>
                    <span style={{
                      fontFamily: "var(--font-label)",
                      fontSize: "10px",
                      letterSpacing: "0.08em",
                      textTransform: "uppercase",
                      color: "var(--color-muted)",
                    }}>
                      {post.date}
                    </span>
                    <span style={{
                      fontFamily: "var(--font-label)",
                      fontSize: "10px",
                      letterSpacing: "0.08em",
                      textTransform: "uppercase",
                      color: "var(--color-muted)",
                    }}>
                      {post.readTime} okuma
                    </span>
                    <span style={{ color: "var(--color-accent)", fontSize: "var(--text-sm)" }}>→</span>
                  </div>
                </article>
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="lumen-cta" style={{ borderTop: "1px solid var(--color-rule)" }}>
        <div className="lumen-shell">
          <span className="eyebrow" style={{ display: "block", marginBottom: "var(--space-5)" }}>
            02 · mevzuat soruları
          </span>
          <h2 className="lumen-cta__title">
            makalede geçen kanunları <em>sorgulayın</em>.
          </h2>
          <p className="lumen-cta__sub">
            rag v2 mimarisi, ilgili kanun maddesini bağlam içinde bulur ve yanıtlar.
          </p>
          <button
            className="lumen-btn lumen-btn--primary"
            onClick={() => window.dispatchEvent(new CustomEvent("toggle-chatbot"))}
            style={{ marginInline: "auto", display: "inline-flex" }}
          >
            asistana sor →
          </button>
        </div>
      </section>
    </>
  );
}
