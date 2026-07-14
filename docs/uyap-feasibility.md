# UYAP Entegrasyonu Kapsamlı Fizibilite Raporu

Bu rapor, LawAgent AI RAG (Retrieval-Augmented Generation) sistemine UYAP (Ulusal Yargı Ağı Bilişim Sistemi) entegrasyonu eklenmesi fikrinin teknik, hukuki, güvenlik, maliyet, operasyonel ve kullanıcı deneyimi (UX) açılarından uygulanabilirliğini değerlendirmektedir.

---

## 1. Yönetici Özeti

*   **Projenin Amacı:** LawAgent AI kullanıcılarının kimliklerini güvenli bir şekilde doğrulaması, kendi UYAP dava dosyalarını sisteme aktarması ve yapay zekâ asistanı aracılığıyla bu kişisel veriler üzerinden özelleştirilmiş hukuki analiz/asistanlık hizmeti alması.
*   **Temel Bulgular:** 
    *   **Resmi API Yokluğu:** UYAP ve e-Devlet sistemlerinin genel kullanıma açık, dış geliştiricilerin doğrudan entegre olabileceği bir public API/SSO (Single Sign-On) altyapısı bulunmamaktadır.
    *   **Yüksek Hukuki Risk:** Dava dosyalarındaki özel nitelikli kişisel verilerin (sağlık, ceza mahkumiyeti vb.) işlenmesi, KVKK (Kişisel Verilerin Korunması Kanunu) ve TCK m.136 (Verileri hukuka aykırı ele geçirme) kapsamında çok sıkı sınırlamalara ve sorumluluklara tabidir.
    *   **Teknik Komplekslik:** Tarayıcı otomasyonu (RPA) veya e-imza gerektiren çözümler, UYAP portallarında yapılacak arayüz güncellemelerine karşı kırılgandır ve sürekli bakım gerektirir.
*   **Fizibilite Kararı:** Doğrudan ve otonom bir **resmi UYAP API entegrasyonu mevcut şartlarda MÜMKÜN DEĞİLDİR (Uygulanamaz).**
*   **Önerilen Strateji (MVP ve Yol Haritası):** 
    1.  **Aşama 1 (MVP):** Kullanıcının UYAP'tan indirdiği belgeleri (UDF, PDF) güvenli bir yerel arayüz üzerinden sisteme yüklemesi, belgelerin yerel parser'lar ile işlenip **Strict User Isolation (Sıkı Kullanıcı İzolasyonu)** altındaki Qdrant veritabanında saklanması.
    2.  **Aşama 2 (Orta Vade):** Lisanslı ve regüle edilmiş üçüncü taraf UYAP Gateway sağlayıcıları (örn. e-imza entegrasyonu sağlayan LegalTech altyapıları) ile iş ortaklığı yapılması.

---

## 2. Problem Tanımı

Mevcut hukuk asistanı uygulaması (LawAgent AI), yalnızca halka açık kanun metinleri, yönetmelikler ve Yargıtay emsal kararları üzerinden RAG (Retrieval-Augmented Generation) araması yapmaktadır.

### Mevcut Durumdaki Kısıtlar (Acı Noktaları):
1.  **Kişiselleştirme Eksikliği:** Kullanıcılar, asistan ile sohbet ederken kendi dava dosyalarındaki özel detayları (iddianameler, bilirkişi raporları, tensip zaptları vb.) bağlam olarak sunamamaktadır.
2.  **Manuel İşlem Yükü:** Kullanıcının dava belgelerindeki bilgileri kopyalayıp chat ekranına yapıştırması gerekmektedir. Bu durum hem kullanıcı deneyimini bozmakta hem de LLM bağlam sınırlarının aşılmasına yol açmaktadır.
3.  **Güvenlik Endişeleri:** Kullanıcıların hassas belgeleri kontrolsüz şekilde chat arayüzüne yapıştırması, verilerin açık LLM API'lerine kontrolsüz sızması riskini doğurmaktadır.

---

## 3. Mevcut Sistem Analizi

LawAgent AI projesinin güncel mimarisi şu şekildedir:
*   **Backend:** Python + FastAPI (İçtihat kazıma, embedding oluşturma, hybrid arama ve Groq LLM API koordinasyonu).
*   **Frontend:** React + TypeScript + TailwindCSS (Chat arayüzü ve döküman yönetimi).
*   **Vektör Veritabanı:** Qdrant (Lokal / Docker üzerinde çalıştırılan dense ve sparse vektör indeksleme).
*   **Metin Vektörleştirme:** `Mursit-Base-TR-Retrieval` (Türkçe hukuk terimlerine duyarlı açık kaynaklı embedding modeli).
*   **Veri Akışı:** Statik veri setleri (Borçlar Kanunu, Ticaret Kanunu vb.) önceden kazınmış ve Qdrant üzerinde indekslenmiştir. Çoklu kullanıcı mimarisi veya kullanıcı bazlı veri izolasyonu henüz aktif değildir.

---

## 4. UYAP Entegrasyon İncelemesi

UYAP altyapısının harici sistemlerle entegrasyon yetenekleri analiz edilmiştir:

| Entegrasyon Kanalı | Erişim Durumu | Kimlik Doğrulama Yöntemi | Veri Kapsamı |
| :--- | :--- | :--- | :--- |
| **UYAP Avukat Portal** | Açık API yok. Sadece web arayüzü. | e-İmza (Akıllı Kart), Mobil İmza, e-Devlet. | Avukatın vekaleti olan veya yetkilendirildiği tüm dava dosyaları, evraklar, safahat, duruşma günleri. |
| **UYAP Vatandaş Portal** | Açık API yok. Sadece web arayüzü. | e-Devlet şifresi, Mobil İmza, T.C. Kimlik Kartı. | Vatandaşın taraf olduğu dava dosyaları ve evrakları. |
| **UYAP Kurum Portal** | Protokole bağlı entegrasyon (API/Web Servis). | Kurumsal Sertifika ve IP Kısıtlaması. | Kurumu ilgilendiren hukuki süreçler ve sorgulamalar. |
| **Üçüncü Parti Gateway** | Özel LegalTech entegrasyonları. | E-imza yönlendirmesi veya RPA aracıları. | İlgili hukuk bürosunun yetkili olduğu veriler. |

### Kritik Soruların Cevapları:
*   **Harici bir uygulama UYAP kullanıcı doğrulaması yapabilir mi?**
    *   *Cevap:* Hayır. Harici uygulamaların doğrudan UYAP üzerinde kimlik doğrulaması yapabileceği bir SSO (Single Sign-On) veya OAuth altyapısı bulunmamaktadır. Kimlik doğrulama işlemi e-Devlet kapısı veya e-imza kütüphaneleri (Kamu SM vb.) üzerinden yapılmak zorundadır.
*   **UYAP üzerinden OAuth, SSO veya benzeri kimlik doğrulama yöntemi mevcut mu?**
    *   *Cevap:* Mevcut değildir. e-Devlet Kapısı Entegrasyon Protokolü imzalanmadan harici bir web uygulamasına "e-Devlet ile Giriş" butonu eklenemez.
*   **Veri erişimi için resmi izin gerekiyor mu?**
    *   *Cevap:* Evet. Resmi web servisleri (API'leri) kullanabilmek için Adalet Bakanlığı Bilgi İşlem Genel Müdürlüğü ile resmi protokol imzalanması şarttır.
*   **Hangi kullanıcı tipleri sisteme entegre olabilir?**
    *   *Cevap:* Avukatlar (Avukat Portal), Vatandaşlar (Vatandaş Portal) ve tüzel kişi temsilcileri (Kurum Portal).

---

## 5. Hukuki ve KVKK Analizi

UYAP verileri, doğası gereği son derece hassas ve koruma altında olan verilerdir.

### Veri Koruma ve KVKK:
1.  **Özel Nitelikli Kişisel Veriler (KVKK m.6):** Dava dosyalarında kişilerin ceza mahkumiyeti, güvenlik tedbirleri, sağlık verileri, sendika üyelikleri gibi özel nitelikli kişisel veriler yer alır. Bu verilerin işlenmesi için **kullanıcının açık rızası (explicit consent)** alınması zorunludur.
2.  **Veri Minimizasyonu:** Uygulama, RAG sistemini beslemek için sadece gerekli olan metinleri (örn. dilekçeler, beyanlar) çekmeli; ilgisiz kişisel verileri (kimlik fotokopileri, adres bilgileri vb.) elenmelidir.
3.  **Veri Saklama Süreleri:** Kullanıcı hesabı kapatıldığında veya kullanıcı verilerini silmek istediğinde, Qdrant ve PostgreSQL üzerindeki tüm dava indexleri ve vektörleri geri döndürülemeyecek şekilde silinmelidir (Veri İmha Politikası).

### Yetkilendirme ve Erişim Kontrolü:
*   **Avukat-Müvekkil Gizliliği:** Bir avukatın sisteme yüklediği veya UYAP'tan çektiği dosyalar, sadece o avukatın yetkilendirdiği alt kullanıcılara (stajyerler, ortak avukatlar) açık olmalıdır. Müvekkiller kendi dava dosyalarını görebilmeli ancak avukatın çalışma notlarına erişememelidir.
*   **Rol Bazlı Erişim Kontrolü (RBAC):** Sistemde `Yönetici`, `Avukat`, `Müvekkil` ve `Destek Personeli` rolleri tanımlanmalı, Qdrant sorgularında bu roller filtre olarak kullanılmalıdır.

### Hukuki Riskler ve Sorumluluklar:
*   **Hukuka Aykırı Veri İşleme (TCK m.135-136):** Resmi izin olmadan UYAP sistemlerinden botlar aracılığıyla otomatik veri çekilmesi, bilişim sistemine izinsiz girme suçu oluşturabilir.
*   **Veri İhlali Bildirimi:** Sistemde oluşabilecek bir sızıntı durumunda, KVKK kuruluna 72 saat içinde bildirim yapılması zorunludur. Ciddi idari para cezaları ile karşılaşılabilir.

---

## 6. Teknik Fizibilite Analizi

### Önerilen Kimlik Doğrulama ve Entegrasyon Akışı

```
Kullanıcı
   |
   ↓ (Giriş Talebi ve UDF/PDF Yükleme veya e-İmza Tetikleme)
UYAP Kimlik Doğrulama / Yerel Session Yönetimi (FastAPI OAuth2)
   |
   ↓ (Kullanıcı e-imza doğrulaması veya Güvenli JWT üretimi)
Token Doğrulama (JWT Signature Verification)
   |
   ↓ (Kullanıcı Rolü ve Workspace Eşleştirme)
User Identity Mapping (PostgreSQL/SQLAlchemy)
   |
   ↓ (Kullanıcıya özel şifreli anahtar ataması)
JWT Session & Tenant-Specific API Client
   |
   ↓ (Qdrant Payload Filter: tenant_id == user_tenant_id)
Hukuk Asistanı (RAG Pipeline)
```

---

## 7. Entegrasyon Alternatifleri ve Karşılaştırma

### Senaryo 1: Doğrudan UYAP API Entegrasyonu (Resmi Protokol)
*   **Açıklama:** Adalet Bakanlığı ile resmi entegrasyon kurularak sağlanan kurumsal API erişimi.
*   **Uygunluk:** Bireysel girişimler veya küçük-orta ölçekli projeler için bürokratik engeller nedeniyle imkansıza yakındır.

### Senaryo 2: Kullanıcının UYAP'tan Belge İndirip Sisteme Manuel Yüklemesi
*   **Açıklama:** Kullanıcı UYAP portalından `.udf` (UYAP Doküman Formatı) veya `.pdf` belgelerini indirir, sürükle-bırak yöntemiyle uygulamaya yükler. Uygulama yerel olarak bu dosyaları parse eder.
*   **Uygunluk:** Teknik olarak en kolay, yasal olarak en güvenli ve en hızlı uygulanabilir senaryodur.

### Senaryo 3: Yetkili Kurum/Gateway Entegrasyonu (İş Ortaklığı)
*   **Açıklama:** Hali hazırda UYAP e-imza entegrasyonu lisansı/altyapısı olan bir aracı kurum (LegalTech sağlayıcısı veya e-imza entegratörü) ile API ortaklığı kurulması.
*   **Uygunluk:** Maliyetli ancak tam otomatik bir kullanıcı deneyimi sunan orta-uzun vade çözümüdür.

### Senaryoların Karşılaştırma Matrisi:

| Kriter | Senaryo 1: Doğrudan API | Senaryo 2: Manuel Yükleme (Önerilen MVP) | Senaryo 3: Gateway Entegrasyonu |
| :--- | :--- | :--- | :--- |
| **Teknik Zorluk** | Çok Yüksek (Özel protokoller) | Düşük (UDF/PDF Parser) | Orta (3. Parti API Entegrasyonu) |
| **Maliyet** | Yüksek (Bürokratik/Altyapı) | Düşük (Sadece sunucu/LLM) | Orta-Yüksek (Komisyon/Lisans ücreti) |
| **Güvenlik** | Çok Yüksek | Yüksek (Lokal veri işleme) | Orta-Yüksek (Veri 3. partiden geçer) |
| **Hukuki Uygunluk**| Tam Uyumlu | Tam Uyumlu (Kullanıcı kendi yükler) | Kısmen Uyumlu (Sözleşmeye bağlı) |
| **Kullanıcı Deneyimi**| Mükemmel (Otomatik senkronize) | Orta (Manuel dosya indirme/yükleme) | İyi (E-imza ile otomatik çekim) |
| **Gerçekleşme Süresi**| 12+ Ay | 2 - 4 Hafta | 2 - 3 Ay |

---

## 8. Sistem Mimari Tasarımı

Önerilen Senaryo 2 (Manuel Güvenli Yükleme + UDF Parser) mimarisi aşağıdaki bileşenleri içerir:

```
[ Frontend: React App ] 
       | (Sürükle-Bırak UDF/PDF & JWT Auth)
       v
[ Backend API: FastAPI ] 
       | (Kullanıcı Oturumu ve Yetki Kontrolü)
       +---> [ Authentication Service ] (JWT, Postgres RBAC)
       |
       +---> [ Document Processing Pipeline ] 
       |            |--> UDF XML Parser
       |            |--> OCR Engine (Tesseract/EasyOCR - taranmış belgeler için)
       |            v
       |     [ Text Chunking & Embedding Generator ] (Mursit-Base-TR)
       |            |
       v            v
[ Qdrant Vector DB ] <--- (Kullanıcı ID filtresi ile kaydeder/arar)
       |
       +---> [ Retriever & Prompt Builder ]
                    |
                    v
[ LLM API (Groq/Llama-3) ] ---> [ Kullanıcıya Yanıt ]
```

### Servis Sorumlulukları ve Güvenlik Önlemleri:
1.  **FastAPI (Backend):** JWT doğrulamasını yapar. `user_id` bilgisini her isteğe ekler.
2.  **UDF Parser:** UDF dosyaları özünde sıkıştırılmış XML dosyalarıdır (`zip` formatında). Python `zipfile` ve `xml.etree.ElementTree` kütüphaneleri kullanılarak e-imza imzası ve XML metni ayrıştırılır.
3.  **Qdrant Multi-Tenancy:** Verilerin birbirine karışmaması için Qdrant'a yüklenen her vektörün payload alanına `tenant_id` (kullanıcı veya hukuk bürosu ID'si) eklenir. Arama yaparken `Filter(must=[FieldCondition(key="tenant_id", match=MatchValue(value=current_user.tenant_id))])` filtresi zorunlu kılınır.

---

## 9. Güvenlik Analizi

### Güvenlik Önlemleri ve Risk Tablosu:
*   **JWT Yönetimi:** Access token'lar kısa ömürlü (15-30 dk) tutulacak, refresh token'lar güvenli HTTP-Only çerezlerde saklanacaktır.
*   **Şifreleme:** Veritabanındaki hassas kullanıcı bilgileri ve diskte geçici olarak saklanan dökümanlar AES-256 ile şifrelenecektir. LLM API'sine gönderilen verilerde kişisel verilerin maskelenmesi için bir veri temizleme katmanı uygulanacaktır.

| Risk | Etki Derecesi | Alınacak Önlem |
| :--- | :--- | :--- |
| **Veri Sızıntısı (Data Leak)** | Yüksek | Qdrant üzerinde sıkı multi-tenancy filtresi ve veritabanı şifrelemesi. |
| **Yetkisiz Erişim (RBAC İhlali)**| Yüksek | Her endpoint'te FastAPI bağımlılık enjeksiyonu (`Depends`) ile rol kontrolü. |
| **Halüsinasyon (Yanlış AI Kararı)**| Orta | Yanıtlara "Yapay zekâ yanıtıdır, hukuki tavsiye niteliği taşımaz" uyarısı ve kaynak belgelere atıf (citations) eklenmesi. |
| **Bilişim Saldırıları (DDoS/Brute Force)**| Orta | API Gateway üzerinde rate-limiting (istek sınırlama) uygulanması. |

---

## 10. Yapay Zekâ ve RAG Entegrasyonu

UYAP dava dosyalarının RAG sistemine entegre edilme akışı aşağıda şematize edilmiştir:

```
[ UYAP Belgesi (UDF / PDF) ]
            |
            v
[ Document Parser ] (UDF XML extraction veya PDF text extraction)
            |
            +---> (Eğer taranmış resim ise) ---> [ OCR Engine (EasyOCR) ]
            v
[ Chunking & Clean-up ] (512-1024 karakterlik anlamlı paragraflara bölme)
            |
            v
[ Embedding Creation ] (Mursit-Base-TR modeli ile 768 boyutlu vektör)
            |
            v
[ Vector DB (Qdrant) ] (Payload: {"tenant_id": "usr_123", "text": "...", "source": "dilekce.udf"})
            |
            v (Kullanıcı Soru Sorar: "Bu davada zamanaşımı savunması yapılmış mı?")
[ Retriever ] (Qdrant'tan tenant_id filtresi ile en benzer 3 chunk getirilir)
            |
            v
[ Prompt Engineering ] ("Aşağıdaki dava metnine göre soruyu yanıtla...")
            |
            v
[ LLM (Groq / Llama-3) ] ---> [ Hukuki Yanıt ]
```

---

## 11. Maliyet Analizi

Projenin tahmini ilk kurulum ve aylık işletme maliyetleri (Senaryo 2 baz alınarak):

### 1. Geliştirme Maliyeti (Tek Seferlik):
*   **Backend Geliştirme (UDF parser, Multi-tenancy RAG, Auth):** 4.000 USD
*   **Frontend Geliştirme (Dosya yükleme, döküman yönetim paneli):** 3.000 USD
*   **Test ve Kalite Güvence (Sızma testleri, KVKK denetimi):** 2.000 USD
*   *Toplam Geliştirme:* **9.000 USD**

### 2. Altyapı Maliyeti (Aylık):
*   **Uygulama Sunucusu (FastAPI + PostgreSQL - AWS/DigitalOcean):** 80 USD / Ay
*   **Qdrant Cloud (Managed Vector DB veya Dedicated Server):** 50 USD / Ay
*   **LLM API Kullanımı (Groq veya OpenAI API - Kullanım bazlı):** ~100 USD / Ay
*   **OCR Sunucu Maliyeti (GPU destekli EC2 örneği - isteğe bağlı):** 120 USD / Ay
*   *Toplam Altyapı:* **~350 USD / Ay**

### 3. Operasyonel ve Hukuki Maliyetler (Yıllık):
*   **KVKK Uyum Danışmanlığı ve Hukuki Sözleşmeler:** 1.500 USD / Yıl
*   **Bakım ve Sistem Güncellemeleri:** 2.000 USD / Yıl

---

## 12. Risk ve SWOT Analizi

### SWOT Analizi:
*   **Güçlü Yönler (S):** Türkçe hukuk alanında uzmanlaşmış RAG altyapısı, açık kaynaklı yerel embedding modeli kullanımı, yüksek veri güvenliği standartları.
*   **Zayıf Yönler (W):** Resmi UYAP API'sinin olmaması nedeniyle kullanıcıların belgeleri manuel indirmek zorunda kalması (kullanıcı deneyiminde sürtünme).
*   **Fırsatlar (O):** Türkiye'deki hukuk bürolarının dijitalleşme ve yapay zeka entegrasyonu talebi, dava analiz süreçlerinin otomatikleştirilmesi ile zaman tasarrufu.
*   **Tehditler (T):** KVKK regülasyonlarının gelecekte daha da sertleşmesi, büyük dil modellerinin (LLM) veri gizliliği politikalarındaki değişiklikler.

### Proje Riskleri:
1.  **Teknik Risk:** Kullanıcının taradığı PDF belgelerinin çözünürlüğünün düşük olması durumunda OCR kalitesinin düşmesi ve RAG'in yanlış bilgi üretmesi (Garbage in, garbage out).
2.  **Hukuki Risk:** Kullanıcıların açık rıza metinlerini onaylamadan üçüncü şahıslara ait verileri sisteme yüklemesi. Sorumluluk tamamen kullanıcıya ait olsa da platformun itibar riski bulunmaktadır.

---

## 13. Sonuç ve Yol Haritası

### Uygulanabilirlik Kararı:
Mevcut yasal çerçevede ve teknik altyapıda, doğrudan UYAP resmi API entegrasyonu **mümkün değildir.** Ancak, **Senaryo 2 (Güvenli Manuel Belge Yükleme ve Yerel UDF/PDF Analizi)** %100 uygulanabilirdir. Bu yöntem projenin MVP (Minimum Viable Product) aşaması için en mantıklı, hızlı ve düşük riskli seçenektir.

### MVP Kapsamı (Aşama 1):
1.  **Kullanıcı Kayıt & Giriş:** FastAPI OAuth2 tabanlı, rol yönetimli (RBAC) üyelik sistemi.
2.  **Belge Yükleme Modülü:** Sürükle-bırak destekli, `.udf` ve `.pdf` formatlarını kabul eden güvenli yükleme ekranı.
3.  **UDF Parser:** UDF XML verisini açıp metne dönüştüren yerel Python modülü.
4.  **Multi-Tenancy RAG:** Qdrant veritabanında `tenant_id` filtresi ile sadece yükleyen kullanıcının erişebileceği vektör indeksleme yapısı.
5.  **Döküman Odaklı Sohbet:** Kullanıcının yüklediği belgelere dayanarak soru sorabileceği chat ekranı.

### Yol Haritası (Geliştirme Takvimi):

```
Hafta 1 - 2: Yetkilendirme (Auth) Altyapısı ve Rol Yönetimi (PostgreSQL/FastAPI)
Hafta 3 - 4: UDF ve PDF Ayrıştırıcıların (Parser) Yazılması, Metin Temizleme (Regex/OCR)
Hafta 5 - 6: Qdrant Multi-Tenancy Geçişi ve Embedding Arama Filtrelerinin Entegrasyonu
Hafta 7 - 8: Ön Arayüz Tasarımı (Dosya Yükleme Ekranı & Belge Kaynak Gösterimi)
Hafta 9 - 10: Güvenlik Sızma Testleri, KVKK Açık Rıza Metinlerinin Hazırlanması ve Canlıya Geçiş (MVP)
```
