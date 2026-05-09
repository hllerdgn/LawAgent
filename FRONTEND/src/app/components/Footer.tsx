import React from "react";
import { Link } from "react-router";
import {
  Scale,
  Mail,
  Phone,
  MapPin,
  Facebook,
  Twitter,
  Linkedin,
  Instagram,
} from "lucide-react";

export function Footer() {
  return (
    <footer className="bg-[var(--color-primary)] text-white">
      <div className="max-w-[1440px] mx-auto px-6 lg:px-24 py-12 lg:py-16">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 lg:gap-12">
          <div className="flex flex-col gap-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-[var(--color-accent)] rounded-lg flex items-center justify-center">
                <Scale className="w-6 h-6 text-[var(--color-primary)]" />
              </div>
              <span className="">LawAgent</span>
            </div>
            <p className="text-gray-300 leading-relaxed">
              Bitirme projesi kapsamında, Türk hukuku alanında uzmanlaşmış yenilikçi yapay zeka asistanı.
            </p>
          </div>
          <div className="flex flex-col gap-4">
            <h3 className="text-white">Hızlı Bağlantılar</h3>
            <div className="flex flex-col gap-3">
              <Link
                to="/"
                className="text-gray-300 hover:text-[var(--color-accent)] transition-colors"
              >
                Ana Sayfa
              </Link>
              <Link
                to="/about"
                className="text-gray-300 hover:text-[var(--color-accent)] transition-colors"
              >
                Proje Hakkında
              </Link>
              <Link
                to="/practice-areas"
                className="text-gray-300 hover:text-[var(--color-accent)] transition-colors"
              >
                Sistem Kapsamı
              </Link>
              <Link
                to="/blog"
                className="text-gray-300 hover:text-[var(--color-accent)] transition-colors"
              >
                Blog
              </Link>
              <Link
                to="/contact"
                className="text-gray-300 hover:text-[var(--color-accent)] transition-colors"
              >
                İletişim
              </Link>
            </div>
          </div>
          <div className="flex flex-col gap-4">
            <h3 className="text-white">İletişim</h3>
            <div className="flex flex-col gap-3">
              <div className="flex items-center gap-3 text-gray-300">
                <Mail className="w-5 h-5 flex-shrink-0" />
                <span>iletisim@lawagent.ai</span>
              </div>
              <div className="flex items-center gap-4 mt-2">
                <a
                  href="#"
                  className="text-gray-300 hover:text-[var(--color-accent)] transition-colors"
                >
                  <Facebook className="w-5 h-5" />
                </a>
                <a
                  href="#"
                  className="text-gray-300 hover:text-[var(--color-accent)] transition-colors"
                >
                  <Twitter className="w-5 h-5" />
                </a>
                <a
                  href="#"
                  className="text-gray-300 hover:text-[var(--color-accent)] transition-colors"
                >
                  <Linkedin className="w-5 h-5" />
                </a>
                <a
                  href="#"
                  className="text-gray-300 hover:text-[var(--color-accent)] transition-colors"
                >
                  <Instagram className="w-5 h-5" />
                </a>
              </div>
            </div>
          </div>
        </div>
        <div className="mt-12 pt-8 border-t border-white/10">
          <div className="flex flex-col md:flex-row justify-between items-center gap-4">
            <p className="text-gray-400 caption text-center md:text-left">
              © 2025 LawAgent. Tüm hakları saklıdır.
            </p>
            <div className="flex flex-wrap justify-center gap-4 md:gap-6">
              <a
                href="#"
                className="text-gray-400 hover:text-[var(--color-accent)] transition-colors caption"
              >
                KVKK Aydınlatma Metni
              </a>
              <a
                href="#"
                className="text-gray-400 hover:text-[var(--color-accent)] transition-colors caption"
              >
                Çerez Politikası
              </a>
              <a
                href="#"
                className="text-gray-400 hover:text-[var(--color-accent)] transition-colors caption"
              >
                Yasal Uyarı
              </a>
            </div>
          </div>
        </div>
      </div>
    </footer>
  );
}

