import { useEffect } from 'react';
import { Outlet, useLocation } from 'react-router';
import { Navbar } from '../Navbar';
import { Footer } from '../Footer';
import { ChatbotWidget } from '../ChatbotWidget';

function ScrollToTop() {
  const { pathname } = useLocation();

  useEffect(() => {
    window.scrollTo({ top: 0, left: 0, behavior: 'instant' });
  }, [pathname]);

  return null;
}

export function Layout() {
  return (
    <div className="lumen-page" style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <ScrollToTop />
      <Navbar />
      <main style={{ flex: 1 }}>
        <Outlet />
      </main>
      <Footer />
      <ChatbotWidget />
    </div>
  );
}
