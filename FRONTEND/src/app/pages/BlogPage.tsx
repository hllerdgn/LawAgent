import React from "react";
import { Link } from "react-router";
import { Calendar, User, ArrowRight } from "lucide-react";
import { ImageWithFallback } from "../components/figma/ImageWithFallback";

export function BlogPage() {
  // Mock blog posts - would come from database in real app
  const blogPosts = [
    {
      title: "Ticaret Hukukunda Sık Karşılaşılan Sorunlar",
      slug: "ticaret-hukukunda-sik-karsilasilan-sorunlar",
      excerpt:
        "Ticari faaliyetlerde en çok karşılaşılan hukuki sorunlar ve çözüm yolları hakkında bilmeniz gerekenler.",
      date: "15 Ocak 2025",
      category: "Ticaret Hukuku",
      image:
        "https://images.unsplash.com/photo-1454165804606-c3d57bc86b40?w=800",
    },
    {
      title: "İş Sözleşmesi Feshi: Haklarınızı Bilin",
      slug: "is-sozlesmesi-feshi-haklarinizi-bilin",
      excerpt:
        "İş sözleşmesinin feshedilmesi durumunda işçi ve işverenin hakları nelerdir? Detaylı açıklamalar.",
      date: "10 Ocak 2025",
      category: "İş Hukuku",
      image:
        "https://images.unsplash.com/photo-1450101499163-c8848c66ca85?w=800",
    },
    {
      title: "Tüketici Haklarında Yeni Düzenlemeler",
      slug: "tuketici-haklarinda-yeni-duzenlemeler",
      excerpt:
        "2025 yılında yürürlüğe giren tüketici hakları düzenlemeleri ve etkileri.",
      date: "5 Ocak 2025",
      category: "Tüketici Hukuku",
      image: "https://images.unsplash.com/photo-1556742049-0cfed4f6a45d?w=800",
    },
  ];

  return (
    <div className="w-full">
      <section className="bg-gradient-to-br from-[var(--color-primary)] to-[var(--color-primary-dark)] text-white">
        <div className="max-w-[1440px] mx-auto px-6 lg:px-24 py-12 lg:py-20">
          <div className="text-center max-w-3xl mx-auto">
            <h1 className="text-white mb-6">Blog</h1>
            <p className="text-gray-200 text-lg">
              Hukuki konularda bilgilendirici makaleler ve güncel gelişmeler.
            </p>
          </div>
        </div>
      </section>
      <section className="bg-white">
        <div className="max-w-[1440px] mx-auto px-6 lg:px-24 py-12 lg:py-20">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            {blogPosts.map((post, index) => (
              <Link key={index} to={`/blog/${post.slug}`} className="group">
                <article className="bg-white border border-[var(--color-border)] rounded-xl overflow-hidden hover:shadow-xl transition-shadow">
                  <div className="relative h-48 overflow-hidden">
                    <ImageWithFallback
                      src={post.image}
                      alt={post.title}
                      className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                    />
                    <div className="absolute top-4 left-4">
                      <span className="px-3 py-1 bg-[var(--color-accent)] text-[var(--color-primary)] text-sm rounded-full">
                        {post.category}
                      </span>
                    </div>
                  </div>
                  <div className="p-6">
                    <div className="flex items-center gap-4 text-sm text-[var(--color-text-secondary)] mb-3">
                      <span className="flex items-center gap-1">
                        <Calendar className="w-4 h-4" />
                        {post.date}
                      </span>
                      <span className="flex items-center gap-1">
                        <User className="w-4 h-4" />
                        Av. LAWAGENT
                      </span>
                    </div>
                    <h3 className="text-[var(--color-primary)] mb-3 group-hover:text-[var(--color-accent)] transition-colors">
                      {post.title}
                    </h3>
                    <p className="text-[var(--color-text-secondary)] mb-4 line-clamp-2">
                      {post.excerpt}
                    </p>
                    <div className="flex items-center gap-2 text-[var(--color-accent)] group-hover:gap-3 transition-all">
                      <span>Devamını Oku</span>
                      <ArrowRight className="w-4 h-4" />
                    </div>
                  </div>
                </article>
              </Link>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}

