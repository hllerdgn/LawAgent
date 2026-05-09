import React from "react";
import { Link, useParams } from "react-router";
import { Button } from "../components/Button";
import { ArrowLeft, CheckCircle2 } from "lucide-react";

export function PracticeAreaDetailPage() {
  const { slug } = useParams();

  // Mock data - in real app this would come from database
  const practiceAreaData: Record<string, any> = {
    "ticaret-hukuku": {
      title: "Ticaret Hukuku",
      description:
        "Ticari faaliyetlerinizi güvence altına alıyor, şirketinizin hukuki ihtiyaçlarını profesyonelce karşılıyorum.",
      services: [
        "Şirket kuruluşu ve tür değişikliği",
        "Şirket birleşme ve devralma işlemleri",
        "Ticari sözleşmeler hazırlama ve inceleme",
        "Ticari uyuşmazlıkların çözümü",
        "Rekabet hukuku danışmanlığı",
        "Ticari dava takibi ve temsil",
      ],
    },
    "is-hukuku": {
      title: "İş Hukuku",
      description:
        "İşçi ve işveren haklarını koruyarak, iş ilişkilerinde hukuki güvence sağlıyorum.",
      services: [
        "İş sözleşmeleri hazırlama ve inceleme",
        "İşe son verme ve kıdem tazminatı",
        "Mobbing ve ayrımcılık davaları",
        "İş kazası ve meslek hastalığı",
        "Toplu iş sözleşmeleri danışmanlığı",
        "İşçi alacakları takibi",
      ],
    },
    "tuketici-hukuku": {
      title: "Tüketici Hukuku",
      description:
        "Tüketici haklarınızı koruyarak, satıcı ve üretici karşısında güçlü temsil sağlıyorum.",
      services: [
        "Ayıplı mal ve hizmet davaları",
        "Tüketici mahkemesi davaları",
        "Tüketici hakem heyeti başvuruları",
        "Mesafeli satış sözleşmeleri",
        "Kredi ve finans ürünleri uyuşmazlıkları",
        "TKHK kapsamında hak aramaları",
      ],
    },
  };

  const data = practiceAreaData[slug || ""] || {
    title: "Çalışma Alanı",
    description: "Bu alanda detaylı hizmet sunuyorum.",
    services: [],
  };

  return (
    <div className="w-full">
      <section className="bg-gradient-to-br from-[var(--color-primary)] to-[var(--color-primary-dark)] text-white">
        <div className="max-w-[1440px] mx-auto px-6 lg:px-24 py-12 lg:py-20">
          <div className="max-w-3xl mx-auto">
            <Link
              to="/practice-areas"
              className="inline-flex items-center gap-2 text-gray-200 hover:text-white mb-6"
            >
              <ArrowLeft className="w-5 h-5" />
              Çalışma Alanlarına Dön
            </Link>
            <h1 className="text-white mb-6">{data.title}</h1>
            <p className="text-gray-200 text-lg">{data.description}</p>
          </div>
        </div>
      </section>
      <section className="bg-white">
        <div className="max-w-[1440px] mx-auto px-6 lg:px-24 py-12 lg:py-20">
          <div className="max-w-4xl mx-auto">
            <h2 className="text-[var(--color-primary)] mb-8">
              Sunduğum Hizmetler
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {data.services.map((service: string, index: number) => (
                <div
                  key={index}
                  className="flex items-start gap-3 p-4 bg-[var(--color-background)] rounded-lg"
                >
                  <CheckCircle2 className="w-6 h-6 text-[var(--color-accent)] flex-shrink-0 mt-1" />
                  <p className="text-[var(--color-text-primary)]">{service}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>
      <section className="bg-[var(--color-background)]">
        <div className="max-w-[1440px] mx-auto px-6 lg:px-24 py-12 lg:py-16">
          <div className="text-center flex flex-col items-center gap-6">
            <h2 className="text-[var(--color-primary)] max-w-3xl">
              {data.title} konusunda size nasıl yardımcı olabilirim?
            </h2>
            <p className="text-[var(--color-text-secondary)] max-w-2xl text-lg">
              Ücretsiz ön görüşme için benimle iletişime geçin.
            </p>
            <Link to="/contact">
              <Button variant="primary">Randevu Al</Button>
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}

