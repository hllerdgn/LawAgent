import { Link } from "react-router-dom";
import { useSiteName } from '../hooks/useSiteName';

export function Footer() {
  const year = new Date().getFullYear();
  const siteName = useSiteName();

  return (
    <footer className="lumen-footer" role="contentinfo">
      <div className="lumen-shell">
        <div className="lumen-footer__inner">
          {/* Brand */}
          <div>
            <div className="lumen-footer__brand">{siteName.toLowerCase()}</div>
            <p className="lumen-footer__tagline">
              türk hukuku için tasarlanmış yapay zeka hukuk asistanı.
              rag v2 mimarisi ile mevzuat kaynaklı yanıtlar.
            </p>
            <p
              style={{
                marginTop: "var(--space-5)",
                fontFamily: "var(--font-label)",
                fontSize: "9px",
                letterSpacing: "0.10em",
                textTransform: "uppercase",
                color: "var(--color-muted)",
                lineHeight: 1.6,
              }}
            >
              kvkk uyumlu · veri paylaşımı yok
            </p>
          </div>

          {/* Mevzuat */}
          <div>
            <p className="lumen-footer__col-head">mevzuat</p>
            <ul className="lumen-footer__links">
              <li><Link to="/practice-areas/is-hukuku">iş hukuku (tbk)</Link></li>
              <li><Link to="/practice-areas/ticaret-hukuku">ticaret hukuku (ttk)</Link></li>
              <li><Link to="/practice-areas/tuketici-hukuku">tüketici hukuku (tkhk)</Link></li>
              <li><Link to="/practice-areas">tüm uygulama alanları</Link></li>
            </ul>
          </div>

          {/* Platform */}
          <div>
            <p className="lumen-footer__col-head">platform</p>
            <ul className="lumen-footer__links">
              <li><Link to="/about">hakkında</Link></li>
              <li><Link to="/work-principles">çalışma ilkeleri</Link></li>
              <li><Link to="/blog">hukuki makaleler</Link></li>
              <li><Link to="/contact">iletişim</Link></li>
            </ul>
          </div>

          {/* Hukuki */}
          <div>
            <p className="lumen-footer__col-head">hukuki</p>
            <ul className="lumen-footer__links">
              <li><a href="#">kvkk aydınlatma metni</a></li>
              <li><a href="#">gizlilik politikası</a></li>
              <li><a href="#">çerez politikası</a></li>
              <li><a href="#">kullanım koşulları</a></li>
            </ul>
          </div>
        </div>

        <div className="lumen-footer__bottom">
          <span>© {year} lawagent · ai karar destek platformu</span>
          <span>fastapi · llama-3 · rag v2 · qdrant</span>
        </div>
      </div>
    </footer>
  );
}
