import React, { useState } from 'react';
import { Outlet, Link, useLocation, useNavigate } from 'react-router-dom';
import { 
  LayoutDashboard, 
  Briefcase, 
  FileText, 
  MessageSquare, 
  Settings,
  LogOut,
  Menu,
  X,
  Scale,
  FolderOpen,
  ExternalLink,
  ChevronLeft,
  ChevronRight,
  Globe,
  Database
} from 'lucide-react';
import { clearAdminKey } from '../../../admin/api/adminClient';

export function AdminLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const location = useLocation();
  const navigate = useNavigate();

  const menuItems = [
    { icon: LayoutDashboard, label: 'Dashboard', path: '/admin/dashboard', badge: 'AI Live' },
    { icon: FolderOpen, label: 'Şirket/Büro/Avukat Belgeleri', path: '/admin/dashboard/documents' },
    { icon: Database, label: 'Corpus Yönetimi', path: '/admin/dashboard/scrape' },
    { icon: Briefcase, label: 'Çalışma Alanları', path: '/admin/dashboard/practice-areas' },
    { icon: FileText, label: 'Blog & İçerik', path: '/admin/dashboard/blog' },
    { icon: MessageSquare, label: 'Müşteri Mesajları', path: '/admin/dashboard/messages' },
    { icon: Settings, label: 'Sistem Ayarları', path: '/admin/dashboard/settings' },
  ];

  const handleLogout = () => {
    clearAdminKey();
    localStorage.removeItem('adminToken'); // eski key temizliği
    navigate('/admin');
  };

  return (
    <div className="admin-shell relative">
      {/* Mobile Backdrop */}
      {sidebarOpen && (
        <div 
          onClick={() => setSidebarOpen(false)}
          className="fixed inset-0 bg-black/40 backdrop-blur-xs z-30 md:hidden transition-opacity"
        />
      )}

      {/* Sidebar */}
      <aside 
        className={`admin-sidebar transition-all duration-300 ${
          sidebarOpen ? 'w-72 translate-x-0' : 'w-20 -translate-x-full md:translate-x-0'
        } flex flex-col justify-between z-40 fixed md:sticky top-0 h-screen shadow-lg`}
      >
        <div>
          {/* Top Branding */}
          <div 
            className="p-5 flex items-center justify-between border-b"
            style={{ borderColor: 'var(--color-rule)' }}
          >
            <div className="flex items-center gap-3.5 overflow-hidden">
              <div 
                className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 transition-transform hover:scale-105"
                style={{
                  backgroundColor: 'color-mix(in oklch, var(--color-accent) 12%, transparent)',
                  border: '1px solid color-mix(in oklch, var(--color-accent) 30%, transparent)',
                }}
              >
                <Scale className="w-5 h-5" style={{ color: 'var(--color-accent)' }} />
              </div>
              {sidebarOpen && (
                <div className="flex flex-col leading-tight">
                  <span className="admin-brand-title text-lg font-normal">LawAgent</span>
                  <span className="admin-eyebrow text-[9.5px]">yönetim paneli</span>
                </div>
              )}
            </div>
            
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="p-1.5 rounded-lg transition-colors cursor-pointer"
              style={{
                backgroundColor: 'var(--color-paper)',
                border: '1px solid var(--color-rule)',
                color: 'var(--color-muted)',
              }}
              title={sidebarOpen ? "Sidebar'ı Daralt" : "Sidebar'ı Genişlet"}
            >
              {sidebarOpen ? <ChevronLeft className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
            </button>
          </div>

          {/* Navigation Menu */}
          <nav className="p-3">
            <ul className="space-y-1">
              {menuItems.map((item) => {
                const Icon = item.icon;
                const isActive = location.pathname === item.path;
                return (
                  <li key={item.path}>
                    <Link
                      to={item.path}
                      onClick={() => {
                        if (window.innerWidth < 768) setSidebarOpen(false);
                      }}
                      className={`admin-nav-link ${isActive ? 'active' : ''}`}
                    >
                      <div className="flex items-center gap-3">
                        <Icon 
                          className="w-4.5 h-4.5 flex-shrink-0 transition-transform group-hover:scale-110" 
                          style={{ color: isActive ? 'var(--color-accent)' : 'inherit' }}
                        />
                        {sidebarOpen && <span className="tracking-normal">{item.label}</span>}
                      </div>

                      {sidebarOpen && item.badge && (
                        <span 
                          className="admin-badge text-[9.5px] py-0.5 px-2"
                          style={{
                            backgroundColor: isActive 
                              ? 'var(--color-accent)' 
                              : 'color-mix(in oklch, var(--color-accent) 14%, transparent)',
                            color: isActive ? '#ffffff' : 'var(--color-accent)',
                            borderColor: 'transparent',
                          }}
                        >
                          {item.badge}
                        </span>
                      )}
                    </Link>
                  </li>
                );
              })}
            </ul>
          </nav>
        </div>

        {/* Sidebar Bottom Footer */}
        <div 
          className="p-4 border-t"
          style={{ borderColor: 'var(--color-rule)' }}
        >
          {sidebarOpen && (
            <div 
              className="mb-3 px-3 py-2.5 rounded-xl flex items-center justify-between"
              style={{
                backgroundColor: 'var(--color-paper)',
                border: '1px solid var(--color-rule-2)',
              }}
            >
              <div className="flex items-center gap-2.5">
                <div 
                  className="w-8 h-8 rounded-lg flex items-center justify-center font-bold text-xs"
                  style={{
                    backgroundColor: 'color-mix(in oklch, var(--color-accent) 15%, transparent)',
                    color: 'var(--color-accent)',
                    border: '1px solid color-mix(in oklch, var(--color-accent) 30%, transparent)',
                    fontFamily: 'var(--font-label)',
                  }}
                >
                  LA
                </div>
                <div className="flex flex-col">
                  <span className="text-xs font-medium" style={{ color: 'var(--color-ink)' }}>Yönetici</span>
                  <span className="text-[10px] font-mono" style={{ color: 'var(--color-muted)' }}>admin@lawagent.ai</span>
                </div>
              </div>
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" title="Sistem Aktif" />
            </div>
          )}

          <div className="flex flex-col gap-1">
            <Link
              to="/"
              className="admin-nav-link text-xs font-medium"
            >
              <div className="flex items-center gap-2.5">
                <Globe className="w-4 h-4 flex-shrink-0" />
                {sidebarOpen && <span>Kamu Sayfası</span>}
              </div>
              {sidebarOpen && <ExternalLink className="w-3 h-3 opacity-60" />}
            </Link>

            <button
              onClick={handleLogout}
              className="admin-nav-link text-xs font-medium cursor-pointer"
              style={{ color: '#ef4444' }}
            >
              <div className="flex items-center gap-2.5">
                <LogOut className="w-4 h-4 flex-shrink-0" />
                {sidebarOpen && <span>Çıkış Yap</span>}
              </div>
            </button>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0">
        <header className="admin-header px-4 md:px-6 py-3.5 sticky top-0 z-20">
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <button
                onClick={() => setSidebarOpen(!sidebarOpen)}
                className="md:hidden p-2 rounded-lg transition-colors cursor-pointer"
                style={{
                  backgroundColor: 'var(--color-paper-2)',
                  border: '1px solid var(--color-rule)',
                  color: 'var(--color-ink)',
                }}
                aria-label="Menüyü Aç/Kapat"
              >
                {sidebarOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
              </button>
              <span 
                className="admin-badge text-[10px] px-2.5 py-1"
                style={{
                  backgroundColor: 'color-mix(in oklch, #10b981 12%, transparent)',
                  color: '#059669',
                  border: '1px solid color-mix(in oklch, #10b981 25%, transparent)',
                }}
              >
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-ping" />
                RAG Motoru Aktif
              </span>
            </div>

            <div className="flex items-center gap-3">
              <Link 
                to="/" 
                target="_blank"
                className="admin-btn-secondary text-xs py-1.5 px-3"
              >
                <span className="hidden sm:inline">Kamu Sayfasını Gör</span>
                <span className="sm:hidden">Site</span>
                <ExternalLink className="w-3.5 h-3.5 opacity-60" />
              </Link>
            </div>
          </div>
        </header>

        <main className="admin-main p-4 sm:p-6 lg:p-8 overflow-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

