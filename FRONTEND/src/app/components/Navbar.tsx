import React, { useState } from "react";
import { Link, useLocation } from "react-router";
import { Button } from "./Button";
import { Scale, Menu, X, Phone, BookOpen, Sparkles } from "lucide-react";

export function Navbar() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const location = useLocation();

  const menuItems = [
    { label: "Ana Sayfa", path: "/" },
    { label: "Proje Hakkında", path: "/about" },
    { label: "Kapsam", path: "/practice-areas" },
    { label: "Blog", path: "/blog" },
    { label: "İletişim", path: "/contact" },
  ];

  return (
    <nav className="bg-white/95 backdrop-blur-md border-b border-gray-200 sticky top-0 z-50 shadow-sm hover:shadow-md transition-shadow">
      <div className="max-w-[1440px] mx-auto px-6 lg:px-24">
        <div className="flex items-center justify-between h-24">
          <Link to="/" className="flex items-center gap-4 group">
            <div className="relative w-14 h-14 bg-gradient-to-br from-[#1e3a5f] to-[#152b47] rounded-xl flex items-center justify-center shadow-lg group-hover:shadow-xl transition-all duration-300">
              <Scale className="w-7 h-7 text-[#D4A574]" strokeWidth={2.5} />
              <BookOpen
                className="w-4 h-4 text-[#D4A574] absolute bottom-2 right-2 opacity-70"
                strokeWidth={2}
              />
            </div>
            <div className="hidden lg:flex flex-col leading-tight">
              <span className="text-[#1e3a5f] text-2xl font-bold tracking-tight">
                LawAgent
              </span>
              <span className="text-[#D4A574] text-sm font-medium tracking-wide">
                Yapay Zeka Asistanı
              </span>
            </div>
          </Link>
          <div className="hidden lg:flex items-center gap-10">
            {menuItems.map((item) => (
              <Link
                key={item.path}
                to={item.path}
                className={`text-sm font-medium transition-all duration-200 px-3 py-2 rounded-lg ${
                  location.pathname === item.path
                    ? "text-[#1e3a5f] bg-[#D4A574]/10"
                    : "text-gray-600 hover:text-[#1e3a5f] hover:bg-gray-50"
                }`}
              >
                {item.label}
              </Link>
            ))}
          </div>
          <div className="hidden lg:flex items-center gap-3">
            <button
              onClick={() => {
                window.dispatchEvent(new CustomEvent("toggle-chatbot"));
              }}
              className="inline-flex items-center justify-center gap-2 bg-gradient-to-r from-[#1e3a5f] to-[#152b47] hover:shadow-lg hover:scale-105 text-white transition-all duration-300 px-6 py-2.5 rounded-lg text-sm font-medium group"
            >
              <Sparkles className="w-4 h-4 group-hover:rotate-12 transition-transform" />
              Asistanı Başlat
            </button>
          </div>
          <button
            className="lg:hidden p-2 hover:bg-gray-100 rounded-lg transition-colors"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            aria-label="Menu"
          >
            {mobileMenuOpen ? (
              <X className="w-6 h-6 text-[#1e3a5f]" />
            ) : (
              <Menu className="w-6 h-6 text-[#1e3a5f]" />
            )}
          </button>
        </div>
        {mobileMenuOpen && (
          <div className="lg:hidden pb-6 pt-2 flex flex-col gap-3 animate-fadeIn">
            {menuItems.map((item) => (
              <Link
                key={item.path}
                to={item.path}
                onClick={() => setMobileMenuOpen(false)}
                className={`transition-all text-left py-3 px-4 rounded-lg ${
                  location.pathname === item.path
                    ? "text-[#1e3a5f] font-semibold bg-[#D4A574]/10"
                    : "text-gray-600 hover:text-[#1e3a5f] hover:bg-gray-50"
                }`}
              >
                {item.label}
              </Link>
            ))}
            <div className="flex flex-col gap-3 pt-4 mt-2 border-t border-gray-200">
              <button
                onClick={() => {
                  setMobileMenuOpen(false);
                  window.dispatchEvent(new CustomEvent("toggle-chatbot"));
                }}
                className="w-full bg-gradient-to-r from-[#1e3a5f] to-[#152b47] text-white flex items-center justify-center gap-2 py-3 rounded-lg text-sm font-medium"
              >
                <Sparkles className="w-4 h-4" />
                Asistanı Başlat
              </button>
            </div>
          </div>
        )}
      </div>
    </nav>
  );
}

