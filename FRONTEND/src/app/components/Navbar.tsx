import React, { useState } from "react";
import { Link, useLocation } from "react-router-dom";

const NAV_LINKS = [
  { label: "uygulama alanları", path: "/practice-areas" },
  { label: "hakkında", path: "/about" },
  { label: "makaleler", path: "/blog" },
  { label: "çalışma ilkeleri", path: "/work-principles" },
  { label: "iletişim", path: "/contact" },
];

export function Navbar() {
  const [open, setOpen] = useState(false);
  const location = useLocation();

  const [siteName, setSiteName] = useState(() => {
    return localStorage.getItem('lawagent_site_name') || 'lawagent';
  });

  React.useEffect(() => {
    const handleUpdate = () => {
      const saved = localStorage.getItem('lawagent_site_name');
      if (saved) setSiteName(saved);
    };
    window.addEventListener('storage', handleUpdate);
    window.addEventListener('lawagent_settings_updated', handleUpdate);
    return () => {
      window.removeEventListener('storage', handleUpdate);
      window.removeEventListener('lawagent_settings_updated', handleUpdate);
    };
  }, []);

  return (
    <header className="lumen-nav" role="banner">
      <div className="lumen-shell lumen-nav__inner">
        {/* Brand wordmark */}
        <Link to="/" className="lumen-nav__brand" aria-label="LawAgent ana sayfa">
          {siteName.toLowerCase()}
          <span
            style={{
              fontFamily: "var(--font-label)",
              fontSize: "9px",
              letterSpacing: "0.10em",
              textTransform: "uppercase",
              color: "var(--color-accent)",
              marginLeft: "8px",
              verticalAlign: "middle",
              opacity: 0.8,
            }}
          >
            ai asistan
          </span>
        </Link>

        {/* Desktop links */}
        <ul className="lumen-nav__links" role="list">
          {NAV_LINKS.map((item) => {
            const active = location.pathname === item.path;
            return (
              <li key={item.path}>
                <Link
                  to={item.path}
                  aria-current={active ? "page" : undefined}
                  style={active ? { color: "var(--color-accent)" } : undefined}
                >
                  {item.label}
                </Link>
              </li>
            );
          })}
        </ul>

        {/* Right cluster: CTA */}
        <div style={{ display: "flex", alignItems: "center", gap: "var(--space-4)" }}>
          <button
            className="lumen-nav__cta"
            onClick={() => window.dispatchEvent(new CustomEvent("toggle-chatbot"))}
            aria-label="yapay zeka asistanını başlat"
          >
            asistanı başlat →
          </button>
          {/* Mobile hamburger */}
          <button
            className="lumen-hamburger"
            onClick={() => setOpen(!open)}
            aria-label={open ? "menüyü kapat" : "menüyü aç"}
            aria-expanded={open}
            style={{
              display: "none",
              background: "none",
              border: "none",
              cursor: "pointer",
              padding: "8px",
              color: "var(--color-ink)",
            }}
          >
            {open ? "✕" : "☰"}
          </button>
        </div>
      </div>

      {/* Mobile drawer */}
      {open && (
        <div
          style={{
            borderTop: "1px solid var(--color-rule)",
            background: "var(--color-paper)",
            padding: "var(--space-5) var(--gutter) var(--space-6)",
          }}
          role="navigation"
          aria-label="mobil gezinme"
        >
          <ul style={{ listStyle: "none", display: "flex", flexDirection: "column", gap: "var(--space-3)" }}>
            {NAV_LINKS.map((item) => (
              <li key={item.path}>
                <Link
                  to={item.path}
                  onClick={() => setOpen(false)}
                  style={{
                    fontFamily: "var(--font-body)",
                    fontSize: "var(--text-md)",
                    color: location.pathname === item.path ? "var(--color-accent)" : "var(--color-ink-2)",
                    textDecoration: "none",
                    textTransform: "lowercase",
                    display: "block",
                    padding: "var(--space-3) 0",
                    borderBottom: "1px solid var(--color-rule-2)",
                  }}
                >
                  {item.label}
                </Link>
              </li>
            ))}
          </ul>
          <button
            className="lumen-btn lumen-btn--primary"
            onClick={() => {
              setOpen(false);
              window.dispatchEvent(new CustomEvent("toggle-chatbot"));
            }}
            style={{ marginTop: "var(--space-5)", width: "100%", justifyContent: "center" }}
          >
            asistanı başlat →
          </button>
        </div>
      )}
    </header>
  );
}
