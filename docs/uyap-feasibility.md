# UYAP Entegrasyonu Fizibilite Raporu

Bu belge, LawAgent AI projesi kapsamında UYAP (Ulusal Yargı Ağı Bilişim Sistemi) entegrasyonunun fizibilitesini, karşılaşılan teknik ve hukuki engelleri ve alternatif veri kaynakları ile RAG sisteminin genişletilmesi planlarını içermektedir.

---

## 1. UYAP Entegrasyonu Durum Analizi

### Resmi API / Erişim Noktası
* **Durum:** Adalet Bakanlığı tarafından üçüncü taraf geliştiricilerin, bireysel avukatların veya ticari hukuk otomasyon yazılımlarının doğrudan erişebileceği halka açık (public) bir **UYAP API hizmeti sunulmamaktadır.**
* **Resmi Protokoller:** UYAP sadece diğer kamu kurumları (MERNİS, SGK, GİB, TAKBİS vb.) ile resmi kurumlar arası protokoller çerçevesinde veri alışverişi yapmaktadır. Özel kuruluşlar veya hukuk bürolarının resmi olarak UYAP entegrasyonu yapabilmesi Adalet Bakanlığı ile imzalanacak özel protokollere tabidir ve bu süreçler oldukça kısıtlayıcıdır.

### e-Devlet Kapısı Entegrasyonu
* e-Devlet Kapısı üzerinden sunulan UYAP Avukat / Vatandaş / Kurum Portal hizmetlerine dışarıdan doğrudan bir API erişimi bulunmamaktadır.
* e-Devlet üzerinden entegrasyon yapmak, T.C. Cumhurbaşkanlığı Dijital Dönüşüm Ofisi ve Türksat A.Ş. ile resmi "Hizmet Entegrasyon Protokolü" imzalanmasını, sızma testlerini ve katı KVKK standartlarını (loglama, veri maskeleme, güvenlik) gerektirir. Bireysel geliştirici düzeyinde bu API'lere erişmek mümkün değildir.

### Üçüncü Parti Çözümler (Hukuk Otomasyonları)
Piyasadaki LegalTech yazılımları (Hukuk Asistanı, T-HOS, LegAI, Lawantra vb.) UYAP entegrasyonunu resmi bir API ile değil, şu yöntemlerle sağlamaktadır:
1. **Tarayıcı Eklentileri (Browser Extensions):** Avukatın tarayıcısına kurulan eklentiler ile UYAP portalına e-imza ile giriş yapıldığında, DOM üzerinden verileri okuyup kendi sistemlerine aktarma.
2. **Yapay Zeka Destekli Otomasyon/Ajanlar:** Yerel bilgisayarda çalışan, e-imzayı lokalde tutarak avukat yerine portalda gezinip işlem yapan masaüstü/web botları (RPA).

---

## 2. Karşılaşılan Engeller ve Riskler

1. **Teknik Engeller:**
   * **Kimlik Doğrulama:** UYAP girişleri e-imza (akıllı kart/dongle), mobil imza veya e-Devlet şifresi / T.C. Kimlik Kartı gerektirir. Bu doğrulama adımları iki aşamalı (2FA) olduğu veya fiziksel donanım (e-imza token'ı) gerektirdiği için tamamen otonom API tabanlı bir entegrasyon teknik olarak çok zordur ve kullanıcı etkileşimi şarttır.
   * **CAPTCHA ve Güvenlik Duvarları:** UYAP portalları bot ve kazıma (scraping) aktivitelerini engellemek amacıyla sıkı rate-limit ve CAPTCHA mekanizmaları kullanmaktadır.
   * **Arayüz Değişiklikleri:** Resmi API olmadığı ve veri kazıma/otomasyon kullanıldığı durumlarda, UYAP portallarında yapılan en ufak bir arayüz güncellemesi veri çeken araçların kırılmasına yol açar.

2. **Hukuki Riskler:**
   * **KVKK (Kişisel Verilerin Korunması Kanunu - 6698 Sayılı Kanun):** Dava dosyaları, safahat bilgileri, tarafların isimleri ve kişisel detayları hassas veri sınıfındadır. UYAP verilerinin yetkisiz veya resmi olmayan yöntemlerle otomatik olarak çekilmesi ve işlenmesi KVKK ihlali ve **TCK m.136** (Kişisel verileri hukuka aykırı olarak ele geçirme veya yayma) kapsamında suç teşkil edebilir.
   * **Bilişim Sistemlerine İzinsiz Erişim:** Resmi izin veya protokol olmadan UYAP sistemlerine otomatik istekler atmak, sistemlerin işleyişini bozmaya teşvik veya izinsiz erişim olarak yorumlanabilir (TCK m.243-244).

---

## 3. Alternatif Plan: Halka Açık Veri Tabanlarının Genişletilmesi

UYAP'ın doğrudan entegre edilemediği durumda, LawAgent RAG sisteminin kapsamını artırmak amacıyla halihazırda yürütülen halka açık içtihat kazıma (scraping) altyapısının genişletilmesi en mantıklı ve yasal alternatiftir.

### Genişletme Stratejisi:
1. **Yargıtay ve Danıştay Karar Veritabanları (Scrapy Altyapısı):**
   * Halihazırda mevzuat ve Yargıtay sitelerinden veri kazıyan Scrapy robotlarının kapsamı genişletilecektir.
   * **Danıştay Karar Arama** portalı için yeni bir kazıma modülü (`scraper_danistay`) eklenecektir.
   * Bölge Adliye Mahkemeleri (BAM) ve Bölge İdare Mahkemeleri (BİM) gibi istinaf mahkemelerinin halka açık emsal kararları sisteme dahil edilecektir.

2. **Veri Anonimleştirme Hattı (KVKK Uyum):**
   * Kazınan kararlar vektör veritabanına (Qdrant) eklenmeden önce, kişisel verilerin (ad-soyad, T.C. kimlik numaraları, özel adresler, telefonlar vb.) otomatik taranıp maskeleneceği (anonimleştirme) bir veri ön işleme (preprocessing) hattı tasarlanacaktır.

3. **Resmi Gazete Tarama Sistemi:**
   * Resmi Gazete (`resmigazete.gov.tr`) günlük olarak taranarak yeni yayımlanan kanun, yönetmelik ve genelgeler otomatik olarak RAG korpusuna dahil edilecektir.

4. **Ticari/Akademik API Entegrasyonları:**
   * Bütçe ve iş birliği imkanları doğrultusunda, verileri yasal olarak derleyen ve API sunan üçüncü parti içtihat platformları (Lexpera API vb.) ile resmi API entegrasyonu seçenekleri değerlendirilecektir.
