import React from "react";
import { Link } from "react-router";
import { PracticeAreaCard } from "../components/PracticeAreaCard";
import {
  Briefcase,
  Users,
  Home as HomeIcon,
  FileText,
  Building2,
  ShoppingCart,
} from "lucide-react";

export function PracticeAreasPage() {
  const practiceAreas = [
    {
      icon: Briefcase,
      title: "Türk Ticaret Kanunu (TTK)",
      description:
        "Türk Ticaret Kanunu kapsamında şirket kuruluşu, ticari işletme hukuku ve ticari uyuşmazlıklar.",
      slug: "Türk Ticaret Kanunu ",
    },
    {
      icon: Users,
      title: "İş Hukuku (TBK)",
      description:
        "Türk Borçlar Kanunu kapsamında iş sözleşmeleri, işçi-işveren uyuşmazlıkları ve iş güvenliği.",
      slug: "is-hukuku",
    },
    {
      icon: ShoppingCart,
      title: "Tüketicinin Korunması Hakkında Kanun (TKHK)",
      description:
        "Tüketicinin Korunması Hakkında Kanun kapsamında tüketici hakları ve ayıplı mal süreçleri.",
      slug: "tuketici-hukuku",
    },
  ];

  return (
    <div className="w-full">
      <section className="bg-gradient-to-br from-[var(--color-primary)] to-[var(--color-primary-dark)] text-white">
        <div className="max-w-[1440px] mx-auto px-6 lg:px-24 py-12 lg:py-20">
          <div className="text-center max-w-3xl mx-auto">
            <h1 className="text-white mb-6">Sistem Kapsamı</h1>
            <p className="text-gray-200 text-lg">
              LawAgent AI asistanı, aşağıda belirtilen temel kanunlar ve mevzuatlar çerçevesinde 
              sorularınızı yanıtlayacak şekilde eğitilmiştir.
            </p>
          </div>
        </div>
      </section>
      <section className="bg-white">
        <div className="max-w-[1440px] mx-auto px-6 lg:px-24 py-12 lg:py-20">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {practiceAreas.map((area, index) => (
              <Link key={index} to={`/practice-areas/${area.slug}`}>
                <PracticeAreaCard
                  icon={area.icon}
                  title={area.title}
                  description={area.description}
                />
              </Link>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}

