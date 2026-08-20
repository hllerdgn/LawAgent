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
  FileUp,
  ExternalLink,
  ChevronLeft,
  ChevronRight,
  Globe
} from 'lucide-react';

export function AdminLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const location = useLocation();
  const navigate = useNavigate();

  const menuItems = [
    { icon: LayoutDashboard, label: 'Dashboard', path: '/admin/dashboard', badge: 'AI Live' },
    { icon: FileUp, label: 'RAG Doküman Yönetimi', path: '/admin/dashboard/documents' },
    { icon: Briefcase, label: 'Çalışma Alanları', path: '/admin/dashboard/practice-areas' },
    { icon: FileText, label: 'Blog & İçerik', path: '/admin/dashboard/blog' },
    { icon: MessageSquare, label: 'Müşteri Mesajları', path: '/admin/dashboard/messages' },
    { icon: Settings, label: 'Sistem Ayarları', path: '/admin/dashboard/settings' },
  ];

  const handleLogout = () => {
    localStorage.removeItem('adminToken');
    navigate('/admin');
  };

  return (
    <div className="min-h-screen bg-slate-100 flex font-sans antialiased text-slate-900 relative overflow-x-hidden">
      {/* Mobile Backdrop */}
      {sidebarOpen && (
        <div 
          onClick={() => setSidebarOpen(false)}
          className="fixed inset-0 bg-slate-950/60 backdrop-blur-xs z-30 md:hidden transition-opacity"
        />
      )}

      {/* Sidebar */}
      <aside 
        className={`bg-slate-950 text-slate-200 border-r border-slate-800 transition-all duration-300 ${
          sidebarOpen ? 'w-72 translate-x-0' : 'w-20 -translate-x-full md:translate-x-0'
        } flex flex-col justify-between z-40 shadow-2xl fixed md:sticky top-0 h-screen`}
      >
        <div>
          {/* Top Branding */}
          <div className="p-5 border-b border-slate-800/80 flex items-center justify-between">
            <div className="flex items-center gap-3.5 overflow-hidden">
              <div className="w-10 h-10 bg-amber-500/10 border border-amber-500/30 rounded-xl flex items-center justify-center flex-shrink-0 shadow-md">
                <Scale className="w-5 h-5 text-amber-400" />
              </div>
              {sidebarOpen && (
                <div className="flex flex-col leading-tight">
                  <span className="text-white text-base font-bold font-serif tracking-tight">LawAgent</span>
                  <span className="text-amber-400 text-xs font-semibold">Admin SaaS Portalı</span>
                </div>
              )}
            </div>
            
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="p-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-white transition-colors border border-slate-800"
              title={sidebarOpen ? "Sidebar'ı Daralt" : "Sidebar'ı Genişlet"}
            >
              {sidebarOpen ? <ChevronLeft className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
            </button>
          </div>

          {/* Navigation Menu */}
          <nav className="p-3">
            <ul className="space-y-1.5">
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
                      className={`flex items-center justify-between px-3.5 py-3 rounded-xl transition-all duration-200 group ${
                        isActive
                          ? 'bg-amber-500/15 text-amber-400 font-semibold border border-amber-500/30 shadow-sm'
                          : 'text-slate-400 hover:bg-slate-900 hover:text-slate-100'
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        <Icon className={`w-5 h-5 flex-shrink-0 transition-transform group-hover:scale-110 ${
                          isActive ? 'text-amber-400' : 'text-slate-400 group-hover:text-amber-400'
                        }`} />
                        {sidebarOpen && <span className="text-sm tracking-wide">{item.label}</span>}
                      </div>

                      {sidebarOpen && item.badge && (
                        <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                          isActive ? 'bg-amber-400 text-slate-950' : 'bg-slate-800 text-amber-400'
                        }`}>
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
        <div className="p-4 border-t border-slate-800/80 bg-slate-900/40">
          {sidebarOpen && (
            <div className="mb-3 px-3 py-2 bg-slate-900 rounded-xl border border-slate-800 flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-amber-500/20 border border-amber-500/40 flex items-center justify-center font-bold text-amber-400 text-xs">
                  LA
                </div>
                <div className="flex flex-col">
                  <span className="text-xs font-semibold text-white">Yönetici Paneli</span>
                  <span className="text-[10px] text-slate-400">admin@lawagent.ai</span>
                </div>
              </div>
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" title="Sistem Aktif" />
            </div>
          )}

          <div className="flex flex-col gap-1">
            <Link
              to="/"
              className="flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-slate-400 hover:bg-slate-900 hover:text-slate-200 transition-colors text-sm font-medium"
            >
              <Globe className="w-4 h-4 flex-shrink-0" />
              {sidebarOpen && <span>Ana Siteye Dön</span>}
            </Link>

            <button
              onClick={handleLogout}
              className="flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-red-400 hover:bg-red-500/10 hover:text-red-300 transition-colors w-full text-sm font-medium cursor-pointer"
            >
              <LogOut className="w-4 h-4 flex-shrink-0" />
              {sidebarOpen && <span>Çıkış Yap</span>}
            </button>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0">
        <header className="bg-white border-b border-slate-200/80 px-4 md:px-6 py-4 sticky top-0 z-20 shadow-xs">
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <button
                onClick={() => setSidebarOpen(!sidebarOpen)}
                className="md:hidden p-2 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 transition-colors border border-slate-200"
                aria-label="Menüyü Aç/Kapat"
              >
                {sidebarOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
              </button>
              <span className="text-xs font-semibold text-emerald-600 bg-emerald-50 px-2.5 py-1 rounded-md border border-emerald-200 flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-ping" />
                RAG Motoru Aktif
              </span>
            </div>

            <div className="flex items-center gap-3">
              <Link 
                to="/" 
                target="_blank"
                className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-600 hover:text-slate-900 hover:bg-slate-100 px-3 py-2 rounded-lg transition-colors border border-slate-200/60"
              >
                <span className="hidden sm:inline">Kamu Sayfasını Gör</span>
                <span className="sm:hidden">Site</span>
                <ExternalLink className="w-3.5 h-3.5 text-slate-400" />
              </Link>
            </div>
          </div>
        </header>

        <main className="flex-1 p-4 sm:p-6 lg:p-8 overflow-auto bg-slate-50">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
